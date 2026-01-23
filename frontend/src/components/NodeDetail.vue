<template>
  <div v-if="graphStore.selectedNode" class="node-detail-card">
    <div class="header">
      <h3 class="title">{{ graphStore.selectedNode.id }}</h3>
      <button class="close-btn" @click="graphStore.selectedNode = null">
        ×
      </button>
    </div>
    
    <div class="badge" :style="{ backgroundColor: 'var(--color-primary)' }">
      {{ graphStore.selectedNode.group }}
    </div>

    <!-- 原始文本展示区 -->
    <div class="section" v-if="relatedChunks.length > 0">
      <div class="section-title">相关原始文献</div>
      <div class="chunks-container">
        <div 
          v-for="chunk in relatedChunks" 
          :key="chunk.doc_id" 
          class="chunk-item"
        >
          <div class="chunk-content">{{ chunk.content.slice(0, 100) }}...</div>
          <a class="source-link" @click.prevent="openChunk(chunk)">查看全文</a>
        </div>
      </div>
    </div>
    
    <div class="actions">
      <button class="action-btn primary" @click="askAbout">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
        在对话中探索
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, ref } from 'vue';
import { useGraphStore } from '../stores/graphStore';
import { useChatStore } from '../stores/chatStore';

const graphStore = useGraphStore();
const chatStore = useChatStore();
const relatedChunks = ref([]);

// 监听选中节点变化，加载相关文档
watch(() => graphStore.selectedNode, async (newNode) => {
  relatedChunks.value = [];
  if (newNode && newNode.sourceChunks && newNode.sourceChunks.length > 0) {
    // 仅加载前 3 个相关文档，避免请求过多
    const chunksToLoad = newNode.sourceChunks.slice(0, 3);
    const chunks = await Promise.all(
      chunksToLoad.map(cid => graphStore.fetchChunk(cid))
    );
    relatedChunks.value = chunks.filter(c => c);
  }
}, { immediate: true });

function askAbout() {
  const node = graphStore.selectedNode;
  if (node) {
    chatStore.sendMessage(`能详细介绍一下"${node.id}"在${node.group}中的应用吗？`);
  }
}

function openChunk(chunk) {
  // TODO: 使用 Modal 或展开展示全文
  console.log('Open chunk:', chunk);
  alert(chunk.content);
}
</script>

<style scoped>
.node-detail-card {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 320px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  padding: 24px;
  border: 1px solid var(--color-border);
  backdrop-filter: blur(12px);
  z-index: 100;
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-10px) translateX(10px); }
  to { opacity: 1; transform: translateY(0) translateX(0); }
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  line-height: 1.4;
  color: var(--color-text-primary);
}

.close-btn {
  background: none;
  border: none;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.badge {
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: 6px;
  color: white;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  background-color: var(--color-primary); /* Default fallback */
}

.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.chunks-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.chunk-item {
  background: var(--color-surface);
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.chunk-item:hover {
  border-color: var(--color-border);
  background: white;
}

.chunk-content {
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin-bottom: 4px;
}

.source-link {
  color: var(--color-primary);
  font-size: 12px;
  text-decoration: none;
  cursor: pointer;
  font-weight: 500;
}

.source-link:hover {
  text-decoration: underline;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.action-btn {
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.action-btn:hover {
  background: var(--color-surface);
  transform: translateY(-1px);
}

.action-btn.primary {
  background: var(--color-text-primary);
  color: white;
  border: 1px solid transparent;
  box-shadow: var(--shadow-md);
}

.action-btn.primary:hover {
  background: #111;
  box-shadow: var(--shadow-lg);
}
</style>
