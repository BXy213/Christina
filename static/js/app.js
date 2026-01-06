/**
 * Christina AI - 前端应用
 */

// ========================================
// 全局状态
// ========================================
const state = {
    isLoading: false,
    messages: []
};

// ========================================
// DOM 元素
// ========================================
const elements = {
    chatContainer: document.getElementById('chatContainer'),
    welcomeScreen: document.getElementById('welcomeScreen'),
    messages: document.getElementById('messages'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    newChatBtn: document.getElementById('newChatBtn'),
    charCount: document.getElementById('charCount'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    toastContainer: document.getElementById('toastContainer'),
    statusIndicator: document.getElementById('statusIndicator')
};

// ========================================
// 工具函数
// ========================================

/**
 * 显示 Toast 通知
 */
function showToast(message, type = 'info') {
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span>${message}</span>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    // 自动移除
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * 设置加载状态
 */
function setLoading(loading) {
    state.isLoading = loading;
    elements.loadingOverlay.classList.toggle('visible', loading);
    elements.sendBtn.disabled = loading || !elements.messageInput.value.trim();
    elements.messageInput.disabled = loading;
}

/**
 * 更新状态指示器
 */
function updateStatus(online) {
    elements.statusIndicator.classList.toggle('offline', !online);
    elements.statusIndicator.querySelector('.status-text').textContent = online ? '在线' : '离线';
}

/**
 * 格式化时间
 */
function formatTime(date) {
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * 简单的 Markdown 渲染
 */
function renderMarkdown(text) {
    // 转义 HTML
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // 代码块
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });
    
    // 行内代码
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // 粗体
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // 斜体
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // 标题
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // 链接
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    
    // 无序列表
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // 有序列表
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    
    // 引用块
    html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
    
    // 换行
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    
    // 包裹段落
    if (!html.startsWith('<')) {
        html = `<p>${html}</p>`;
    }
    
    return html;
}

/**
 * 自动调整文本框高度
 */
function autoResize(textarea) {
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 200);
    textarea.style.height = newHeight + 'px';
}

// ========================================
// 消息处理
// ========================================

/**
 * 添加消息到界面
 */
function addMessage(role, content) {
    // 隐藏欢迎屏幕
    elements.welcomeScreen.classList.add('hidden');
    
    const message = {
        role,
        content,
        time: new Date()
    };
    state.messages.push(message);
    
    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;
    
    const avatar = role === 'user' ? '👤' : '✦';
    const renderedContent = role === 'assistant' ? renderMarkdown(content) : content;
    
    messageEl.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-bubble">${renderedContent}</div>
            <div class="message-time">${formatTime(message.time)}</div>
        </div>
    `;
    
    elements.messages.appendChild(messageEl);
    
    // 滚动到底部
    requestAnimationFrame(() => {
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    });
}

/**
 * 发送消息
 */
async function sendMessage() {
    const message = elements.messageInput.value.trim();
    
    if (!message || state.isLoading) return;
    
    // 清空输入框
    elements.messageInput.value = '';
    elements.charCount.textContent = '0';
    autoResize(elements.messageInput);
    elements.sendBtn.disabled = true;
    
    // 添加用户消息
    addMessage('user', message);
    
    // 发送请求
    setLoading(true);
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message }),
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessage('assistant', data.response);
        } else {
            showToast(data.error || '请求失败', 'error');
        }
    } catch (error) {
        console.error('发送消息失败:', error);
        showToast('网络错误，请检查连接', 'error');
        updateStatus(false);
    } finally {
        setLoading(false);
    }
}

/**
 * 重置对话
 */
async function resetChat() {
    try {
        const response = await fetch('/api/reset', {
            method: 'POST',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 清空消息
            state.messages = [];
            elements.messages.innerHTML = '';
            
            // 显示欢迎屏幕
            elements.welcomeScreen.classList.remove('hidden');
            
            showToast('对话已重置', 'success');
        } else {
            showToast(data.error || '重置失败', 'error');
        }
    } catch (error) {
        console.error('重置失败:', error);
        showToast('网络错误，请检查连接', 'error');
    }
}

/**
 * 健康检查
 */
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        updateStatus(data.status === 'ok');
    } catch (error) {
        updateStatus(false);
    }
}

// ========================================
// 事件绑定
// ========================================

// 发送按钮点击
elements.sendBtn.addEventListener('click', sendMessage);

// 新对话按钮
elements.newChatBtn.addEventListener('click', resetChat);

// 输入框事件
elements.messageInput.addEventListener('input', () => {
    const value = elements.messageInput.value;
    elements.charCount.textContent = value.length;
    elements.sendBtn.disabled = !value.trim() || state.isLoading;
    autoResize(elements.messageInput);
});

// 回车发送（Shift+Enter 换行）
elements.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// 建议卡片点击
document.querySelectorAll('.suggestion-card').forEach(card => {
    card.addEventListener('click', () => {
        const message = card.dataset.message;
        elements.messageInput.value = message;
        elements.charCount.textContent = message.length;
        elements.sendBtn.disabled = false;
        autoResize(elements.messageInput);
        elements.messageInput.focus();
    });
});

// ========================================
// 初始化
// ========================================

// 页面加载完成
document.addEventListener('DOMContentLoaded', () => {
    // 健康检查
    checkHealth();
    
    // 定期健康检查
    setInterval(checkHealth, 30000);
    
    // 聚焦输入框
    elements.messageInput.focus();
});

// 页面可见性变化时检查状态
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        checkHealth();
    }
});

