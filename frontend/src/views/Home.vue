<template>
  <div class="home-view">
    <AppHeader 
      title="Cross Learning" 
    />
    <div class="content">
      <SearchPanel @search="handleSearch" />
      
      <!-- 历史记录区域 -->
      <div class="history-section" v-if="!isLoadingHistory">
        <div class="history-header" v-if="historyList.length > 0">
          <h3>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            已构建的知识图谱
          </h3>
          <button @click="refreshHistory" class="refresh-history-btn" :disabled="isLoadingHistory">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
          </button>
        </div>
        <div class="history-list" v-if="historyList.length > 0">
          <button 
            v-for="concept in historyList" 
            :key="concept" 
            @click="loadHistoryConcept(concept)"
            class="history-item"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>
            {{ concept }}
          </button>
        </div>
        <p class="no-history" v-else>
          暂无已构建的知识图谱，搜索一个概念开始探索吧！
        </p>
      </div>
      
      <!-- 加载中状态 -->
      <div class="history-loading" v-else>
        <div class="mini-spinner"></div>
        <span>加载历史记录...</span>
      </div>
    </div>
    
    <footer class="footer">
      <p>Powered by Cross-Disciplinary Knowledge Agent</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import SearchPanel from '../components/SearchPanel.vue';
import AppHeader from '../components/AppHeader.vue';
import { useSearchStore } from '../stores/searchStore';
import { useGraphStore } from '../stores/graphStore';
import { useChatStore } from '../stores/chatStore';

const router = useRouter();
const searchStore = useSearchStore();
const graphStore = useGraphStore();
const chatStore = useChatStore();

const historyList = ref([]);
const isLoadingHistory = ref(false);

// 获取已构建的概念列表
async function fetchHistory() {
  isLoadingHistory.value = true;
  try {
    const concepts = await graphStore.fetchAvailableConcepts();
    historyList.value = concepts || [];
  } catch (error) {
    console.error('获取历史记录失败:', error);
    historyList.value = [];
  } finally {
    isLoadingHistory.value = false;
  }
}

// 刷新历史记录
async function refreshHistory() {
  await fetchHistory();
}

// 加载历史概念图谱
async function loadHistoryConcept(concept) {
  // 设置概念
  searchStore.setConcept(concept);
  chatStore.setConcept(concept);
  
  // 直接跳转到工作区
  router.push('/workspace');
}

async function handleSearch(concept) {
  searchStore.setConcept(concept);
  // Clear previous data
  searchStore.setDisciplines([]);
  router.push('/select-disciplines');
}

// 页面加载时获取历史记录
onMounted(() => {
  fetchHistory();
});
</script>

<style scoped>
.home-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: radial-gradient(circle at 50% 30%, #fff, #f8f9fa);
}

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 100%;
  padding: 0 20px;
  transform: translateY(-5vh);
}

/* 历史记录区域 */
.history-section {
  margin-top: 48px;
  width: 100%;
  max-width: 680px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.history-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin: 0;
}

.refresh-history-btn {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 6px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.refresh-history-btn:hover {
  background: var(--color-surface);
  color: var(--color-primary);
}

.refresh-history-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  font-size: 14px;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow-sm);
}

.history-item:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.history-item svg {
  color: var(--color-primary);
  opacity: 0.7;
}

.no-history {
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 14px;
  padding: 20px;
}

.history-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 48px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.mini-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.footer {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  color: var(--color-text-secondary);
  font-size: 12px;
  opacity: 0.6;
}
</style>
