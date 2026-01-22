<template>
  <PageContainer>
    <!-- 步骤1: 配置题目 -->
    <el-card v-if="!questions.length">
      <template #header>
        <PageTitle title="生成练习题" subtitle="从指定文件中检索上下文并自动出题">
          <template #icon>
            <el-icon><EditPen /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-form :model="form" label-width="120px">
        <el-form-item label="文件ID">
          <FileIdField v-model="form.file_id" placeholder="请输入文件ID（上传后可复制）" />
        </el-form-item>

        <el-form-item label="知识点定位">
          <el-input v-model="form.focus_query" placeholder="例如：链式法则 / 卷积神经网络" />
        </el-form-item>

        <el-form-item label="检索TopK">
          <el-input-number v-model="form.top_k" :min="1" :max="10" />
        </el-form-item>

        <el-form-item label="严格上下文">
          <el-switch v-model="form.strict_context" />
        </el-form-item>

        <el-form-item label="题目数量">
          <el-input-number v-model="form.num_questions" :min="1" :max="20" />
        </el-form-item>

        <el-form-item label="题目类型">
          <el-checkbox-group v-model="form.question_types">
            <el-checkbox label="choice">选择题</el-checkbox>
            <el-checkbox label="short_answer">简答题</el-checkbox>
            <el-checkbox label="true_false">判断题</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="难度等级">
          <el-checkbox-group v-model="form.difficulty_levels">
            <el-checkbox label="easy">简单</el-checkbox>
            <el-checkbox label="medium">中等</el-checkbox>
            <el-checkbox label="hard">困难</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="generating" @click="handleGenerate">
            {{ generating ? '生成中...' : '生成题目' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 步骤2: 答题 -->
    <el-card v-else>
      <template #header>
        <PageTitle
          :title="`练习测验 (${currentIndex + 1} / ${questions.length})`"
          subtitle="逐题作答，最后统一评测"
        >
          <template #icon>
            <el-icon><EditPen /></el-icon>
          </template>
        </PageTitle>
      </template>

      <div v-if="currentQuestion" class="question-container">
        <el-tag :type="getDifficultyType(currentQuestion.difficulty)" class="difficulty-tag">
          {{ getDifficultyText(currentQuestion.difficulty) }}
        </el-tag>

        <h3>{{ currentIndex + 1 }}. {{ currentQuestion.content }}</h3>

        <!-- 选择题 -->
        <el-radio-group
          v-if="currentQuestion.question_type === 'choice'"
          v-model="answers[currentIndex]"
          class="answer-group"
        >
          <el-radio
            v-for="option in currentQuestion.options"
            :key="option.key"
            :label="option.key"
            class="answer-option"
          >
            {{ option.key }}. {{ option.value }}
          </el-radio>
        </el-radio-group>

        <!-- 简答题/判断题 -->
        <el-input
          v-else
          v-model="answers[currentIndex]"
          type="textarea"
          :rows="4"
          placeholder="请输入您的答案"
          class="answer-input"
        />

        <div class="button-group">
          <el-button
            v-if="currentIndex > 0"
            @click="currentIndex--"
          >
            上一题
          </el-button>
          <el-button
            v-if="currentIndex < questions.length - 1"
            type="primary"
            @click="currentIndex++"
          >
            下一题
          </el-button>
          <el-button
            v-if="currentIndex === questions.length - 1"
            type="success"
            @click="handleSubmit"
          >
            提交答卷
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 步骤3: 查看结果 -->
    <el-card v-if="evaluations.length > 0" class="result-card">
      <template #header>
        <PageTitle title="评测结果" subtitle="支持语义相似度与详细反馈">
          <template #icon>
            <el-icon><Trophy /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-descriptions :column="2" border class="stats">
        <el-descriptions-item label="总题数">{{ questions.length }}</el-descriptions-item>
        <el-descriptions-item label="正确题数">{{ correctCount }}</el-descriptions-item>
        <el-descriptions-item label="平均分">{{ averageScore.toFixed(1) }}</el-descriptions-item>
        <el-descriptions-item label="正确率">{{ (correctRate * 100).toFixed(1) }}%</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <el-collapse v-model="activeEvaluations">
        <el-collapse-item
          v-for="(evaluation, idx) in evaluations"
          :key="idx"
          :name="idx"
        >
          <template #title>
            <span :class="evaluation.is_correct ? 'correct' : 'wrong'">
              {{ evaluation.is_correct ? '✓' : '✗' }}
              第 {{ idx + 1 }} 题 - 得分: {{ evaluation.score }}
            </span>
          </template>
          <div class="evaluation-detail">
            <p><strong>您的答案：</strong>{{ evaluation.user_answer }}</p>
            <p><strong>正确答案：</strong>{{ evaluation.correct_answer }}</p>
            <p v-if="evaluation.semantic_similarity !== null && evaluation.semantic_similarity !== undefined">
              <strong>语义相似度：</strong>{{ evaluation.semantic_similarity.toFixed(3) }}
            </p>
            <p v-if="evaluation.error_type">
              <strong>错误类型：</strong>{{ evaluation.error_type }}
            </p>
            <p v-if="evaluation.alignment_score !== null && evaluation.alignment_score !== undefined">
              <strong>对齐评分：</strong>{{ evaluation.alignment_score }}
            </p>
            <p v-if="evaluation.alignment_summary">
              <strong>对齐简述：</strong>{{ evaluation.alignment_summary }}
            </p>
            <p><strong>详细反馈：</strong></p>
            <pre class="feedback">{{ evaluation.detailed_feedback }}</pre>
            <div v-if="evaluation.improvement_suggestions.length > 0">
              <p><strong>改进建议：</strong></p>
              <ul>
                <li v-for="(suggestion, sIdx) in evaluation.improvement_suggestions" :key="sIdx">
                  {{ suggestion }}
                </li>
              </ul>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>

      <el-divider />

      <el-button @click="resetPractice">重新练习</el-button>
    </el-card>
  </PageContainer>
</template>

<script setup>
import PageContainer from '@/components/PageContainer.vue'
import PageTitle from '@/components/PageTitle.vue'
import FileIdField from '@/components/FileIdField.vue'

import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { EditPen, Trophy } from '@element-plus/icons-vue'
import { generateQuestions, evaluateAnswer } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'

const workspaceStore = useWorkspaceStore()

const form = ref({
  file_id: '',
  focus_query: '',
  top_k: 3,
  strict_context: true,
  num_questions: 5,
  question_types: ['choice'],
  difficulty_levels: ['medium'],
})

const generating = ref(false)
const questions = ref([])
const currentIndex = ref(0)
const answers = ref([])
const evaluations = ref([])
const activeEvaluations = ref([])

watch(
  () => workspaceStore.fileId,
  (fileId) => {
    if (!form.value.file_id && fileId) form.value.file_id = String(fileId)
  },
  { immediate: true }
)

watch(
  () => form.value.file_id,
  (fileId) => {
    if (fileId !== workspaceStore.fileId) workspaceStore.setFileId(fileId)
  }
)

const currentQuestion = computed(() => questions.value[currentIndex.value])

const correctCount = computed(() => 
  evaluations.value.filter(e => e.is_correct).length
)

const averageScore = computed(() => {
  if (evaluations.value.length === 0) return 0
  return evaluations.value.reduce((sum, e) => sum + e.score, 0) / evaluations.value.length
})

const correctRate = computed(() => {
  if (questions.value.length === 0) return 0
  return correctCount.value / questions.value.length
})

const handleGenerate = async () => {
  if (!form.value.file_id) {
    ElMessage.warning('请输入文件ID')
    return
  }

  generating.value = true

  try {
    const res = await generateQuestions(form.value)
    questions.value = res.questions
    answers.value = new Array(res.questions.length).fill('')
    if (res.llm_validation) {
      workspaceStore.setLlmValidation(res.llm_validation)
    }
    ElMessage.success(`成功生成 ${res.questions.length} 道题目！`)
  } catch (error) {
    console.error('生成题目失败:', error)
  } finally {
    generating.value = false
  }
}

const handleSubmit = async () => {
  // 检查是否所有题目都已作答
  const unanswered = answers.value.findIndex(a => !a)
  if (unanswered !== -1) {
    ElMessage.warning(`第 ${unanswered + 1} 题尚未作答`)
    return
  }

  ElMessage.info('正在评估答案...')

  try {
    const evals = []
    for (let i = 0; i < questions.value.length; i++) {
      const evaluation = await evaluateAnswer({
        question_id: questions.value[i].question_id,
        user_answer: answers.value[i],
        user_id: workspaceStore.userId,
      })
      if (evaluation?.llm_validation) {
        workspaceStore.setLlmValidation(evaluation.llm_validation)
      }
      evals.push(evaluation)
    }
    evaluations.value = evals
    ElMessage.success('评估完成！')
  } catch (error) {
    console.error('评估失败:', error)
  }
}

const resetPractice = () => {
  questions.value = []
  answers.value = []
  evaluations.value = []
  currentIndex.value = 0
}

const getDifficultyType = (difficulty) => {
  const types = { easy: 'success', medium: 'warning', hard: 'danger' }
  return types[difficulty] || 'info'
}

const getDifficultyText = (difficulty) => {
  const texts = { easy: '简单', medium: '中等', hard: '困难' }
  return texts[difficulty] || difficulty
}
</script>

<style scoped>
.question-container {
  padding: 8px 2px 0;
}

.difficulty-tag {
  margin-bottom: 16px;
}

.question-container h3 {
  margin: 16px 0;
  color: var(--el-text-color-primary);
}

.answer-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 20px 0;
}

.answer-option {
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background: var(--el-fill-color-blank);
}

.answer-input {
  margin: 20px 0;
}

.button-group {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}

.result-card {
  margin-top: 20px;
}

.stats {
  margin-bottom: 20px;
}

.correct {
  color: var(--el-color-success);
  font-weight: bold;
}

.wrong {
  color: var(--el-color-danger);
  font-weight: bold;
}

.evaluation-detail p {
  margin: 12px 0;
}

.feedback {
  background-color: var(--el-fill-color-lighter);
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.6;
}

.evaluation-detail ul {
  margin-left: 20px;
}
</style>
