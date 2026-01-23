// 简单的 API 调用函数
async function callAPI(method, endpoint, data) {
    try {
        const response = await axios({
            method: method,
            url: 'http://localhost:8000' + endpoint,
            data: data,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        console.error('API调用失败:', error);
        
        if (error.response) {
            return {
                success: false,
                error: error.response.data?.detail || '请求失败'
            };
        }
        return {
            success: false,
            error: error.message || '网络错误'
        };
    }
}

// 用户认证函数
async function loginUser(username, password) {
    return await callAPI('POST', '/api/login', {
        username: username,
        password: password
    });
}

// 获取当前用户
function getCurrentUser() {
    try {
        const user = localStorage.getItem('currentUser');
        return user ? JSON.parse(user) : null;
    } catch (e) {
        return null;
    }
}

// 保存用户
function setCurrentUser(userData) {
    localStorage.setItem('currentUser', JSON.stringify(userData));
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('登录页面加载完成');
    
    // 检查是否已登录
    const currentUser = getCurrentUser();
    if (currentUser) {
        console.log('用户已登录，跳转到仪表板');
        window.location.href = 'dashboard.html';
        return;
    }
    
    const loginForm = document.getElementById('loginForm');
    const registerLink = document.getElementById('registerLink');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const usernameError = document.getElementById('usernameError');
    const passwordError = document.getElementById('passwordError');

    // 切换到注册页面
    if (registerLink) {
        registerLink.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = 'register.html';
        });
    }

    // 登录表单验证和提交
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // 重置错误信息
            if (usernameError) usernameError.style.display = 'none';
            if (passwordError) passwordError.style.display = 'none';
            
            let isValid = true;
            
            // 验证用户名
            const username = usernameInput.value.trim();
            if (!username) {
                if (usernameError) {
                    usernameError.textContent = '请输入用户名';
                    usernameError.style.display = 'block';
                }
                isValid = false;
            }
            
            // 验证密码
            const password = passwordInput.value;
            if (!password) {
                if (passwordError) {
                    passwordError.textContent = '请输入密码';
                    passwordError.style.display = 'block';
                }
                isValid = false;
            }
            
            if (isValid) {
                // 显示加载状态
                const submitBtn = loginForm.querySelector('button[type="submit"]');
                const originalText = submitBtn.textContent;
                submitBtn.textContent = '登录中...';
                submitBtn.disabled = true;
                
                try {
                    // 调用后端登录API
                    const result = await loginUser(username, password);
                    
                    console.log('登录结果:', result);
                    
                    if (result.success) {
                        // 登录成功
                        const userData = {
                            username: username,
                            loginTime: new Date().toISOString()
                        };
                        
                        // 保存用户信息
                        setCurrentUser(userData);
                        
                        // 显示成功消息
                        showMessage('登录成功！正在跳转...', 'success');
                        
                        // 延迟跳转到仪表板
                        setTimeout(function() {
                            window.location.href = 'dashboard.html';
                        }, 1000);
                    } else {
                        // 登录失败
                        showMessage(result.error || '登录失败', 'error');
                        
                        // 根据错误类型显示具体错误信息
                        if (result.error && result.error.includes('密码')) {
                            if (passwordError) {
                                passwordError.textContent = result.error;
                                passwordError.style.display = 'block';
                            }
                        } else if (result.error && result.error.includes('用户')) {
                            if (usernameError) {
                                usernameError.textContent = result.error;
                                usernameError.style.display = 'block';
                            }
                        }
                        
                        // 恢复按钮状态
                        submitBtn.textContent = originalText;
                        submitBtn.disabled = false;
                    }
                } catch (error) {
                    console.error('登录过程中发生错误:', error);
                    showMessage('登录请求失败，请检查网络连接', 'error');
                    
                    // 恢复按钮状态
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                }
            }
        });
    }

    // 显示消息函数
    function showMessage(message, type) {
        // 移除现有的消息
        const existingMsg = document.querySelector('.message-box');
        if (existingMsg) existingMsg.remove();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-box';
        messageDiv.textContent = message;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#f44336' : '#4CAF50'};
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(messageDiv);
        
        // 3秒后自动消失
        setTimeout(function() {
            messageDiv.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(function() {
                if (messageDiv.parentNode) {
                    messageDiv.remove();
                }
            }, 300);
        }, 3000);
    }
    
    // 添加动画样式
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
    
    // 输入框回车事件
    if (passwordInput) {
        passwordInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                if (loginForm) {
                    loginForm.dispatchEvent(new Event('submit'));
                }
            }
        });
    }
});