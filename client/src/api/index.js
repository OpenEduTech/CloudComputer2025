/**
 * PatPat-Inconsistency-Hunter API 客户端
 * 封装与后端的所有API交互
 */

import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5分钟超时（分析可能需要较长时间）
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 自动添加Authorization header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('patpat_access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

/**
 * 健康检查
 */
export const checkHealth = () => api.get('/health')

/**
 * 提交文档分析任务
 * @param {Object} data - 请求数据
 * @param {string} data.content - 文档内容
 * @param {string} [data.title] - 文档标题
 * @param {boolean} [data.skip_verification] - 是否跳过验证
 */
export const analyzeDocument = (data) => api.post('/analyze', data)

/**
 * 获取任务状态
 * @param {string} taskId - 任务ID
 */
export const getTaskStatus = (taskId) => api.get(`/task/${taskId}/status`)

/**
 * 获取任务结果
 * @param {string} taskId - 任务ID
 */
export const getTaskResult = (taskId) => api.get(`/task/${taskId}/result`)

/**
 * 获取事实列表
 * @param {string} taskId - 任务ID
 * @param {Object} [params] - 查询参数
 */
export const getTaskFacts = (taskId, params = {}) => 
  api.get(`/task/${taskId}/facts`, { params })

/**
 * 获取冲突列表
 * @param {string} taskId - 任务ID
 * @param {Object} [params] - 查询参数
 */
export const getTaskConflicts = (taskId, params = {}) => 
  api.get(`/task/${taskId}/conflicts`, { params })

/**
 * 删除任务
 * @param {string} taskId - 任务ID
 */
export const deleteTask = (taskId) => api.delete(`/task/${taskId}`)

/**
 * 获取统计概览
 */
export const getStatsOverview = () => api.get('/stats/overview')

/**
 * 获取详细统计数据（用于仪表盘图表）
 */
export const getStatsDetailed = () => api.get('/stats/detailed')

/**
 * 获取用户仪表盘统计数据
 */
export const getUserDashboardStats = () => api.get('/user/dashboard-stats')

/**
 * 获取用户分析历史
 */
export const getUserAnalysisHistory = () => api.get('/user/analysis-history')

/**
 * 删除分析记录
 * @param {string} taskId - 任务ID
 */
export const deleteAnalysisRecord = (taskId) => api.delete(`/task/${taskId}`)

/**
 * 更新用户资料
 * @param {Object} data - 用户资料数据
 */
export const updateUserProfile = (data) => api.put('/auth/profile', data)

/**
 * 上传用户头像
 * @param {File} file - 图片文件
 */
export const uploadAvatar = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const token = localStorage.getItem('patpat_access_token')
  const response = await fetch('/api/auth/avatar', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  })
  
  if (!response.ok) {
    const data = await response.json()
    throw new Error(data.detail || '头像上传失败')
  }
  
  return response.json()
}

/**
 * 上传文档图片
 * @param {File} file - 图片文件
 * @param {string} [documentId] - 关联的文档ID
 * @param {string} [roomId] - 关联的房间ID
 */
/**
 * 解析文档文件（支持富文本格式）
 * @param {File} file - 文件对象
 * @returns {Promise<{content, content_json, title}>} 解析结果
 */
export const parseDocumentFile = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  
  // 获取 token 以支持图片上传（需要用户认证）
  const token = localStorage.getItem('patpat_access_token')
  const headers = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  const response = await fetch('/api/parse-document', {
    method: 'POST',
    headers,
    body: formData,
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || '解析文件失败')
  }
  
  return await response.json()
}

export const uploadDocumentImage = async (file, documentId = null, roomId = null) => {
  const formData = new FormData()
  formData.append('file', file)
  if (documentId) {
    formData.append('document_id', documentId)
  }
  if (roomId) {
    formData.append('room_id', roomId)
  }
  
  const token = localStorage.getItem('patpat_access_token')
  const response = await fetch('/api/documents/images/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  })
  
  if (!response.ok) {
    const data = await response.json()
    throw new Error(data.detail || '图片上传失败')
  }
  
  return response.json()
}

/**
 * 获取文档原文（带分块信息）
 * @param {string} taskId - 任务ID
 */
export const getDocumentContent = (taskId) => api.get(`/task/${taskId}/document`)

/**
 * 导出分析报告（包含完整冲突列表和事实列表）
 * @param {string} taskId - 任务ID
 * @param {string} format - 导出格式 (json/markdown/md/pdf/docx/txt)
 */
export const exportReport = async (taskId, format = 'markdown') => {
  const response = await fetch(`/api/task/${taskId}/export?format=${format}`)
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || '导出失败')
  }
  return response
}

/**
 * 导出任务文档原文（支持富文本格式）
 * @param {string} taskId - 任务ID
 * @param {string} format - 导出格式 (txt/md/pdf/docx)
 */
export const exportTaskDocument = async (taskId, format = 'txt') => {
  const response = await fetch(`/api/task/${taskId}/document/export?format=${format}`)
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || '导出失败')
  }
  return response
}

/**
 * 更新任务文档内容（保存编辑后的文档）
 * @param {string} taskId - 任务ID
 * @param {Object} data - 文档数据
 * @param {string} data.content - 文档纯文本内容
 * @param {Object} [data.content_json] - 文档富文本JSON格式
 * @param {string} [data.title] - 文档标题
 */
export const updateTaskDocument = (taskId, data) => 
  api.put(`/task/${taskId}/document`, data)

/**
 * 重新分析任务文档（检测冲突）
 * @param {string} taskId - 任务ID
 */
export const reanalyzeTaskDocument = (taskId) => 
  api.post(`/task/${taskId}/reanalyze`)

/**
 * 创建WebSocket连接获取实时进度
 * @param {string} taskId - 任务ID
 * @param {Function} onMessage - 消息回调
 * @param {Function} onError - 错误回调
 * @param {Function} onClose - 关闭回调
 */
export const createProgressWebSocket = (taskId, onMessage, onError, onClose) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/task/${taskId}/progress`)
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage?.(data)
    } catch (e) {
      console.error('WebSocket消息解析失败:', e)
    }
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket错误:', error)
    onError?.(error)
  }
  
  ws.onclose = () => {
    onClose?.()
  }
  
  return ws
}

export default api

