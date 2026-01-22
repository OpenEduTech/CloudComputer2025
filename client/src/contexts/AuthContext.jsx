/**
 * PatPat-Inconsistency-Hunter 认证上下文
 * 管理全局用户认证状态
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { 
  getStoredUser, 
  setStoredUser, 
  checkAuth, 
  logout as apiLogout,
  isAuthenticated,
  getToken,
} from '../api/auth'

// 创建上下文
const AuthContext = createContext(null)

/**
 * 认证上下文提供者
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [initialized, setInitialized] = useState(false)

  // 初始化时检查认证状态
  useEffect(() => {
    const initAuth = async () => {
      // 先从本地存储获取用户信息
      const storedUser = getStoredUser()
      if (storedUser) {
        setUser(storedUser)
      }

      // 如果有Token，验证有效性
      if (getToken()) {
        try {
          const result = await checkAuth()
          if (result.authenticated && result.user) {
            setUser(result.user)
          } else {
            setUser(null)
          }
        } catch {
          setUser(null)
        }
      }

      setLoading(false)
      setInitialized(true)
    }

    initAuth()
  }, [])

  // 登录成功后更新用户
  const updateUser = useCallback((userData) => {
    setUser(userData)
    if (userData) {
      setStoredUser(userData)
    }
  }, [])

  // 登出
  const logout = useCallback(async () => {
    await apiLogout()
    setUser(null)
  }, [])

  // 刷新用户信息
  const refreshUser = useCallback(async () => {
    if (getToken()) {
      try {
        const result = await checkAuth()
        if (result.authenticated && result.user) {
          setUser(result.user)
          // 同时更新本地存储
          setStoredUser(result.user)
          return result.user
        }
      } catch {
        // 忽略错误
      }
    }
    return null
  }, [])

  const value = {
    user,
    setUser: updateUser,
    loading,
    initialized,
    isAuthenticated: !!user,
    logout,
    refreshUser,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * 使用认证上下文的Hook
 */
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext

