/**
 * PatPat-Inconsistency-Hunter 布局组件
 * 包含导航栏和页脚
 */

import { useState, useRef, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FileSearch, 
  LayoutDashboard, 
  Home,
  Shield,
  Github,
  Users,
  LogIn,
  LogOut,
  User,
  Settings,
  ChevronDown,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const navItems = [
  { path: '/', label: '首页', icon: Home },
  { path: '/analyze', label: '文档分析', icon: FileSearch },
  { path: '/collaborate', label: '协作空间', icon: Users },
  { path: '/dashboard', label: '仪表盘', icon: LayoutDashboard },
]

// 用户头像组件
function UserAvatar({ user, size = 'md' }) {
  const [imageError, setImageError] = useState(false)
  
  // 当 avatar_url 变化时重置错误状态
  useEffect(() => {
    setImageError(false)
  }, [user?.avatar_url])
  
  const sizes = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-10 h-10 text-base',
  }

  // 如果有头像URL且没有加载错误，显示图片
  if (user?.avatar_url && !imageError) {
    // 添加时间戳防止缓存
    const avatarSrc = user.avatar_url.includes('?') 
      ? user.avatar_url 
      : `${user.avatar_url}?t=${Date.now()}`
    
    return (
      <img
        src={avatarSrc}
        alt={user.display_name || user.username}
        className={`${sizes[size]} rounded-full object-cover`}
        onError={() => setImageError(true)}
      />
    )
  }

  // 默认显示颜色+首字母头像
  return (
    <div 
      className={`${sizes[size]} rounded-full flex items-center justify-center font-medium text-white`}
      style={{ backgroundColor: user?.avatar_color || '#64a386' }}
    >
      {(user?.display_name || user?.username || '?').charAt(0).toUpperCase()}
    </div>
  )
}

// 用户菜单组件
function UserMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl hover:bg-serene-100/70 transition-colors"
      >
        <UserAvatar user={user} />
        <span className="hidden sm:inline text-sm font-medium text-slate-700">
          {user?.display_name || user?.username}
        </span>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border border-slate-100 py-2 z-50"
          >
            <div className="px-4 py-2 border-b border-slate-100">
              <p className="text-sm font-medium text-slate-900">{user?.display_name || user?.username}</p>
              <p className="text-xs text-slate-500">@{user?.username}</p>
            </div>
            <Link
              to="/profile"
              className="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
              onClick={() => setOpen(false)}
            >
              <User className="w-4 h-4" />
              个人中心
            </Link>
            <button
              onClick={() => {
                setOpen(false)
                onLogout()
              }}
              className="flex items-center gap-2 px-4 py-2 text-sm text-danger-600 hover:bg-danger-50 w-full"
            >
              <LogOut className="w-4 h-4" />
              退出登录
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Layout({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated, logout, loading } = useAuth()

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <div className="relative min-h-screen gradient-bg overflow-hidden">
      <div className="relative flex flex-col min-h-screen">
        {/* 导航栏 */}
        <header className="sticky top-0 z-50 glass border-b border-serene-200/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className="logo-badge w-10 h-10 rounded-xl flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-lg font-bold gradient-text">PatPat 事实卫士</h1>
                <p className="text-xs text-slate-500">长文本一致性检测</p>
              </div>
            </Link>

            {/* 导航链接 */}
            <nav className="flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.path
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`
                      relative flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all duration-200 border backdrop-blur-sm
                      ${isActive 
                        ? 'text-primary-600 bg-white/85 border-white/70 shadow-lg shadow-primary-100' 
                        : 'text-slate-600 bg-white/55 border-white/45 hover:text-slate-900 hover:bg-white/80 hover:border-white/65'
                      }
                    `}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="hidden sm:inline">{item.label}</span>
                    {isActive && (
                      <motion.div
                        layoutId="nav-indicator"
                        className="absolute inset-0 bg-primary-100/80 rounded-xl -z-10"
                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                      />
                    )}
                  </Link>
                )
              })}
            </nav>

            {/* 用户区域 */}
            <div className="flex items-center gap-2">
              {loading ? (
                <div className="w-8 h-8 bg-slate-200 rounded-full animate-pulse" />
              ) : isAuthenticated ? (
                <UserMenu user={user} onLogout={handleLogout} />
              ) : (
                <>
                  <Link to="/login" className="btn-ghost text-sm">
                    <LogIn className="w-4 h-4" />
                    <span className="hidden sm:inline">登录</span>
                  </Link>
                  <Link to="/register" className="btn-primary py-2 px-4 text-sm">
                    注册
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
        </header>

        {/* 主内容区 */}
        <main className="flex-1 relative z-10">
          <div>
            {children}
          </div>
        </main>

        {/* 页脚 */}
        <footer className="border-t border-slate-200/50 bg-white/50 relative z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Shield className="w-4 h-4" />
                <span>PatPat-Inconsistency-Hunter © 2026</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm text-slate-500">云计算系统课程大作业</span>
                <a 
                  href="https://github.com/WuTong-ww/PatPat-Inconsistency-Hunter" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <Github className="w-5 h-5" />
                </a>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default Layout

