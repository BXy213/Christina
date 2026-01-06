"""
Flask Web 后端
提供 AI 聊天助手的 Web API 和前端页面
"""
import uuid
import time
from functools import wraps
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from config import config
from chatbot import AIAssistant
from logger import logger


# 创建 Flask 应用
app = Flask(__name__)
app.secret_key = config.SERVER_SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# 配置 CORS
CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)

# 存储用户会话的 AI 助手实例
# 格式: {session_id: {'assistant': AIAssistant, 'last_active': timestamp}}
user_sessions = {}

# 速率限制存储
# 格式: {ip: [timestamp1, timestamp2, ...]}
rate_limit_store = {}


def cleanup_sessions():
    """清理过期的会话"""
    current_time = time.time()
    expired = [
        sid for sid, data in user_sessions.items()
        if current_time - data['last_active'] > config.SESSION_TIMEOUT
    ]
    for sid in expired:
        del user_sessions[sid]
        logger.log(f"[INFO] Session expired and cleaned: {sid[:8]}...")


def rate_limit(f):
    """速率限制装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not config.RATE_LIMIT_ENABLED:
            return f(*args, **kwargs)
        
        client_ip = request.remote_addr
        current_time = time.time()
        window = 60  # 1分钟窗口
        
        # 清理过期记录
        if client_ip in rate_limit_store:
            rate_limit_store[client_ip] = [
                t for t in rate_limit_store[client_ip]
                if current_time - t < window
            ]
        else:
            rate_limit_store[client_ip] = []
        
        # 检查是否超过限制
        if len(rate_limit_store[client_ip]) >= config.RATE_LIMIT_RPM:
            return jsonify({
                'success': False,
                'error': '请求过于频繁，请稍后再试',
                'retry_after': window
            }), 429
        
        # 记录本次请求
        rate_limit_store[client_ip].append(current_time)
        
        return f(*args, **kwargs)
    return decorated_function


def get_or_create_assistant():
    """获取或创建用户的 AI 助手实例"""
    # 定期清理过期会话
    cleanup_sessions()
    
    # 获取或创建会话 ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    
    # 获取或创建助手实例
    if session_id not in user_sessions:
        try:
            assistant = AIAssistant()
            user_sessions[session_id] = {
                'assistant': assistant,
                'last_active': time.time()
            }
            logger.log(f"[OK] New session created: {session_id[:8]}...")
        except Exception as e:
            logger.error(f"[ERROR] Failed to create assistant: {e}")
            raise
    else:
        # 更新最后活跃时间
        user_sessions[session_id]['last_active'] = time.time()
    
    return user_sessions[session_id]['assistant']


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
@rate_limit
def chat():
    """
    聊天 API
    
    请求体:
        {
            "message": "用户消息"
        }
    
    响应:
        {
            "success": true,
            "response": "AI 回复"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': '请提供消息内容'
            }), 400
        
        user_message = data['message'].strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': '消息不能为空'
            }), 400
        
        # 获取 AI 助手并处理消息
        assistant = get_or_create_assistant()
        response = assistant.chat(user_message)
        
        return jsonify({
            'success': True,
            'response': response
        })
    
    except Exception as e:
        logger.error(f"[ERROR] Chat error: {e}")
        return jsonify({
            'success': False,
            'error': f'处理请求时出错: {str(e)}'
        }), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    """
    重置对话历史
    
    响应:
        {
            "success": true,
            "message": "对话已重置"
        }
    """
    try:
        if 'session_id' in session:
            session_id = session['session_id']
            if session_id in user_sessions:
                user_sessions[session_id]['assistant'].reset_memory()
                logger.log(f"[OK] Session reset: {session_id[:8]}...")
        
        return jsonify({
            'success': True,
            'message': '对话已重置'
        })
    
    except Exception as e:
        logger.error(f"[ERROR] Reset error: {e}")
        return jsonify({
            'success': False,
            'error': f'重置失败: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """
    健康检查接口
    
    响应:
        {
            "status": "ok",
            "sessions": 活跃会话数
        }
    """
    cleanup_sessions()
    return jsonify({
        'status': 'ok',
        'sessions': len(user_sessions),
        'version': '1.0.0'
    })


@app.route('/api/status', methods=['GET'])
def status():
    """
    系统状态接口
    
    响应:
        {
            "success": true,
            "config": 配置信息
        }
    """
    return jsonify({
        'success': True,
        'config': {
            'model': config.MODEL_NAME,
            'search_engine': config.search_engine,
            'rate_limit_enabled': config.RATE_LIMIT_ENABLED,
            'rate_limit_rpm': config.RATE_LIMIT_RPM
        }
    })


@app.errorhandler(404)
def not_found(e):
    """404 错误处理"""
    return jsonify({
        'success': False,
        'error': '页面未找到'
    }), 404


@app.errorhandler(500)
def internal_error(e):
    """500 错误处理"""
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500


def run_server():
    """启动服务器"""
    logger.log(f"[OK] Starting server on {config.SERVER_HOST}:{config.SERVER_PORT}")
    
    ssl_context = None
    if config.SSL_ENABLED and config.SSL_CERT_PATH and config.SSL_KEY_PATH:
        ssl_context = (config.SSL_CERT_PATH, config.SSL_KEY_PATH)
        logger.log("[OK] SSL enabled")
    
    app.run(
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        debug=config.SERVER_DEBUG,
        ssl_context=ssl_context
    )


if __name__ == '__main__':
    run_server()

