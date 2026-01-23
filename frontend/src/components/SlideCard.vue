<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  slide: Object
})

const isExpanded = ref(false)
const activeTab = ref('content')

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

const switchTab = (tab) => {
  activeTab.value = tab
}

const hasReferences = computed(() => {
  return props.slide.references && props.slide.references.length > 0
})

const hasCode = computed(() => {
  return props.slide.expanded_html && props.slide.expanded_html.includes('code-block')
})
</script>

<template>
  <div class="slide-card" :class="{ 'expanded': isExpanded }">
    <div class="slide-header" @click="toggleExpand">
      <div class="slide-info">
        <span class="page-number">P{{ slide.page_num }}</span>
        <h3 class="slide-title">{{ slide.title }}</h3>
      </div>
      <div class="expand-icon">
        <span :class="{ 'rotated': isExpanded }">▼</span>
      </div>
    </div>

    <div class="slide-content" v-show="isExpanded">
      <div class="content-split">
        <div class="original-content">
          <div class="label">📋 PPT 原始逻辑层级</div>
          <ul class="points-list">
            <li v-for="point in slide.raw_points" :key="point">{{ point }}</li>
          </ul>
        </div>

        <div class="expanded-content">
          <div class="tabs">
            <button
              :class="{ 'active': activeTab === 'content' }"
              @click="switchTab('content')"
              class="tab-button"
            >
              💡 扩展内容
            </button>
            <button
              v-if="hasReferences"
              :class="{ 'active': activeTab === 'references' }"
              @click="switchTab('references')"
              class="tab-button"
            >
              📚 参考文献
            </button>
          </div>

          <div class="tab-content">
            <div v-if="activeTab === 'content'" class="markdown-body" v-html="slide.expanded_html"></div>

            <div v-if="activeTab === 'references'" class="reference-section">
              <div class="ref-title">📚 延伸阅读资源</div>
              <div class="ref-list">
                <a v-for="ref in slide.references" :key="ref.url" :href="ref.url" target="_blank" class="ref-item">
                  <div class="ref-icon">
                    <span v-if="ref.source === 'Arxiv'">📄</span>
                    <span v-else-if="ref.source === 'Wikipedia'">📖</span>
                    <span v-else>🔗</span>
                  </div>
                  <div class="ref-info">
                    <div class="ref-title-text">{{ ref.title }}</div>
                    <div class="ref-source">来源: {{ ref.source }}</div>
                  </div>
                  <div class="ref-arrow">→</div>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.slide-card {
  background: white;
  border-radius: 16px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  overflow: hidden;
  border: 1px solid #f1f5f9;
  transition: all 0.3s ease;
}

.slide-card:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}

.slide-header {
  background: #1e293b;
  color: white;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: background 0.3s;
}

.slide-header:hover {
  background: #334155;
}

.slide-info {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.page-number {
  font-weight: bold;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.9rem;
  white-space: nowrap;
}

.slide-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  flex: 1;
}

.expand-icon {
  font-size: 0.8rem;
  color: #94a3b8;
  transition: transform 0.3s;
}

.expand-icon span {
  display: inline-block;
  transition: transform 0.3s;
}

.expand-icon span.rotated {
  transform: rotate(180deg);
}

.slide-content {
  border-top: 1px solid #e2e8f0;
}

.content-split {
  display: grid;
  grid-template-columns: 1fr 1.8fr;
  min-height: 200px;
}

.original-content {
  padding: 24px;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
}

.expanded-content {
  padding: 24px;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.points-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.points-list li {
  position: relative;
  padding-left: 20px;
  margin-bottom: 12px;
  color: #475569;
  line-height: 1.6;
  font-size: 0.95rem;
}

.points-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #3b82f6;
  font-weight: bold;
}

.label {
  font-size: 0.75rem;
  font-weight: 700;
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #64748b;
}

/* 标签页样式 */
.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 10px;
}

.tab-button {
  background: transparent;
  border: none;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  color: #64748b;
  border-radius: 6px;
  transition: all 0.2s;
  position: relative;
}

.tab-button:hover {
  color: #3b82f6;
  background: #f0f7ff;
}

.tab-button.active {
  color: #3b82f6;
  background: #dbeafe;
}

.tab-button.active::after {
  content: '';
  position: absolute;
  bottom: -12px;
  left: 0;
  width: 100%;
  height: 2px;
  background: #3b82f6;
}

.tab-content {
  flex: 1;
}

.markdown-body {
  color: #334155;
  line-height: 1.8;
  font-size: 0.95rem;
}

.markdown-body :deep(.formula) {
  background: #f8fafc;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-family: 'Times New Roman', serif;
  text-align: center;
  border-left: 3px solid #3b82f6;
}

.markdown-body :deep(.code-block) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  overflow-x: auto;
}

.markdown-body :deep(.code-block pre) {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
}

.markdown-body :deep(strong) {
  color: #1e293b;
  font-weight: 600;
}

.markdown-body :deep(p) {
  margin-bottom: 1rem;
}

/* 参考文献样式 */
.reference-section {
  background: #f8fafc;
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.ref-title {
  font-weight: 700;
  margin-bottom: 1rem;
  color: #1e293b;
  font-size: 1rem;
}

.ref-list {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.ref-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
  border: 1px solid #e2e8f0;
}

.ref-item:hover {
  border-color: #3b82f6;
  background: #f0f7ff;
  transform: translateX(4px);
}

.ref-icon {
  font-size: 1.5rem;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  border-radius: 8px;
  flex-shrink: 0;
}

.ref-info {
  flex: 1;
  min-width: 0;
}

.ref-title-text {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.9rem;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ref-source {
  font-size: 0.75rem;
  color: #94a3b8;
}

.ref-arrow {
  color: #94a3b8;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.ref-item:hover .ref-arrow {
  color: #3b82f6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .content-split {
    grid-template-columns: 1fr;
  }

  .original-content {
    border-right: none;
    border-bottom: 1px solid #e2e8f0;
  }

  .slide-header {
    padding: 12px 16px;
  }

  .slide-title {
    font-size: 1rem;
  }

  .expanded-content,
  .original-content {
    padding: 16px;
  }
}
</style>
