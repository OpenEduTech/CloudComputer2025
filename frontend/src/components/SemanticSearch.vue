<script setup>
import { ref, computed } from 'vue'
import { pptApi } from '../api/index.js'

const props = defineProps({
  currentFileName: String
})

const emit = defineEmits(['select-slide'])

const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)
const searchError = ref(null)
const showResults = ref(false)
const previewDialog = ref({
  show: false,
  result: null,
  slideData: null,
  loading: false
})

const hasResults = computed(() => searchResults.value.length > 0)

// 提取文件名的基础名称
const getBaseFileName = (fileName) => {
  if (!fileName) return ''
  const baseName = fileName.split(/[/\\]/).pop() || fileName
  return baseName.trim()
}

const isCurrentFile = (result) => {
  const resultFileName = result.metadata?.file_name
  const currentFileName = props.currentFileName

  if (!resultFileName || !currentFileName) {
    if (import.meta.env.DEV) {
      console.log('🔍 文件匹配检查 - 缺少文件名:', {
        resultFileName: resultFileName || 'null',
        currentFileName: currentFileName || 'null'
      })
    }
    return false
  }
  
  // 提取基础文件名
  const resultBase = getBaseFileName(resultFileName)
  const currentBase = getBaseFileName(currentFileName)

  const match = resultBase === currentBase

  if (import.meta.env.DEV) {
    if (!match) {
      console.log('🔍 文件不匹配:', {
        resultFileName: resultFileName,
        resultBase: resultBase,
        currentFileName: currentFileName,
        currentBase: currentBase,
        match: match
      })
    } else {
      console.log('✅ 文件匹配:', {
        resultBase: resultBase,
        currentBase: currentBase
      })
    }
  }
  
  return match
}

const performSearch = async () => {
  if (!searchQuery.value.trim()) {
    searchError.value = '请输入搜索关键词'
    return
  }

  isSearching.value = true
  searchError.value = null
  showResults.value = false

  try {
    console.log('🔍 发起搜索:', {
      query: searchQuery.value,
      currentFileName: props.currentFileName
    })
    
    const response = await pptApi.searchSemantic(
      searchQuery.value,
      10, // top_k 
      null, // 不过滤文件，搜索所有文档，然后前端排序
      null, // file_type
      0.0 //获取所有结果，前端再过滤
    )

    if (response.data.success) {
      let results = response.data.results || []
      
      console.log('📊 原始搜索结果:', results.length, '个')
      
      // 过滤掉第一页的结果
      results = results.filter(r => {
        const pageNum = r.metadata?.page_num
        if (pageNum === 1 || pageNum === 0) {
          console.log(`⏭️ 跳过第一页结果: ${r.metadata?.file_name} 第 ${pageNum} 页`)
          return false
        }
        return true
      })
      
      console.log('📊 过滤第一页后结果数:', results.length, '个')
      
      // 优先显示当前文件的结果
      const currentFileResults = results.filter(r => 
        r.metadata?.file_name === props.currentFileName
      )
      const otherFileResults = results.filter(r => 
        r.metadata?.file_name !== props.currentFileName
      )
      
      console.log('📂 当前文件结果:', currentFileResults.length, '个')
      console.log('📁 其他文件结果:', otherFileResults.length, '个')
      
      // 当前文件结果排在前面
      searchResults.value = [...currentFileResults, ...otherFileResults]
      showResults.value = true
      
      if (currentFileResults.length === 0 && props.currentFileName) {
        console.warn('⚠️ 当前文件没有匹配结果，只显示其他文件的结果')
      }
    } else {
      searchError.value = response.data.error || '搜索失败'
    }
  } catch (error) {
    console.error('搜索错误:', error)
    searchError.value = error.response?.data?.error || '搜索请求失败，请检查网络连接'
  } finally {
    isSearching.value = false
  }
}

