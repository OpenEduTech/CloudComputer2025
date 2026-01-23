<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { pptApi } from '../api/index.js'
import MindmapGraph from './MindmapGraph.vue'
import SemanticSearch from './SemanticSearch.vue'
import ExternalSearch from './ExternalSearch.vue'

const props = defineProps({
  slide: Object,
  activeTool: String,
  mindmap: Object,
  mindmapLoading: Boolean,
  mindmapError: String,
  isAnalyzing: Boolean,  
  docId: String
})

const emit = defineEmits(['select-slide', 'load-document'])

const chatMessages = ref([])
const userChatInput = ref('')
const isChatting = ref(false)
const messagesContainer = ref(null)
const isInitializingChat = ref(false)

const isLoadingKeywords = ref(false)

const searchQuery = ref('')
const isSearching = ref(false)
const searchResults = ref([])
const searchType = ref('all')

const analysisStages = ref({
  clustering: { name: '知识聚类', completed: false, message: '' },
  understanding: { name: '生成学习笔记', completed: false, message: '' },
  gaps: { name: '识别知识缺口', completed: false, message: '' },
  expansion: { name: '补充说明', completed: false, message: '' },
  retrieval: { name: '搜索参考资料', completed: false, message: '' },
  complete: { name: '分析完成', completed: false, message: '' }
})

const shouldShowAIAnalysis = ref(false)  
const isAnalyzingPage = ref(false)  

