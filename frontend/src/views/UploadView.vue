<template>
  <PageContainer>
    <el-card>
      <template #header>
        <PageTitle title="上传PPT文件" subtitle="支持 PPT/PPTX/PDF，解析后可直接扩充/练习">
          <template #icon>
            <el-icon><Upload /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-upload
        ref="uploadRef"
        class="upload-demo"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :before-upload="beforeUpload"
        :limit="1"
        accept=".ppt,.pptx,.pdf"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处 或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PPT/PPTX/PDF 格式，文件大小不超过 50MB
          </div>
        </template>
      </el-upload>

      <div v-if="selectedFile" class="file-info">
        <el-divider />
        <h3>已选择文件</h3>
        <p><strong>文件名：</strong>{{ selectedFile.name }}</p>
        <p><strong>文件大小：</strong>{{ formatFileSize(selectedFile.size) }}</p>
        <el-button
          type="primary"
          :loading="uploading"
          @click="handleUpload"
        >
          {{ uploading ? '上传中...' : '开始上传' }}
        </el-button>
      </div>
    </el-card>

    <el-card v-if="parseResult" ref="resultRef" class="result-card">
      <template #header>
        <PageTitle title="解析结果" subtitle="按页浏览提取出的内容与备注">
          <template #icon>
            <el-icon><Document /></el-icon>
          </template>
          <template #extra>
            <el-button
              v-if="parseMarkdown"
              type="primary"
              @click="downloadParseMarkdown"
            >
              下载 Markdown
            </el-button>
            <el-button
              v-if="parseMarkdown"
              @click="showParseMarkdown = !showParseMarkdown"
            >
              {{ showParseMarkdown ? '收起Markdown预览' : '预览Markdown' }}
            </el-button>
          </template>
        </PageTitle>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="文件ID">
          <FileIdField
            :model-value="parseResult.file_id"
            readonly
            :show-actions="false"
            :allow-clear="false"
          />
        </el-descriptions-item>
        <el-descriptions-item label="总页数">{{ parseResult.total_slides }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <div v-if="parseResult.metadata?.outline?.length">
        <h3>目录结构</h3>
        <ul>
          <li v-for="(o, idx) in parseResult.metadata.outline" :key="idx">
            第 {{ o.slide_number }} 页：{{ o.title || '无标题' }}
            <span v-if="o.subtitle"> - {{ o.subtitle }}</span>
          </li>
        </ul>
        <div v-if="parseResult.metadata?.outline_summary?.length" class="notes">
          <strong>目录概括：</strong>
          <ul>
            <li v-for="(s, sIdx) in parseResult.metadata.outline_summary" :key="sIdx">{{ s }}</li>
          </ul>
        </div>
        <el-divider />
      </div>

      <h3>PPT内容预览</h3>
      <el-collapse v-model="activeSlides" accordion>
        <el-collapse-item
          v-for="slide in parseResult.slides"
          :key="slide.slide_number"
          :name="slide.slide_number"
        >
          <template #title>
            <strong>第 {{ slide.slide_number }} 页：{{ slide.title || '无标题' }}</strong>
          </template>
          <div class="slide-content">
            <p v-if="slide.subtitle"><strong>副标题：</strong>{{ slide.subtitle }}</p>
            <p v-for="(content, idx) in (slide.body?.length ? slide.body : slide.content)" :key="idx">{{ content }}</p>
            <el-tag v-if="slide.images.length > 0" type="info">
              包含 {{ slide.images.length }} 张图片
            </el-tag>
            <div v-if="slide.image_descriptions?.length" class="notes">
              <strong>图片描述：</strong>
              <ul>
                <li v-for="(desc, dIdx) in slide.image_descriptions" :key="dIdx">{{ desc }}</li>
              </ul>
            </div>
            <div v-if="slide.notes" class="notes">
              <strong>备注：</strong>{{ slide.notes }}
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>

      <div v-if="showParseMarkdown && parseMarkdown" class="markdown-preview">
        <el-divider />
        <h3>Markdown 预览</h3>
        <div class="markdown-body" v-html="parseMarkdownHtml"></div>
      </div>

      <el-divider />

      <el-row :gutter="16">
        <el-col :span="12">
          <el-button
            type="success"
            @click="$router.push({ path: '/knowledge', query: { file_id: parseResult.file_id } })"
          >
            前往知识扩充
          </el-button>
        </el-col>
        <el-col :span="12">
          <el-button
            type="warning"
            @click="$router.push({ path: '/practice', query: { file_id: parseResult.file_id } })"
          >
            开始练习
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card v-if="history.length" class="result-card">
      <template #header>
        <PageTitle title="解析历史" subtitle="可查看最近解析记录">
          <template #icon>
            <el-icon><Document /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-timeline>
        <el-timeline-item
          v-for="(item, idx) in visibleHistory"
          :key="idx"
          :timestamp="item.parsed_at"
        >
          <p><strong>{{ item.filename || item.file_id }}</strong>（{{ item.total_slides }} 页）</p>
          <ul v-if="item.outline?.length">
            <li v-for="(o, oIdx) in item.outline" :key="oIdx">
              第 {{ o.slide_number }} 页：{{ o.title || '无标题' }}
              <span v-if="o.subtitle"> - {{ o.subtitle }}</span>
            </li>
          </ul>
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

import { ref, onMounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, UploadFilled, Document } from '@element-plus/icons-vue'
import { uploadPPT, parsePPT, getPptHistory } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import MarkdownIt from 'markdown-it'

const uploadRef = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const parseResult = ref(null)
const activeSlides = ref(null)
const history = ref([])
const resultRef = ref(null)
const showAllHistory = ref(false)
const showParseMarkdown = ref(false)
const md = new MarkdownIt({ linkify: true, breaks: true })
const visibleHistory = computed(() => {
  return showAllHistory.value ? history.value : history.value.slice(0, 2)
})

const toggleHistory = () => {
  showAllHistory.value = !showAllHistory.value
}

const workspaceStore = useWorkspaceStore()

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const beforeUpload = (file) => {
  const isValidType = ['.ppt', '.pptx', '.pdf'].some(ext => 
    file.name.toLowerCase().endsWith(ext)
  )
  const isValidSize = file.size / 1024 / 1024 < 50

  if (!isValidType) {
    ElMessage.error('只支持 PPT/PPTX/PDF 格式文件！')
    return false
  }
  if (!isValidSize) {
    ElMessage.error('文件大小不能超过 50MB！')
    return false
  }
  return true
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  parseResult.value = null
  activeSlides.value = null
  showParseMarkdown.value = false

  try {
    // 上传文件
    const uploadResult = await uploadPPT(selectedFile.value, workspaceStore.userId)
    ElMessage.success('文件上传成功！')

    if (uploadResult?.file_id) {
      workspaceStore.setFileId(uploadResult.file_id)
    }

    // 解析文件
    ElMessage.info('正在解析文件...')
    const result = await parsePPT(uploadResult.file_id, workspaceStore.userId)
    parseResult.value = result
    activeSlides.value = result?.slides?.[0]?.slide_number || null
    if (result?.file_id) {
      workspaceStore.setFileId(result.file_id)
    }
    if (result?.metadata?.llm_validation) {
      workspaceStore.setLlmValidation(result.metadata.llm_validation)
    }
    ElMessage.success('文件解析完成！')
    loadHistory()
    await nextTick()
    if (resultRef.value?.$el?.scrollIntoView) {
      resultRef.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  } catch (error) {
    const message = error?.response?.data?.detail || '上传或解析失败，请稍后重试'
    ElMessage.error(message)
    console.error('上传或解析失败:', error)
    loadHistory()
  } finally {
    uploading.value = false
  }
}

const parseMarkdown = computed(() => {
  return parseResult.value?.markdown || ''
})

const parseMarkdownHtml = computed(() => {
  return parseMarkdown.value ? md.render(parseMarkdown.value) : ''
})

const downloadParseMarkdown = () => {
  const content = parseMarkdown.value
  if (!content) return
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ppt-parse-${parseResult.value?.file_id || 'result'}.md`
  a.click()
  URL.revokeObjectURL(url)
}

const loadHistory = async () => {
  try {
    const res = await getPptHistory(workspaceStore.userId, 20)
    history.value = res.items || []
  } catch (error) {
    console.error('加载解析历史失败:', error)
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.upload-demo {
  margin-bottom: 20px;
}

.file-info {
  margin-top: 20px;
}

.file-info h3 {
  margin-bottom: 12px;
}

.file-info p {
  margin: 8px 0;
  color: var(--el-text-color-secondary);
}

.result-card {
  margin-top: 20px;
}

.slide-content {
  padding: 12px;
}

.slide-content p {
  margin: 8px 0;
  line-height: 1.6;
}

.notes {
  margin-top: 12px;
  padding: 12px;
  background-color: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.history-toggle {
  margin-top: 12px;
  text-align: center;
}

.markdown-preview {
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
</style>
