
import axios from 'axios';

// 后端API地址 - 根据实际情况修改
const API_BASE_URL = 'http://localhost:8000';

// 创建axios实例
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
});

// 用户认证API
export const authAPI = {
    // 登录
    login: async (username, password) => {
        try {
            const response = await apiClient.post('/api/login', {
                username,
                password
            });
            
            return {
                success: true,
                data: response.data
            };
        } catch (error) {
            console.error('登录请求失败:', error);
            
            // 处理不同的错误情况
            if (error.response) {
                // 服务器返回了错误状态码
                const status = error.response.status;
                const message = error.response.data?.detail || '登录失败';
                
                if (status === 401) {
                    return {
                        success: false,
                        error: '密码错误'
                    };
                } else if (status === 404) {
                    return {
                        success: false,
                        error: '用户不存在'
                    };
                } else {
                    return {
                        success: false,
                        error: message
                    };
                }
            } else if (error.request) {
                // 请求已发送但没有收到响应
                return {
                    success: false,
                    error: '无法连接到服务器，请检查网络连接'
                };
            } else {
                // 请求配置错误
                return {
                    success: false,
                    error: '请求配置错误'
                };
            }
        }
    },
    
    // 注册
    register: async (username, password) => {
        try {
            const response = await apiClient.post('/api/register', {
                username,
                password
            });
            
            return {
                success: true,
                data: response.data
            };
        } catch (error) {
            console.error('注册请求失败:', error);
            
            if (error.response) {
                const status = error.response.status;
                const message = error.response.data?.detail || '注册失败';
                
                if (status === 400 && message.includes('用户已存在')) {
                    return {
                        success: false,
                        error: '用户名已存在'
                    };
                } else {
                    return {
                        success: false,
                        error: message
                    };
                }
            } else if (error.request) {
                return {
                    success: false,
                    error: '无法连接到服务器'
                };
            } else {
                return {
                    success: false,
                    error: '请求配置错误'
                };
            }
        }
    },
    
    // 获取当前登录状态（从本地存储）
    getCurrentUser: () => {
        const user = localStorage.getItem('currentUser');
        if (user) {
            try {
                return JSON.parse(user);
            } catch (e) {
                return null;
            }
        }
        return null;
    },
    
    // 保存登录状态到本地存储
    setCurrentUser: (userData) => {
        localStorage.setItem('currentUser', JSON.stringify(userData));
    },
    
    // 退出登录
    logout: () => {
        localStorage.removeItem('currentUser');
        return {
            success: true
        };
    }
};

// 其他API模块（文件上传、题目生成等）将在后续添加
export const fileAPI = {};
export const questionAPI = {};
export const evaluationAPI = {};

export default {
    auth: authAPI,
    file: fileAPI,
    question: questionAPI,
    evaluation: evaluationAPI
};