const markdownToHtml = (markdown) => {
  if (!markdown) return ''
  
  let html = markdown
  
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  
  html = html.replace(/^#### (.*)$/gm, '<h4>$1</h4>')
  html = html.replace(/^### (.*)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.*)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.*)$/gm, '<h1>$1</h1>')
  
  html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
  
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  
  html = html.replace(/(?<!\n)\*([^*\n]+?)\*(?!\*)/g, '<em>$1</em>')
  
  html = html.replace(/~~(.*?)~~/g, '<del>$1</del>')
  
  html = html.replace(/^> (.*)$/gm, '<blockquote>$1</blockquote>')
  
  html = html.replace(/^[\*\-\+] (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)(?=\s*<li>|$)/gs, (match) => {
    if (match.includes('<ul>')) return match
    return '<ul>' + match + '</ul>'
  })
  
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
  
  html = html.replace(/^---$/gm, '<hr>')
  html = html.replace(/^\*\*\*$/gm, '<hr>')
  
  html = html.split('\n\n').map(para => {
    if (para.match(/^<[h|u|o|p|b|d|h]/)) {
      return para
    }
    para = para.trim()
    if (!para) return ''
    return '<p>' + para + '</p>'
  }).join('')
  
  html = html.replace(/\n/g, '<br>')
  
  return html
}


// 监听 slide 变化，重置 AI 分析状态
watch(() => props.slide?.page_num, () => {
  shouldShowAIAnalysis.value = false
})

const initChat = async () => {
  if (!props.slide?.page_num) {
    console.warn('⚠️ 无法初始化聊天：页面信息缺失')
    return
  }
  
  console.log('🔄 初始化聊天，页面:', props.slide.page_num, props.slide.title)
  
  try {
    isInitializingChat.value = true
    
    console.log('📞 调用单页设置上下文接口，page_id:', props.slide.page_num)
    const contextResponse = await pptApi.setTutorContext(
      props.slide.page_num,
      props.slide.title || '',
      props.slide.raw_content || props.slide.content || '',
      props.slide.key_concepts || [],
      props.slide.deep_analysis || ''
    )
    
    if (contextResponse.data?.cached) {
      console.log('✅ 上下文已存在（批量设置已完成），后端已跳过重复设置')
    } else {
      console.log('⚠️ 上下文不存在，已单独设置:', contextResponse.data?.message)
    }
    
    const greeting = contextResponse.data?.greeting || 
                     contextResponse.data?.data?.greeting ||
                     `你好!我是基于当前 PPT 的助教。关于 "${props.slide.title}" 你有什么疑问吗？`
    
    chatMessages.value = [
      {
        role: 'assistant',
        content: greeting,
        timestamp: new Date().toISOString()
      }
    ]
    
    console.log('✅ 聊天初始化完成')
    
  } catch (error) {
    console.error('❌ 初始化聊天失败:', error)
    
    chatMessages.value = [
      {
        role: 'assistant',
        content: `⚠️ 初始化失败: ${error.message || '未知错误'}。请检查后端连接。`,
        timestamp: new Date().toISOString()
      }
    ]
  } finally {
    isInitializingChat.value = false
  }
}


const triggerAIAnalysis = async (force = false) => {
  if (!props.slide?.page_num) return
  
  force = Boolean(force)
  
  console.log('🎯 triggerAIAnalysis 被调用:', { 
    force, 
    forceType: typeof force,
    page_num: props.slide.page_num,
    stackTrace: new Error().stack?.split('\n').slice(0, 5).join('\n')
  })
  
  shouldShowAIAnalysis.value = true
  
  if (force) {
    console.log('🔄 用户触发强制重新分析，页面 ' + props.slide.page_num)
    props.slide.deep_analysis = ''
    props.slide.deep_analysis_html = ''
    props.slide.knowledge_clusters = []
    props.slide.knowledge_gaps = []
    props.slide.expanded_content = []
    props.slide.references = []
    Object.keys(analysisStages.value).forEach(stage => {
      analysisStages.value[stage].completed = false
      analysisStages.value[stage].message = ''
    })
    analyzePageWithAI(true)
    return
  }
  
  const slide = props.slide
  
  if (!slide) {
    console.warn('⚠️ slide 对象为空，无法进行分析')
    return
  }
  
  if (props.docId && slide.page_num) {
    console.log('🔍 有 docId，先尝试从后端获取缓存（确保数据完整性）...')
    try {
      const cachedRes = await pptApi.getPageAnalysis(props.docId, slide.page_num)
      const cachedData = cachedRes.data?.data
      console.log('📦 后端返回的缓存数据:', {
        hasData: !!cachedData,
        hasUnderstandingNotes: !!(cachedData?.understanding_notes),
        hasDeepAnalysis: !!(cachedData?.deep_analysis),
        understandingNotesLength: cachedData?.understanding_notes?.length || 0,
        deepAnalysisLength: cachedData?.deep_analysis?.length || 0
      })
      if (cachedData && (cachedData.understanding_notes || cachedData.deep_analysis)) {
        console.log('✅ 从后端获取到缓存分析结果，合并到 slide 对象')
        const understandingNotes = cachedData.understanding_notes || cachedData.deep_analysis || ''
        const deepAnalysis = cachedData.deep_analysis || understandingNotes || ''
        Object.assign(slide, {
          ...cachedData,
          understanding_notes: understandingNotes,
          deep_analysis: deepAnalysis,
          deep_analysis_html: deepAnalysis ? markdownToHtml(deepAnalysis) : ''
        })
        // 更新分析阶段状态
        Object.keys(analysisStages.value).forEach(stage => {
          if (stage === 'complete') {
            analysisStages.value[stage].completed = true
            analysisStages.value[stage].message = '分析已完成'
          }
        })
        console.log('✅ 缓存数据已合并到 slide 对象，直接显示，不重新分析')
        return
      } else {
        console.log('⚠️ 后端返回的缓存数据为空或不完整')
      }
    } catch (err) {
      console.warn('⚠️ 从后端获取缓存失败:', err.message)
    }
  }
  
  const deepAnalysis = slide.deep_analysis || slide.understanding_notes || ''
  const hasDeepAnalysis = deepAnalysis && 
                          typeof deepAnalysis === 'string' &&
                          !deepAnalysis.includes('❌') &&
                          deepAnalysis.trim().length > 0
  
  const hasOtherAnalysis = (slide.knowledge_clusters && Array.isArray(slide.knowledge_clusters) && slide.knowledge_clusters.length > 0) ||
                          (slide.knowledge_gaps && Array.isArray(slide.knowledge_gaps) && slide.knowledge_gaps.length > 0) ||
                          (slide.expanded_content && Array.isArray(slide.expanded_content) && slide.expanded_content.length > 0) ||
                          (slide.references && Array.isArray(slide.references) && slide.references.length > 0)
  
  const hasAnalysis = hasDeepAnalysis || hasOtherAnalysis
  
  console.log('🔍 检查分析结果:', {
    page_num: slide.page_num,
    hasDeepAnalysis,
    hasOtherAnalysis,
    hasAnalysis,
    deep_analysis: deepAnalysis ? (typeof deepAnalysis === 'string' ? deepAnalysis.substring(0, 50) + '...' : '非字符串') : '无',
    deep_analysis_type: typeof slide.deep_analysis,
    understanding_notes_type: typeof slide.understanding_notes,
    knowledge_clusters: slide.knowledge_clusters?.length || 0,
    knowledge_gaps: slide.knowledge_gaps?.length || 0,
    expanded_content: slide.expanded_content?.length || 0,
    references: slide.references?.length || 0,
    slide_keys: Object.keys(slide),
    docId: props.docId
  })
  
  if (hasAnalysis) {
    console.log('✅ 已有分析结果，直接显示，不重新分析')
    if (slide.understanding_notes && !slide.deep_analysis) {
      slide.deep_analysis = slide.understanding_notes
      slide.deep_analysis_html = markdownToHtml(slide.understanding_notes)
    }
    Object.keys(analysisStages.value).forEach(stage => {
      if (stage === 'complete') {
        analysisStages.value[stage].completed = true
        analysisStages.value[stage].message = '分析已完成'
      }
    })
    return
  }
  
  if (!hasAnalysis && props.docId && slide.page_num) {
    console.log('🔍 前端未检测到分析结果，但有 docId，尝试从后端获取缓存...')
    try {
      const cachedRes = await pptApi.getPageAnalysis(props.docId, slide.page_num)
      const cachedData = cachedRes.data?.data
      console.log('📦 后端返回的缓存数据:', {
        hasData: !!cachedData,
        hasUnderstandingNotes: !!(cachedData?.understanding_notes),
        hasDeepAnalysis: !!(cachedData?.deep_analysis),
        understandingNotesLength: cachedData?.understanding_notes?.length || 0,
        deepAnalysisLength: cachedData?.deep_analysis?.length || 0
      })
      if (cachedData && (cachedData.understanding_notes || cachedData.deep_analysis)) {
        console.log('✅ 从后端获取到缓存分析结果，直接使用')
        // 将缓存数据合并到 slide 对象
        const understandingNotes = cachedData.understanding_notes || cachedData.deep_analysis || ''
        const deepAnalysis = cachedData.deep_analysis || understandingNotes || ''
        // 直接修改 props.slide 的属性，保持响应式
        Object.assign(slide, {
          ...cachedData,
          understanding_notes: understandingNotes,
          deep_analysis: deepAnalysis,
          deep_analysis_html: deepAnalysis ? markdownToHtml(deepAnalysis) : ''
        })
        // 更新分析阶段状态
        Object.keys(analysisStages.value).forEach(stage => {
          if (stage === 'complete') {
            analysisStages.value[stage].completed = true
            analysisStages.value[stage].message = '分析已完成'
          }
        })
        console.log('✅ 缓存数据已合并到 slide 对象')
        return
      } else {
        console.log('⚠️ 后端返回的缓存数据为空或不完整')
      }
    } catch (err) {
      console.warn('⚠️ 从后端获取缓存失败，将继续正常分析流程:', err.message)
    }
  }
  
  console.log('⚠️ 未检测到分析结果，将调用 API 进行分析（force=false，后端会检查缓存）')
  
  console.log('🤖 用户触发了 AI 分析，开始分析页面 ' + props.slide.page_num + ' (force=false)')
  analyzePageWithAI(false)
}

const analyzePageWithAI = async (force = false) => {
  const pageId = props.slide.page_num || 1
  
  force = Boolean(force)
  
  console.log('🚀 analyzePageWithAI 被调用:', { 
    pageId, 
    force, 
    forceType: typeof force,
    docId: props.docId,
    hasDeepAnalysis: !!(props.slide?.deep_analysis && props.slide.deep_analysis.trim().length > 0),
    hasUnderstandingNotes: !!(props.slide?.understanding_notes && props.slide.understanding_notes.trim().length > 0),
    stackTrace: new Error().stack?.split('\n').slice(0, 5).join('\n')
  })
  
  try {
    isAnalyzingPage.value = true
    
    Object.keys(analysisStages.value).forEach(stage => {
      analysisStages.value[stage].completed = false
      analysisStages.value[stage].message = ''
    })
    
    const docId = props.docId || null
    console.log('📤 发送流式 AI 分析请求...', {
      pageId,
      docId,
      force: force ? '(强制重新分析)' : '(正常分析，会检查缓存)'
    })
    
    let analysisData = {
      knowledge_clusters: [],
      understanding_notes: '',
      knowledge_gaps: [],
      expanded_content: [],
      references: [],
      page_structure: {}
    }
    
    await pptApi.analyzePageStream(
      pageId,
      props.slide.title || '',
      props.slide.raw_content || '',
      props.slide.raw_points || [],
      (chunk) => {
        // 每收到一个 chunk 就立即更新 UI
        const isCached = chunk.cached === true
        const prefix = isCached ? '📦 [缓存]' : '📨'
        console.log(`${prefix} 收到流式数据:`, chunk.stage, '-', chunk.message)
        
        // 更新阶段状态
        if (analysisStages.value[chunk.stage]) {
          analysisStages.value[chunk.stage].completed = true
          analysisStages.value[chunk.stage].message = chunk.message
        }
        
        if (chunk.stage === 'clustering') {
          // 知识聚类结果
          analysisData.knowledge_clusters = chunk.data || []
          console.log(`${prefix} 知识聚类完成:`, analysisData.knowledge_clusters.length, '个概念')
        } 
        else if (chunk.stage === 'understanding') {
          // 学习笔记
          analysisData.understanding_notes = chunk.data || ''
          console.log(`${prefix} 学习笔记生成完成`)
        }
        else if (chunk.stage === 'gaps') {
          // 知识缺口
          analysisData.knowledge_gaps = chunk.data || []
          console.log(`${prefix} 缺口识别完成:`, analysisData.knowledge_gaps.length, '个缺口')
        }
        else if (chunk.stage === 'expansion') {
          // 知识扩展
          analysisData.expanded_content = chunk.data || []
          console.log(`${prefix} 知识扩展完成:`, analysisData.expanded_content.length, '条补充')
        }
        else if (chunk.stage === 'retrieval') {
          // 参考文献
          analysisData.references = chunk.data || []
          console.log(`${prefix} 参考文献检索完成:`, analysisData.references.length, '条参考')
        }
        else if (chunk.stage === 'complete') {
          // 最终完成
          if (chunk.data) {
            // 如果 complete 阶段有完整数据，直接使用
            analysisData = {
              knowledge_clusters: chunk.data.knowledge_clusters || analysisData.knowledge_clusters,
              understanding_notes: chunk.data.understanding_notes || analysisData.understanding_notes,
              knowledge_gaps: chunk.data.knowledge_gaps || analysisData.knowledge_gaps,
              expanded_content: chunk.data.expanded_content || analysisData.expanded_content,
              references: chunk.data.references || analysisData.references,
              page_structure: chunk.data.page_structure || analysisData.page_structure
            }
          }
          console.log(`${prefix} 分析完全完成`, isCached ? '(来自缓存)' : '(新生成)')
        }
        else if (chunk.stage === 'info') {
          // 信息提示（如强制重新分析的提示）
          console.log('ℹ️', chunk.message)
        }
        
        // 实时更新 slide 对象
        updateSlideWithAnalysis(analysisData)
      },
      docId,
      force
    )
    
  } catch (error) {
    console.error('❌ AI 分析失败:', error)
    props.slide.deep_analysis = `❌ 分析失败: ${error.message || '未知错误'}`
  } finally {
    isAnalyzingPage.value = false
  }
}

const updateSlideWithAnalysis = (analysisData) => {
  if (analysisData.knowledge_clusters !== undefined) {
    props.slide.knowledge_clusters = analysisData.knowledge_clusters || []
  }
  
  if (analysisData.understanding_notes !== undefined) {
    const notes = analysisData.understanding_notes || ''
    props.slide.deep_analysis = notes
    props.slide.deep_analysis_html = notes ? markdownToHtml(notes) : ''
  }
  
  if (analysisData.knowledge_gaps !== undefined) {
    props.slide.knowledge_gaps = analysisData.knowledge_gaps || []
  }
  
  if (analysisData.expanded_content !== undefined) {
    props.slide.expanded_content = analysisData.expanded_content || []
  }
  
  if (analysisData.references !== undefined) {
    props.slide.references = analysisData.references || []
  }
  
  if (analysisData.page_structure !== undefined) {
    props.slide.page_structure = analysisData.page_structure || {}
  }
}


const handleChatKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendChatMessage()
  }
}

