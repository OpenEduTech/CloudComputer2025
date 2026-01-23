<script setup>
import { ref } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const isCollapsed = ref(false)

const toggle = () => {
  if (props.node?.children?.length) {
    isCollapsed.value = !isCollapsed.value
  }
}
</script>

<template>
  <div class="tree-node">
    <div class="node-header" @click="toggle">
      <span v-if="node.children?.length" class="toggle">
        {{ isCollapsed ? '＋' : '－' }}
      </span>
      <span v-else class="leaf-dot">•</span>
      <span class="label">{{ node.label }}</span>
    </div>

    <div v-if="node.children?.length && !isCollapsed" class="children">
      <MindmapTree
        v-for="child in node.children"
        :key="child.id"
        :node="child"
      />
    </div>
  </div>
</template>

<style scoped>
.tree-node {
  margin-left: 12px;
  padding-left: 8px;
  border-left: 1px dashed #e2e8f0;
}

.node-header {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 8px;
  background: #f8fafc;
  color: #1e293b;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}

.node-header:hover {
  background: #eef2ff;
  transform: translateY(-1px);
}

.toggle {
  font-weight: 700;
  color: #3b82f6;
  width: 16px;
  text-align: center;
}

.leaf-dot {
  color: #94a3b8;
  width: 12px;
  text-align: center;
}

.label {
  font-size: 0.95rem;
  white-space: nowrap;
}

.children {
  margin-left: 8px;
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>

