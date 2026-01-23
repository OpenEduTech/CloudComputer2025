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

async function registerUser(username, password) {
    return await callAPI('POST', '/api/register', {
        username: username,
        password: password
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    const backLink = document.getElementById('backLink');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    
    const errorElements = {
        username: document.getElementById('usernameError'),
        email: document.getElementById('emailError'),
        password: document.getElementById('passwordError'),
        confirmPassword: document.getElementById('confirmPasswordError')
    };

    // 返回登录页面
    if (backLink) {
        backLink.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = 'login.html';
        });
    }

    // 注册表单验证和提交
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // 重置错误信息
            Object.values(errorElements).forEach(function(error) {
                if (error) error.style.display = 'none';
            });
            
            let isValid = true;
            
            // 验证用户名
            const username = usernameInput.value.trim();
            if (!username) {
                if (errorElements.username) {
                    errorElements.username.textContent = '请输入用户名';
                    errorElements.username.style.display = 'block';
                }
                isValid = false;
            } else if (username.length < 3) {
                if (errorElements.username) {
                    errorElements.username.textContent = '用户名至少3个字符';
                    errorElements.username.style.display = 'block';
                }
                isValid = false;
            }
            
            // 验证密码
            const password = passwordInput.value;
            if (!password) {
                if (errorElements.password) {
                    errorElements.password.textContent = '请输入密码';
                    errorElements.password.style.display = 'block';
                }
                isValid = false;
            } else if (password.length < 6) {
                if (errorElements.password) {
                    errorElements.password.textContent = '密码至少6个字符';
                    errorElements.password.style.display = 'block';
                }
                isValid = false;
            }
            
            // 验证确认密码
            const confirmPassword = confirmPasswordInput.value;
            if (!confirmPassword) {
                if (errorElements.confirmPassword) {
                    errorElements.confirmPassword.textContent = '请确认密码';
                    errorElements.confirmPassword.style.display = 'block';
                }
                isValid = false;
            } else if (password !== confirmPassword) {
                if (errorElements.confirmPassword) {
                    errorElements.confirmPassword.textContent = '两次输入的密码不一致';
                    errorElements.confirmPassword.style.display = 'block';
                }
                isValid = false;
            }
            
            if (isValid) {
                // 显示加载状态
                const submitBtn = registerForm.querySelector('button[type="submit"]');
                const originalText = submitBtn.textContent;
                submitBtn.textContent = '注册中...';
                submitBtn.disabled = true;
                
                try {
                    // 调用后端注册API
                    const result = await registerUser(username, password);
                    
                    if (result.success) {
                        // 注册成功
                        showMessage('注册成功！即将跳转到登录页面...', 'success');
                        
                        // 延迟跳转到登录页面
                        setTimeout(function() {
                            window.location.href = 'login.html';
                        }, 2000);
                    } else {
                        // 注册失败
                        if (result.error && result.error.includes('用户已存在')) {
                            if (errorElements.username) {
                                errorElements.username.textContent = result.error;
                                errorElements.username.style.display = 'block';
                            }
                        } else {
                            showMessage(result.error || '注册失败', 'error');
                        }
                        
                        // 恢复按钮状态
                        submitBtn.textContent = originalText;
                        submitBtn.disabled = false;
                    }
                } catch (error) {
                    console.error('注册过程中发生错误:', error);
                    showMessage('注册请求失败，请检查网络连接', 'error');
                    
                    // 恢复按钮状态
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                }
            }
        });
    }

    // 显示消息函数
    function showMessage(message, type) {
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
});