// 搜索参考文献
const performSearch = async () => {
  if (!searchQuery.value.trim()) return
  
  isSearching.value = true
  
  try {
    const response = await pptApi.searchReferences(
      searchQuery.value,
      10,
      searchType.value === 'all' ? null : searchType.value
    )
    
    searchResults.value = response.data.references || response.data.data?.references || []
  } catch (error) {
    console.error('搜索失败:', error)
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

const learningObjectives = computed(() => {
  return props.slide?.learning_objectives || []
})

// 关键概念列表
const keyConcepts = computed(() => {
  return props.slide?.key_concepts || []
})

const handleSearch = () => {
  isSearching.value = true
  setTimeout(() => {
    isSearching.value = false
  }, 1000)
}

watch(() => props.slide?.page_num, (newPageNum, oldPageNum) => {
  if (newPageNum !== oldPageNum && newPageNum) {
    initChat()
  }
})

// 监听 activeTool 切换到 chat 时自动滚动到底部
watch(() => props.activeTool, (newTool) => {
  if (newTool === 'chat') {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  }
})


// 发送聊天消息 - 添加更多错误处理
const sendChatMessage = async () => {
  if (!userChatInput.value.trim() || !props.slide) return
  
  const pageId = props.slide.page_num || 1
  const message = userChatInput.value
  
  chatMessages.value.push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  })
  
  userChatInput.value = ''
  isChatting.value = true
  
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
  
  try {
    const response = await pptApi.chat(pageId, message)
    console.log('💬 AI 回复:', response.data)
    
    const aiResponse = response.data.response || 
                       response.data.data?.response || 
                       'AI 助教暂时无法回答'
    
    if (response.data.need_context || response.data.status === 'error') {
      console.warn('⚠️ 需要重新初始化上下文或出现错误，尝试重新初始化...')
      // 移除用户消息和AI错误消息，重新初始化
      chatMessages.value = chatMessages.value.slice(0, -1)
      await initChat()
      await new Promise(resolve => setTimeout(resolve, 500))
      userChatInput.value = message
      await sendChatMessage()
      return
    }
    
    chatMessages.value.push({
      role: 'assistant',
      content: aiResponse,
      timestamp: new Date().toISOString()
    })
    
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
    
  } catch (error) {
    console.error('❌ 聊天失败:', error)
    
    let errorMsg = '❌ 对不起，AI 暂时无法回答。'
    
    if (error.response?.status === 500) {
      errorMsg += '后端服务错误，请查看后端日志。'
    } else if (error.code === 'ECONNABORTED') {
      errorMsg += '请求超时，请稍后重试。'
    } else if (!error.response) {
      errorMsg += '无法连接到后端服务。'
    } else {
      errorMsg += `错误: ${error.message}`
    }
    
    chatMessages.value.push({
      role: 'assistant',
      content: errorMsg,
      timestamp: new Date().toISOString()
    })
  } finally {
    isChatting.value = false
  }
}

