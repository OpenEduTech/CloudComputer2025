<template>
  <PageContainer>
    <el-card>
      <template #header>
        <PageTitle title="知识扩充" subtitle="给知识点补充解释、公式、代码与外部资源">
          <template #icon>
            <el-icon><DataAnalysis /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-form :model="form" label-width="100px">
        <el-form-item label="文件ID">
          <FileIdField v-model="form.file_id" placeholder="请输入文件ID（上传后可复制）" />
        </el-form-item>

        <el-form-item label="知识点">
          <el-input
            v-model="form.query"
            type="textarea"
            :rows="3"
            placeholder="输入要扩充的知识点，例如：机器学习的基本概念"
          />
        </el-form-item>

        <el-form-item label="最大长度">
          <el-slider v-model="form.max_length" :min="200" :max="1000" show-input />
        </el-form-item>

        <el-form-item label="外部资源">
          <el-switch v-model="form.include_external" />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            @click="handleExpand"
          >
            {{ loading ? '扩充中...' : '开始扩充' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="result" class="result-card">
      <template #header>
        <PageTitle title="扩充结果" subtitle="可直接复制到笔记或复习卡片">
          <template #icon>
            <el-icon><Reading /></el-icon>
          </template>
          <template #extra>
            <el-button
              v-if="resultMarkdown"
              type="primary"
              @click="downloadResultMarkdown"
            >
              下载 Markdown
            </el-button>
            <el-button
              v-if="resultMarkdown"
              @click="showResultMarkdown = !showResultMarkdown"
            >
              {{ showResultMarkdown ? '收起Markdown预览' : '预览Markdown' }}
            </el-button>
          </template>
        </PageTitle>
      </template>

      <div class="expansion-content">
        <h3>知识点：{{ result.query }}</h3>
        <el-divider />

        <div class="explanation">
          <h4>详细解释</h4>
          <p>{{ result.expansion }}</p>
        </div>

        <div v-if="result.formulas && result.formulas.length > 0" class="formulas">
          <el-divider />
          <h4>相关公式</h4>
          <el-tag v-for="(formula, idx) in result.formulas" :key="idx" type="info" class="formula-tag">
            {{ formula }}
          </el-tag>
        </div>

        <div v-if="result.code_examples && result.code_examples.length > 0" class="code-examples">
          <el-divider />
          <h4>代码示例</h4>
          <div v-for="(example, idx) in result.code_examples" :key="idx" class="code-example">
            <p><strong>{{ example.description }}</strong></p>
            <el-input
              v-model="example.code"
              type="textarea"
              :rows="6"
              readonly
              class="code-block"
            />
          </div>
        </div>

        <div v-if="result.related_topics && result.related_topics.length > 0" class="related-topics">
          <el-divider />
          <h4>相关主题</h4>
          <el-tag
            v-for="(topic, idx) in result.related_topics"
            :key="idx"
            type="success"
            class="topic-tag"
          >
            {{ topic }}
          </el-tag>
        </div>

        <div v-if="result.external_resources && result.external_resources.length > 0" class="external-resources">
          <el-divider />
          <h4>外部资源</h4>
          <el-card
            v-for="(resource, idx) in result.external_resources"
            :key="idx"
            shadow="hover"
            class="resource-card"
          >
            <p><strong>{{ resource.source }}</strong>: {{ resource.title }}</p>
            <p class="summary">{{ resource.summary }}</p>
            <el-link :href="resource.url" target="_blank" type="primary">
              查看详情
            </el-link>
          </el-card>
        </div>

        <div v-if="showResultMarkdown && resultMarkdown" class="markdown-preview">
          <el-divider />
          <h4>Markdown 预览</h4>
          <div class="markdown-body" v-html="resultMarkdownHtml"></div>
        </div>
      </div>
    </el-card>

    <el-card v-if="history.length" class="result-card">
      <template #header>
        <PageTitle title="扩充历史" subtitle="最近的知识扩充记录">
          <template #icon>
            <el-icon><Reading /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-timeline>
        <el-timeline-item
          v-for="(item, idx) in visibleHistory"
          :key="idx"
          :timestamp="item.created_at"
        >
          <p><strong>{{ item.query }}</strong></p>
          <p class="summary">{{ item.expansion }}</p>
        </el-timeline-item>
      </el-timeline>

      <div v-if="history.length > 2" class="history-toggle">
        <el-button size="small" type="primary" @click="toggleHistory">
          {{ showAllHistory ? '收起' : '查看更多' }}
        </el-button>
      </div>
    </el-card>
  </PageContainer>
</template>

<script setup>
import PageContainer from '@/components/PageContainer.vue'
import PageTitle from '@/components/PageTitle.vue'
import FileIdField from '@/components/FileIdField.vue'

import { ref, watch, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Reading } from '@element-plus/icons-vue'
import { expandKnowledge, getKnowledgeHistory } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import MarkdownIt from 'markdown-it'

const workspaceStore = useWorkspaceStore()

const form = ref({
  file_id: '',
  query: '',
  max_length: 500,
  include_external: true,
  user_id: 'default',
})

const loading = ref(false)
const result = ref(null)
const history = ref([])
const showAllHistory = ref(false)
const showResultMarkdown = ref(false)
const md = new MarkdownIt({ linkify: true, breaks: true })
const visibleHistory = computed(() => {
  return showAllHistory.value ? history.value : history.value.slice(0, 2)
})

const toggleHistory = () => {
  showAllHistory.value = !showAllHistory.value
}

watch(
  () => workspaceStore.fileId,
  (fileId) => {
    if (!form.value.file_id && fileId) form.value.file_id = String(fileId)
  },
  { immediate: true }
)

watch(
  () => workspaceStore.userId,
  (userId) => {
    form.value.user_id = userId || 'default'
  },
  { immediate: true }
)

watch(
  () => form.value.file_id,
  (fileId) => {
    if (fileId !== workspaceStore.fileId) workspaceStore.setFileId(fileId)
  }
)

const handleExpand = async () => {
  if (!form.value.file_id) {
    ElMessage.warning('请输入文件ID')
    return
  }
  if (!form.value.query) {
    ElMessage.warning('请输入要扩充的知识点')
    return
  }

  loading.value = true
  result.value = null
  showResultMarkdown.value = false

  try {
    const res = await expandKnowledge(form.value)
    result.value = res
    if (res?.llm_validation) {
      workspaceStore.setLlmValidation(res.llm_validation)
    }
    ElMessage.success('知识扩充完成！')
    loadHistory()
  } catch (error) {
    console.error('知识扩充失败:', error)
  } finally {
    loading.value = false
  }
}

const resultMarkdown = computed(() => {
  return result.value?.markdown || ''
})

const resultMarkdownHtml = computed(() => {
  return resultMarkdown.value ? md.render(resultMarkdown.value) : ''
})

const downloadResultMarkdown = () => {
  const content = resultMarkdown.value
  if (!content) return
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const safeQuery = (result.value?.query || 'knowledge').toString().slice(0, 24).replace(/\s+/g, '-')
  a.download = `knowledge-${safeQuery}.md`
  a.click()
  URL.revokeObjectURL(url)
}

const loadHistory = async () => {
  try {
    const res = await getKnowledgeHistory(workspaceStore.userId, 20)
    history.value = res.items || []
  } catch (error) {
    console.error('加载扩充历史失败:', error)
  }
}

onMounted(() => {
  form.value.user_id = workspaceStore.userId
  loadHistory()
})
</script>

<style scoped>
.result-card {
  margin-top: 20px;
}

.expansion-content h3 {
  color: var(--el-text-color-primary);
  margin-bottom: 16px;
}

.expansion-content h4 {
  color: var(--el-text-color-secondary);
  margin: 16px 0 12px;
}

.explanation p {
  line-height: 1.8;
  color: var(--el-text-color-secondary);
  text-align: justify;
}

.formula-tag,
.topic-tag {
  margin: 4px 8px 4px 0;
}

.code-example {
  margin-bottom: 16px;
}

.code-block {
  background-color: var(--el-fill-color-lighter);
}

.resource-card {
  margin-bottom: 12px;
}

.summary {
  color: var(--el-text-color-secondary);
}

.history-toggle {
  margin-top: 12px;
  text-align: center;
}

.resource-card .summary {
  color: var(--el-text-color-secondary);
  margin: 8px 0;
}

.markdown-preview {
  margin-top: 10px;
}

.markdown-body {
  line-height: 1.7;
  color: var(--el-text-color-primary);
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4 {
  margin: 12px 0 8px;
}

.markdown-body ul {
  margin-left: 18px;
}
</style>
