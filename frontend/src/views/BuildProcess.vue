<template>
  <div class="build-process-view">
    <AppHeader :title="searchStore.currentConcept || '正在处理...'">
      <ProgressSteps :current-step="3" />
    </AppHeader>

    <main class="main-content">
      <div class="process-container">
        <div class="header-section">
          <h2>正在构建知识图谱</h2>
          <p class="subtitle">AI正在为您进行跨学科搜索并整合知识，请稍候...</p>
        </div>

        <div class="process-visualization">
          <div 
            v-for="(label, key) in displayStages" 
            :key="key" 
            class="process-step" 
            :class="getStepStatus(key)"
          >
            <div class="step-indicator">
              <div class="line" v-if="key !== Object.keys(displayStages)[0]"></div>
              <div class="icon-wrapper">
                <span v-if="getStepStatus(key) === 'completed'" class="icon-check">✓</span>
                <span v-else-if="getStepStatus(key) === 'active'" class="spinner-small"></span>
                <span v-else class="icon-dot">•</span>
              </div>
            </div>
            
            <div class="step-content">
              <div class="step-title">{{ label }}</div>
              <div class="step-desc" v-if="getStepStatus(key) === 'active'">
                {{ getActiveDescription(key) }}
              </div>
            </div>
          </div>
        </div>
        
        <div class="progress-section">
           <div class="progress-bar-container">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: searchStore.searchProgress.overall + '%' }"></div>
              </div>
              <span class="progress-text">{{ searchStore.searchProgress.overall }}%</span>
           </div>
           
           <div class="logs-section" v-if="searchStore.partialResults.totalChunksFound > 0">
              <div class="log-item">
                <span class="log-icon">🔍</span>
                <span>已发现 {{ searchStore.partialResults.totalChunksFound }} 个相关的知识片段</span>
              </div>
           </div>
        </div>

        <div class="actions-section">
          <button class="cancel-btn" @click="cancelBuild">取消任务</button>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useSearchStore } from '../stores/searchStore';
import { useGraphStore } from '../stores/graphStore';
import AppHeader from '../components/AppHeader.vue';
import ProgressSteps from '../components/ProgressSteps.vue';

const router = useRouter();
const searchStore = useSearchStore();
const graphStore = useGraphStore();

const displayStages = {
  'classification': '概念领域分析',
  'search': '全网跨学科搜索',
  'aggregation': '知识结构化聚合',
  'validation': '逻辑一致性验证',
  'completed': '图谱生成'
};

// 映射后端状态到前端显示的顺序
const stageOrder = ['pending', 'classification', 'search', 'aggregation', 'validation', 'completed'];

function getStepStatus(stageKey) {
  const currentStage = searchStore.searchProgress.currentStage || 'pending';
  
  // 如果当前是 completed，所有步骤都完成
  if (currentStage === 'completed' && stageKey !== 'completed') return 'completed';
  if (currentStage === 'completed' && stageKey === 'completed') return 'active'; // or completed

  // 特殊处理：如果是 completed 阶段，我们希望 'completed' key 显示为 active 或者 finishing
  // 但实际上后端到了 completed 就会跳转。
  
  const currentIndex = stageOrder.indexOf(currentStage);
  const stageIndex = stageOrder.indexOf(stageKey);

  if (stageIndex < currentIndex) return 'completed';
  if (stageIndex === currentIndex) return 'active';
  return 'pending';
}

function getActiveDescription(stageKey) {
  switch(stageKey) {
    case 'classification': return '正在分析该概念涉及的学科领域...';
    case 'search': return '正在从各个学科视角检索相关资料...';
    case 'aggregation': return '正在对检索到的碎片知识进行整合...';
    case 'validation': return '正在验证知识之间的逻辑关系...';
    case 'completed': return '即将进入可视化工作区...';
    default: return '处理中...';
  }
}

let pollInterval = null;

