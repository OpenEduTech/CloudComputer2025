<template>
  <el-container class="shell">
    <el-aside class="shell__aside" :width="collapsed ? '64px' : '220px'">
      <SideNav :collapsed="collapsed" />
    </el-aside>

    <el-container class="shell__main">
      <el-header class="shell__header" height="56px">
        <TopBar :collapsed="collapsed" @toggle="collapsed = !collapsed" />
      </el-header>

      <el-main class="shell__content">
        <slot />
      </el-main>

      <el-drawer
        v-model="workspaceStore.llmValidationOpen"
        title="LLM结果校验"
        size="360px"
        direction="rtl"
        :with-header="true"
        :lock-scroll="false"
        @close="workspaceStore.closeLlmValidation"
      >
        <div v-if="workspaceStore.llmValidation">
          <p><strong>类型：</strong>{{ workspaceStore.llmValidation.kind }}</p>
          <p><strong>通过：</strong>{{ workspaceStore.llmValidation.valid ? '是' : '否' }}</p>

          <div v-if="workspaceStore.llmValidation.issues?.length">
            <p><strong>问题：</strong></p>
            <ul>
              <li v-for="(item, idx) in workspaceStore.llmValidation.issues" :key="idx">{{ item }}</li>
            </ul>
          </div>

          <div v-if="workspaceStore.llmValidation.warnings?.length">
            <p><strong>告警：</strong></p>
            <ul>
              <li v-for="(item, idx) in workspaceStore.llmValidation.warnings" :key="idx">{{ item }}</li>
            </ul>
          </div>

          <div v-if="workspaceStore.llmValidation.raw_preview">
            <p><strong>原始预览：</strong></p>
            <pre class="validation-preview">{{ workspaceStore.llmValidation.raw_preview }}</pre>
          </div>
        </div>
        <el-empty v-else description="暂无校验信息" />
      </el-drawer>

      <el-footer class="shell__footer" height="auto">
        <AppFooter />
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import SideNav from './SideNav.vue'
import TopBar from './TopBar.vue'
import AppFooter from './AppFooter.vue'
import { useWorkspaceStore } from '@/stores/workspace'

const collapsed = ref(false)
const route = useRoute()
const workspaceStore = useWorkspaceStore()
let validationTimer = null

watch(
  () => route.query?.file_id,
  (fileId) => {
    if (fileId) workspaceStore.setFileId(fileId)
  },
  { immediate: true }
)

watch(
  () => workspaceStore.llmValidationOpen,
  (open) => {
    if (validationTimer) {
      clearTimeout(validationTimer)
      validationTimer = null
    }
    if (open) {
      validationTimer = setTimeout(() => {
        workspaceStore.closeLlmValidation()
        validationTimer = null
      }, 3000)
    }
  }
)

onMounted(async () => {
  const existing = workspaceStore.initLlmValidationPreference()
  if (existing !== null) return
  try {
    await ElMessageBox.confirm(
      '是否启用 LLM 校验弹层提示？',
      '提示',
      { confirmButtonText: '启用', cancelButtonText: '不启用', type: 'info' }
    )
    workspaceStore.setLlmValidationEnabled(true)
  } catch (e) {
    workspaceStore.setLlmValidationEnabled(false)
  }
})
</script>

<style scoped>
.shell {
  min-height: 100vh;
  background: var(--app-bg);
}

.shell__aside {
  background: var(--app-surface-alt);
  border-right: 1px solid rgba(37, 99, 235, 0.12);
}

.shell__main {
  min-width: 0;
}

.shell__header {
  padding: 0;
}

.shell__content {
  padding: 0;
  background: var(--app-bg);
}

.shell__footer {
  padding: 0;
}

.validation-preview {
  background: var(--el-fill-color-lighter);
  padding: 8px;
  border-radius: 6px;
  white-space: pre-wrap;
  line-height: 1.5;
}
</style>
