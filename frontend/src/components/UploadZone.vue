<script setup>
import { ref } from 'vue'

const emit = defineEmits(['file-selected', 'url-submitted'])
const isDragging = ref(false)
const isProcessing = ref(false)
const fileInput = ref(null)
const urlInput = ref('')
const urlError = ref('')
const uploadMode = ref('file') // 'file' | 'url'

const handleFileChange = (e) => {
  const file = e.target.files[0]
  if (file) {
    validateAndUpload(file)
  }
}

const handleDrop = (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    validateAndUpload(file)
  }
}

const validateAndUpload = (file) => {
  const validExtensions = ['.pptx', '.pdf']
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase()

  if (!validExtensions.includes(fileExtension)) {
    alert('请上传 .pptx 或 .pdf 格式的文件')
    return
  }

  if (file.size > 50 * 1024 * 1024) {
    alert('文件大小不能超过 50MB')
    return
  }

  emit('file-selected', file)
}

const submitUrl = () => {
  const trimmed = urlInput.value.trim()
  if (!trimmed) {
    urlError.value = '请输入文件链接（需包含 .pptx 或 .pdf）'
    return
  }
  const lower = trimmed.toLowerCase()
  if (!lower.startsWith('http://') && !lower.startsWith('https://')) {
    urlError.value = '链接需以 http:// 或 https:// 开头'
    return
  }
  if (!lower.includes('.pptx') && !lower.includes('.pdf')) {
    urlError.value = '当前仅支持 .pptx / .pdf 链接'
    return
  }
  urlError.value = ''
  emit('url-submitted', trimmed)
  isProcessing.value = true
  setTimeout(() => {
    isProcessing.value = false
  }, 400)
}


const handleUploadBoxClick = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}
</script>

<template>
  <section class="welcome-area">
    <div class="welcome-layout">
      <!-- 左侧：品牌与功能介绍 -->
      <aside class="intro-panel">
        <div class="brand-badge">AI Powered Study Assistant</div>
        
        <div class="hero-text">
          <h1 class="hero-title">
            <span class="gradient-text">PPTAS</span>
            <br>
            内容扩展智能体
          </h1>
          <p class="hero-description">
            深度重塑您的学习体验。通过 AI 语义解析，将静态幻灯片转化为具备完整逻辑链条、权威引用的深度知识库。
          </p>
        </div>

        <div class="feature-vertical-list">
          <div class="feature-card">
            <div class="feature-card-icon">🎯</div>
            <div class="feature-card-content">
              <h3>语义逻辑重构</h3>
              <p>超越文字提取，自动识别章节层级与核心论点，构建思维导图。</p>
            </div>
          </div>

          <div class="feature-card">
            <div class="feature-card-icon">🌐</div>
            <div class="feature-card-content">
              <h3>全网知识联动</h3>
              <p>实时检索 Wikipedia、Arxiv 及学术期刊，多维权威资源延伸。</p>
            </div>
          </div>

          <div class="feature-card">
            <div class="feature-card-icon">✍️</div>
            <div class="feature-card-content">
              <h3>智能笔记生成</h3>
              <p>一键导出结构化 Markdown 笔记，包含层级结构、AI分析、参考资料。</p>
            </div>
          </div>
        </div>

        <div class="tech-stack">
          <span class="tech-tag">DeepSeek-V3</span>
          <span class="tech-tag">RAG 增强检索</span>
          <span class="tech-tag">多模态解析</span>
        </div>
      </aside>

      <!-- 右侧：交互上传区 -->
      <section class="upload-panel">
        <div class="upload-container-glass">
          <div class="mode-selector">
            <button 
              class="mode-tab" 
              :class="{ active: uploadMode === 'file' }"
              @click="uploadMode = 'file'"
            >
              本地文件
            </button>
            <button 
              class="mode-tab" 
              :class="{ active: uploadMode === 'url' }"
              @click="uploadMode = 'url'"
            >
              在线链接
            </button>
          </div>

          <!-- 文件上传 -->
          <div
            v-if="uploadMode === 'file'"
            class="drop-zone"
            :class="{ 'is-dragging': isDragging, 'is-processing': isProcessing }"
            @click="handleUploadBoxClick"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <input type="file" ref="fileInput" hidden @change="handleFileChange" accept=".pptx,.pdf" />
            
            <div class="drop-content">
              <div class="main-icon">
                <div v-if="!isProcessing" class="icon-bounce">📂</div>
                <div v-else class="loader-ring"></div>
              </div>
              
              <div class="text-group" v-if="!isProcessing">
                <h2 class="drop-title">释放您的 PPT</h2>
                <p class="drop-subtitle">拖拽文件至此 或 <span class="text-primary">点击浏览</span></p>
                <div class="file-support">支持 .pptx / .pdf (Max 50MB)</div>
              </div>
              
              <div v-else class="text-group">
                <h2 class="drop-title">正在上传...</h2>
                <p class="drop-subtitle">请稍候，正在准备解析环境</p>
              </div>
            </div>

            <div class="upload-footer-tags">
              <span>⚡ 极速解析</span>
              <span>🔒 隐私加密</span>
              <span>✨ 智能增强</span>
            </div>
          </div>

          <!-- URL 解析 -->
          <div v-else class="url-zone drop-zone">
            <div class="url-content drop-content">
              <div class="main-icon">
                <div v-if="!isProcessing">🔗</div>
                <div v-else class="loader-ring"></div>
              </div>
              
              <div class="text-group" v-if="!isProcessing">
                <h2 class="drop-title">解析远程文档</h2>
                <p class="drop-subtitle">输入公开的 PPT/PDF 访问链接</p>
              </div>
              <div v-else class="text-group">
                <h2 class="drop-title">正在准备...</h2>
                <p class="drop-subtitle">正在连接并准备下载环境</p>
              </div>
              
              <div class="url-input-group" v-if="!isProcessing">
                <input
                  v-model="urlInput"
                  class="modern-input"
                  type="url"
                  placeholder="https://example.com/lecture.pptx"
                  @keyup.enter="submitUrl"
                />
                <button class="modern-btn" @click="submitUrl" :disabled="isProcessing">
                  开始解析
                </button>
              </div>
              <p v-if="urlError" class="error-msg">{{ urlError }}</p>
              

            </div>
          </div>
        </div>

        <div class="quick-tips">
          <span class="tip-icon">💡</span>
          <p>提示：建议上传结构清晰的 PPT 以获得最佳的语义解析效果。</p>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.welcome-area {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  height: 100%;
  max-width: 1300px;
  margin: 0 auto;
  padding: 2rem;
  color: #1e293b;
  overflow: hidden;
}

