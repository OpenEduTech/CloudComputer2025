<template>
  <PageContainer>
    <el-card>
      <template #header>
        <PageTitle title="错题本" subtitle="自动收集错题，支持复习标记与小灶补救">
          <template #icon>
            <el-icon><Notebook /></el-icon>
          </template>
          <template #extra>
            <el-button type="primary" @click="loadMistakes">刷新错题</el-button>
          </template>
        </PageTitle>
      </template>

      <el-descriptions v-if="stats" :column="2" border class="stats">
        <el-descriptions-item label="总错题数">{{ stats.total_mistakes }}</el-descriptions-item>
        <el-descriptions-item label="改进率">{{ (stats.improvement_rate * 100).toFixed(1) }}%</el-descriptions-item>
      </el-descriptions>

      <el-divider />
    </el-card>

    <el-card v-if="mistakes.length > 0" class="mistakes-card">
      <template #header>
        <h3>错题列表 ({{ mistakes.length }})</h3>
      </template>

      <el-collapse v-model="activeMistakes">
        <el-collapse-item
          v-for="(mistake, idx) in mistakes"
          :key="idx"
          :name="idx"
        >
          <template #title>
            <div class="mistake-title">
              <el-tag type="danger">错题 {{ idx + 1 }}</el-tag>
              <span class="mistake-topic">{{ getMistakeTopic(mistake) }}</span>
              <span class="timestamp">{{ formatTime(mistake.timestamp) }}</span>
            </div>
          </template>

          <div class="mistake-detail">
            <p v-if="mistake.question?.content"><strong>题目：</strong>{{ mistake.question.content }}</p>
            <div v-if="mistake.question?.options?.length">
              <p><strong>选项：</strong></p>
              <ul>
                <li v-for="opt in mistake.question.options" :key="opt.key">{{ opt.key }}. {{ opt.value }}</li>
              </ul>
            </div>
            <p><strong>您的答案：</strong>{{ mistake.evaluation.user_answer }}</p>
            <p><strong>正确答案：</strong>{{ mistake.evaluation.correct_answer }}</p>
            <p><strong>得分：</strong>{{ mistake.evaluation.score }}</p>
            
            <el-divider />
            
            <p><strong>详细反馈：</strong></p>
            <pre class="feedback">{{ mistake.evaluation.detailed_feedback }}</pre>
            
            <div v-if="mistake.evaluation.improvement_suggestions?.length > 0">
              <p><strong>改进建议：</strong></p>
              <ul>
                <li v-for="(suggestion, sIdx) in mistake.evaluation.improvement_suggestions" :key="sIdx">
                  {{ suggestion }}
                </li>
              </ul>
            </div>

            <el-divider />

            <div class="actions">
              <el-button size="small" type="success" @click="markReviewed(mistake.question_id)">
                标记已复习
              </el-button>
              <el-button size="small" type="primary" @click="openRemediation(mistake)">
                生成小灶
              </el-button>
              <el-button size="small" type="danger" @click="removeMistake(mistake.question_id)">
                从错题本移除
              </el-button>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <el-empty v-else-if="loaded && mistakes.length === 0" description="暂无错题记录" />

    <el-dialog v-model="remediationDialog" title="个性化小灶" width="700px">
      <el-alert
        type="info"
        show-icon
        :closable="false"
        title="系统将基于你的错题记录自动匹配用户画像与知识点"
      />

      <div class="remediation-actions">
        <el-button type="primary" :loading="remediationLoading" @click="handleRemediate">
        {{ remediationLoading ? '生成中...' : '生成小灶' }}
        </el-button>
        <el-button v-if="remediationResult?.markdown" @click="downloadMarkdown">下载Markdown</el-button>
      </div>

      <div v-if="remediationResult" class="remediation-result">
        <el-divider />
        <div class="markdown-body" v-html="remediationHtml"></div>
      </div>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import PageContainer from '@/components/PageContainer.vue'
import PageTitle from '@/components/PageTitle.vue'

import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Notebook } from '@element-plus/icons-vue'
import { getMistakes, getMistakeStats, markAsReviewed, removeMistake as apiRemoveMistake, remediateMistake } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import MarkdownIt from 'markdown-it'

const mistakes = ref([])
const stats = ref(null)
const activeMistakes = ref([])
const loaded = ref(false)
const remediationDialog = ref(false)
const remediationLoading = ref(false)
const remediationResult = ref(null)
const md = new MarkdownIt({ linkify: true, breaks: true })
const remediationForm = ref({
  question_id: '',
  user_id: 'default',
})

const workspaceStore = useWorkspaceStore()

const loadMistakes = async () => {
  try {
    const res = await getMistakes(20, workspaceStore.userId)
    mistakes.value = res.mistakes || []
    loaded.value = true
    
    const statsRes = await getMistakeStats(workspaceStore.userId)
    stats.value = statsRes
  } catch (error) {
    console.error('加载错题失败:', error)
    loaded.value = true
  }
}

const markReviewed = async (questionId) => {
  try {
    await markAsReviewed(questionId, workspaceStore.userId)
    ElMessage.success('已标记为复习')
    loadMistakes()
  } catch (error) {
    console.error('标记失败:', error)
  }
}

const removeMistake = async (questionId) => {
  try {
    await ElMessageBox.confirm('确定要从错题本中移除吗？', '提示', {
      type: 'warning',
    })
    
    await apiRemoveMistake(questionId, workspaceStore.userId)
    ElMessage.success('已移除')
    loadMistakes()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('移除失败:', error)
    }
  }
}

const openRemediation = (mistake) => {
  remediationForm.value = {
    question_id: mistake.question_id,
    user_id: workspaceStore.userId,
  }
  remediationResult.value = null
  remediationDialog.value = true
}

const handleRemediate = async () => {
  remediationLoading.value = true
  try {
    const res = await remediateMistake(remediationForm.value)
    remediationResult.value = res
  } catch (error) {
    console.error('生成小灶失败:', error)
  } finally {
    remediationLoading.value = false
  }
}

const remediationMarkdown = computed(() => {
  return remediationResult.value?.markdown || ''
})

const remediationHtml = computed(() => {
  return remediationMarkdown.value ? md.render(remediationMarkdown.value) : ''
})

const downloadMarkdown = () => {
  const content = remediationMarkdown.value
  if (!content) return
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `remediation-${remediationForm.value.question_id}.md`
  a.click()
  URL.revokeObjectURL(url)
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}

const getMistakeTopic = (mistake) => {
  const tags = mistake?.question?.tags || []
  if (tags.length) return tags[0]
  const title = mistake?.question?.content || ''
  return title.length > 18 ? `${title.slice(0, 18)}...` : (title || '未命名题目')
}

onMounted(() => {
  loadMistakes()
})
</script>

<style scoped>
.stats {
  margin-bottom: 20px;
}

.mistakes-card {
  margin-top: 20px;
}

.mistake-title {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.mistake-topic {
  color: var(--el-text-color-primary);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 420px;
}

.timestamp {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin-left: auto;
}

.mistake-detail p {
  margin: 12px 0;
}

.feedback {
  background-color: var(--el-fill-color-lighter);
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.6;
  margin: 12px 0;
}

.mistake-detail ul {
  margin-left: 20px;
}

.actions {
  display: flex;
  gap: 12px;
}

.remediation-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
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

.remediation-result h4 {
  margin: 12px 0 6px;
}

.remediation-result p {
  margin: 6px 0;
}
</style>
