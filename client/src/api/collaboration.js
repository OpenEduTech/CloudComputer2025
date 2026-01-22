/**
 * PatPat-Inconsistency-Hunter 协作API客户端
 * 处理协作相关的所有API请求
 */

const API_BASE = '/api/collaboration'

/**
 * 获取认证token
 */
function getAuthToken() {
  return localStorage.getItem('patpat_access_token')
}

/**
 * 统一请求处理
 */
async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  const headers = {
    'Content-Type': 'application/json',
  }
  
  // 添加认证token
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  const config = {
    headers,
    ...options,
  }

  const response = await fetch(url, config)
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `请求失败: ${response.status}`)
  }

  return response.json()
}

// ==================== 房间管理 ====================

/**
 * 创建协作房间
 * @param {Object} data - 房间数据
 * @param {string} data.room_name - 房间名称
 * @param {string} data.mode - 协作模式 (realtime | chapter_lock)
 * @param {string} data.document_title - 文档标题
 * @param {string} data.initial_content - 初始内容
 * @param {string} data.owner_name - 房主名称
 */
export async function createRoom(data) {
  return fetchAPI('/rooms', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * 获取房间列表
 * @param {number} limit - 返回数量限制
 */
export async function listRooms(limit = 20) {
  return fetchAPI(`/rooms?limit=${limit}`)
}

/**
 * 获取房间详情
 * @param {string} roomId - 房间ID
 */
export async function getRoom(roomId) {
  return fetchAPI(`/rooms/${roomId}`)
}

/**
 * 加入房间
 * @param {string} roomId - 房间ID
 * @param {string} username - 用户名
 * @param {string} inviteCode - 邀请码（可选）
 */
export async function joinRoom(roomId, username, inviteCode = null) {
  const payload = { username }
  if (inviteCode) {
    payload.invite_code = inviteCode
  }
  return fetchAPI(`/rooms/${roomId}/join`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * 获取当前用户的文档列表
 * 用于创建房间时选择已有文档
 */
export async function getUserDocuments() {
  return fetchAPI('/user/documents')
}

/**
 * 离开房间
 * @param {string} roomId - 房间ID
 * @param {string} userId - 用户ID
 */
export async function leaveRoom(roomId, userId) {
  return fetchAPI(`/rooms/${roomId}/leave?user_id=${userId}`, {
    method: 'POST',
  })
}

/**
 * 更新房间内容
 * @param {string} roomId - 房间ID
 * @param {string} content - 新内容
 * @param {string} userId - 用户ID
 * @param {Object|null} contentJson - 富文本JSON
 */
export async function updateContent(roomId, content, userId, contentJson = null) {
  return fetchAPI(`/rooms/${roomId}/content`, {
    method: 'PUT',
    body: JSON.stringify({
      content,
      user_id: userId,
      content_json: contentJson,
    }),
  })
}

/**
 * 更新章节内容
 * @param {string} roomId - 房间ID
 * @param {string} chapterId - 章节ID
 * @param {string} content - 新内容
 * @param {string} userId - 用户ID
 */
export async function updateChapterContent(roomId, chapterId, content, userId) {
  return fetchAPI(`/rooms/${roomId}/chapters/${chapterId}`, {
    method: 'PUT',
    body: JSON.stringify({ chapter_id: chapterId, content, user_id: userId }),
  })
}

// ==================== 章节锁定 ====================

/**
 * 获取章节锁
 * @param {string} roomId - 房间ID
 * @param {string} chapterId - 章节ID
 * @param {string} userId - 用户ID
 * @param {string} username - 用户名
 * @param {number} duration - 锁定时长（秒）
 */
export async function acquireLock(roomId, chapterId, userId, username, duration = 300) {
  return fetchAPI(`/rooms/${roomId}/locks`, {
    method: 'POST',
    body: JSON.stringify({
      chapter_id: chapterId,
      user_id: userId,
      username: username,
      duration: duration,
    }),
  })
}

/**
 * 释放章节锁
 * @param {string} roomId - 房间ID
 * @param {string} chapterId - 章节ID
 * @param {string} userId - 用户ID
 */
export async function releaseLock(roomId, chapterId, userId) {
  return fetchAPI(`/rooms/${roomId}/locks/${chapterId}?user_id=${userId}`, {
    method: 'DELETE',
  })
}

/**
 * 获取房间所有锁
 * @param {string} roomId - 房间ID
 */
export async function getRoomLocks(roomId) {
  return fetchAPI(`/rooms/${roomId}/locks`)
}

// ==================== 房主权限管理 ====================

/**
 * 更新房间设置（仅房主）
 * @param {string} roomId - 房间ID
 * @param {Object} settings - 设置数据
 */
export async function updateRoomSettings(roomId, settings) {
  return fetchAPI(`/rooms/${roomId}/settings`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  })
}

/**
 * 为用户分配章节编辑权限（仅房主）
 * @param {string} roomId - 房间ID
 * @param {string} chapterId - 章节ID
 * @param {string} userId - 目标用户ID
 * @param {boolean} force - 是否强制分配
 */
export async function assignChapter(roomId, chapterId, userId, force = false) {
  return fetchAPI(`/rooms/${roomId}/assign-chapter`, {
    method: 'POST',
    body: JSON.stringify({
      chapter_id: chapterId,
      user_id: userId,
      force: force,
    }),
  })
}

/**
 * 取消用户章节编辑权限（仅房主）
 * @param {string} roomId - 房间ID
 * @param {string} chapterId - 章节ID
 * @param {string|null} userId - 目标用户ID（可选）
 */
export async function unassignChapter(roomId, chapterId, userId = null) {
  return fetchAPI(`/rooms/${roomId}/unassign-chapter`, {
    method: 'POST',
    body: JSON.stringify({
      chapter_id: chapterId,
      user_id: userId,
    }),
  })
}

/**
 * 添加新章节（仅房主）
 * @param {string} roomId - 房间ID
 * @param {string} title - 章节标题
 * @param {string} content - 章节内容
 * @param {number} position - 插入位置
 */
export async function addChapter(roomId, title, content = '', position = null) {
  return fetchAPI(`/rooms/${roomId}/chapters`, {
    method: 'POST',
    body: JSON.stringify({ title, content, position }),
  })
}

/**
 * 删除章节（仅房主）
 * @param {string} roomId - 房间ID
 * @param {string} chapterId - 章节ID
 */
export async function deleteChapter(roomId, chapterId) {
  return fetchAPI(`/rooms/${roomId}/chapters/${chapterId}`, {
    method: 'DELETE',
  })
}

/**
 * 获取房间成员列表
 * @param {string} roomId - 房间ID
 */
export async function getRoomMembers(roomId) {
  return fetchAPI(`/rooms/${roomId}/members`)
}

// ==================== 冲突检测 ====================

/**
 * 触发冲突检测
 * @param {string} roomId - 房间ID
 * @param {boolean} force - 是否强制检测
 * @param {string|null} content - 可选：用于检测的临时内容（不落库）
 */
export async function triggerDetection(roomId, force = false, content = null) {
  const options = {
    method: 'POST',
  }

  if (content !== null && content !== undefined) {
    options.body = JSON.stringify({ content })
  }

  return fetchAPI(`/rooms/${roomId}/detect?force=${force}`, options)
}

/**
 * 获取房间冲突
 * @param {string} roomId - 房间ID
 */
export async function getRoomConflicts(roomId) {
  return fetchAPI(`/rooms/${roomId}/conflicts`)
}

/**
 * 获取房间检测状态
 * @param {string} roomId - 房间ID
 */
export async function getDetectionStatus(roomId) {
  return fetchAPI(`/rooms/${roomId}/detection/status`)
}

/**
 * 取消房间检测
 * @param {string} roomId - 房间ID
 */
export async function cancelDetection(roomId) {
  return fetchAPI(`/rooms/${roomId}/detection/cancel`, {
    method: 'POST',
  })
}

// ==================== 房间管理 API ====================

/**
 * 结束房间
 * @param {string} roomId - 房间ID
 * @param {boolean} runDetection - 是否在结束前进行冲突检测
 */
export async function endRoom(roomId, runDetection = false) {
  return fetchAPI(`/rooms/${roomId}/end`, {
    method: 'POST',
    body: JSON.stringify({ run_detection: runDetection }),
  })
}

/**
 * 导出房间文档
 * @param {string} roomId - 房间ID
 * @param {string} format - 导出格式 (md, html, txt, docx, pdf)
 * @param {boolean} includeAnalysis - 是否包含冲突和事实分析结果
 */
export async function exportRoomDocument(roomId, format = 'md', includeAnalysis = false) {
  return fetchAPI(`/rooms/${roomId}/export?format=${format}&include_analysis=${includeAnalysis}`)
}

/**
 * 踢出成员
 * @param {string} roomId - 房间ID
 * @param {string} userId - 要踢出的用户ID
 * @param {string} reason - 踢出原因
 */
export async function kickMember(roomId, userId, reason = '') {
  return fetchAPI(`/rooms/${roomId}/kick`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, reason }),
  })
}

