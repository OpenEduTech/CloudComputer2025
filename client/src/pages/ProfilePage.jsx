/**
 * PatPat-Inconsistency-Hunter 个人中心页面
 * 展示用户信息和历史分析记录
 */

import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User,
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle,
  Settings,
  LogOut,
  Trash2,
  Eye,
  RefreshCw,
  Loader2,
  Calendar,
  BarChart3,
  Edit3,
  Save,
  X,
  Mail,
  Shield,
  Key,
  Activity,
  TrendingUp,
  Award,
  ChevronRight,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { getUserAnalysisHistory, deleteAnalysisRecord, updateUserProfile, uploadAvatar } from '../api'
import { changePassword } from '../api/auth'

// 用户头像组件
function UserAvatar({ user, size = 'lg' }) {
  const [imageError, setImageError] = useState(false)
  
  // 当 avatar_url 变化时重置错误状态
  useEffect(() => {
    setImageError(false)
  }, [user?.avatar_url])
  
  const sizes = {
    sm: 'w-12 h-12 text-lg',
    md: 'w-16 h-16 text-2xl',
    lg: 'w-24 h-24 text-4xl',
  }

  // 如果有头像URL且图片加载没有失败，显示图片
  if (user?.avatar_url && !imageError) {
    // 添加时间戳防止浏览器缓存
    const avatarSrc = user.avatar_url.includes('?') 
      ? user.avatar_url 
      : `${user.avatar_url}?t=${Date.now()}`
    
    return (
      <img
        src={avatarSrc}
        alt={user.display_name || user.username}
        className={`${sizes[size]} rounded-full object-cover shadow-lg border-2 border-white`}
        onError={() => setImageError(true)}
      />
    )
  }

  // 默认显示颜色+首字母头像
  return (
    <div
      className={`${sizes[size]} rounded-full flex items-center justify-center font-bold text-white shadow-lg`}
      style={{ backgroundColor: user?.avatar_color || '#64a386' }}
    >
      {(user?.display_name || user?.username || '?').charAt(0).toUpperCase()}
    </div>
  )
}

