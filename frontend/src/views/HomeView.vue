<template>
  <PageContainer>
    <el-card class="workspace-card">
      <template #header>
        <PageTitle title="工作区" subtitle="此处为当前处理PPT之统一ID，方便您复制使用">
          <template #icon>
            <el-icon><Collection /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="16">
          <FileIdField v-model="workspaceStore.fileId" placeholder="粘贴上传后得到的 file_id" />
        </el-col>
        <el-col :xs="24" :sm="8" class="workspace-actions">
          <el-button type="primary" @click="$router.push('/upload')">上传新文件</el-button>
          <el-button :disabled="!workspaceStore.fileId" @click="workspaceStore.clearFileId()">清空工作区</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="welcome-card">
      <template #header>
        <PageTitle title="欢迎使用 SmartLecPPTKiller" subtitle="智能学习，高效复习">
          <template #icon>
            <el-icon><Reading /></el-icon>
          </template>
        </PageTitle>
      </template>
      <div class="welcome-content">
        <h2>把 PPT 变成可练、可查、可复习的知识库</h2>
        <p>上传课件后，一键完成知识扩充、外部延伸阅读、练习测验与错题复盘</p>
      </div>
    </el-card>

    <div class="feature-grid">
      <el-card shadow="hover" class="feature-card">
        <el-icon :size="44" class="feature-icon feature-icon--primary"><Upload /></el-icon>
        <h3>PPT上传</h3>
        <p>支持PPT/PPTX/PDF格式文件上传，解析课件结构</p>
        <el-button type="primary" @click="$router.push('/upload')">
          开始上传
        </el-button>
      </el-card>

      <el-card shadow="hover" class="feature-card">
        <el-icon :size="44" class="feature-icon feature-icon--success"><DataAnalysis /></el-icon>
        <h3>知识扩充</h3>
        <p>AI自动补充原理说明、公式推导、代码示例</p>
        <el-button type="success" @click="$router.push('/knowledge')">
          知识扩充
        </el-button>
      </el-card>

      <el-card shadow="hover" class="feature-card">
        <el-icon :size="44" class="feature-icon feature-icon--info"><Search /></el-icon>
        <h3>外部搜索</h3>
        <p>联动权威资源获取延伸阅读材料</p>
        <el-button @click="$router.push('/external-search')">
          外部搜索
        </el-button>
      </el-card>

      <el-card shadow="hover" class="feature-card">
        <el-icon :size="44" class="feature-icon feature-icon--warning"><EditPen /></el-icon>
        <h3>智能出题</h3>
        <p>基于学习内容自动生成题目，智能判卷评分</p>
        <el-button type="warning" @click="$router.push('/practice')">
          开始练习
        </el-button>
      </el-card>

      <el-card shadow="hover" class="feature-card">
        <el-icon :size="44" class="feature-icon feature-icon--danger"><Notebook /></el-icon>
        <h3>错题本</h3>
        <p>自动收集错题，提供个性化学习建议</p>
        <el-button type="danger" @click="$router.push('/mistakes')">
          查看错题
        </el-button>
      </el-card>
    </div>

    <el-row :gutter="20" class="tech-row">
      <el-col :span="24">
        <el-card>
          <template #header>
            <PageTitle title="技术特性" subtitle="课程项目的关键能力点">
              <template #icon>
                <el-icon><TrendCharts /></el-icon>
              </template>
            </PageTitle>
          </template>
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12" :md="8">
              <div class="tech-item">
                <el-icon><Connection /></el-icon>
                <h4>云原生架构</h4>
                <p>Docker容器化部署，微服务架构</p>
              </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8">
              <div class="tech-item">
                <el-icon><MagicStick /></el-icon>
                <h4>LLM Agents</h4>
                <p>基于DEEPSEEK的Agent系统</p>
              </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8">
              <div class="tech-item">
                <el-icon><TrendCharts /></el-icon>
                <h4>向量检索</h4>
                <p>ChromaDB语义搜索</p>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </PageContainer>
</template>

<script setup>
import PageContainer from '@/components/PageContainer.vue'
import PageTitle from '@/components/PageTitle.vue'
import FileIdField from '@/components/FileIdField.vue'
import { useWorkspaceStore } from '@/stores/workspace'

import {
  Reading,
  Upload,
  DataAnalysis,
  EditPen,
  Notebook,
  Connection,
  MagicStick,
  TrendCharts,
  Search,
  Collection,
} from '@element-plus/icons-vue'

const workspaceStore = useWorkspaceStore()
</script>

<style scoped>
.workspace-card {
  margin-bottom: 16px;
}

.workspace-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.workspace-actions .el-button {
  width: 100%;
}

@media (min-width: 640px) {
  .workspace-actions .el-button {
    width: auto;
  }
}

.welcome-card {
  margin-bottom: 16px;
}

.welcome-content {
  text-align: center;
  padding: 28px 16px 30px;
}

.welcome-content h2 {
  font-size: 26px;
  margin: 0 0 10px;
  color: var(--el-text-color-primary);
}

.welcome-content p {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin: 0;
}

.feature-grid {
  margin-bottom: 16px;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 1100px) {
  .feature-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }
}

.feature-card {
  text-align: center;
  padding: 18px;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.feature-icon {
  margin: 4px auto 10px;
}

.feature-icon--primary {
  color: var(--el-color-primary);
}

.feature-icon--success {
  color: var(--el-color-success);
}

.feature-icon--warning {
  color: var(--el-color-warning);
}

.feature-icon--danger {
  color: var(--el-color-danger);
}

.feature-icon--info {
  color: var(--el-color-info);
}

.feature-card h3 {
  font-size: 20px;
  margin: 6px 0 8px;
  color: var(--el-text-color-primary);
}

.feature-card p {
  color: var(--el-text-color-secondary);
  margin: 0 0 14px;
  flex-grow: 1;
}

.tech-row {
  margin-top: 8px;
}

.tech-item {
  text-align: center;
  padding: 20px;
}

.tech-item .el-icon {
  font-size: 36px;
  color: var(--el-color-primary);
  margin-bottom: 12px;
}

.tech-item h4 {
  font-size: 18px;
  margin: 8px 0;
  color: var(--el-text-color-primary);
}

.tech-item p {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
</style>
