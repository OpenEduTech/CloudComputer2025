<template>
  <header class="app-header">
    <div class="app-header__inner">
      <div class="app-brand" @click="$router.push('/')" role="button" tabindex="0">
        <el-icon class="app-brand__icon" :size="26"><Reading /></el-icon>
        <div class="app-brand__text">
          <div class="app-brand__title">SmartLecPPTKiller</div>
          <div class="app-brand__subtitle">Cloud-native · LLM Agents</div>
        </div>
      </div>

      <el-menu
        class="app-nav"
        :default-active="activeIndex"
        mode="horizontal"
        router
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/upload">上传与解析</el-menu-item>
        <el-menu-item index="/knowledge">知识扩充</el-menu-item>
        <el-menu-item index="/external-search">外部搜索</el-menu-item>
        <el-menu-item index="/practice">练习测验</el-menu-item>
        <el-menu-item index="/mistakes">错题本</el-menu-item>
        <el-menu-item index="/team">项目组介绍</el-menu-item>
      </el-menu>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Reading } from '@element-plus/icons-vue'

const route = useRoute()
const activeIndex = computed(() => route.path)
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--app-surface);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.app-header__inner {
  max-width: var(--app-max-width);
  margin: 0 auto;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.app-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.app-brand:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
  border-radius: 8px;
}

.app-brand__icon {
  color: var(--el-color-primary);
}

.app-brand__text {
  display: flex;
  font-size: 14px;
  line-height: 1.15;
  max-width: 420px;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-brand__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.app-brand__subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.app-nav {
  flex: 1;
  justify-content: flex-end;
  background: transparent;
  border-bottom: none;
  overflow-x: auto;
}

:deep(.el-menu--horizontal) {
  border-bottom: none;
}

:deep(.el-menu--horizontal .el-menu-item) {
  border-bottom: 2px solid transparent;
  height: 44px;
  line-height: 44px;
}

:deep(.el-menu--horizontal .el-menu-item:hover) {
  background: var(--el-fill-color-light);
}

:deep(.el-menu--horizontal .el-menu-item.is-active) {
  border-bottom-color: var(--el-color-primary);
}

@media (max-width: 720px) {
  .app-header__inner {
    flex-wrap: wrap;
    gap: 10px;
  }

  .app-nav {
    justify-content: flex-start;
    width: 100%;
  }
}
</style>