// 分析记录卡片
function AnalysisRecordCard({ record, onDelete, onView }) {
  const [deleting, setDeleting] = useState(false)
  
  const statusColors = {
    completed: 'text-success-600 bg-success-50',
    failed: 'text-danger-600 bg-danger-50',
    pending: 'text-warning-600 bg-warning-50',
    processing: 'text-primary-600 bg-primary-50',
  }

  const statusLabels = {
    completed: '已完成',
    failed: '失败',
    pending: '等待中',
    processing: '处理中',
  }

  const handleDelete = async () => {
    if (!confirm('确定要删除这条分析记录吗？')) return
    setDeleting(true)
    try {
      await onDelete(record.task_id)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="card p-4 hover:shadow-lg transition-shadow"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-primary-500 flex-shrink-0" />
            <h3 className="font-medium text-slate-900 truncate">
              {record.title || '未命名文档'}
            </h3>
            <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[record.status]}`}>
              {statusLabels[record.status]}
            </span>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-slate-500 mb-3">
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              <span>{new Date(record.created_at).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center gap-1">
              <FileText className="w-3 h-3" />
              <span>{record.content_length?.toLocaleString() || 0} 字</span>
            </div>
            <div className="flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-primary-500" />
              <span>{record.total_facts || 0} 事实</span>
            </div>
            <div className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-danger-500" />
              <span>{record.total_conflicts || 0} 冲突</span>
            </div>
          </div>

          {record.analysis_time && (
            <div className="text-xs text-slate-400 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              分析耗时: {record.analysis_time.toFixed(1)}s
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {record.status === 'completed' && (
            <button
              onClick={() => onView(record.task_id)}
              className="btn-ghost text-primary-600 hover:bg-primary-50 p-2"
              title="查看详情"
            >
              <Eye className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="btn-ghost text-danger-600 hover:bg-danger-50 p-2"
            title="删除记录"
          >
            {deleting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// 密码修改表单组件
function PasswordChangeForm({ onSuccess, onCancel }) {
  const [formData, setFormData] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [showPasswords, setShowPasswords] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    // 验证
    if (formData.newPassword.length < 6) {
      setError('新密码至少需要6个字符')
      return
    }

    if (formData.newPassword !== formData.confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    setSaving(true)
    try {
      await changePassword(formData.oldPassword, formData.newPassword)
      if (onSuccess) {
        onSuccess()
      }
    } catch (err) {
      setError(err.message || '密码修改失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          当前密码
        </label>
        <input
          type={showPasswords ? 'text' : 'password'}
          value={formData.oldPassword}
          onChange={(e) => setFormData({ ...formData, oldPassword: e.target.value })}
          className="input w-full"
          placeholder="输入当前密码"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          新密码
        </label>
        <input
          type={showPasswords ? 'text' : 'password'}
          value={formData.newPassword}
          onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
          className="input w-full"
          placeholder="输入新密码（至少6个字符）"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          确认新密码
        </label>
        <input
          type={showPasswords ? 'text' : 'password'}
          value={formData.confirmPassword}
          onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
          className="input w-full"
          placeholder="再次输入新密码"
          required
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="showPasswords"
          checked={showPasswords}
          onChange={(e) => setShowPasswords(e.target.checked)}
          className="w-4 h-4 text-primary-600 rounded"
        />
        <label htmlFor="showPasswords" className="text-sm text-slate-600">
          显示密码
        </label>
      </div>

      {error && (
        <div className="text-sm text-danger-600 bg-danger-50 p-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={saving}
          className="btn-primary"
        >
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Key className="w-4 h-4" />
              修改密码
            </>
          )}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="btn-ghost"
        >
          <X className="w-4 h-4" />
          取消
        </button>
      </div>
    </form>
  )
}

// 个人信息编辑表单
function ProfileEditForm({ user, onSave, onCancel, onAvatarUploaded }) {
  const [formData, setFormData] = useState({
    display_name: user?.display_name || '',
    email: user?.email || '',
    avatar_color: user?.avatar_color || '#64a386',
    avatar_url: user?.avatar_url || '',
  })
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [avatarMode, setAvatarMode] = useState(user?.avatar_url ? 'image' : 'color')
  const fileInputRef = useRef(null)

  const colorOptions = [
    '#1f3b33', '#64a386', '#a9d4a6', '#bcdabe',
    '#cde2e8', '#fbfccd', '#8fc4d1', '#6b8a7b',
    '#bad7e2', '#dff0e6',
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    
    try {
      await onSave(formData)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      setError('请选择图片文件')
      return
    }

    // 验证文件大小（最大5MB）
    if (file.size > 5 * 1024 * 1024) {
      setError('图片大小不能超过5MB')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const result = await uploadAvatar(file)
      // 更新表单数据
      setFormData({ ...formData, avatar_url: result.avatar_url })
      // 触发回调，上传后立即刷新用户信息
      if (onAvatarUploaded) {
        await onAvatarUploaded(result.avatar_url)
      }
    } catch (err) {
      setError(err.message || '头像上传失败')
    } finally {
      setUploading(false)
    }
  }

  const triggerFileSelect = () => {
    fileInputRef.current?.click()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          显示名称
        </label>
        <input
          type="text"
          value={formData.display_name}
          onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
          className="input w-full"
          placeholder="输入显示名称"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          邮箱
        </label>
        <input
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          className="input w-full"
          placeholder="输入邮箱地址"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-slate-700">
            头像设置
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setAvatarMode('color')}
              className={`text-xs px-2 py-1 rounded ${
                avatarMode === 'color' 
                  ? 'bg-primary-100 text-primary-700' 
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              颜色头像
            </button>
            <button
              type="button"
              onClick={() => setAvatarMode('image')}
              className={`text-xs px-2 py-1 rounded ${
                avatarMode === 'image' 
                  ? 'bg-primary-100 text-primary-700' 
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              图片头像
            </button>
          </div>
        </div>
        
        {avatarMode === 'image' ? (
          <div className="space-y-3">
            {/* 隐藏的文件输入 */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              onChange={handleFileSelect}
              className="hidden"
            />
            
            {/* 上传按钮 */}
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={triggerFileSelect}
                disabled={uploading}
                className="btn-ghost border border-dashed border-slate-300 px-4 py-3 hover:border-primary-400 hover:bg-primary-50"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
                    <span className="text-sm text-slate-600">上传中...</span>
                  </>
                ) : (
                  <>
                    <User className="w-5 h-5 text-slate-400" />
                    <span className="text-sm text-slate-600">点击选择图片</span>
                  </>
                )}
              </button>
              
              {/* 预览 */}
              {formData.avatar_url && (
                <div className="flex items-center gap-2">
                  <img
                    src={formData.avatar_url}
                    alt="头像预览"
                    className="w-12 h-12 rounded-full object-cover border-2 border-primary-200"
                    onError={(e) => {
                      e.target.src = ''
                      e.target.style.display = 'none'
                    }}
                  />
                  <span className="text-xs text-success-600">已上传</span>
                </div>
              )}
            </div>
            
            <p className="text-xs text-slate-500">
              支持 JPG、PNG、GIF、WEBP 格式，最大 5MB
            </p>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {colorOptions.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setFormData({ ...formData, avatar_color: color, avatar_url: '' })}
                className={`w-8 h-8 rounded-full transition-transform ${
                  formData.avatar_color === color && !formData.avatar_url ? 'ring-2 ring-offset-2 ring-slate-400 scale-110' : ''
                }`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="text-sm text-danger-600 bg-danger-50 p-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={saving || uploading}
          className="btn-primary"
        >
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              保存
            </>
          )}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="btn-ghost"
        >
          <X className="w-4 h-4" />
          取消
        </button>
      </div>
    </form>
  )
}

function ProfilePage() {
  const navigate = useNavigate()
  const { user, isAuthenticated, logout, refreshUser } = useAuth()
  const [loading, setLoading] = useState(true)
  const [analysisHistory, setAnalysisHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(false)
  const [activeTab, setActiveTab] = useState('history')
  const [changingPassword, setChangingPassword] = useState(false)
  const [passwordChangeSuccess, setPasswordChangeSuccess] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    loadData()
  }, [isAuthenticated])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const data = await getUserAnalysisHistory()
      setAnalysisHistory(data.records || [])
      setStats(data.stats || null)
    } catch (err) {
      setError(err.message)
      // 如果API不存在，使用空数据
      setAnalysisHistory([])
      setStats({
        total_analyses: 0,
        completed_analyses: 0,
        total_facts_extracted: 0,
        total_conflicts_found: 0,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteRecord = async (taskId) => {
    try {
      await deleteAnalysisRecord(taskId)
      setAnalysisHistory(prev => prev.filter(r => r.task_id !== taskId))
    } catch (err) {
      alert('删除失败: ' + err.message)
    }
  }

  const handleViewRecord = (taskId) => {
    navigate(`/result/${taskId}`)
  }

  const handleSaveProfile = async (formData) => {
    await updateUserProfile(formData)
    await refreshUser()
    setEditing(false)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 用户信息卡片 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-6 mb-8"
        >
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
            <UserAvatar user={user} size="lg" />
            
            <div className="flex-1 text-center sm:text-left">
              {editing ? (
                <ProfileEditForm
                  user={user}
                  onSave={handleSaveProfile}
                  onCancel={() => setEditing(false)}
                  onAvatarUploaded={(url) => refreshUser()}
                />
              ) : (
                <>
                  <h1 className="text-2xl font-bold text-slate-900 mb-1">
                    {user?.display_name || user?.username}
                  </h1>
                  <p className="text-slate-500 mb-2">@{user?.username}</p>
                  
                  {user?.email && (
                    <div className="flex items-center justify-center sm:justify-start gap-2 text-sm text-slate-600 mb-4">
                      <Mail className="w-4 h-4" />
                      {user.email}
                    </div>
                  )}
                  
                  <div className="flex items-center justify-center sm:justify-start gap-3">
                    <button
                      onClick={() => setEditing(true)}
                      className="btn-ghost text-sm"
                    >
                      <Edit3 className="w-4 h-4" />
                      编辑资料
                    </button>
                    <button
                      onClick={handleLogout}
                      className="btn-ghost text-sm text-danger-600 hover:bg-danger-50"
                    >
                      <LogOut className="w-4 h-4" />
                      退出登录
                    </button>
                  </div>
                </>
              )}
            </div>

            {/* 统计数据 */}
            {!editing && stats && (
              <div className="grid grid-cols-2 gap-4 text-center">
                <div className="p-4 bg-primary-50 rounded-xl">
                  <div className="text-2xl font-bold text-primary-600">
                    {stats.total_analyses || 0}
                  </div>
                  <div className="text-xs text-slate-500">分析次数</div>
                </div>
                <div className="p-4 bg-success-50 rounded-xl">
                  <div className="text-2xl font-bold text-success-600">
                    {stats.completed_analyses || 0}
                  </div>
                  <div className="text-xs text-slate-500">已完成</div>
                </div>
                <div className="p-4 bg-warning-50 rounded-xl">
                  <div className="text-2xl font-bold text-warning-600">
                    {stats.total_facts_extracted?.toLocaleString() || 0}
                  </div>
                  <div className="text-xs text-slate-500">提取事实</div>
                </div>
                <div className="p-4 bg-danger-50 rounded-xl">
                  <div className="text-2xl font-bold text-danger-600">
                    {stats.total_conflicts_found || 0}
                  </div>
                  <div className="text-xs text-slate-500">发现冲突</div>
                </div>
              </div>
            )}
          </div>
        </motion.div>

        {/* 标签页切换 */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all ${
              activeTab === 'history'
                ? 'bg-primary-100 text-primary-700'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <FileText className="w-4 h-4" />
            分析历史 ({analysisHistory.length})
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all ${
              activeTab === 'settings'
                ? 'bg-primary-100 text-primary-700'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Settings className="w-4 h-4" />
            账户设置
          </button>
          
          <button
            onClick={loadData}
            className="btn-ghost ml-auto"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>

        {/* 内容区域 */}
        {activeTab === 'history' ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            {error && (
              <div className="card p-4 bg-danger-50 text-danger-700">
                {error}
              </div>
            )}
            
            {analysisHistory.length === 0 ? (
              <div className="card p-12 text-center">
                <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-slate-900 mb-2">
                  暂无分析记录
                </h3>
                <p className="text-slate-600 mb-6">
                  开始分析你的第一份文档吧
                </p>
                <Link to="/analyze" className="btn-primary">
                  开始分析
                </Link>
              </div>
            ) : (
              <AnimatePresence>
                {analysisHistory.map((record) => (
                  <AnalysisRecordCard
                    key={record.task_id}
                    record={record}
                    onDelete={handleDeleteRecord}
                    onView={handleViewRecord}
                  />
                ))}
              </AnimatePresence>
            )}
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            {/* 账户信息卡片 */}
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-6 flex items-center gap-2">
                <Shield className="w-5 h-5 text-primary-500" />
                账户信息
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-4 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-3 mb-3">
                    <User className="w-5 h-5 text-slate-500" />
                    <span className="font-medium text-slate-700">基本信息</span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">用户名</span>
                      <span className="font-medium">{user?.username}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">显示名称</span>
                      <span className="font-medium">{user?.display_name || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">邮箱</span>
                      <span className="font-medium">{user?.email || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">用户ID</span>
                      <span className="font-mono text-xs">{user?.user_id}</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-3 mb-3">
                    <Clock className="w-5 h-5 text-slate-500" />
                    <span className="font-medium text-slate-700">时间信息</span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">注册时间</span>
                      <span className="font-medium">
                        {user?.created_at ? new Date(user.created_at).toLocaleDateString('zh-CN') : '-'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">最后登录</span>
                      <span className="font-medium">
                        {user?.last_login_at ? new Date(user.last_login_at).toLocaleString('zh-CN') : '-'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">账户状态</span>
                      <span className="font-medium text-success-600">正常</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 使用统计卡片 */}
            {stats && (
              <div className="card p-6">
                <h2 className="text-lg font-semibold text-slate-900 mb-6 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary-500" />
                  使用统计
                </h2>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-gradient-to-br from-primary-50 to-primary-100 rounded-xl">
                    <div className="text-3xl font-bold text-primary-600 mb-1">
                      {stats.total_analyses || 0}
                    </div>
                    <div className="text-sm text-slate-600">总分析次数</div>
                    <div className="mt-2 flex items-center justify-center gap-1 text-xs text-primary-500">
                      <TrendingUp className="w-3 h-3" />
                      <span>持续增长</span>
                    </div>
                  </div>
                  
                  <div className="text-center p-4 bg-gradient-to-br from-success-50 to-success-100 rounded-xl">
                    <div className="text-3xl font-bold text-success-600 mb-1">
                      {stats.completed_analyses || 0}
                    </div>
                    <div className="text-sm text-slate-600">已完成分析</div>
                    <div className="mt-2 flex items-center justify-center gap-1 text-xs text-success-500">
                      <CheckCircle className="w-3 h-3" />
                      <span>
                        {stats.total_analyses > 0 
                          ? `${Math.round((stats.completed_analyses / stats.total_analyses) * 100)}%`
                          : '0%'
                        } 完成率
                      </span>
                    </div>
                  </div>
                  
                  <div className="text-center p-4 bg-gradient-to-br from-warning-50 to-warning-100 rounded-xl">
                    <div className="text-3xl font-bold text-warning-600 mb-1">
                      {stats.total_facts_extracted?.toLocaleString() || 0}
                    </div>
                    <div className="text-sm text-slate-600">提取事实</div>
                    <div className="mt-2 flex items-center justify-center gap-1 text-xs text-warning-500">
                      <Award className="w-3 h-3" />
                      <span>
                        {stats.completed_analyses > 0 
                          ? `平均 ${Math.round(stats.total_facts_extracted / stats.completed_analyses)}/文档`
                          : '0/文档'
                        }
                      </span>
                    </div>
                  </div>
                  
                  <div className="text-center p-4 bg-gradient-to-br from-danger-50 to-danger-100 rounded-xl">
                    <div className="text-3xl font-bold text-danger-600 mb-1">
                      {stats.total_conflicts_found || 0}
                    </div>
                    <div className="text-sm text-slate-600">发现冲突</div>
                    <div className="mt-2 flex items-center justify-center gap-1 text-xs text-danger-500">
                      <AlertTriangle className="w-3 h-3" />
                      <span>
                        {stats.completed_analyses > 0 
                          ? `平均 ${(stats.total_conflicts_found / stats.completed_analyses).toFixed(1)}/文档`
                          : '0/文档'
                        }
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 安全设置卡片 */}
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-6 flex items-center gap-2">
                <Key className="w-5 h-5 text-primary-500" />
                安全设置
              </h2>

              {changingPassword ? (
                <PasswordChangeForm
                  onSuccess={() => {
                    setChangingPassword(false)
                    setPasswordChangeSuccess(true)
                    setTimeout(() => setPasswordChangeSuccess(false), 3000)
                  }}
                  onCancel={() => setChangingPassword(false)}
                />
              ) : (
                <div className="space-y-4">
                  {passwordChangeSuccess && (
                    <div className="p-4 bg-success-50 text-success-700 rounded-xl flex items-center gap-2">
                      <CheckCircle className="w-5 h-5" />
                      密码修改成功！
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer"
                    onClick={() => setChangingPassword(true)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
                        <Key className="w-5 h-5 text-primary-600" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">修改密码</div>
                        <div className="text-sm text-slate-500">定期更改密码可以提高账户安全性</div>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-slate-400" />
                  </div>
                  
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-success-100 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-success-600" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">账户安全</div>
                        <div className="text-sm text-slate-500">您的账户当前处于安全状态</div>
                      </div>
                    </div>
                    <span className="px-3 py-1 bg-success-100 text-success-700 text-sm rounded-full">安全</span>
                  </div>
                </div>
              )}
            </div>

            {/* 危险操作卡片 */}
            <div className="card p-6 border border-danger-200">
              <h2 className="text-lg font-semibold text-danger-700 mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                危险操作
              </h2>
              
              <p className="text-sm text-slate-600 mb-4">
                以下操作不可恢复，请谨慎操作。删除账户将永久删除您的所有数据，包括分析历史和个人信息。
              </p>
              
              <button
                className="btn-ghost text-danger-600 hover:bg-danger-50 border border-danger-200"
                onClick={() => {
                  if (confirm('确定要删除账户吗？此操作不可恢复！')) {
                    alert('功能开发中')
                  }
                }}
              >
                <Trash2 className="w-4 h-4" />
                删除账户
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default ProfilePage