// 加载关键词
const loadKeywords = async () => {
  if (!props.slide || !props.slide.page_num) {
    console.warn('⚠️ 无法加载关键词：页面信息缺失')
    return
  }
  
  if (props.slide.keywords && Array.isArray(props.slide.keywords) && props.slide.keywords.length > 0) {
    console.log('✅ 关键词缓存存在，使用已提取的关键词:', props.slide.keywords)
    isLoadingKeywords.value = false
    return
  }
  
  try {
    isLoadingKeywords.value = true
    console.log('🔍 开始加载关键词...', {
      page_num: props.slide.page_num,
      title: props.slide.title,
      content_length: props.slide.raw_content?.length || 0,
      raw_points: props.slide.raw_points?.length || 0
    })
    
    const response = await pptApi.extractKeywords(
      props.slide.page_num,
      props.slide.title || '',
      props.slide.raw_content || '',
      props.slide.raw_points || [],
      5  // 5个关键词
    )
    
    console.log('📦 API响应:', response.data)
    
    if (response.data?.success && response.data?.keywords) {
      // 将关键词保存到slide对象（缓存）
      props.slide.keywords = response.data.keywords
      console.log('✅ 关键词已提取并缓存:', props.slide.keywords)
    } else {
      console.warn('⚠️ 关键词加载返回成功但无数据:', response.data)
      props.slide.keywords = []
    }
  } catch (error) {
    console.error('❌ 关键词加载错误:', error)
    props.slide.keywords = []
  } finally {
    isLoadingKeywords.value = false
  }
}

watch(() => props.slide?.page_num, async (newPageNum, oldPageNum) => {
  if (newPageNum !== oldPageNum && newPageNum) {
    console.log('📄 页面切换:', oldPageNum, '->', newPageNum)
    
    await loadKeywords()
    
    if (props.activeTool === 'chat') {
      await initChat()
    }
  }
})

watch(() => props.activeTool, async (newTool, oldTool) => {
  if (newTool === 'chat' && oldTool !== 'chat') {
    console.log('💬 切换到聊天标签')
    
    if (!chatMessages.value.length) {
      await initChat()
    }
    
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }
})