// ==================== WebSocket工具类 ====================

/**
 * 协作WebSocket客户端
 */
export class CollaborationWebSocket {
  constructor(roomId, userId, username) {
    this.roomId = roomId
    this.userId = userId
    this.username = username
    this.ws = null
    this.handlers = {}
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
  }

  /**
   * 连接WebSocket
   */
  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}${API_BASE}/ws/${this.roomId}/${this.userId}/${encodeURIComponent(this.username)}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('协作WebSocket连接成功')
      this.reconnectAttempts = 0
      this._emit('connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        this._emit(message.type, message.data)
        this._emit('message', message)
      } catch (e) {
        console.error('解析消息失败:', e)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
      this._emit('error', error)
    }

    this.ws.onclose = () => {
      console.log('WebSocket连接关闭')
      this._emit('disconnected')
      this._tryReconnect()
    }
  }

  /**
   * 尝试重连
   */
  _tryReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      console.log(`将在 ${delay}ms 后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      setTimeout(() => this.connect(), delay)
    }
  }

  /**
   * 发送消息
   */
  send(type, data = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type,
        room_id: this.roomId,
        user_id: this.userId,
        data,
      }))
    }
  }

  /**
   * 发送内容更新
   */
  sendContentUpdate(content) {
    this.send('content_update', { content })
  }

  /**
   * 发送光标更新
   */
  sendCursorUpdate(position, selectionStart = null, selectionEnd = null) {
    this.send('cursor_update', { position, selection_start: selectionStart, selection_end: selectionEnd })
  }

  /**
   * 发送心跳
   */
  sendPing() {
    this.send('ping')
  }

  /**
   * 注册事件处理器
   */
  on(event, handler) {
    if (!this.handlers[event]) {
      this.handlers[event] = []
    }
    this.handlers[event].push(handler)
    return () => this.off(event, handler)
  }

  /**
   * 移除事件处理器
   */
  off(event, handler) {
    if (this.handlers[event]) {
      this.handlers[event] = this.handlers[event].filter(h => h !== handler)
    }
  }

  /**
   * 触发事件
   */
  _emit(event, data) {
    if (this.handlers[event]) {
      this.handlers[event].forEach(handler => handler(data))
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.maxReconnectAttempts = 0 // 阻止重连
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

export default {
  createRoom,
  listRooms,
  getRoom,
  joinRoom,
  leaveRoom,
  updateContent,
  updateChapterContent,
  acquireLock,
  releaseLock,
  getRoomLocks,
  triggerDetection,
  getRoomConflicts,
  updateRoomSettings,
  assignChapter,
  addChapter,
  deleteChapter,
  getRoomMembers,
  endRoom,
  exportRoomDocument,
  kickMember,
  CollaborationWebSocket,
}

