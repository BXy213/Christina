"""
Flask Web 后端
提供 AI 聊天助手的 Web API 和前端页面
支持 JSON 文件持久化存储会话
"""
import uuid
import time
import json
from pathlib import Path
from datetime import datetime
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

# 存储用户会话的 AI 助手实例（内存缓存）
# 格式: {session_id: {'assistant': AIAssistant, 'last_active': timestamp, 'created_at': timestamp}}
user_sessions = {}

# 速率限制存储
# 格式: {ip: [timestamp1, timestamp2, ...]}
rate_limit_store = {}

# 会话文件存储目录
SESSIONS_DIR = Path(__file__).parent / config.SESSIONS_DIR


def ensure_sessions_dir():
    """确保会话存储目录存在"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def get_session_file_path(session_id: str) -> Path:
    """获取会话文件路径"""
    return SESSIONS_DIR / f"{session_id}.json"


def save_session_to_file(session_id: str, assistant: AIAssistant, created_at: float):
    """
    保存会话到 JSON 文件
    
    Args:
        session_id: 会话 ID
        assistant: AI 助手实例
        created_at: 创建时间戳
    """
    ensure_sessions_dir()
    
    session_data = {
        "session_id": session_id,
        "created_at": datetime.fromtimestamp(created_at).isoformat(),
        "last_active": datetime.now().isoformat(),
        "chat_history": assistant.export_history()
    }
    
    file_path = get_session_file_path(session_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save session {session_id[:8]}...: {e}")


def load_session_from_file(session_id: str) -> dict | None:
    """
    从 JSON 文件加载会话
    
    Args:
        session_id: 会话 ID
        
    Returns:
        会话数据字典，如果不存在则返回 None
    """
    file_path = get_session_file_path(session_id)
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load session {session_id[:8]}...: {e}")
        return None


def delete_session_file(session_id: str):
    """删除会话文件"""
    file_path = get_session_file_path(session_id)
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.error(f"Failed to delete session file {session_id[:8]}...: {e}")


def cleanup_sessions():
    """清理过期的会话（内存和文件）"""
    current_time = time.time()
    cleaned_count = 0
    
    # 清理内存中的过期会话
    expired = [
        sid for sid, data in user_sessions.items()
        if current_time - data['last_active'] > config.SESSION_TIMEOUT
    ]
    for sid in expired:
        del user_sessions[sid]
        cleaned_count += 1
    
    # 清理过期的会话文件
    ensure_sessions_dir()
    for file_path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            last_active = datetime.fromisoformat(data.get('last_active', ''))
            if (datetime.now() - last_active).total_seconds() > config.SESSION_TIMEOUT:
                file_path.unlink()
                cleaned_count += 1
        except Exception:
            # 损坏的文件也删除
            try:
                file_path.unlink()
                cleaned_count += 1
            except:
                pass
    
    if cleaned_count > 0:
        logger.log(f"Cleanup: removed {cleaned_count} expired sessions")


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
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
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
    current_time = time.time()
    
    # 检查内存中是否有该会话
    if session_id in user_sessions:
        user_sessions[session_id]['last_active'] = current_time
        return user_sessions[session_id]['assistant']
    
    # 尝试从文件恢复会话
    session_data = load_session_from_file(session_id)
    
    if session_data:
        try:
            assistant = AIAssistant()
            assistant.import_history(session_data.get('chat_history', []))
            
            created_at = datetime.fromisoformat(session_data['created_at']).timestamp()
            user_sessions[session_id] = {
                'assistant': assistant,
                'last_active': current_time,
                'created_at': created_at
            }
            
            msg_count = assistant.get_history_count()
            logger.log(f"Session restored: {session_id[:8]}... ({msg_count} messages)")
            return assistant
        except Exception as e:
            logger.error(f"Failed to restore session {session_id[:8]}...: {e}")
    
    # 创建新会话
    try:
        assistant = AIAssistant()
        user_sessions[session_id] = {
            'assistant': assistant,
            'last_active': current_time,
            'created_at': current_time
        }
        logger.log(f"New session created: {session_id[:8]}...")
        return assistant
    except Exception as e:
        logger.error(f"Failed to create assistant: {e}")
        raise


def save_current_session():
    """保存当前会话到文件"""
    if 'session_id' not in session:
        return
    
    session_id = session['session_id']
    if session_id in user_sessions:
        data = user_sessions[session_id]
        save_session_to_file(session_id, data['assistant'], data['created_at'])


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
        
        # 记录用户消息（截取前50字符）
        msg_preview = user_message[:50] + "..." if len(user_message) > 50 else user_message
        logger.log(f'User message: "{msg_preview}"')
        
        # 获取 AI 助手并处理消息
        assistant = get_or_create_assistant()
        
        start_time = time.time()
        response = assistant.chat(user_message)
        elapsed = time.time() - start_time
        
        # 保存会话到文件
        save_current_session()
        
        # 记录响应信息
        logger.log(f"AI response completed ({elapsed:.1f}s)")
        
        return jsonify({
            'success': True,
            'response': response
        })
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
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
            
            # 重置内存中的会话
            if session_id in user_sessions:
                user_sessions[session_id]['assistant'].reset_memory()
            
            # 删除会话文件
            delete_session_file(session_id)
            
            logger.log(f"Session reset: {session_id[:8]}...")
        
        return jsonify({
            'success': True,
            'message': '对话已重置'
        })
    
    except Exception as e:
        logger.error(f"Reset error: {e}")
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
    # 确保会话目录存在
    ensure_sessions_dir()
    
    logger.log(f"Starting server on {config.SERVER_HOST}:{config.SERVER_PORT}")
    logger.log(f"Sessions directory: {SESSIONS_DIR}")
    
    ssl_context = None
    if config.SSL_ENABLED and config.SSL_CERT_PATH and config.SSL_KEY_PATH:
        ssl_context = (config.SSL_CERT_PATH, config.SSL_KEY_PATH)
        logger.log("SSL enabled")
    
    app.run(
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        debug=config.SERVER_DEBUG,
        ssl_context=ssl_context
    )


if __name__ == '__main__':
    run_server()
