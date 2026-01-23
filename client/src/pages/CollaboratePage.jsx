/**
 * PatPat-Inconsistency-Hunter 协作空间页面
 * 支持创建房间、邀请码机制、选择已有文档
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Users, 
  FileText, 
  Lock,
  Plus,
  ArrowRight,
  Clock,
  Loader2,
  RefreshCw,
  Key,
  FolderOpen,
  Check,
  X,
  Shield,
} from 'lucide-react'
import { listRooms, createRoom, getUserDocuments } from '../api/collaboration'
import { useAuth } from '../contexts/AuthContext'

const collaborationModes = [
  {
    id: 'realtime',
    title: '实时协同编辑',
    description: '多人同时编辑同一文档，实时同步所有更改，支持光标和选区同步',
    icon: Users,
    color: 'primary',
    features: ['实时内容同步', '光标位置共享', '多人同时编辑', '即时冲突检测'],
  },
  {
    id: 'chapter_lock',
    title: '分章节锁定编辑',
    description: '每个章节同一时间只能被一人编辑，避免冲突，适合分工明确的团队',
    icon: Lock,
    color: 'accent',
    features: ['章节级别锁定', '防止编辑冲突', '清晰分工', '跨章节冲突检测'],
  },
]

function CollaboratePage() {
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuth()
  const [rooms, setRooms] = useState([])
  const [userDocuments, setUserDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [creating, setCreating] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedMode, setSelectedMode] = useState(null)
  
  // 创建房间表单
  const [formData, setFormData] = useState({
    roomName: '',
    documentTitle: '',
    ownerName: '',
    initialContent: '',
    inviteCode: '',
    description: '',
    selectedDocId: null,
    useExistingDoc: false,
  })
  
  // 如果已登录，使用用户名作为默认值
  useEffect(() => {
    if (user) {
      setFormData(prev => ({
        ...prev,
        ownerName: user.display_name || user.username,
      }))
    }
  }, [user])

  // 加载房间列表
  useEffect(() => {
    loadRooms()
  }, [])

  const loadRooms = async () => {
    setLoading(true)
    try {
      const data = await listRooms()
      setRooms(data)
    } catch (error) {
      console.error('加载房间列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 加载用户文档列表
  const loadUserDocuments = async () => {
    if (!isAuthenticated) return
    setLoadingDocs(true)
    try {
      const docs = await getUserDocuments()
      setUserDocuments(docs)
    } catch (error) {
      console.error('加载用户文档失败:', error)
    } finally {
      setLoadingDocs(false)
    }
  }

  const handleCreateRoom = async () => {
    if (!selectedMode || !formData.roomName || !formData.ownerName) {
      return
    }

    setCreating(true)
    try {
      const roomData = {
        room_name: formData.roomName,
        mode: selectedMode,
        document_title: formData.documentTitle || '未命名文档',
        initial_content: formData.initialContent,
        owner_name: formData.ownerName,
        description: formData.description,
      }
      
      // 添加邀请码（如果设置）
      if (formData.inviteCode) {
        roomData.invite_code = formData.inviteCode.toUpperCase()
      }
      
      // 添加已有文档ID（如果选择）
      if (formData.useExistingDoc && formData.selectedDocId) {
        roomData.document_id = formData.selectedDocId
      }
      
      const room = await createRoom(roomData)
      
      // 跳转到协作编辑页面
      navigate(`/collaborate/${room.room_id}`)
    } catch (error) {
      console.error('创建房间失败:', error)
      alert('创建房间失败: ' + error.message)
    } finally {
      setCreating(false)
    }
  }

  const openCreateModal = (mode) => {
    // 如果未登录，提示登录
    if (!isAuthenticated) {
      if (confirm('创建房间需要登录账号，是否前往登录？')) {
        navigate('/login', { state: { from: { pathname: '/collaborate' } } })
      }
      return
    }
    setSelectedMode(mode)
    setShowCreateModal(true)
    // 加载用户文档
    loadUserDocuments()
  }

  // 选择已有文档
  const handleSelectDocument = (doc) => {
    setFormData(prev => ({
      ...prev,
      selectedDocId: doc.id,
      documentTitle: doc.title,
      useExistingDoc: true,
    }))
  }

  // 生成随机邀请码
  const generateInviteCode = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    let code = ''
    for (let i = 0; i < 6; i++) {
      code += chars[Math.floor(Math.random() * chars.length)]
    }
    setFormData(prev => ({ ...prev, inviteCode: code }))
  }

  return (
    <div className="relative z-10 min-h-screen py-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 标题 */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-slate-900 mb-3">
            协作空间
          </h1>
          <p className="text-slate-600 max-w-2xl mx-auto">
            与团队成员一起编辑文档，实时检测并解决内容冲突
          </p>
        </div>

        {/* 协作模式选择 */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold text-slate-900 mb-6 flex items-center gap-2">
            <Plus className="w-5 h-5" />
            选择协作模式创建房间
          </h2>
          
          <div className="grid md:grid-cols-2 gap-6">
            {collaborationModes.map((mode) => {
              const Icon = mode.icon
              const colorClasses = {
                primary: 'from-primary-500 to-primary-600 shadow-primary-500/25 hover:shadow-primary-500/40',
                accent: 'from-accent-500 to-accent-600 shadow-accent-500/25 hover:shadow-accent-500/40',
              }
              
              return (
                <motion.div
                  key={mode.id}
                  whileHover={{ y: -4 }}
                  className="card-hover p-6 cursor-pointer"
                  onClick={() => openCreateModal(mode.id)}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${colorClasses[mode.color]} flex items-center justify-center shadow-lg`}>
                      <Icon className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-slate-900 mb-2">
                        {mode.title}
                      </h3>
                      <p className="text-slate-600 text-sm mb-4">
                        {mode.description}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {mode.features.map((feature, idx) => (
                          <span
                            key={idx}
                            className={`badge ${mode.color === 'primary' ? 'badge-primary' : 'bg-accent-100 text-accent-700'}`}
                          >
                            {feature}
                          </span>
                        ))}
                      </div>
                    </div>
                    <ArrowRight className="w-5 h-5 text-slate-400" />
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>

        {/* 现有房间列表 */}
        <div>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              加入现有房间
            </h2>
            <button onClick={loadRooms} className="btn-ghost">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </button>
          </div>

          {loading ? (
            <div className="card p-12 text-center">
              <Loader2 className="w-8 h-8 text-primary-500 animate-spin mx-auto mb-4" />
              <p className="text-slate-500">加载房间列表...</p>
            </div>
          ) : rooms.length === 0 ? (
            <div className="card p-12 text-center">
              <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-700 mb-2">暂无协作房间</h3>
              <p className="text-slate-500">选择上方的协作模式创建第一个房间</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {rooms.map((room, index) => (
                <motion.div
                  key={room.room_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="card p-4 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => navigate(`/collaborate/${room.room_id}/join`)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        room.mode === 'realtime' 
                          ? 'bg-primary-100 text-primary-600' 
                          : 'bg-accent-100 text-accent-600'
                      }`}>
                        {room.mode === 'realtime' ? (
                          <Users className="w-5 h-5" />
                        ) : (
                          <Lock className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-slate-900">{room.room_name}</h3>
                          {room.has_invite_code && (
                            <span className="flex items-center gap-1 text-xs bg-warning-100 text-warning-700 px-2 py-0.5 rounded-full">
                              <Key className="w-3 h-3" />
                              需要邀请码
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-500">{room.document_title}</p>
                        {room.description && (
                          <p className="text-xs text-slate-400 mt-1 line-clamp-1">{room.description}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-sm text-slate-600">
                          <Users className="w-4 h-4" />
                          <span>{room.online_count}/{room.member_count} 在线</span>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-slate-400">
                          <Clock className="w-3 h-3" />
                          <span>创建于 {new Date(room.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                      <ArrowRight className="w-5 h-5 text-slate-400" />
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 创建房间弹窗 */}
      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative rounded-3xl bg-white/80 shadow-[0_25px_60px_rgba(31,59,51,0.25)] border border-white/60 p-8 w-full max-w-lg max-h-[90vh] overflow-y-auto backdrop-blur-2xl"
            >
              <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-white/55 via-white/35 to-primary-50/35 pointer-events-none" />
              <button
                onClick={() => setShowCreateModal(false)}
                className="absolute top-4 right-4 p-2 rounded-full bg-white/70 hover:bg-white text-slate-500 hover:text-slate-700 transition-colors z-20 shadow-sm"
              >
                <X className="w-5 h-5" />
              </button>
              <div className="relative z-10">
                <div className="text-center mb-8">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-primary-500/25">
                    <Users className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-semibold text-slate-900">创建协作房间</h3>
                  <p className="text-sm text-slate-500 mt-1">与团队成员实时编辑，保持叙述一致</p>
                </div>
              
              <div className="flex items-center gap-2 mb-6 p-3 rounded-xl bg-white/65 border border-white/75 shadow-inner shadow-white/50 relative z-10">
                {selectedMode === 'realtime' ? (
                  <>
                    <Users className="w-5 h-5 text-primary-600" />
                    <span className="text-slate-700">实时协同编辑</span>
                  </>
                ) : (
                  <>
                    <Lock className="w-5 h-5 text-accent-600" />
                    <span className="text-slate-700">分章节锁定编辑</span>
                  </>
                )}
              </div>

              <div className="space-y-4 relative z-10">
                {/* 房间名称 */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    房间名称 <span className="text-danger-500">*</span>
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="例如：毕业论文协作"
                    value={formData.roomName}
                    onChange={(e) => setFormData({ ...formData, roomName: e.target.value })}
                  />
                </div>

                {/* 房间描述 */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    房间描述
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="简短描述这个协作房间的用途..."
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>

                {/* 邀请码 */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      邀请码（可选，用于限制加入）
                    </div>
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      className="input flex-1 uppercase"
                      placeholder="4-8位字母数字，不填则自动生成"
                      maxLength={8}
                      value={formData.inviteCode}
                      onChange={(e) => setFormData({ ...formData, inviteCode: e.target.value.toUpperCase() })}
                    />
                    <button
                      type="button"
                      onClick={generateInviteCode}
                      className="px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 text-sm transition-colors"
                    >
                      随机生成
                    </button>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    设置邀请码后，其他人需要输入正确的邀请码才能加入房间
                  </p>
                </div>

                {/* 您的昵称 */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    您的昵称 <span className="text-danger-500">*</span>
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="例如：张三"
                    value={formData.ownerName}
                    onChange={(e) => setFormData({ ...formData, ownerName: e.target.value })}
                  />
                </div>

                {/* 选择已有文档 */}
                {isAuthenticated && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-slate-700">
                        <div className="flex items-center gap-2">
                          <FolderOpen className="w-4 h-4" />
                          初始内容来源
                        </div>
                      </label>
                    </div>
                    
                    <div className="flex gap-2 mb-3">
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, useExistingDoc: false, selectedDocId: null })}
                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                          !formData.useExistingDoc
                            ? 'bg-primary-100 text-primary-700 border-2 border-primary-300'
                            : 'bg-slate-100 text-slate-600 border-2 border-transparent hover:bg-slate-200'
                        }`}
                      >
                        手动输入
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setFormData({ ...formData, useExistingDoc: true })
                          if (userDocuments.length === 0) loadUserDocuments()
                        }}
                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                          formData.useExistingDoc
                            ? 'bg-primary-100 text-primary-700 border-2 border-primary-300'
                            : 'bg-slate-100 text-slate-600 border-2 border-transparent hover:bg-slate-200'
                        }`}
                      >
                        请选择已有文档
                      </button>
                    </div>

                    {formData.useExistingDoc ? (
                      <div className="border border-slate-200 rounded-lg p-3 max-h-48 overflow-y-auto">
                        {loadingDocs ? (
                          <div className="text-center py-4">
                            <Loader2 className="w-5 h-5 animate-spin mx-auto text-slate-400" />
                            <p className="text-sm text-slate-500 mt-2">加载文档列表...</p>
                          </div>
                        ) : userDocuments.length === 0 ? (
                          <div className="text-center py-4">
                            <FileText className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                            <p className="text-sm text-slate-500">暂无已分析的文档</p>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {userDocuments.map((doc) => (
                              <div
                                key={doc.id}
                                onClick={() => handleSelectDocument(doc)}
                                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                                  formData.selectedDocId === doc.id
                                    ? 'bg-primary-100 border-2 border-primary-300'
                                    : 'bg-slate-50 hover:bg-slate-100 border-2 border-transparent'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <div>
                                    <p className="font-medium text-slate-800 text-sm">{doc.title}</p>
                                    <p className="text-xs text-slate-500">
                                      {doc.content_length?.toLocaleString()} 字 · {doc.total_facts} 事实 · {doc.total_conflicts} 冲突
                                    </p>
                                  </div>
                                  {formData.selectedDocId === doc.id && (
                                    <Check className="w-5 h-5 text-primary-600" />
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <>
                        {/* 文档标题 */}
                        <div className="mb-3">
                          <label className="block text-sm font-medium text-slate-700 mb-1">
                            文档标题
                          </label>
                          <input
                            type="text"
                            className="input"
                            placeholder="例如：项目可行性报告"
                            value={formData.documentTitle}
                            onChange={(e) => setFormData({ ...formData, documentTitle: e.target.value })}
                          />
                        </div>

                        {/* 初始内容 */}
                        <div>
                          <label className="block text-sm font-medium text-slate-700 mb-1">
                            初始内容（可选）
                          </label>
                          <textarea
                            className="textarea"
                            rows={4}
                            placeholder="可以粘贴已有的文档内容..."
                            value={formData.initialContent}
                            onChange={(e) => setFormData({ ...formData, initialContent: e.target.value })}
                          />
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* 非登录用户显示简化表单 */}
                {!isAuthenticated && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        文档标题
                      </label>
                      <input
                        type="text"
                        className="input"
                        placeholder="例如：项目可行性报告"
                        value={formData.documentTitle}
                        onChange={(e) => setFormData({ ...formData, documentTitle: e.target.value })}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        初始内容（可选）
                      </label>
                      <textarea
                        className="textarea"
                        rows={4}
                        placeholder="可以粘贴已有的文档内容..."
                        value={formData.initialContent}
                        onChange={(e) => setFormData({ ...formData, initialContent: e.target.value })}
                      />
                    </div>
                  </>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary flex-1"
                  disabled={creating}
                >
                  取消
                </button>
                <button
                  onClick={handleCreateRoom}
                  className="btn-primary flex-1"
                  disabled={creating || !formData.roomName || !formData.ownerName}
                >
                  {creating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      创建中...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      创建房间
                    </>
                  )}
                </button>
              </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default CollaboratePage
