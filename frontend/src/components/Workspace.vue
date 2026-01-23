<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { pptApi } from '../api/index.js'
import ToolSidebar from './ToolSidebar.vue'
import PPTPreview from './PPTPreview.vue'
import ContentView from './ContentView.vue'

const props = defineProps({
  slides: Array,
  mindmap: Object,
  mindmapLoading: Boolean,
  mindmapError: String,
  docId: String
})

const currentSlideIndex = ref(0)
const activeTool = ref('explain')
const isAnalyzing = ref(false)
const analysisCache = ref({}) 
const hasPreloaded = ref(false)
const isAnalyzingGlobal = ref(false)  
const globalAnalysisResult = ref(null)  
const isExporting = ref(false)  
const showExportOptions = ref(false)  

const currentSlide = computed(() => props.slides[currentSlideIndex.value])

// 生命周期：当 slides 加载完成后，自动分析第一页
onMounted(async () => {
  if (props.slides && props.slides.length > 0) {
    console.log('📋 Workspace 挂载，slides 数量:', props.slides.length)
    // 自动分析第一页
    setTimeout(() => {
      selectSlide(0)
    }, 500)
  }
})

watch(
  () => [props.docId, props.slides?.length],
  async ([docId, len]) => {
    console.log('👀 watch 触发: docId=', docId, 'slides.length=', len, 'hasPreloaded=', hasPreloaded.value)
    if (docId && len && !hasPreloaded.value) {
      // 添加小延迟，确保所有数据都已准备好
      await new Promise(resolve => setTimeout(resolve, 100))
      console.log('🚀 开始预加载缓存分析...')
      await preloadCachedAnalyses()
      hasPreloaded.value = true
      console.log('✅ 预加载完成')
    } else {
      console.log('⏭️ 跳过预加载:', { docId: !!docId, len: !!len, hasPreloaded: hasPreloaded.value })
    }
  },
  { immediate: true }
)