onMounted(async () => {
  await loadKeywords()
  
  if (props.slide?.page_num && props.activeTool === 'chat') {
    await initChat()
  }
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}
</script>

<template>
  <div class="content-view">
    <div v-if="activeTool === 'explain' && slide" class="view-section">
      <div class="content-header">
        <h2 class="slide-title">{{ slide.title }}</h2>
        <span class="ai-badge">✨ AI 自动扩展</span>
      </div>

      <div class="content-body">
        <div class="card">
          <h3 class="card-title">原始逻辑</h3>
          
          <!-- 关键词加载中提示 -->
          <div v-if="isLoadingKeywords" class="keywords-loading">
            <div class="loading-spinner">⏳</div>
            <div class="loading-text">正在提取关键词，请稍候...</div>
          </div>
          
          <!-- 关键词展示 -->
          <div v-if="!isLoadingKeywords && slide.keywords && slide.keywords.length > 0" class="keywords-section">
            <div class="keywords-label">📌 关键词提取</div>
            <div class="keywords-container">
              <span v-for="(keyword, idx) in slide.keywords" :key="idx" class="keyword-tag">
                {{ keyword }}
              </span>
            </div>
          </div>
          
          <!-- 图片信息展示区域 -->
          <div v-if="slide.images && slide.images.length > 0" class="image-info-section">
            <div class="info-label">🖼️ 幻灯片图像信息:</div>
            <ul class="image-list">
              <li v-for="(imgInfo, index) in slide.images" :key="index" class="image-item">
                {{ imgInfo }}
              </li>
            </ul>
          </div>
        </div>

        <!-- AI 分析触发按钮 -->
        <div class="ai-analysis-trigger">
          <button 
            v-if="!shouldShowAIAnalysis"
            @click.stop="triggerAIAnalysis(false)"
            :disabled="isAnalyzingPage"
            class="btn-analyze-page"
          >
            <span v-if="isAnalyzingPage" class="analyzing-spinner">⏳</span>
            <span v-else>🤖</span>
            {{ isAnalyzingPage ? '正在分析中...' : '使用 AI 深度分析此页面' }}
          </button>
          <button 
            v-else
            @click.stop="shouldShowAIAnalysis = false"
            :disabled="isAnalyzingPage"
            class="btn-analyze-page btn-collapse"
          >
            ⏷ 收起 AI 分析
          </button>
        </div>

        <!-- AI 深度分析 - 仅在用户点击按钮时显示 -->
        <div v-if="shouldShowAIAnalysis" class="ai-analysis-container">
          <!-- 头部操作栏 -->
          <div class="ai-analysis-header">
            <h3 class="ai-analysis-title">
              <span class="ai-icon">🤖</span>
              <span>AI 深度解析</span>
            </h3>
            <div class="ai-analysis-actions">
              <button 
                v-if="props.slide?.deep_analysis && !props.slide.deep_analysis.includes('❌') && !isAnalyzingPage"
                @click.stop="triggerAIAnalysis(true)"
                class="btn-reanalyze"
                title="重新生成AI分析结果"
              >
                🔄 重新分析
              </button>
              <div v-else-if="isAnalyzingPage" class="reanalyze-status">
                <span class="analyzing-spinner">⏳</span>
                <span>分析中...</span>
              </div>
            </div>
          </div>

          <!-- 分析进度显示 -->
          <div v-if="isAnalyzingPage" class="analysis-progress">
            <div class="progress-title">📊 分析进度</div>
            <div class="stages-container">
              <div v-for="(stage, key) in analysisStages" :key="key" class="stage-item">
                <div class="stage-status">
                  <span v-if="stage.completed" class="stage-icon completed">✓</span>
                  <span v-else class="stage-icon pending">◉</span>
                  <span class="stage-name">{{ stage.name }}</span>
                </div>
                <div v-if="stage.message" class="stage-message">{{ stage.message }}</div>
              </div>
            </div>
          </div>

          <!-- 学习目标和关键概念 - 扁平化展示 -->
          <div v-if="learningObjectives.length > 0 || keyConcepts.length > 0" class="ai-metadata">
            <div v-if="learningObjectives.length > 0" class="metadata-item">
              <span class="metadata-label">📚 学习目标</span>
              <ul class="metadata-list">
                <li v-for="(obj, idx) in learningObjectives" :key="idx">{{ obj }}</li>
              </ul>
            </div>
            <div v-if="keyConcepts.length > 0" class="metadata-item">
              <span class="metadata-label">🎯 关键概念</span>
              <div class="metadata-tags">
                <span v-for="concept in keyConcepts" :key="concept" class="tag">{{ concept }}</span>
              </div>
            </div>
          </div>
          
          <!-- 深度解析内容主体 -->
          <div class="ai-content-main">
            <!-- 成功加载的分析内容 -->
            <div v-if="slide.deep_analysis && !slide.deep_analysis.includes('待补充') && !slide.deep_analysis.includes('❌')" class="markdown-body">
              <div v-html="slide.deep_analysis_html || markdownToHtml(slide.deep_analysis)"></div>
            </div>

            <!-- 错误状态 -->
            <div v-else-if="slide.deep_analysis && slide.deep_analysis.includes('❌')" class="error-state">
              <div class="error-icon">⚠️</div>
              <div class="error-content">
                <strong>分析失败</strong>
                <p>{{ slide.deep_analysis }}</p>
                <details class="error-details">
                  <summary>查看错误详情</summary>
                  <pre>{{ slide.deep_analysis }}</pre>
                </details>
              </div>
            </div>

            <!-- 等待分析状态 -->
            <div v-else class="waiting-state">
              <div v-if="props.isAnalyzing" class="waiting-content">
                <div class="waiting-spinner"></div>
                <p class="waiting-text">正在生成 AI 分析...</p>
              </div>
              <div v-else class="waiting-content">
                <div class="waiting-icon">⏳</div>
                <p class="waiting-text">等待 AI 解析...</p>
                <p class="waiting-hint">如果长时间未显示结果，请检查系统连接</p>
              </div>
              
              <!-- 调试信息 - 默认折叠 -->
              <details class="debug-collapsible">
                <summary>🔧 调试信息</summary>
                <div class="debug-content-compact">
                  <div class="debug-row">
                    <span class="debug-label">页面:</span>
                    <span class="debug-value">{{ slide.page_num || '未知' }} - {{ slide.title }}</span>
                  </div>
                  <div class="debug-row">
                    <span class="debug-label">数据状态:</span>
                    <span class="debug-value" :class="!slide.deep_analysis ? 'status-empty' : slide.deep_analysis.includes('待补充') ? 'status-pending' : 'status-ok'">
                      <span v-if="!slide.deep_analysis">LLM尚未回复</span>
                      <span v-else-if="slide.deep_analysis.includes('待补充')">⏳ 待补充</span>
                      <span v-else>✓ 已有内容 ({{ slide.deep_analysis.length }} 字符)</span>
                    </span>
                  </div>
                  <div class="debug-row">
                    <span class="debug-label">服务器:</span>
                    <span class="debug-value code">http://localhost:8000</span>
                  </div>
                </div>
              </details>
            </div>
          </div>
        </div>

        <!-- 参考文献 -->
        <div v-if="slide.references && slide.references.length > 0" class="card references-card">
          <h3 class="card-title">📚 参考文献</h3>
          <div class="references-list">
            <a 
              v-for="(ref, idx) in slide.references" 
              :key="idx" 
              :href="ref.url" 
              target="_blank"
              rel="noopener noreferrer"
              class="reference-link"
            >
              <div class="ref-header">
                <span class="ref-title">{{ ref.title }}</span>
                <span class="ref-source">{{ ref.source }}</span>
              </div>
              <p v-if="ref.snippet" class="ref-snippet">{{ ref.snippet }}</p>
            </a>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTool === 'state-of-art'" class="view-section mindmap-view">
      <div class="mindmap-header">
        <div>
          <div class="content-header">
            <h2 class="slide-title">思维导图</h2>
            <span class="ai-badge">🧠 自动构建</span>
          </div>
          <p class="text-hint">基于整个 PPT 的层级要点生成</p>
        </div>
      </div>

      <div v-if="mindmapLoading" class="mindmap-loading">
        <div class="mini-spinner"></div>
        <p>正在生成思维导图...</p>
      </div>

      <div v-else-if="mindmapError" class="mindmap-error">
        <p>生成失败：{{ mindmapError }}</p>
      </div>

      <div v-else-if="mindmap?.root" class="mindmap-tree-wrapper">
        <MindmapGraph :root="mindmap.root" />
      </div>

      <div v-else class="mindmap-empty">
        <p>暂无思维导图数据，请先上传 PPT。</p>
      </div>
    </div>

    <div v-if="activeTool === 'search'" class="view-section search-view">
      <!-- 语义搜索组件 - 搜索已上传的 PPT/PDF 切片 -->
      <SemanticSearch 
        :current-file-name="slide?.file_name || null"
        @select-slide="emit('select-slide', $event)"
        @load-document="emit('load-document', $event)"
      />
    </div>

    <div v-if="activeTool === 'external-search'" class="view-section external-search-view">
      <!-- 外部资源搜索组件 - 搜索 Wikipedia、Arxiv、Web -->
      <ExternalSearch />
      
      <!-- 保留原有的简单搜索作为备用（可选） -->
      <div v-if="false" class="external-search-section-legacy" style="margin-top: 2rem;">
        <h3 style="margin-bottom: 1rem; color: #1e293b; font-size: 1.1rem;">🌐 外部资源搜索（旧版）</h3>
        <div class="search-bar">
          <input v-model="searchQuery" type="text" placeholder="输入关键词搜索学术资源..." class="search-input" />
          <button @click="handleSearch" class="search-btn">🔍</button>
        </div>

        <div v-if="!isSearching && searchResults.length > 0" class="search-results">
          <div v-for="(result, idx) in searchResults" :key="idx" class="result-item">
            <div :class="['result-source', result.source === 'Wikipedia' ? 'wiki' : '']">{{ result.source }}</div>
            <h4 class="result-title">{{ result.title }}</h4>
            <p class="result-snippet">{{ result.snippet }}</p>
            <a :href="result.url" target="_blank" class="result-link">查看详情 →</a>
          </div>
        </div>

        <div v-if="isSearching" class="loading-state">
          <div class="mini-spinner"></div>
          <p>正在搜索知识库...</p>
        </div>
      </div>
    </div>

    <div v-if="activeTool === 'chat'" class="view-section chat-view">
  <div class="chat-header">
    <h3 class="chat-title">💬 AI 助教对话</h3>
    <p class="chat-subtitle">关于 "{{ slide?.title }}" 的智能问答</p>
  </div>
  
  <div class="chat-container" ref="messagesContainer">
    <div 
      v-for="(msg, idx) in chatMessages" 
      :key="idx" 
      class="message"
      :class="msg.role"
    >
      <span class="avatar">{{ msg.role === 'assistant' ? '🤖' : '👤' }}</span>
      <div class="bubble" :class="{ 'markdown-content': msg.role === 'assistant' }">
        <div v-if="msg.role === 'assistant'" v-html="markdownToHtml(msg.content)"></div>
        <div v-else>{{ msg.content }}</div>
        <span class="timestamp">{{ formatTime(msg.timestamp) }}</span>
      </div>
    </div>
    
    <!-- 正在输入提示 -->
    <div v-if="isChatting" class="message ai typing-indicator">
      <span class="avatar">🤖</span>
      <div class="bubble">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>
  </div>
  
  <div class="chat-input-area">
    <input 
      v-model="userChatInput"
      @keydown="handleChatKeydown"
      :disabled="isChatting || !slide"
      type="text" 
      placeholder="向 AI 提问..." 
      class="chat-input" 
    />
    <button 
      @click="sendChatMessage"
      :disabled="!userChatInput.trim() || isChatting || !slide"
      class="send-btn"
    >
      {{ isChatting ? '发送中...' : '发送' }}
    </button>
  </div>
</div>

  </div>
</template>

<style scoped>
.content-view {
  height: 100%;
  overflow-y: auto;
  padding: 1rem;
  background: #ffffff;
}

.view-section {
  animation: fadeIn 0.3s ease;
  height: 100%;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  border-bottom: 2px solid #f1f5f9;
  padding-bottom: 0.5rem;
}

.slide-title {
  font-size: 1.5rem;
  color: #1e293b;
  margin: 0;
}

.ai-badge {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.content-body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  background: #fff;
}

/* AI 分析容器 - 扁平化设计 */
.ai-analysis-container {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0;
  margin-top: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.ai-analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  background: linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%);
  border-bottom: 1px solid #e2e8f0;
}

