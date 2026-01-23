<template>
  <div class="search-container" :class="{ 'compact': isCompact }">
    <h1 v-if="!isCompact" class="title">探索跨学科知识</h1>
    
    <div class="search-box">
      <div class="icon-wrapper">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
      </div>
      <textarea 
        v-model="query" 
        @keydown.enter.prevent="handleEnter"
        @input="autoResize"
        ref="textareaRef"
        placeholder="输入你所感兴趣的概念，例如：熵、神经网络、最小二乘法..."
        class="search-input"
        autofocus
        rows="1"
      ></textarea>
      <button v-if="query" @click="clearQuery" class="clear-btn">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>

    <div v-if="!isCompact" class="suggestions">
      <button @click="quickSearch('熵')" class="suggestion-pill">熵</button>
      <button @click="quickSearch('最小二乘法')" class="suggestion-pill">最小二乘法</button>
      <button @click="quickSearch('神经网络')" class="suggestion-pill">神经网络</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue';

const props = defineProps({
  isCompact: Boolean
});

const emit = defineEmits(['search']);
const query = ref('');
const textareaRef = ref(null);

function autoResize() {
  const el = textareaRef.value;
  if (el) {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }
}

function handleEnter(e) {
  if (!e.shiftKey) {
    handleSearch();
  }
}

function handleSearch() {
  if (query.value.trim()) {
    emit('search', query.value.trim());
  }
}

function clearQuery() {
  query.value = '';
  nextTick(() => {
    autoResize();
    textareaRef.value?.focus();
  });
}

function quickSearch(term) {
  query.value = term;
  nextTick(() => {
    autoResize();
    handleSearch();
  });
}
</script>

<style scoped>
.search-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 680px;
  margin: 0 auto;
  transition: all 0.3s ease;
}

.title {
  font-size: 3rem;
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 2rem;
  letter-spacing: -1px;
}

.search-box {
  width: 100%;
  min-height: 56px;
  height: auto;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 28px;
  display: flex;
  align-items: flex-start;
  padding: 4px 16px;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.search-box:hover, .search-box:focus-within {
  box-shadow: var(--shadow-md);
  border-color: transparent;
  transform: translateY(-1px);
}

.icon-wrapper {
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  margin-right: 12px;
  margin-top: 12px;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 16px;
  min-height: 24px;
  color: var(--color-text-primary);
  resize: none;
  overflow: hidden;
  font-family: inherit;
  background: transparent;
  padding: 12px 0;
  line-height: 1.5;
}

.clear-btn {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  margin-top: 8px;
}

.clear-btn:hover {
  background: var(--color-surface);
}

.suggestions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

.suggestion-pill {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 8px 16px;
  border-radius: 100px;
  font-size: 14px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-pill:hover {
  background: white;
  border-color: var(--color-text-secondary);
  color: var(--color-text-primary);
}

/* Compact Mode (for header) */
.compact .title {
  display: none;
}

.compact .suggestions {
  display: none;
}

.compact .search-box {
  height: 44px;
  background: var(--color-surface);
  border: none;
  box-shadow: none;
}

.compact .search-box:focus-within {
  background: white;
  box-shadow: var(--shadow-sm);
}
</style>