const handleKeyPress = (e) => {
  if (e.key === 'Enter') {
    performSearch()
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = []
  showResults.value = false
  searchError.value = null
}

const formatScore = (score) => {
  return (score * 100).toFixed(1) + '%'
}

const handleResultClick = async (result) => {
  // 检查是否来自其他文件
  if (!isCurrentFile(result)) {
    const fileName = result.metadata?.file_name
    const pageNum = result.metadata?.page_num
    
    if (fileName) {
      console.log(`🔍 预览其他文档: ${fileName} 第 ${pageNum} 页`)
      await showPreview(result)
    }
  } else {
    if (result.metadata && result.metadata.page_num) {
      emit('select-slide', result.metadata.page_num - 1) 
    }
  }
}

// 显示其他文档页面的预览
const showPreview = async (result) => {
  previewDialog.value.show = true
  previewDialog.value.result = result
  previewDialog.value.loading = true
  previewDialog.value.slideData = null
  
  try {
    const fileName = result.metadata?.file_name
    const pageNum = result.metadata?.page_num

    const response = await pptApi.getDocumentByName(fileName)
    
    if (response.data.success && response.data.slides) {
      const slides = response.data.slides
      const slide = slides.find(s => s.page_num === pageNum)
      
      if (slide) {
        previewDialog.value.slideData = slide
      } else {
        console.error('未找到对应页面')
      }
    }
  } catch (error) {
    console.error('获取文档失败:', error)
  } finally {
    previewDialog.value.loading = false
  }
}

const closePreview = () => {
  previewDialog.value.show = false
  previewDialog.value.result = null
  previewDialog.value.slideData = null
}

const highlightKeywords = (text, query) => {
  if (!text || !query) return text
  
  let highlightedText = text
  const queryTrimmed = query.trim()
  
  // 首先尝试完整查询匹配
  if (queryTrimmed.length >= 2) {
    const escapedQuery = queryTrimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const regex = new RegExp(`(${escapedQuery})`, 'gi')
    highlightedText = highlightedText.replace(regex, '<mark>$1</mark>')
  }
  
  // 然后处理空格分割的关键词
  const keywords = queryTrimmed.split(/\s+/)
  keywords.forEach(keyword => {
    if (keyword.length < 2 || keyword === queryTrimmed) return 
    
    // 转义特殊字符
    const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const regex = new RegExp(`(${escapedKeyword})`, 'gi')
    highlightedText = highlightedText.replace(regex, '<mark>$1</mark>')
  })
  
  if (highlightedText.length > 200) {
    const markIndex = highlightedText.indexOf('<mark>')
    if (markIndex > 50) {
      highlightedText = '...' + highlightedText.substring(markIndex - 50, markIndex + 200) + '...'
    } else {
      highlightedText = highlightedText.substring(0, 200) + '...'
    }
  }
  
  return highlightedText
}
</script>

<template>
  <div class="semantic-search-container">
    <div class="search-header">
      <h3>🔍 语义搜索</h3>
      <p class="search-hint">基于向量数据库的智能语义检索，支持 PDF 和 PPTX 文件</p>
    </div>

    <div class="search-input-wrapper">
      <input
        v-model="searchQuery"
        type="text"
        class="search-input"
        placeholder="输入关键词进行语义搜索..."
        @keypress="handleKeyPress"
        :disabled="isSearching"
      />
      <button
        class="search-btn"
        @click="performSearch"
        :disabled="isSearching || !searchQuery.trim()"
      >
        <span v-if="!isSearching">搜索</span>
        <span v-else class="spinner">搜索中...</span>
      </button>
      <button
        v-if="showResults || searchQuery"
        class="clear-btn"
        @click="clearSearch"
      >
        清除
      </button>
    </div>

    <div v-if="searchError" class="error-message">
      ⚠️ {{ searchError }}
    </div>

    <div v-if="showResults && hasResults" class="search-results">
      <div class="results-header">
        <span>找到 {{ searchResults.length }} 个相关结果</span>
      </div>

      <div class="results-list">
          <div
            v-for="(result, index) in searchResults"
            :key="`${result.metadata?.file_name}_${result.metadata?.page_num}_${index}`"
            class="result-item"
            @click="handleResultClick(result)"
          >
            <div class="result-header">
              <span class="result-score">相似度: {{ formatScore(result.score) }}</span>
              <span class="result-meta">
                {{ result.metadata?.file_name || '未知文件' }} - 
                第 {{ result.metadata?.page_num || '?' }} 页
              </span>
            </div>
          <div class="result-content" v-html="highlightKeywords(result.content, searchQuery)">
          </div>
          <div class="result-footer">
            <span class="result-type">{{ result.metadata?.slide_type || 'content' }}</span>
            <span v-if="result.metadata?.slide_title" class="result-title">
              {{ result.metadata.slide_title }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showResults && !hasResults" class="no-results">
      <p>未找到相关结果，请尝试其他关键词</p>
    </div>

    <!-- 预览弹窗（显示其他文档的页面） -->
    <div v-if="previewDialog.show" class="preview-dialog-overlay" @click="closePreview">
      <div class="preview-dialog" @click.stop>
        <div class="preview-header">
          <h3>📄 页面预览</h3>
          <button class="close-btn" @click="closePreview">✕</button>
        </div>
        
        <div class="preview-meta">
          <div class="meta-item">
            <span class="meta-label">文件:</span>
            <span class="meta-value">{{ previewDialog.result?.metadata?.file_name }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">页码:</span>
            <span class="meta-value">第 {{ previewDialog.result?.metadata?.page_num }} 页</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">标题:</span>
            <span class="meta-value">{{ previewDialog.result?.metadata?.slide_title }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">相似度:</span>
            <span class="meta-value">{{ formatScore(previewDialog.result?.score) }}</span>
          </div>
        </div>
        
        <div class="preview-body">
          <div v-if="previewDialog.loading" class="preview-loading">
            <div class="spinner">加载中...</div>
          </div>
          
          <div v-else-if="previewDialog.slideData" class="preview-content">
            <!-- 只显示页面预览图片 -->
            <div v-if="previewDialog.slideData.image" class="preview-image">
              <img 
                :src="previewDialog.slideData.image" 
                :alt="`第 ${previewDialog.slideData.page_num} 页`"
                style="max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"
              />
            </div>
            <div v-else class="no-image">
              <p>该页面没有预览图片</p>
            </div>
          </div>
          
          <div v-else class="preview-error">
            加载失败
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.semantic-search-container {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
}

.search-header {
  margin-bottom: 1rem;
}

.search-header h3 {
  margin: 0 0 0.5rem 0;
  color: #1e293b;
  font-size: 1.2rem;
}

.search-hint {
  margin: 0;
  color: #64748b;
  font-size: 0.85rem;
}

.search-input-wrapper {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.search-input:disabled {
  background: #f1f5f9;
  cursor: not-allowed;
}

.search-btn {
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.search-btn:hover:not(:disabled) {
  background: #2563eb;
}

.search-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.clear-btn {
  padding: 0.75rem 1rem;
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #e2e8f0;
}

.spinner {
  display: inline-block;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.error-message {
  padding: 0.75rem;
  background: #fee2e2;
  color: #dc2626;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.search-results {
  margin-top: 1rem;
}

.results-header {
  padding: 0.5rem 0;
  color: #64748b;
  font-size: 0.9rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 1rem;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-item {
  padding: 1rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.result-item:hover {
  background: #f1f5f9;
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}


.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}

.result-score {
  color: #10b981;
  font-weight: 600;
}

.result-meta {
  color: #64748b;
}

.result-content {
  color: #1e293b;
  line-height: 1.6;
  margin-bottom: 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-content :deep(mark) {
  background: #fef08a;
  color: #854d0e;
  padding: 0.125rem 0.25rem;
  border-radius: 2px;
  font-weight: 600;
}

.result-footer {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.8rem;
}

.result-type {
  padding: 0.25rem 0.5rem;
  background: #e0e7ff;
  color: #4f46e5;
  border-radius: 4px;
  font-weight: 500;
}

.result-title {
  color: #64748b;
  font-style: italic;
}

.no-results {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

@media (max-width: 768px) {
  .search-input-wrapper {
    flex-direction: column;
  }

  .result-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}

/* 预览弹窗样式 */
.preview-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.preview-dialog {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 900px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.preview-header h3 {
  margin: 0;
  color: #1e293b;
  font-size: 1.3rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #64748b;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.preview-meta {
  padding: 1rem 1.5rem;
  background: #f8fafc;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
}

.meta-label {
  color: #64748b;
  font-weight: 600;
  font-size: 0.85rem;
}

.meta-value {
  color: #1e293b;
  font-size: 0.85rem;
}

.preview-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.preview-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem;
  color: #64748b;
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.preview-image {
  text-align: center;
  background: #f8fafc;
  border-radius: 8px;
  padding: 1rem;
}

.preview-image img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.no-image {
  text-align: center;
  padding: 3rem;
  color: #94a3b8;
}

.preview-error {
  text-align: center;
  padding: 3rem;
  color: #dc2626;
}
</style>