.ai-analysis-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.ai-icon {
  font-size: 1.3rem;
}

.ai-analysis-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

/* AI 元数据区域 - 扁平化 */
.ai-metadata {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.metadata-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metadata-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.metadata-list li {
  padding: 0.5rem 0.75rem;
  background: white;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
  color: #334155;
  font-size: 0.9rem;
}

.metadata-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

/* AI 内容主体 */
.ai-content-main {
  padding: 1.5rem;
}

/* 等待状态 - 简化设计 */
.waiting-state {
  text-align: center;
  padding: 2rem 1rem;
}

.waiting-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.waiting-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.waiting-icon {
  font-size: 3rem;
  animation: pulse 2s ease-in-out infinite;
}

.waiting-text {
  font-size: 1.1rem;
  font-weight: 500;
  color: #334155;
  margin: 0;
}

.waiting-hint {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0;
}

/* 错误状态 - 简化设计 */
.error-state {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  border-left: 4px solid #ef4444;
}

.error-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.error-content {
  flex: 1;
}

.error-content strong {
  display: block;
  font-size: 1rem;
  color: #991b1b;
  margin-bottom: 0.5rem;
}

.error-content p {
  margin: 0.5rem 0;
  color: #7f1d1d;
  line-height: 1.6;
}

/* 调试信息 - 紧凑折叠 */
.debug-collapsible {
  margin-top: 1.5rem;
  padding: 0.75rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.debug-collapsible summary {
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748b;
  user-select: none;
  padding: 0.25rem 0;
}

.debug-collapsible summary:hover {
  color: #3b82f6;
}

.debug-content-compact {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.debug-row {
  display: flex;
  gap: 0.75rem;
  font-size: 0.85rem;
  padding: 0.4rem 0;
}

.debug-label {
  font-weight: 600;
  color: #475569;
  min-width: 80px;
  flex-shrink: 0;
}

.debug-value {
  color: #64748b;
  flex: 1;
}

.debug-value.code {
  background: #f1f5f9;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.8rem;
  display: inline-block;
}

.debug-value.status-empty {
  color: #dc2626;
  font-weight: 500;
}

.debug-value.status-pending {
  color: #f59e0b;
  font-weight: 500;
}

.debug-value.status-ok {
  color: #059669;
  font-weight: 500;
}

.card-title {
  font-size: 1rem;
  color: #64748b;
  margin: 0 0 1rem 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.point-list {
  padding-left: 1.2rem;
  color: #475569;
  line-height: 1.8;
}

.image-info-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px dashed #e2e8f0;
}

.info-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.image-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.image-item {
  font-size: 0.85rem;
  color: #059669;
  background: #ecfdf5;
  padding: 4px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
  display: inline-block;
  margin-right: 6px;
}

.markdown-body {
  color: #334155;
  line-height: 1.8;
  word-wrap: break-word;
  padding: 0;
}

.markdown-body strong {
  font-weight: 600;
  color: #1e293b;
}

.markdown-body em {
  font-style: italic;
  color: #475569;
}

.markdown-body ul,
.markdown-body ol {
  margin: 0.75rem 0;
  padding-left: 2rem;
}

.markdown-body li {
  margin: 0.25rem 0;
}

.markdown-body code {
  background: #f1f5f9;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  color: #dc2626;
}

.markdown-body pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  margin: 1rem 0;
}

.markdown-body pre code {
  background: none;
  padding: 0;
  border-radius: 0;
  color: inherit;
  font-size: 0.95em;
}

.markdown-body blockquote {
  border-left: 4px solid #cbd5e1;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #64748b;
  font-style: italic;
}

.ai-analysis-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 移除旧的 analysis-section 样式，使用新的扁平化设计 */

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #0066cc;
  margin: 0 0 0.75rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.objectives-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.objective-item {
  padding: 0.5rem 0.75rem;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #3b82f6;
  color: #334155;
  font-size: 0.9rem;
}

.concepts-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  background: #e0e7ff;
  color: #4338ca;
  padding: 0.35rem 0.9rem;
  border-radius: 16px;
  font-size: 0.85rem;
  border: 1px solid #c7d2fe;
  font-weight: 500;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #999;
  background: #f9fafb;
  border-radius: 6px;
}

.no-data p {
  margin: 0.5rem 0;
  font-size: 0.95rem;
}

.hint {
  color: #666;
  font-size: 0.85rem;
  margin-top: 1rem !important;
}

.hint-list {
  text-align: left;
  display: inline-block;
  color: #666;
  font-size: 0.85rem;
  padding: 0.5rem 1.5rem;
  list-style-type: disc;
}

.hint-list li {
  margin: 0.25rem 0;
}

.debug-info {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #f5f5f5;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.debug-info summary {
  cursor: pointer;
  color: #666;
  font-size: 0.85rem;
  font-weight: 500;
  padding: 0.5rem;
  user-select: none;
}

.debug-info summary:hover {
  color: #0066cc;
}

.debug-info pre {
  margin: 0.75rem 0 0 0;
  padding: 0.75rem;
  background: white;
  border-radius: 4px;
  border: 1px solid #ddd;
  overflow-x: auto;
  font-size: 0.75rem;
  line-height: 1.4;
  color: #333;
  max-height: 200px;
  overflow-y: auto;
}

.references-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  background: #fff;
}

.references-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.reference-link {
  padding: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f9fafb;
  text-decoration: none;
  transition: all 0.2s ease;
  display: block;
  cursor: pointer;
}

