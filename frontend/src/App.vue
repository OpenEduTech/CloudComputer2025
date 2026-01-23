<script setup>
import {ref, onMounted, onUnmounted} from 'vue';
import Navbar from './components/Navbar.vue';
import UploadZone from './components/UploadZone.vue';
import Workspace from './components/Workspace.vue';
import {pptApi} from './api/index.js';

// 应用状态
const appState = ref('upload'); // 'upload' | 'workspace'
const isLoading = ref(false);
const fileName = ref('');
const slidesData = ref([]);
const mindmapData = ref(null);
const mindmapLoading = ref(false);
const mindmapError = ref('');
const docId = ref('');

// 上传处理
const handleFileUpload = async (file) => {
  if (!file) {
    fileName.value = "深度学习架构分析.pptx";
    simulateMockData();
    return;
  }

  fileName.value = file.name;
  isLoading.value = true;
  appState.value = 'upload';

  try {
    const response = await pptApi.uploadAndExpand(file);
    slidesData.value = response.data.slides || [];
    docId.value = response.data.doc_id || '';
    appState.value = 'workspace';
    buildMindmapForDeck().catch(err => console.error("思维导图生成失败:", err));
  } catch (error) {
    console.error("上传失败", error);
    alert("解析失败: " + (error.response?.data?.detail || error.message));
  } finally {
    isLoading.value = false;
  }
};

const handleUrlUpload = async (url) => {
  if (!url) return;
  isLoading.value = true;
  appState.value = 'upload';
  try {
    const response = await pptApi.uploadByUrl(url);
    let remoteName = '在线文件';
    try {
      const parsed = new URL(url);
      remoteName = parsed.pathname.split('/').pop() || remoteName;
    } catch {
      remoteName = url.split('/').pop() || remoteName;
    }
    fileName.value = remoteName;
    slidesData.value = response.data.slides || [];
    docId.value = response.data.doc_id || '';
    appState.value = 'workspace';
    buildMindmapForDeck().catch(err => console.error("思维导图生成失败:", err));
  } catch (error) {
    console.error("链接解析失败", error);
    alert("解析失败: " + (error.response?.data?.detail || error.message));
  } finally {
    isLoading.value = false;
  }
};

const simulateMockData = async () => {
    isLoading.value = true;
    appState.value = 'upload';
    
    // 模拟 API 延迟
    await new Promise(resolve => setTimeout(resolve, 800));
    
    slidesData.value = [
      {
        page_num: 1,
        title: "Transformer 结构总览",
        image: "https://via.placeholder.com/960x720?text=Slide+1",
        raw_points: [
          { type: "text", text: "Encoder-Decoder 架构", level: 0 },
          { type: "text", text: "自注意力机制", level: 1 },
          { type: "text", text: "进入工作台", level: 0 }
        ],
        expanded_html: "<p><strong>核心概念：</strong>Transformer 是一种完全基于注意力机制的架构，摒弃了传统的循环和卷积网络。</p>",
        references: [{title: "Attention Is All You Need", url: "#", source: "Arxiv"}]
      },
      {
        page_num: 2,
        title: "Self-Attention 机制详解",
        image: "https://via.placeholder.com/960x720?text=Slide+2",
        raw_points: [
          { type: "text", text: "Q, K, V 向量计算", level: 0 },
          { type: "text", text: "缩放点积", level: 1 },
          { type: "text", text: "Softmax 归一化", level: 1 }
        ],
        expanded_html: "<p><strong>计算公式：</strong>Attention(Q, K, V) = softmax(QK^T / √d_k)V。</p>",
        references: [{title: "Self-Attention Networks", url: "#", source: "Arxiv"}]
      }
    ];
    
    appState.value = 'workspace'; 
    isLoading.value = false;
    
    // 异步生成思维导图
    buildMindmapForDeck().catch(err => console.error("思维导图生成失败:", err));
};

