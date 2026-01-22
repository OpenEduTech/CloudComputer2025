<template>
  <div class="topbar">
    <div class="topbar__left">
      <el-button class="collapse-btn" @click="$emit('toggle')">
        <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
      </el-button>

      <div class="brand" @click="$router.push('/')" role="button" tabindex="0">
        <el-icon class="brand__icon"><Reading /></el-icon>
        <div class="brand__text">SmartLecPPTKiller</div>
      </div>

      <el-breadcrumb separator="/" class="breadcrumb">
        <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="topbar__right">
      <div class="workspace">
        <div class="workspace__label">工作区文件ID</div>
        <el-input
          v-model="workspaceStore.fileId"
          placeholder="粘贴 file_id 后可快速跳转"
          size="small"
          class="workspace__input"
          clearable
        >
          <template #append>
            <el-button :disabled="!workspaceStore.fileId" @click="copy">复制</el-button>
          </template>
        </el-input>
        <el-button
          size="small"
          type="success"
          :disabled="!workspaceStore.fileId"
          @click="$router.push({ path: '/knowledge', query: { file_id: workspaceStore.fileId } })"
        >
          知识扩充
        </el-button>
        <el-button
          size="small"
          type="warning"
          :disabled="!workspaceStore.fileId"
          @click="$router.push({ path: '/practice', query: { file_id: workspaceStore.fileId } })"
        >
          练习
        </el-button>
        <el-divider direction="vertical" />
        <div class="validation-toggle">
          <span>LLM校验</span>
          <el-switch
            v-model="workspaceStore.llmValidationEnabled"
            @change="workspaceStore.setLlmValidationEnabled"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Fold, Expand, Reading } from '@element-plus/icons-vue'
import { useWorkspaceStore } from '@/stores/workspace'

defineEmits(['toggle'])

defineProps({
  collapsed: { type: Boolean, default: false },
})

const route = useRoute()
const workspaceStore = useWorkspaceStore()

const currentTitle = computed(() => route.meta?.title || '功能页')

const copy = async () => {
  if (!workspaceStore.fileId) return
  try {
    await navigator.clipboard.writeText(String(workspaceStore.fileId))
    ElMessage.success('已复制文件ID')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.topbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--app-surface);
}

.topbar__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.collapse-btn {
  padding: 6px 10px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.brand__icon {
  color: var(--el-color-primary);
}

.brand__text {
  font-weight: 700;
  color: var(--el-text-color-primary);
  max-width: 420px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.breadcrumb {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workspace {
  display: flex;
  align-items: center;
  gap: 8px;
}

.validation-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.workspace__label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.workspace__input {
  width: 320px;
}

@media (max-width: 980px) {
  .workspace__label {
    display: none;
  }

  .workspace__input {
    width: 220px;
  }
}

@media (max-width: 720px) {
  .breadcrumb {
    display: none;
  }

  .workspace__input {
    width: 180px;
  }
}
</style>
