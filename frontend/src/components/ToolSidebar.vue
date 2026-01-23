<script setup>
defineProps({
  activeTool: String
})

const emit = defineEmits(['tool-change'])

const tools = [
  { id: 'explain', icon: '🧠', label: '深度解析' },
  { id: 'state-of-art', icon: '🕸️', label: '思维导图' },
  { id: 'search', icon: '🔍', label: '语义搜索' },
  { id: 'external-search', icon: '🌐', label: '外部资源' },
  { id: 'chat', icon: '💬', label: 'AI 问答' }
]
</script>

<template>
  <div class="tool-sidebar">
    <div class="logo-area">
      <span class="mini-logo">🧬</span>
    </div>

    <nav class="tools-nav">
      <button
        v-for="tool in tools"
        :key="tool.id"
        :class="['tool-btn', { active: activeTool === tool.id }]"
        @click="$emit('tool-change', tool.id)"
        :title="tool.label"
      >
        <span class="tool-icon">{{ tool.icon }}</span>
        <span class="tool-tooltip">{{ tool.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <button class="tool-btn" title="设置">⚙️</button>
    </div>
  </div>
</template>

<style scoped>
.tool-sidebar {
  width: 60px;
  background: #1e293b;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem 0;
  z-index: 10;
  box-shadow: 2px 0 10px rgba(0,0,0,0.1);
}

.logo-area {
  margin-bottom: 2rem;
}

.mini-logo {
  font-size: 1.5rem;
}

.tools-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 100%;
}

.tool-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tool-btn:hover {
  background: rgba(255,255,255,0.1);
  color: white;
}

.tool-btn.active {
  background: #3b82f6;
  color: white;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.tool-tooltip {
  position: absolute;
  left: 50px;
  background: #0f172a;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  opacity: 0;
  visibility: hidden;
  transition: 0.2s;
  white-space: nowrap;
  pointer-events: none;
}

.tool-btn:hover .tool-tooltip {
  opacity: 1;
  visibility: visible;
}

.sidebar-footer {
  margin-top: auto;
}
</style>