const buildMindmapForDeck = async () => {
  // 优先使用全局分析结果生成思维导图
  if (docId.value) {
    mindmapLoading.value = true;
    mindmapError.value = '';

    try {
      const analysisRes = await pptApi.analyzeDocumentGlobal(docId.value, false);
      if (analysisRes.data?.success && analysisRes.data?.global_analysis) {
        // 使用全局分析结果生成思维导图
        const res = await pptApi.mindmapFromGlobalAnalysis(
          docId.value,
          fileName.value || null,
          6,
          25
        );
        mindmapData.value = res.data;  
      } else {
        // 如果没有全局分析结果，回退到基于slides的方式
        console.warn('全局分析结果不可用，回退到基于slides的思维导图生成');
        await buildMindmapFromSlides();
      }
    } catch (err) {
      console.error('基于全局分析的思维导图生成失败', err);
      // 如果全局分析失败，回退到基于slides的方式
      if (err.response?.status === 400 && err.response?.data?.detail?.includes('尚未进行全局分析')) {
        console.warn('文档尚未进行全局分析，回退到基于slides的思维导图生成');
        await buildMindmapFromSlides();
      } else {
        mindmapError.value = err.response?.data?.detail || err.message || '生成失败';
        mindmapData.value = null;
      }
    } finally {
      mindmapLoading.value = false;
    }
  } else if (slidesData.value && slidesData.value.length > 0) {
    // 如果没有docId，使用原来的基于slides的方式
    await buildMindmapFromSlides();
  } else {
    mindmapData.value = null;
  }
};

const buildMindmapFromSlides = async () => {
  if (!slidesData.value || slidesData.value.length === 0) {
    mindmapData.value = null;
    return;
  }
  mindmapLoading.value = true;
  mindmapError.value = '';

  const payload = {
    title: fileName.value || 'PPT 思维导图',
    slides: slidesData.value,
    max_depth: 6,
    max_children_per_node: 25
  }

  try {
    const res = await pptApi.mindmapFromSlides(payload);
    mindmapData.value = res.data;  
  } catch (err) {
    console.error('思维导图生成失败', err);
    mindmapError.value = err.response?.data?.detail || err.message || '生成失败';
    mindmapData.value = null;
  } finally {
    mindmapLoading.value = false;
  }
};

const resetApp = () => {
  appState.value = 'upload';
  slidesData.value = [];
  fileName.value = '';
  mindmapData.value = null;
  mindmapError.value = '';
  docId.value = '';
};
</script>

<template>
  <div class="app-container">
    <!-- 顶部导航 -->
    <Navbar>
      <div v-if="appState === 'workspace'" class="workspace-controls">
        <span class="file-name-display">{{ fileName }}</span>
        <button @click="resetApp" class="btn-close">✕ 关闭</button>
      </div>
    </Navbar>

    <!-- 上传页 -->
    <main v-if="appState === 'upload'" class="upload-main">
      <UploadZone
          v-if="!isLoading"
          @file-selected="handleFileUpload"
          @url-submitted="handleUrlUpload"
      />

      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-overlay">
        <div class="spinner"></div>
        <h3>正在解析 PPT 结构...</h3>
        <p>提取语义层级并构建知识图谱</p>
      </div>
    </main>

    <!-- 工作台页 (核心布局) -->
    <Workspace
        v-if="appState === 'workspace'"
        :slides="slidesData"
        :mindmap="mindmapData"
        :mindmap-loading="mindmapLoading"
        :mindmap-error="mindmapError"
        :doc-id="docId"
    />
  </div>
</template>

<style scoped>
.app-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.upload-main {
  flex: 1;
  overflow: hidden;
  background: radial-gradient(circle at top right, #f8fafc, #eff6ff);
  display: flex;
  flex-direction: column;
  padding: 0;
  min-height: 0;
}

.workspace-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.file-name-display {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 12px;
  border-radius: 4px;
}

.btn-close {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #fca5a5;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: 0.3s;
}

.btn-close:hover {
  background: rgba(239, 68, 68, 0.4);
  color: white;
}

.loading-overlay {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #64748b;
}

.spinner {
  width: 60px;
  height: 60px;
  border: 5px solid #e2e8f0;
  border-top: 5px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