.welcome-layout {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 3rem;
  height: 100%;
  align-items: center;
}

/* 左侧面板 */
.intro-panel {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.brand-badge {
  display: inline-flex;
  padding: 0.5rem 1rem;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border-radius: 99px;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  width: fit-content;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: 1.5rem;
  letter-spacing: -0.02em;
}

.gradient-text {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-description {
  font-size: 1.15rem;
  line-height: 1.6;
  color: #64748b;
  max-width: 520px;
}

.feature-vertical-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-top: 1rem;
}

.feature-card {
  display: flex;
  gap: 1.25rem;
  padding: 1.25rem;
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #f1f5f9;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateX(8px);
  border-color: #e2e8f0;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
}

.feature-card-icon {
  font-size: 1.75rem;
  flex-shrink: 0;
}

.feature-card-content h3 {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
  color: #0f172a;
}

.feature-card-content p {
  font-size: 0.95rem;
  color: #64748b;
  line-height: 1.5;
}

.tech-stack {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.tech-tag {
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
  padding: 0.25rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

/* 右侧面板 */
.upload-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1.5rem;
}

.upload-container-glass {
  background: #ffffff;
  border-radius: 24px;
  border: 1px solid #f1f5f9;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02);
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 480px; /* 固定高度，确保两个模式完全一致 */
}

.mode-selector {
  display: flex;
  background: #f1f5f9;
  padding: 0.4rem;
  border-radius: 12px;
  gap: 0.25rem;
}

.mode-tab {
  flex: 1;
  padding: 0.6rem;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-tab.active {
  background: #ffffff;
  color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.drop-zone {
  flex: 1;
  border: 2px dashed #e2e8f0;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #f8fafc;
}

.drop-zone:hover, .drop-zone.is-dragging {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.02);
}

.main-icon {
  font-size: 4rem;
  margin-bottom: 0.5rem;
}

.icon-bounce {
  animation: bounce 2s infinite;
}

.text-group {
  text-align: center;
}

.drop-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.5rem;
}

.drop-subtitle {
  font-size: 1rem;
  color: #64748b;
}

.text-primary {
  color: #3b82f6;
  font-weight: 600;
}

.file-support {
  margin-top: 1rem;
  font-size: 0.8rem;
  color: #94a3b8;
  background: #ffffff;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
}

.upload-footer-tags {
  display: flex;
  gap: 1.5rem;
  margin-top: 1rem;
}

.upload-footer-tags span {
  font-size: 0.85rem;
  font-weight: 500;
  color: #94a3b8;
}

/* URL Zone */
.url-zone {
  padding: 0; /* 移除额外padding，避免撑高 */
  cursor: default; /* URL模式不需要点击整个盒子 */
}

.url-input-group {
  margin-top: 1.2rem;
  margin-bottom: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
  max-width: 380px; /* 限制输入框宽度，避免太散 */
  margin-left: auto;
  margin-right: auto;
}

.modern-input {
  width: 100%;
  padding: 0.8rem 1rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  font-size: 0.95rem;
  outline: none;
  transition: all 0.2s ease;
}

.modern-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.modern-btn {
  width: 100%;
  padding: 0.8rem;
  border-radius: 10px;
  border: none;
  background: #3b82f6;
  color: #ffffff;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.modern-btn:hover {
  background: #2563eb;
  transform: translateY(-2px);
}

.modern-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.url-hint-list {
  margin-top: 1.2rem;
  text-align: left;
  display: inline-block;
}

.url-hint-list p {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 0.5rem;
}

.error-msg {
  color: #ef4444;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.quick-tips {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  background: rgba(245, 158, 11, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(245, 158, 11, 0.1);
}

.tip-icon {
  font-size: 1.25rem;
}

.quick-tips p {
  font-size: 0.85rem;
  color: #b45309;
  line-height: 1.5;
}

/* Animations */
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.loader-ring {
  width: 48px;
  height: 48px;
  border: 3px solid #f1f5f9;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 1024px) {
  .welcome-layout {
    grid-template-columns: 1fr;
    gap: 2rem;
    overflow-y: auto;
  }
  
  .welcome-area {
    overflow-y: auto;
  }

  .hero-title {
    font-size: 2.5rem;
  }
  
  .intro-panel {
    text-align: center;
    align-items: center;
  }
  
  .hero-description {
    margin: 0 auto;
  }
  
  .feature-card {
    text-align: left;
  }
}
</style>
