/**
 * PatPat-Inconsistency-Hunter 注册页面
 * 用户注册界面
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Shield,
  User,
  Lock,
  Mail,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
  Check,
} from 'lucide-react'
import { register } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'

function RegisterPage() {
  const navigate = useNavigate()
  const { setUser } = useAuth()
  
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    email: '',
    display_name: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 密码强度检查
  const passwordChecks = {
    length: formData.password.length >= 6,
    hasLetter: /[a-zA-Z]/.test(formData.password),
    hasNumber: /[0-9]/.test(formData.password),
  }
  const passwordStrength = Object.values(passwordChecks).filter(Boolean).length

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // 表单验证
    if (!formData.username || !formData.password) {
      setError('请填写用户名和密码')
      return
    }
    
    if (formData.username.length < 3) {
      setError('用户名至少3个字符')
      return
    }
    
    if (formData.password.length < 6) {
      setError('密码至少6个字符')
      return
    }
    
    if (formData.password !== formData.confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const result = await register({
        username: formData.username,
        password: formData.password,
        email: formData.email || undefined,
        display_name: formData.display_name || undefined,
      })
      // 更新 AuthContext 中的用户状态
      if (result.user) {
        setUser(result.user)
      }
      // 刷新页面以确保所有组件都更新
      window.location.href = '/'
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
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-primary-200/30 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-accent-200/30 rounded-full blur-3xl" />
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
          <h1 className="text-2xl font-bold text-slate-900">创建账号</h1>
          <p className="text-slate-500 mt-1">加入 PatPat 事实卫士</p>
        </div>

        {/* 注册表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              用户名 <span className="text-danger-500">*</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                className="input pl-10"
                placeholder="3-32个字符"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              显示名称
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                className="input pl-10"
                placeholder="在协作中显示的名称（默认为用户名）"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              邮箱
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="email"
                className="input pl-10"
                placeholder="可选，用于找回密码"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              密码 <span className="text-danger-500">*</span>
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type={showPassword ? 'text' : 'password'}
                className="input pl-10 pr-10"
                placeholder="至少6个字符"
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
            
            {/* 密码强度指示 */}
            {formData.password && (
              <div className="mt-2 space-y-1">
                <div className="flex gap-1">
                  {[1, 2, 3].map((level) => (
                    <div
                      key={level}
                      className={`h-1 flex-1 rounded-full ${
                        passwordStrength >= level
                          ? passwordStrength === 1
                            ? 'bg-danger-500'
                            : passwordStrength === 2
                            ? 'bg-warning-500'
                            : 'bg-success-500'
                          : 'bg-slate-200'
                      }`}
                    />
                  ))}
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className={`flex items-center gap-1 ${passwordChecks.length ? 'text-success-600' : 'text-slate-400'}`}>
                    {passwordChecks.length ? <Check className="w-3 h-3" /> : null}
                    6个字符以上
                  </span>
                  <span className={`flex items-center gap-1 ${passwordChecks.hasLetter ? 'text-success-600' : 'text-slate-400'}`}>
                    {passwordChecks.hasLetter ? <Check className="w-3 h-3" /> : null}
                    包含字母
                  </span>
                  <span className={`flex items-center gap-1 ${passwordChecks.hasNumber ? 'text-success-600' : 'text-slate-400'}`}>
                    {passwordChecks.hasNumber ? <Check className="w-3 h-3" /> : null}
                    包含数字
                  </span>
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              确认密码 <span className="text-danger-500">*</span>
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type={showPassword ? 'text' : 'password'}
                className="input pl-10"
                placeholder="再次输入密码"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              />
            </div>
            {formData.confirmPassword && formData.password !== formData.confirmPassword && (
              <p className="mt-1 text-xs text-danger-500">两次输入的密码不一致</p>
            )}
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
                注册中...
              </>
            ) : (
              <>
                注册
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        {/* 登录链接 */}
        <div className="mt-6 text-center">
          <span className="text-slate-500">已有账号？</span>
          <Link to="/login" className="ml-1 text-primary-600 hover:text-primary-700 font-medium">
            立即登录
          </Link>
        </div>
      </motion.div>
    </div>
  )
}

export default RegisterPage

