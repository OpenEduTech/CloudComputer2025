<script setup>
import { ref, computed } from 'vue'
import { pptApi } from '../api/index.js'

const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)
const searchError = ref(null)
const showResults = ref(false)
const selectedSources = ref(['wikipedia', 'arxiv', 'web'])
const availableSources = ref(['wikipedia', 'arxiv', 'web'])

const hasResults = computed(() => searchResults.value.length > 0)

const sourceLabels = {
  wikipedia: 'Wikipedia',
  arxiv: 'Arxiv 学术',
  web: 'Web 搜索'
}

const sourceIcons = {
  wikipedia: '📚',
  arxiv: '🎓',
  web: '🌐'
}

const performSearch = async () => {
  if (!searchQuery.value.trim()) {
    searchError.value = '请输入搜索关键词'
    return
  }

  if (selectedSources.value.length === 0) {
    searchError.value = '请至少选择一个搜索源'
    return
  }

  isSearching.value = true
  searchError.value = null
  showResults.value = false

  try {
    const response = await pptApi.searchExternal(
      searchQuery.value,
      selectedSources.value,
      10
    )

    if (response.data.success) {
      searchResults.value = response.data.results || []
      availableSources.value = response.data.available_sources || []
      showResults.value = true
      
      if (searchResults.value.length === 0) {
        searchError.value = '未找到相关结果，请尝试其他关键词'
      }
    } else {
      searchError.value = response.data.error || '搜索失败'
    }
  } catch (error) {
    console.error('外部搜索错误:', error)
    searchError.value = error.response?.data?.error || '搜索请求失败，请检查网络连接或后端服务'
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

const toggleSource = (source) => {
  const index = selectedSources.value.indexOf(source)
  if (index > -1) {
    selectedSources.value.splice(index, 1)
  } else {
    selectedSources.value.push(source)
  }
}

const openLink = (url) => {
  window.open(url, '_blank')
}

const getSourceColor = (source) => {
  const colors = {
    wikipedia: '#3b82f6',
    arxiv: '#10b981',
    web: '#8b5cf6'
  }
  return colors[source] || '#64748b'
}
</script>

<template>
  <div class="external-search-container">
    <div class="search-header">
      <h3>🌐 外部资源搜索</h3>
      <p class="search-hint">联网搜索 Wikipedia、Arxiv 学术论文和 Web 资源</p>
    </div>

    <!-- 搜索源选择 -->
    <div class="source-selector">
      <span class="selector-label">搜索源：</span>
      <div class="source-buttons">
        <button
          v-for="source in availableSources"
          :key="source"
          :class="['source-btn', { active: selectedSources.includes(source) }]"
          @click="toggleSource(source)"
          :disabled="isSearching"
        >
          <span class="source-icon">{{ sourceIcons[source] }}</span>
          <span>{{ sourceLabels[source] }}</span>
        </button>
      </div>
    </div>

    <!-- 搜索输入 -->
    <div class="search-input-wrapper">
      <input
        v-model="searchQuery"
        type="text"
        class="search-input"
        placeholder="输入关键词搜索外部资源..."
        @keypress="handleKeyPress"
        :disabled="isSearching"
      />
      <button
        class="search-btn"
        @click="performSearch"
        :disabled="isSearching || !searchQuery.trim() || selectedSources.length === 0"
      >
        <span v-if="!isSearching">🔍 搜索</span>
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

    <!-- 错误提示 -->
    <div v-if="searchError" class="error-message">
      ⚠️ {{ searchError }}
    </div>

    <!-- 搜索结果 -->
    <div v-if="showResults && hasResults" class="search-results">
      <div class="results-header">
        <span>找到 {{ searchResults.length }} 个相关资源</span>
        <span class="sources-used">
          来源: {{ selectedSources.map(s => sourceLabels[s]).join(', ') }}
        </span>
      </div>

      <div class="results-list">
        <div
          v-for="(result, index) in searchResults"
          :key="index"
          class="result-item"
          @click="openLink(result.url)"
        >
          <div class="result-header">
            <span 
              class="result-source"
              :style="{ backgroundColor: getSourceColor(result.source) }"
            >
              {{ sourceIcons[result.source] }} {{ sourceLabels[result.source] }}
            </span>
            <span v-if="result.published" class="result-date">
              📅 {{ result.published }}
            </span>
          </div>
          
          <h4 class="result-title">{{ result.title }}</h4>
          
          <div v-if="result.authors" class="result-authors">
            👤 {{ result.authors.join(', ') }}
          </div>
          
          <div class="result-snippet">
            {{ result.snippet }}
          </div>
          
          <div class="result-footer">
            <a :href="result.url" target="_blank" class="result-link" @click.stop>
              🔗 查看原文
            </a>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showResults && !hasResults && !searchError" class="no-results">
      <p>未找到相关结果，请尝试：</p>
      <ul>
        <li>使用不同的关键词</li>
        <li>选择更多搜索源</li>
        <li>使用更通用的术语</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.external-search-container {
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

/* 搜索源选择器 */
.source-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #f8fafc;
  border-radius: 6px;
}

.selector-label {
  font-weight: 600;
  color: #475569;
  font-size: 0.9rem;
}

.source-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.source-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.85rem;
}

.source-btn:hover:not(:disabled) {
  border-color: #3b82f6;
  transform: translateY(-1px);
}

.source-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.source-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.source-icon {
  font-size: 1rem;
}

/* 搜索输入 */
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

/* 错误提示 */
.error-message {
  padding: 0.75rem;
  background: #fee2e2;
  color: #dc2626;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

/* 搜索结果 */
.search-results {
  margin-top: 1rem;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  color: #64748b;
  font-size: 0.9rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 1rem;
}

.sources-used {
  font-size: 0.8rem;
  color: #94a3b8;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-item {
  padding: 1.25rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.result-item:hover {
  background: #f1f5f9;
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.result-source {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  color: white;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}

.result-date {
  color: #64748b;
  font-size: 0.8rem;
}

.result-title {
  margin: 0 0 0.5rem 0;
  color: #1e293b;
  font-size: 1.1rem;
  font-weight: 600;
  line-height: 1.4;
}

.result-authors {
  color: #64748b;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
  font-style: italic;
}

.result-snippet {
  color: #475569;
  line-height: 1.6;
  margin-bottom: 0.75rem;
}

.result-footer {
  display: flex;
  justify-content: flex-end;
}

.result-link {
  color: #3b82f6;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s;
}

.result-link:hover {
  color: #2563eb;
  text-decoration: underline;
}

/* 无结果提示 */
.no-results {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.no-results ul {
  text-align: left;
  display: inline-block;
  margin-top: 1rem;
}

.no-results li {
  margin: 0.5rem 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .search-input-wrapper {
    flex-direction: column;
  }

  .source-selector {
    flex-direction: column;
    align-items: flex-start;
  }

  .results-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .result-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>