// 将 Markdown 转换为 HTML
const markdownToHtml = (markdown) => {
  if (!markdown) return ''
  return markdown
    .replace(/^### (.*)/gm, '<h3>$1</h3>')
    .replace(/^## (.*)/gm, '<h2>$1</h2>')
    .replace(/^# (.*)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^- (.*)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n/g, '<br>')
}

const analyzeCurrentPage = async () => {
  if (!currentSlide.value) {
    console.warn('⚠️ currentSlide 为空，无法分析')
    return
  }

  const pageId = currentSlideIndex.value + 1

  // 检查缓存
  if (analysisCache.value[pageId]) {
    const cached = analysisCache.value[pageId]
    Object.assign(currentSlide.value, cached)
    console.log('✅ 使用缓存数据 (页面 ' + pageId + '):', {
      deep_analysis_length: (cached.deep_analysis || '').length,
      key_concepts: cached.key_concepts?.length || 0,
      learning_objectives: cached.learning_objectives?.length || 0
    })
    return
  }

  isAnalyzing.value = true
  console.log('🔄 开始分析页面:', pageId, '| 标题:', currentSlide.value.title)

  try {
    // 1. 分析页面
    console.log('📤 发送分析请求到后端 /api/v1/analyze-page')
    console.log('   参数: pageId=' + pageId + ', title="' + currentSlide.value.title + '"')
    
    const analysisRes = await pptApi.analyzePage(
      pageId,
      currentSlide.value.title || '',
      currentSlide.value.raw_content || '',
      currentSlide.value.raw_points || [],
      props.docId || null
    )

    console.log('📥 后端响应状态:', analysisRes.status)
    console.log('📥 后端响应:', JSON.stringify(analysisRes.data).substring(0, 200) + '...')
    
    // 处理响应数据
    let analysisData = null
    if (analysisRes.data?.data) {
      analysisData = analysisRes.data.data
    } else if (analysisRes.data?.success) {
      analysisData = analysisRes.data
    }
    
    if (!analysisData) {
      console.error('❌ 响应格式错误，缺少 data')
      console.error('完整响应:', analysisRes.data)
      throw new Error('后端返回的数据格式不正确')
    }
    
    console.log('✅ 成功提取分析数据:')
    console.log('   - deep_analysis 长度:', analysisData.deep_analysis.length, '字符')
    console.log('   - key_concepts 数量:', analysisData.key_concepts?.length || 0)
    console.log('   - learning_objectives 数量:', analysisData.learning_objectives?.length || 0)
    console.log('   - references 数量:', analysisData.references?.length || 0)

    // 2. 更新页面数据
    const enrichedSlide = {
      ...currentSlide.value,
      deep_analysis: analysisData.deep_analysis || analysisData.understanding_notes || '',
      deep_analysis_html: markdownToHtml(analysisData.deep_analysis || analysisData.understanding_notes || ''),
      key_concepts: analysisData.key_concepts || [],
      learning_objectives: analysisData.learning_objectives || [],
      references: analysisData.references || [],
      raw_points: analysisData.raw_points || currentSlide.value.raw_points || []
    }

    console.log('📝 页面数据已更新，准备显示在 UI 中')

    // 3. 缓存结果
    analysisCache.value[pageId] = enrichedSlide
    Object.assign(currentSlide.value, enrichedSlide)
    console.log('💾 分析结果已缓存')

    // 4. 初始化助教
    if (!hasPreloaded.value) {
      try {
        console.log('🤖 初始化 AI 助教 (页面 ' + pageId + ') - 批量设置未完成，单独设置')
        await pptApi.setTutorContext(
          pageId,
          currentSlide.value.title || '',
          currentSlide.value.raw_content || '',
          analysisData.key_concepts || []
        )
        console.log('✅ AI 助教初始化成功')
      } catch (err) {
        console.warn('⚠️ 初始化助教失败（非致命错误）:', err.message)
      }
    } else {
      console.log('✅ 批量设置已完成，跳过单独设置助教上下文')
    }
  } catch (error) {
    console.error('❌ 页面分析失败:', error)
    if (currentSlide.value) {
      currentSlide.value.deep_analysis = `❌ 分析失败: ${error.message || '未知错误'}`
      currentSlide.value.deep_analysis_html = `<div style="color: red; padding: 1rem; background: #ffe0e0; border-radius: 4px;"><strong>分析错误：</strong><br>${error.message || '未知错误'}</div>`
    }
  } finally {
    isAnalyzing.value = false
  }
}

const selectSlide = async (index) => {
  currentSlideIndex.value = index
  const pageId = index + 1

  // 已缓存则直接使用
  if (analysisCache.value[pageId]) {
    const cached = analysisCache.value[pageId]
    Object.assign(props.slides[index], {
      ...cached,
      deep_analysis: cached.deep_analysis || cached.understanding_notes || '',
      understanding_notes: cached.understanding_notes || cached.deep_analysis || '',
      deep_analysis_html: cached.deep_analysis_html || (cached.deep_analysis || cached.understanding_notes ? markdownToHtml(cached.deep_analysis || cached.understanding_notes || '') : '')
    })
    console.log('✅ 使用缓存数据 (页面 ' + pageId + '):', {
      hasDeepAnalysis: !!(cached.deep_analysis && cached.deep_analysis.trim().length > 0),
      hasUnderstandingNotes: !!(cached.understanding_notes && cached.understanding_notes.trim().length > 0),
      knowledge_clusters: cached.knowledge_clusters?.length || 0,
      knowledge_gaps: cached.knowledge_gaps?.length || 0,
      expanded_content: cached.expanded_content?.length || 0
    })
    return
  }

  console.log('📄 加载页面 ' + pageId + '，等待用户决定是否进行 AI 分析')
}


const preloadCachedAnalyses = async () => {
  if (!props.docId) {
    console.warn('⚠️ preloadCachedAnalyses: docId 为空，跳过')
    return
  }
  console.log('📦 开始预加载缓存分析，docId:', props.docId, 'slides数量:', props.slides?.length)
  try {
    // 步骤1: 先进行全局分析
    console.log('🌐 开始全局文档分析...')
    try {
      const globalRes = await pptApi.analyzeDocumentGlobal(props.docId)
      if (globalRes.data?.success) {
        globalAnalysisResult.value = globalRes.data.global_analysis
        if (globalRes.data.cached) {
          console.log('♻️  全局分析已存在，直接使用')
        } else {
          console.log('✅ 全局分析完成:', {
            main_topic: globalRes.data.global_analysis?.main_topic,
            knowledge_units: globalRes.data.global_analysis?.knowledge_units?.length || 0
          })
        }
      }
    } catch (globalErr) {
      console.warn('⚠️ 全局分析失败（非致命错误）:', globalErr.message)
    }
    
    // 步骤2: 获取已保存的页面分析
    const res = await pptApi.getAllPageAnalysis(props.docId)
    const data = res.data?.data || {}
    console.log('📊 获取到已保存分析:', Object.keys(data).length, '页')
    
    Object.entries(data).forEach(([pageStr, ana]) => {
      const pageId = Number(pageStr)
      const slideIdx = pageId - 1
      if (!props.slides[slideIdx]) return

      const understandingNotes = ana?.understanding_notes || ana?.deep_analysis || ''
      const deepAnalysis = ana?.deep_analysis || understandingNotes || ''
      
      const enriched = {
        ...props.slides[slideIdx],
        ...(ana || {}),
        understanding_notes: understandingNotes,
        deep_analysis: deepAnalysis,
        deep_analysis_html: deepAnalysis ? markdownToHtml(deepAnalysis) : '',
        knowledge_clusters: ana?.knowledge_clusters || [],
        knowledge_gaps: ana?.knowledge_gaps || [],
        expanded_content: ana?.expanded_content || [],
        references: ana?.references || [],
        raw_points: ana.raw_points || props.slides[slideIdx].raw_points || []
      }
      
      console.log(`📦 预加载页面 ${pageId} 分析数据:`, {
        hasDeepAnalysis: !!deepAnalysis,
        deep_analysis_length: deepAnalysis.length,
        knowledge_clusters: enriched.knowledge_clusters.length,
        knowledge_gaps: enriched.knowledge_gaps.length
      })
      
      analysisCache.value[pageId] = enriched
      Object.assign(props.slides[slideIdx], enriched)
    })
    if (Object.keys(data).length > 0) {
      console.log('✅ 已预加载历史分析页:', Object.keys(data))
    }
    
    // 预先为所有页设置助教上下文
    console.log('🤖 开始批量设置助教上下文，docId:', props.docId)
    try {
      const bulkRes = await pptApi.setTutorContextBulk(props.docId)
      console.log('✅ 批量设置助教上下文完成:', bulkRes.data)
    } catch (err) {
      console.error('❌ 批量设置助教上下文失败:', err)
      console.error('错误详情:', err.response?.data || err.message)
    }
  } catch (err) {
    console.error('❌ 预加载历史分析失败:', err)
    console.error('错误详情:', err.response?.data || err.message)
    console.log('🔄 尝试仅批量设置上下文（无分析数据）...')
    try {
      const bulkRes = await pptApi.setTutorContextBulk(props.docId)
      console.log('✅ 批量设置助教上下文完成（无分析数据）:', bulkRes.data)
    } catch (bulkErr) {
      console.error('❌ 批量设置上下文也失败:', bulkErr)
    }
  }
}

const handleToolChange = (toolName) => {
  activeTool.value = toolName
}

const triggerGlobalAnalysis = async (force = false) => {
  if (!props.docId) {
    console.warn('⚠️ docId 为空，无法进行全局分析')
    return
  }
  
  try {
    isAnalyzingGlobal.value = true
    console.log(`🌐 开始${force ? '强制重新' : ''}全局分析，docId:`, props.docId)
    
    const res = await pptApi.analyzeDocumentGlobal(props.docId, force)
    
    if (res.data?.success) {
      globalAnalysisResult.value = res.data.global_analysis
      console.log('✅ 全局分析完成:', {
        main_topic: res.data.global_analysis?.main_topic,
        knowledge_units: res.data.global_analysis?.knowledge_units?.length || 0,
        cached: res.data.cached
      })
 
      if (force) {
        alert(`✅ 全局分析重新完成！\n主题: ${res.data.global_analysis?.main_topic || '未知'}\n知识点单元: ${res.data.global_analysis?.knowledge_units?.length || 0} 个`)
      } else {
        if (res.data.cached) {
          console.log('♻️  使用了缓存的全局分析结果')
        } else {
          alert(`✅ 全局分析完成！\n主题: ${res.data.global_analysis?.main_topic || '未知'}\n知识点单元: ${res.data.global_analysis?.knowledge_units?.length || 0} 个`)
        }
      }
    }
  } catch (err) {
    console.error('❌ 全局分析失败:', err)
    alert(`❌ 全局分析失败: ${err.response?.data?.detail || err.message || '未知错误'}`)
  } finally {
    isAnalyzingGlobal.value = false
  }
}

const exportAnalysis = async (options = {}) => {
  if (!props.docId) {
    alert('❌ 无法导出：未找到文档ID')
    return
  }
  
  try {
    isExporting.value = true
    console.log('📥 开始导出AI分析内容...', {
      docId: props.docId,
      options: options
    })
    
    const response = await pptApi.exportAnalysis(props.docId, options)
    
    console.log('📦 收到响应:', {
      status: response.status,
      dataType: typeof response.data,
      dataSize: response.data?.size || response.data?.length,
      headers: response.headers
    })

    const blob = new Blob([response.data], { type: 'text/markdown; charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    const contentDisposition = response.headers['content-disposition']
    let fileName = 'AI分析内容.md'
    if (contentDisposition) {
      const rfc5987Match = contentDisposition.match(/filename\*=UTF-8''(.+)/)
      if (rfc5987Match && rfc5987Match[1]) {
        fileName = decodeURIComponent(rfc5987Match[1])
      } else {
        const fileNameMatch = contentDisposition.match(/filename="?([^"]+)"?/)
        if (fileNameMatch && fileNameMatch[1]) {
          fileName = decodeURIComponent(fileNameMatch[1])
        }
      }
    }
    
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    console.log('✅ 导出成功:', fileName)
    
  } catch (err) {
    console.error('❌ 导出失败详情:', {
      message: err.message,
      response: err.response,
      status: err.response?.status,
      data: err.response?.data
    })

    let errorMsg = '未知错误'
    if (err.response?.data) {
      if (err.response.data instanceof Blob) {
        try {
          const text = await err.response.data.text()
          const json = JSON.parse(text)
          errorMsg = json.detail || text
        } catch (e) {
          errorMsg = '无法解析错误信息'
        }
      } else if (typeof err.response.data === 'object') {
        errorMsg = err.response.data.detail || JSON.stringify(err.response.data)
      } else {
        errorMsg = err.response.data
      }
    } else {
      errorMsg = err.message
    }
    
    alert(`❌ 导出失败: ${errorMsg}`)
  } finally {
    isExporting.value = false
    showExportOptions.value = false
  }
}

const quickExportFull = () => {
  exportAnalysis({
    includeGlobal: true,
    includePages: true,
    pageRange: null,
    exportType: 'full'
  })
}

const quickExportSummary = () => {
  exportAnalysis({
    includeGlobal: true,
    includePages: false,
    pageRange: null,
    exportType: 'summary'
  })
}

const toggleExportOptions = () => {
  showExportOptions.value = !showExportOptions.value
}
</script>

<template>
  <div class="workspace-layout">
    <div class="workspace-main">
      <div class="left-panel">
        <PPTPreview
          :slides="slides"
          :current-index="currentSlideIndex"
          @select="selectSlide"
        />
      </div>

      <div class="right-panel">
        <!-- 全局分析按钮 - 只在深度分析工具激活时显示 -->
        <div v-if="props.docId && activeTool === 'explain'" class="global-analysis-bar">
          <div class="global-analysis-info">
            <span class="info-label">📚 文档全局分析:</span>
            <span v-if="globalAnalysisResult" class="info-value">
              {{ globalAnalysisResult.main_topic || '未知主题' }} 
              ({{ globalAnalysisResult.knowledge_units?.length || 0 }} 个知识点)
            </span>
            <span v-else class="info-value">分析中...</span>
          </div>
          <button 
            @click="triggerGlobalAnalysis(true)"
            :disabled="isAnalyzingGlobal"
            class="btn-global-reanalyze"
            title="重新进行全局分析（系统已自动分析，此按钮用于强制重新分析）"
          >
            <span v-if="isAnalyzingGlobal" class="analyzing-spinner">⏳</span>
            <span v-else>🔄</span>
            {{ isAnalyzingGlobal ? '重新分析中...' : '重新分析' }}
          </button>
          
          <!-- 导出按钮 -->
          <div class="export-dropdown" v-if="!isExporting">
            <button 
              @click="toggleExportOptions"
              class="btn-export"
              title="导出AI分析内容为Markdown文件"
            >
              📥 导出分析
            </button>
            
            <!-- 导出选项下拉菜单 -->
            <div v-if="showExportOptions" class="export-options">
              <button @click="quickExportFull" class="export-option">
                📄 导出完整分析
                <span class="option-desc">包含全局分析和所有页面的详细分析</span>
              </button>
              <button @click="quickExportSummary" class="export-option">
                📋 导出摘要
                <span class="option-desc">仅包含全局分析和统计信息</span>
              </button>
            </div>
          </div>
          
          <!-- 导出中状态 -->
          <button 
            v-else
            disabled
            class="btn-export"
          >
            <span class="analyzing-spinner">⏳</span>
            导出中...
          </button>
        </div>
        
        <!-- 内容展示 -->
        <div class="content-wrapper">
          <ContentView
            :slide="currentSlide"
            :active-tool="activeTool"
            :mindmap="mindmap"
            :mindmap-loading="mindmapLoading"
            :mindmap-error="mindmapError"
            :is-analyzing="isAnalyzing"
            :doc-id="props.docId"
            @select-slide="selectSlide"
          />
        </div>
        
        <!-- 加载状态浮层 -->
        <div v-if="isAnalyzing" class="loading-overlay">
          <div class="spinner"></div>
          <p>🤖 AI 正在深度分析...</p>
        </div>
      </div>
    </div>

    <!-- 工具栏 -->
    <ToolSidebar
      :active-tool="activeTool"
      @tool-change="handleToolChange"
    />
  </div>
</template>

<style scoped>
.workspace-layout {
  flex: 1;
  display: flex;
  height: calc(100vh - 60px);
  overflow: hidden;
  width: 100vw;
}
.workspace-container {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.graph-wrapper {
  flex: 1;
  height: 100%;
  position: relative;
}
.workspace-main {
  flex: 1;
  display: flex;
  min-width: 0;
}

.left-panel {
  width: 40%;
  border-right: 1px solid #e2e8f0;
  background: #f1f5f9;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.right-panel {
  width: 60%;
  background: #ffffff;
  overflow: hidden;
  position: relative;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 100;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #0066cc;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-overlay p {
  font-size: 1rem;
  color: #666;
  margin: 0;
}

/* 全局分析按钮栏 */
.global-analysis-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.global-analysis-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.info-label {
  font-weight: 600;
  opacity: 0.9;
}

.info-value {
  font-weight: 500;
  opacity: 0.95;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.btn-global-reanalyze,
.btn-export {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.btn-global-reanalyze {
  background: rgba(255, 193, 7, 0.9);
  color: #333;
  border: 1px solid rgba(255, 193, 7, 1);
}

.btn-global-reanalyze:hover:not(:disabled) {
  background: rgba(255, 193, 7, 1);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 193, 7, 0.4);
}

.btn-global-reanalyze:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.analyzing-spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
}

/* 导出按钮样式 */
.export-dropdown {
  position: relative;
}

.btn-export {
  background: rgba(76, 175, 80, 0.9);
  color: white;
  border: 1px solid rgba(76, 175, 80, 1);
}

.btn-export:hover:not(:disabled) {
  background: rgba(76, 175, 80, 1);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.4);
}

.btn-export:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 导出选项下拉菜单 */
.export-options {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  z-index: 1000;
  min-width: 280px;
}

.export-option {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: white;
  color: #333;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.export-option:last-child {
  border-bottom: none;
}

.export-option:hover {
  background: #f8f9fa;
}

.option-desc {
  font-size: 12px;
  font-weight: normal;
  color: #666;
  margin-top: 4px;
}

/* 内容包装器 - 解决双重滚动条问题 */
.content-wrapper {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* 覆盖 ContentView 的滚动 */
.content-wrapper :deep(.content-view) {
  height: auto;
  overflow-y: visible;
  overflow-x: visible;
  min-height: 100%;
}
</style>