async function pollStatus() {
  if (!searchStore.currentTaskId) {
      // 模拟演示模式：如果没有任务ID（直接访问页面），则模拟进度
      if (!searchStore.currentConcept) {
          searchStore.currentConcept = "演示概念";
      }
      
      // 模拟进度增加
      if (searchStore.searchProgress.overall < 100) {
          searchStore.searchProgress.overall += 2;
          
          if (searchStore.searchProgress.overall < 20) searchStore.searchProgress.currentStage = 'classification';
          else if (searchStore.searchProgress.overall < 50) searchStore.searchProgress.currentStage = 'search';
          else if (searchStore.searchProgress.overall < 80) searchStore.searchProgress.currentStage = 'aggregation';
          else if (searchStore.searchProgress.overall < 95) searchStore.searchProgress.currentStage = 'validation';
          else {
            searchStore.searchProgress.currentStage = 'completed';
            searchStore.searchStatus = 'completed';
          }
          
          if (searchStore.searchProgress.currentStage === 'search') {
            searchStore.partialResults.totalChunksFound += Math.floor(Math.random() * 3);
          }
      } else {
        // 完成模拟
        stopPolling();
        setTimeout(() => {
          router.push('/workspace'); 
        }, 1500);
      }
      
      return;
  }
  
  try {
    await searchStore.pollSearchStatus();
    
    if (searchStore.searchStatus === 'completed') {
      stopPolling();
      // 等待一点时间展示 100%
      setTimeout(async () => {
         // 获取图谱数据
         await graphStore.fetchGraph(searchStore.currentConcept);
         // 跳转
         router.push('/workspace');
      }, 1500);
    } else if (searchStore.searchStatus === 'failed' || searchStore.searchStatus === 'cancelled') {
      stopPolling();
      alert('搜索失败或被取消');
      // 可以提供重试按钮，这里简单处理
      router.push('/select-disciplines');
    }
  } catch (error) {
    console.error('轮询状态失败:', error);
  }
}

function startPolling() {
  if (pollInterval) return;
  // 立即执行一次
  pollStatus();
  pollInterval = setInterval(pollStatus, 1500);
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

onMounted(() => {
  if (!searchStore.currentTaskId) {
     console.log('No task ID found, entering demo mode...');
     // 初始化模拟数据
     searchStore.searchProgress = {
       overall: 0,
       currentStage: 'pending',
       stages: {}
     };
     searchStore.partialResults = {
       totalChunksFound: 0
     };
  }
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});

async function cancelBuild() {
  if (confirm('确定要取消当前构建任务吗？')) {
    await searchStore.cancelSearch();
    stopPolling();
    router.push('/select-disciplines');
  }
}

</script>

<style scoped>
.build-process-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-background);
}

.main-content {
  flex: 1;
  display: flex;
  justify-content: center;
  padding-top: 60px;
  overflow-y: auto;
}

.process-container {
  width: 100%;
  max-width: 600px;
  padding: 0 20px;
}

.header-section {
  text-align: center;
  margin-bottom: 40px;
}

h2 {
  font-size: 24px;
  margin-bottom: 8px;
  color: var(--color-text-primary);
}

.subtitle {
  color: var(--color-text-secondary);
}

.process-visualization {
  background: white;
  border-radius: 16px;
  padding: 30px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 30px;
}

.process-step {
  display: flex;
  position: relative;
  min-height: 60px; /* Space for content */
}

/* Step Indicator Setup */
.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-right: 20px;
  position: relative;
  width: 24px; 
}

.process-step:last-child .step-indicator {
    height: auto;
}

/* Vertical Line */
.line {
  position: absolute;
  top: -30px; /* Connect to previous */
  bottom: 12px;
  width: 2px;
  background-color: var(--color-border);
  z-index: 0;
}

.process-step:first-child .line {
  display: none;
}

/* Icon Wrapper */
.icon-wrapper {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: white;
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  margin-top: 2px; /* Align with text top */
  transition: all 0.3s ease;
}

.icon-check {
  font-size: 14px;
  font-weight: bold;
}

.icon-dot {
  font-size: 24px;
  line-height: 10px;
  color: var(--color-text-secondary);
}

/* Styles based on status */
.process-step.completed .icon-wrapper {
  background-color: #34A853;
  border-color: #34A853;
  color: white;
}
.process-step.completed .line {
  background-color: #34A853; /* Completed lines are green */
}

.process-step.active .icon-wrapper {
  border-color: var(--color-primary);
  /* color depends on spinner */
}

.process-step.pending .icon-wrapper {
  border-color: var(--color-border);
  color: var(--color-text-tertiary);
}

/* Step Content */
.step-content {
  flex: 1;
  padding-bottom: 24px;
}

.process-step:last-child .step-content {
  padding-bottom: 0;
}

.step-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: color 0.3s;
  margin-bottom: 4px;
}

.process-step.active .step-title {
  color: var(--color-text-primary);
  font-weight: 600;
}

.process-step.completed .step-title {
  color: var(--color-text-primary);
}

.step-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  animation: fadeIn 0.5s ease;
}

/* Progress Bar at bottom */
.progress-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: var(--color-surface);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  width: 40px;
  text-align: right;
}

.logs-section {
    padding-top: 10px;
    border-top: 1px solid var(--color-border);
}

.log-item {
    font-size: 13px;
    color: var(--color-text-secondary);
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Utilities */
.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-primary);
  border-top: 2px solid transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

.actions-section {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  margin-bottom: 24px;
}

.cancel-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  padding: 8px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.cancel-btn:hover {
  background: white;
  color: #ef4444;
  border-color: #ef4444;
}
</style>