.reference-link:hover {
  border-color: #3b82f6;
  background: #f0f7ff;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}

.ref-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.ref-title {
  color: #0066cc;
  font-weight: 600;
  font-size: 0.95rem;
  flex: 1;
}

.ref-source {
  background: #e0e7ff;
  color: #4338ca;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.ref-snippet {
  color: #64748b;
  font-size: 0.85rem;
  line-height: 1.5;
  margin: 0;
}

.content-link {
  display: block;
  padding: 10px;
  background: #f1f5f9;
  border-radius: 6px;
  margin-bottom: 8px;
  color: #3b82f6;
  text-decoration: none;
  transition: 0.2s;
}

.content-link:hover {
  background: #e2e8f0;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 500;
  background: #cbd5e1;
  color: #475569;
  margin-left: 8px;
}

.mindmap-view {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.mindmap-header {
  margin-bottom: 0.5rem;
  flex-shrink: 0;
}

.mindmap-tree-wrapper {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0;
  background: #f8fafc;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 0;
  width: 100%;
}

.mindmap-loading,
.mindmap-error,
.mindmap-empty {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 2rem;
}

.search-input {
  flex: 1;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
}

.search-btn {
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  width: 50px;
  cursor: pointer;
  font-size: 1.2rem;
}

.result-item {
  padding: 1.5rem;
  border-bottom: 1px solid #f1f5f9;
  transition: 0.2s;
}

.result-item:hover {
  background: #f8fafc;
}

.result-source {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  background: #cbd5e1;
  color: #475569;
}

.result-source.wiki {
  background: #dbeafe;
  color: #1e40af;
}

.result-title {
  font-size: 1.1rem;
  margin: 0 0 0.5rem 0;
  color: #1e293b;
}

.result-link {
  color: #3b82f6;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 600;
  display: inline-block;
  margin-top: 0.5rem;
}

.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 1rem;
}

.message {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.message.ai {
  flex-direction: row;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.bubble {
  background: #f1f5f9;
  padding: 1rem;
  border-radius: 12px;
  border-top-left-radius: 2px;
  max-width: 80%;
  line-height: 1.6;
}

.bubble.markdown-content {
  word-wrap: break-word;
}

.bubble.markdown-content h1,
.bubble.markdown-content h2,
.bubble.markdown-content h3 {
  margin: 0.5rem 0;
  font-weight: 600;
}

.bubble.markdown-content h1 {
  font-size: 1.5rem;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0.5rem;
}

.bubble.markdown-content h2 {
  font-size: 1.25rem;
  margin-top: 1rem;
}

.bubble.markdown-content h3 {
  font-size: 1.1rem;
  margin-top: 0.75rem;
}

.bubble.markdown-content p {
  margin: 0.5rem 0;
}

.bubble.markdown-content strong {
  font-weight: 600;
  color: #1e293b;
}

.bubble.markdown-content em {
  font-style: italic;
}

.bubble.markdown-content ul,
.bubble.markdown-content ol {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.bubble.markdown-content li {
  margin: 0.25rem 0;
}

.bubble.markdown-content code {
  background: #e2e8f0;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.bubble.markdown-content pre {
  background: #1e293b;
  color: #f1f5f9;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.bubble.markdown-content pre code {
  background: transparent;
  padding: 0;
  color: inherit;
}

.bubble.markdown-content blockquote {
  border-left: 4px solid #3b82f6;
  padding-left: 1rem;
  margin: 0.5rem 0;
  color: #64748b;
  font-style: italic;
}

.chat-input-area {
  display: flex;
  gap: 10px;
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid #f1f5f9;
}

.chat-input {
  flex: 1;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  outline: none;
}

.send-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0 20px;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 600;
}

.mini-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #e2e8f0;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* New Semantic Styles */
.point-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.point-item {
  display: flex;
  gap: 0.5rem;
  line-height: 1.6;
  color: #334155;
}
.point-marker {
  color: #64748b;
  font-weight: bold;
  min-width: 15px;
  text-align: center;
}
.level-0 { margin-left: 0; font-weight: 500; }
.level-1 { margin-left: 1.5rem; font-size: 0.95em; color: #475569; }
.level-2 { margin-left: 3rem; font-size: 0.9em; color: #64748b; }
.level-3 { margin-left: 4.5rem; }

.point-table-wrapper {
  margin: 1rem 0;
  overflow-x: auto;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}
.simple-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.simple-table td {
  border: 1px solid #e2e8f0;
  padding: 8px 12px;
}
.simple-table tr:first-child td {
  background-color: #f1f5f9;
  font-weight: 600;
  color: #1e293b;
}

/* 关键词样式 */
.keywords-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-left: 4px solid #0284c7;
  border-radius: 6px;
}

.keywords-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #0c4a6e;
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.keywords-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.keyword-tag {
  display: inline-block;
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  color: white;
  padding: 0.4rem 0.8rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(2, 132, 199, 0.2);
  transition: all 0.3s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

/* 关键词加载中样式 */
.keywords-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-left: 4px solid #0284c7;
  border-radius: 6px;
  margin-bottom: 1.5rem;
}

.loading-spinner {
  font-size: 1.5rem;
  animation: spin 1.5s linear infinite;
}

.loading-text {
  color: #0c4a6e;
  font-size: 0.9rem;
  font-weight: 500;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.keyword-tag:hover {
  background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
  box-shadow: 0 4px 8px rgba(2, 132, 199, 0.3);
  transform: translateY(-2px);
}

/* 分析状态样式 */
.analysis-status {
  padding: 1.5rem;
  border-radius: 8px;
  margin: 1rem 0;
}

/* 移除旧的 pending-box 相关样式，已使用新的 waiting-state */

.error-box {
  background: #ffe0e0;
  border: 2px solid #dc2626;
  border-radius: 8px;
  padding: 1.5rem;
  color: #991b1b;
}

.error-box strong {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 1rem;
}

.error-box p {
  margin: 0.5rem 0;
  line-height: 1.6;
}

.error-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #fecaca;
}

.error-details summary {
  cursor: pointer;
  color: #991b1b;
  font-weight: 600;
  user-select: none;
}

.error-details summary:hover {
  text-decoration: underline;
}

.error-details pre {
  background: #fff5f5;
  border: 1px solid #fecaca;
  border-radius: 4px;
  padding: 1rem;
  overflow-x: auto;
  font-size: 0.8rem;
  margin-top: 0.5rem;
  color: #7c2d12;
}

/* 移除旧的调试区域样式，已整合到新的设计 */

/* markdown-body 样式已在上面定义 */

.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  color: #1e293b;
}

.markdown-body h1 { 
  font-size: 1.6rem;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0.5rem;
}
.markdown-body h2 { 
  font-size: 1.3rem;
  margin-top: 1.25rem;
}
.markdown-body h3 { 
  font-size: 1.1rem;
  margin-top: 1rem;
}

.markdown-body p {
  margin: 0.75rem 0;
  line-height: 1.8;
}

.markdown-body strong {
  font-weight: 600;
  color: #1e293b;
}

.markdown-body em {
  font-style: italic;
  color: #475569;
}

.markdown-body ul,
.markdown-body ol {
  list-style: disc;
  padding-left: 1.75rem;
  margin: 0.75rem 0;
  line-height: 1.8;
}

.markdown-body li {
  margin: 0.4rem 0;
}

.markdown-body code {
  background: #f1f5f9;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  color: #e11d48;
}

.markdown-body pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  margin: 1rem 0;
}

.markdown-body pre code {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-body blockquote {
  border-left: 4px solid #3b82f6;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #64748b;
  font-style: italic;
}

/* 移除旧的调试信息样式，已整合到新的设计 */

/* 移除旧的连接面板样式，已整合到 debug-collapsible */

.check-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
}

.check-btn:hover {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}

.check-btn:active {
  transform: translateY(0);
}

.check-btn.llm-btn {
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
}

.check-btn.llm-btn:hover {
  background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
}


/* AI 分析触发按钮样式 */
.ai-analysis-trigger {
  display: flex;
  justify-content: center;
  margin: 2rem 0;
}

.btn-analyze-page {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  padding: 1rem 2rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-analyze-page:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
  transform: translateY(-2px);
}

.btn-analyze-page:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.btn-analyze-page:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
}

.btn-analyze-page.btn-collapse {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
  box-shadow: 0 4px 12px rgba(107, 114, 128, 0.3);
}

.btn-analyze-page.btn-collapse:hover:not(:disabled) {
  background: linear-gradient(135deg, #4b5563 0%, #374151 100%);
  box-shadow: 0 6px 16px rgba(107, 114, 128, 0.4);
}

/* 卡片标题和操作按钮布局 */
.card-header-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.card-header-with-action .card-title {
  margin: 0;
  flex: 1;
}

/* 重新分析按钮样式 */
.btn-reanalyze {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.btn-reanalyze:hover {
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
  transform: translateY(-1px);
}

.btn-reanalyze:active {
  transform: translateY(0);
  box-shadow: 0 2px 6px rgba(245, 158, 11, 0.3);
}

.reanalyze-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 500;
}

/* 加载动画 */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.analyzing-spinner {
  display: inline-block;
  animation: spin 1.5s linear infinite;
}
.chat-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
  min-height: 500px;
}

.chat-header {
  padding-bottom: 1rem;
  border-bottom: 2px solid #f1f5f9;
  margin-bottom: 1rem;
}

.chat-title {
  font-size: 1.5rem;
  color: #1e293b;
  margin: 0 0 0.5rem 0;
}

.chat-subtitle {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message {
  display: flex;
  gap: 0.75rem;
  animation: slideIn 0.3s ease;
}

.message.user {
  flex-direction: row-reverse;
}

.message.ai {
  flex-direction: row;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.message.user .avatar {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

.bubble {
  background: white;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  max-width: 70%;
  line-height: 1.6;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  position: relative;
}

.message.ai .bubble {
  border-top-left-radius: 2px;
  background: #f1f5f9;
}

.message.user .bubble {
  border-top-right-radius: 2px;
  background: #3b82f6;
  color: white;
}

.bubble.markdown-content {
  word-wrap: break-word;
}

.bubble.markdown-content h1,
.bubble.markdown-content h2,
.bubble.markdown-content h3 {
  margin: 0.5rem 0;
  font-weight: 600;
}

.bubble.markdown-content h1 {
  font-size: 1.5rem;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0.5rem;
}

.bubble.markdown-content h2 {
  font-size: 1.25rem;
  margin-top: 1rem;
}

.bubble.markdown-content h3 {
  font-size: 1.1rem;
  margin-top: 0.75rem;
}

.bubble.markdown-content p {
  margin: 0.5rem 0;
}

.bubble.markdown-content strong {
  font-weight: 600;
  color: #1e293b;
}

.bubble.markdown-content em {
  font-style: italic;
}

.bubble.markdown-content ul,
.bubble.markdown-content ol {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.bubble.markdown-content li {
  margin: 0.25rem 0;
}

.bubble.markdown-content code {
  background: #e2e8f0;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.bubble.markdown-content pre {
  background: #1e293b;
  color: #f1f5f9;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.bubble.markdown-content pre code {
  background: transparent;
  padding: 0;
  color: inherit;
}

.bubble.markdown-content blockquote {
  border-left: 4px solid #3b82f6;
  padding-left: 1rem;
  margin: 0.5rem 0;
  color: #64748b;
  font-style: italic;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.analyzing-spinner {
  display: inline-block;
  animation: spin 1.5s linear infinite;
}
.chat-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
  min-height: 500px;
}

.chat-header {
  padding-bottom: 1rem;
  border-bottom: 2px solid #f1f5f9;
  margin-bottom: 1rem;
}

.chat-title {
  font-size: 1.5rem;
  color: #1e293b;
  margin: 0 0 0.5rem 0;
}

.chat-subtitle {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message {
  display: flex;
  gap: 0.75rem;
  animation: slideIn 0.3s ease;
}

.message.user {
  flex-direction: row-reverse;
}

.message.ai {
  flex-direction: row;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.message.user .avatar {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

.bubble {
  background: white;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  max-width: 70%;
  line-height: 1.6;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  position: relative;
}

.message.ai .bubble {
  border-top-left-radius: 2px;
  background: #f1f5f9;
}

.message.user .bubble {
  border-top-right-radius: 2px;
  background: #3b82f6;
  color: white;
}

.timestamp {
  display: block;
  font-size: 0.7rem;
  color: #94a3b8;
  margin-top: 0.25rem;
}

.message.user .timestamp {
  color: rgba(255, 255, 255, 0.7);
}

.typing-indicator .bubble {
  display: flex;
  gap: 0.3rem;
  padding: 1rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typing 1.4s infinite;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

.chat-input-area {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.chat-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  outline: none;
  font-size: 0.95rem;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: #3b82f6;
}

.chat-input:disabled {
  background: #f1f5f9;
  cursor: not-allowed;
}

.send-btn {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.send-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
  transform: translateY(-1px);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

/* 分析进度显示样式 - 扁平化 */
.analysis-progress {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  margin: 0 1.5rem 1.5rem 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.progress-title {
  font-weight: 700;
  font-size: 1rem;
  color: #1e293b;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stages-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stage-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: white;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.stage-item:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.1);
}

.stage-status {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.stage-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: bold;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.stage-icon.completed {
  background: #10b981;
  color: white;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.stage-icon.pending {
  background: #f59e0b;
  color: white;
  animation: pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.05);
  }
}

.stage-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.95rem;
  white-space: nowrap;
}

.stage-message {
  font-size: 0.85rem;
  color: #64748b;
  padding-left: 0.5rem;
  display: block;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 响应式调整 */
@media (max-width: 768px) {
  .ai-analysis-container {
    margin-top: 1rem;
    border-radius: 8px;
  }

  .ai-analysis-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1rem;
  }

  .ai-analysis-title {
    font-size: 1rem;
  }

  .ai-metadata {
    padding: 1rem;
  }

  .ai-content-main {
    padding: 1rem;
  }

  .analysis-progress {
    padding: 1rem;
    margin: 0 1rem 1rem 1rem;
  }

  .stage-item {
    padding: 0.6rem;
  }

  .stage-name {
    font-size: 0.9rem;
  }

  .stage-message {
    font-size: 0.8rem;
  }

  .progress-title {
    font-size: 0.95rem;
  }

  .waiting-state {
    padding: 1.5rem 0.5rem;
  }

  .waiting-icon {
    font-size: 2.5rem;
  }

  .waiting-text {
    font-size: 1rem;
  }

  .error-state {
    flex-direction: column;
    padding: 1rem;
  }

  .markdown-body h1 {
    font-size: 1.4rem;
  }

  .markdown-body h2 {
    font-size: 1.2rem;
  }

  .markdown-body h3 {
    font-size: 1rem;
  }
}
</style>
