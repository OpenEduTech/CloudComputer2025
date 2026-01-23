/**
 * PatPat-Inconsistency-Hunter 认证API客户端
 * 处理用户注册、登录、认证等功能
 */

const API_BASE = '/api/auth'

// Token存储键
const TOKEN_KEY = 'patpat_access_token'
const USER_KEY = 'patpat_user'

/**
 * 获取存储的Token
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * 设置Token
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 清除Token
 */
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/**
 * 获取存储的用户信息
 */
export function getStoredUser() {
  const userStr = localStorage.getItem(USER_KEY)
  if (userStr) {
    try {
      return JSON.parse(userStr)
    } catch {
      return null
    }
  }
  return null
}

/**
 * 设置用户信息
 */
export function setStoredUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

/**
 * 带认证的请求
 */
async function fetchWithAuth(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers,
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `请求失败: ${response.status}`)
  }

  return response.json()
}

/**
 * 用户注册
 * @param {Object} data - 注册数据
 * @param {string} data.username - 用户名
 * @param {string} data.password - 密码
 * @param {string} [data.email] - 邮箱
 * @param {string} [data.display_name] - 显示名称
 */
export async function register(data) {
  const result = await fetchWithAuth('/register', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  
  // 保存Token和用户信息
  setToken(result.access_token)
  setStoredUser(result.user)
  
  return result
}

/**
 * 用户登录
 * @param {Object} data - 登录数据
 * @param {string} data.username - 用户名
 * @param {string} data.password - 密码
 */
export async function login(data) {
  const result = await fetchWithAuth('/login', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  
  // 保存Token和用户信息
  setToken(result.access_token)
  setStoredUser(result.user)
  
  return result
}

/**
 * 用户登出
 */
export async function logout() {
  try {
    await fetchWithAuth('/logout', { method: 'POST' })
  } catch {
    // 忽略登出错误
  }
  clearToken()
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser() {
  return fetchWithAuth('/me')
}

/**
 * 更新用户信息
 * @param {Object} data - 更新数据
 */
export async function updateUser(data) {
  const params = new URLSearchParams()
  if (data.display_name) params.append('display_name', data.display_name)
  if (data.email) params.append('email', data.email)
  if (data.avatar_color) params.append('avatar_color', data.avatar_color)
  
  const result = await fetchWithAuth(`/me?${params.toString()}`, {
    method: 'PUT',
  })
  
  setStoredUser(result)
  return result
}

/**
 * 修改密码
 * @param {string} oldPassword - 旧密码
 * @param {string} newPassword - 新密码
 */
export async function changePassword(oldPassword, newPassword) {
  const params = new URLSearchParams({
    old_password: oldPassword,
    new_password: newPassword,
  })
  
  return fetchWithAuth(`/change-password?${params.toString()}`, {
    method: 'POST',
  })
}

/**
 * 检查认证状态
 */
export async function checkAuth() {
  try {
    const result = await fetchWithAuth('/check')
    if (result.authenticated && result.user) {
      setStoredUser(result.user)
    }
    return result
  } catch {
    clearToken()
    return { authenticated: false }
  }
}

/**
 * 是否已登录
 */
export function isAuthenticated() {
  return !!getToken()
}

export default {
  getToken,
  setToken,
  clearToken,
  getStoredUser,
  setStoredUser,
  register,
  login,
  logout,
  getCurrentUser,
  updateUser,
  changePassword,
  checkAuth,
  isAuthenticated,
}

