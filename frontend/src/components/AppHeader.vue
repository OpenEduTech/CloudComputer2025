<template>
  <header class="app-header">
    <div class="left-section">
      <div class="branding" @click="handleNew">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="logo-icon"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
        <span class="site-name">Cross Learning</span>
      </div>
    </div>
    
    <div class="center-section">
      <h2 class="concept-title" v-if="title">{{ title }}</h2>
    </div>
    
    <div class="right-section">
      <div class="slot-content">
        <slot></slot>
      </div>
      <button class="new-btn" @click="handleNew">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        发起新探索
      </button>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router';

defineProps({
  title: {
    type: String,
    default: ''
  }
});

const router = useRouter();

function handleNew() {
  router.push('/');
}
</script>

<style scoped>
.app-header {
  height: 64px;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: white;
  z-index: 10;
  width: 100%;
  flex-shrink: 0;
  color: var(--color-text-primary);
}

.left-section {
  flex: 1;
  display: flex;
  align-items: center;
}

.branding {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text-primary);
  cursor: pointer;
}

.logo-icon {
  stroke-width: 2.5;
}

.site-name {
  font-weight: 700;
  font-size: 20px;
  letter-spacing: -0.5px;
  color: var(--color-text-primary);
}

.center-section {
  flex: 2;
  display: flex;
  justify-content: center;
  align-items: center;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.right-section {
  flex: 1; 
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 24px;
  margin-left: auto;
}

.concept-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  white-space: nowrap;
  text-align: center;
}

.slot-content {
  display: flex;
  align-items: center;
}

.new-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 6px;
  background: var(--color-text-primary);
  border: 1px solid var(--color-text-primary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: white;
  transition: all 0.2s;
  height: 36px;
}

.new-btn:hover {
  background: white;
  color: var(--color-text-primary);
}
</style>
