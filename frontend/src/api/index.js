import apiClient from './client'

/**
 * 上传PPT文件
 */
export const uploadPPT = (file, userId = 'default') => {
  const formData = new FormData()
  formData.append('file', file)
  
  return apiClient.post('/ppt/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    params: { user_id: userId },
  })
}

/**
 * 解析PPT
 */
export const parsePPT = (fileId, userId = 'default') => {
  return apiClient.get(`/ppt/parse/${fileId}`, {
    params: { user_id: userId },
  })
}

/**
 * 删除PPT
 */
export const deletePPT = (fileId) => {
  return apiClient.delete(`/ppt/${fileId}`)
}

/**
 * 扩充知识
 */
export const expandKnowledge = (data) => {
  return apiClient.post('/knowledge/expand', data)
}

/**
 * 获取PPT解析历史
 */
export const getPptHistory = (userId = 'default', limit = 20) => {
  return apiClient.get('/ppt/history', {
    params: { user_id: userId, limit },
  })
}

/**
 * 获取知识扩充历史
 */
export const getKnowledgeHistory = (userId = 'default', limit = 20) => {
  return apiClient.get('/knowledge/history', {
    params: { user_id: userId, limit },
  })
}

/**
 * 语义搜索
 */
export const searchKnowledge = (fileId, query, topK = 5) => {
  return apiClient.post('/knowledge/search', null, {
    params: { file_id: fileId, query, top_k: topK },
  })
}

/**
 * 外部权威资源搜索
 */
export const externalSearch = (query) => {
  return apiClient.get('/knowledge/external-search', {
    params: { query },
  })
}

/**
 * 生成题目
 */
export const generateQuestions = (data) => {
  return apiClient.post('/questions/generate', data)
}

/**
 * 评估答案
 */
export const evaluateAnswer = (data) => {
  return apiClient.post('/questions/evaluate', data)
}

/**
 * 获取错题列表
 */
export const getMistakes = (limit = 20, userId = 'default') => {
  return apiClient.get('/mistakes/list', {
    params: { limit, user_id: userId },
  })
}

/**
 * 获取错题统计
 */
export const getMistakeStats = (userId = 'default') => {
  return apiClient.get('/mistakes/stats', {
    params: { user_id: userId },
  })
}

/**
 * 标记为已复习
 */
export const markAsReviewed = (questionId, userId = 'default') => {
  return apiClient.post(`/mistakes/${questionId}/review`, null, {
    params: { user_id: userId },
  })
}

/**
 * 从错题本移除
 */
export const removeMistake = (questionId, userId = 'default') => {
  return apiClient.delete(`/mistakes/${questionId}`, {
    params: { user_id: userId },
  })
}

/**
 * 生成小灶纠偏内容
 */
export const remediateMistake = (data) => {
  return apiClient.post('/mistakes/remediate', data)
}
