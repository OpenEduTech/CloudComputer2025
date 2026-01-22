/**
 * PatPat-Inconsistency-Hunter 登录页面
 * 用户登录界面
 */

import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Shield,
  User,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
} from 'lucide-react'
import { login } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'

function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setUser } = useAuth()
  
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 获取重定向地址
  const from = location.state?.from?.pathname || '/'

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.username || !formData.password) {
      setError('请填写用户名和密码')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const result = await login(formData)
      // 更新 AuthContext 中的用户状态
      if (result.user) {
        setUser(result.user)
      }
      // 刷新页面以确保所有组件都更新
      window.location.href = from
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4">
      {/* 背景装饰 */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-200/30 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-200/30 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-8 w-full max-w-md"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-primary-500/25">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">欢迎回来</h1>
          <p className="text-slate-500 mt-1">登录 PatPat 事实卫士</p>
        </div>

        {/* 登录表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              用户名
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                className="input pl-10"
                placeholder="请输入用户名"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              密码
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type={showPassword ? 'text' : 'password'}
                className="input pl-10 pr-10"
                placeholder="请输入密码"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 bg-danger-50 text-danger-700 rounded-lg text-sm"
            >
              {error}
            </motion.div>
          )}

          <button
            type="submit"
            className="btn-primary w-full"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                登录中...
              </>
            ) : (
              <>
                登录
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        {/* 注册链接 */}
        <div className="mt-6 text-center">
          <span className="text-slate-500">还没有账号？</span>
          <Link to="/register" className="ml-1 text-primary-600 hover:text-primary-700 font-medium">
            立即注册
          </Link>
        </div>

        {/* 跳过登录 */}
        <div className="mt-4 text-center">
          <Link to="/" className="text-sm text-slate-400 hover:text-slate-600">
            暂不登录，先看看
          </Link>
        </div>
      </motion.div>
    </div>
  )
}

export default LoginPage

