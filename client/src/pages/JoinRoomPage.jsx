/**
 * PatPat-Inconsistency-Hunter 加入房间页面
 * 用户输入昵称和邀请码后加入协作房间
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Users, 
  Lock,
  User,
  Key,
  ArrowRight,
  Loader2,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react'
import { getRoom, joinRoom } from '../api/collaboration'
import { useAuth } from '../contexts/AuthContext'

function JoinRoomPage() {
  const { roomId } = useParams()
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuth()
  
  const [room, setRoom] = useState(null)
  const [loading, setLoading] = useState(true)
  const [joining, setJoining] = useState(false)
  const [username, setUsername] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [error, setError] = useState(null)
  const [alreadyMember, setAlreadyMember] = useState(false)

  useEffect(() => {
    loadRoom()
    
    // 如果已登录，使用登录用户的名称
    if (isAuthenticated && user) {
      setUsername(user.display_name || user.username)
    } else {
      // 否则检查是否已有保存的用户名
      const savedUsername = localStorage.getItem('patpat_username')
      if (savedUsername) {
        setUsername(savedUsername)
      }
    }
  }, [roomId, isAuthenticated, user])

  const loadRoom = async () => {
    setLoading(true)
    try {
      const data = await getRoom(roomId)
      setRoom(data)
      
      // 检查已登录用户是否已在房间中
      if (isAuthenticated && user && data.members) {
        const userIdToCheck = user.user_id
        const existingMember = data.members[userIdToCheck]
        if (existingMember) {
          // 已是房间成员，直接跳转
          setAlreadyMember(true)
          setTimeout(() => {
            navigate(`/collaborate/${roomId}`)
          }, 500)
          return
        }
      }
    } catch (err) {
      setError('房间不存在或已关闭')
    } finally {
      setLoading(false)
    }
  }

  const handleJoin = async () => {
    if (!username.trim()) {
      setError('请输入您的昵称')
      return
    }

    // 如果房间需要邀请码，检查是否输入
    if (room.has_invite_code && !inviteCode.trim()) {
      setError('该房间需要邀请码才能加入')
      return
    }

    setJoining(true)
    setError(null)
    
    try {
      const result = await joinRoom(
        roomId, 
        username.trim(),
        room.has_invite_code ? inviteCode.trim().toUpperCase() : null
      )
      
      // 保存用户信息（如果后端返回了user_id）
      if (result.user_id) {
        localStorage.setItem('patpat_user_id', result.user_id)
      }
      localStorage.setItem('patpat_username', username.trim())
      
      // 检查是否已经是成员
      if (result.already_member) {
        setAlreadyMember(true)
        // 延迟跳转，让用户看到提示
        setTimeout(() => {
          navigate(`/collaborate/${roomId}`)
        }, 1000)
      } else {
        // 跳转到房间
        navigate(`/collaborate/${roomId}`)
      }
    } catch (err) {
      setError(err.message || '加入房间失败')
    } finally {
      setJoining(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleJoin()
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-primary-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">正在加载房间信息...</p>
        </div>
      </div>
    )
  }

  if (!room) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-primary-50">
        <div className="card p-8 text-center max-w-md">
          <div className="w-16 h-16 bg-danger-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Users className="w-8 h-8 text-danger-600" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 mb-2">房间不存在</h2>
          <p className="text-slate-600 mb-6">该房间可能已关闭或链接无效</p>
          <button onClick={() => navigate('/collaborate')} className="btn-primary">
            返回协作空间
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 bg-gradient-to-br from-slate-50 via-white to-primary-50">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-8 w-full max-w-md"
      >
        {/* 房间信息 */}
        <div className="text-center mb-8">
          <div className={`w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center ${
            room.mode === 'realtime' 
              ? 'bg-primary-100 text-primary-600' 
              : 'bg-accent-100 text-accent-600'
          }`}>
            {room.mode === 'realtime' ? (
              <Users className="w-8 h-8" />
            ) : (
              <Lock className="w-8 h-8" />
            )}
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mb-2">
            {room.room_name}
          </h1>
          <p className="text-slate-500">{room.document_title}</p>
          {room.description && (
            <p className="text-sm text-slate-400 mt-2">{room.description}</p>
          )}
          <div className="flex items-center justify-center gap-4 mt-4 text-sm text-slate-500">
            <span className={`badge ${room.mode === 'realtime' ? 'badge-primary' : 'bg-accent-100 text-accent-700'}`}>
              {room.mode === 'realtime' ? '实时协同' : '分章节锁定'}
            </span>
            <span>
              <Users className="w-4 h-4 inline mr-1" />
              {room.online_count} 人在线
            </span>
            {room.has_invite_code && (
              <span className="flex items-center gap-1 text-warning-600">
                <Key className="w-4 h-4" />
                需要邀请码
              </span>
            )}
          </div>
        </div>

        {/* 输入表单 */}
        <div className="space-y-4">
          {/* 昵称输入 */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              您的昵称
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                className="input pl-10"
                placeholder="例如：张三"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyPress={handleKeyPress}
                autoFocus={!room.has_invite_code}
              />
            </div>
          </div>

          {/* 邀请码输入（如果需要） */}
          {room.has_invite_code && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                <div className="flex items-center gap-2">
                  <Key className="w-4 h-4 text-warning-600" />
                  邀请码
                </div>
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  className="input pl-10 uppercase tracking-widest text-center font-mono"
                  placeholder="请输入邀请码"
                  maxLength={8}
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                  onKeyPress={handleKeyPress}
                  autoFocus={room.has_invite_code}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                请向房主获取邀请码
              </p>
            </div>
          )}

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 bg-danger-50 text-danger-700 rounded-lg text-sm flex items-center gap-2"
            >
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              {error}
            </motion.div>
          )}

          {alreadyMember && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 bg-success-50 text-success-700 rounded-lg text-sm flex items-center gap-2"
            >
              <CheckCircle className="w-5 h-5" />
              您已是房间成员，正在重新连接...
            </motion.div>
          )}
          
          {/* 已登录提示 */}
          {isAuthenticated && (
            <div className="p-3 bg-primary-50 text-primary-700 rounded-lg text-sm">
              已使用账号 <strong>@{user?.username}</strong> 登录，将以此身份加入房间
            </div>
          )}

          <button
            onClick={handleJoin}
            className="btn-primary w-full"
            disabled={joining || !username.trim() || (room.has_invite_code && !inviteCode.trim())}
          >
            {joining ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                加入中...
              </>
            ) : (
              <>
                加入房间
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>

        {/* 当前成员 */}
        {Object.keys(room.members).length > 0 && (
          <div className="mt-8 pt-6 border-t border-slate-100">
            <p className="text-sm text-slate-500 mb-3">当前成员</p>
            <div className="flex flex-wrap gap-2">
              {Object.values(room.members).map((member) => (
                <div
                  key={member.user_id}
                  className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-full text-sm"
                >
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-medium"
                    style={{ backgroundColor: member.color }}
                  >
                    {member.username.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-slate-700">{member.username}</span>
                  {member.is_online && (
                    <span className="w-2 h-2 bg-success-500 rounded-full" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}

export default JoinRoomPage
