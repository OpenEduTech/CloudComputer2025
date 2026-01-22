<template>
  <PageContainer>
    <el-card class="overview-card">
      <template #header>
        <PageTitle title="项目组介绍" subtitle="SmartLecPPTKiller 云计算系统课程期末项目 团队信息">
          <template #icon>
            <el-icon><UserFilled /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-alert
        type="info"
        show-icon
        :closable="false"
        title="项目作业时间：2026.01"
        description="面向PPT学习场景的知识抽取与题目生成平台，强调可视化与交互体验。"
      />

      <el-divider />

      <el-row :gutter="16">
        <el-col :xs="24" :md="12">
          <el-card shadow="hover" class="member-card">
            <div class="member-header">
              <el-avatar :size="54" class="member-avatar" :src="kyAvatar" />
              <div>
                <h3>柯宇</h3>
                <p class="member-id">ECNU学号：10235501461</p>
              </div>
            </div>
            <p class="member-role">(50%)职责方向：负责LLM Agent 设计 + 智能逻辑实现，PPT 内容理解 Agent，知识扩展 / RAG Agent，DeepSeek API 调用，向量化与检索逻辑，Prompt 设计与优化，前端界面优化，项目统筹测试与最终细节调优</p>
            <div class="member-contact">
              <el-tag type="info">邮箱</el-tag>
              <span class="email">10235501461@stu.ecnu.edu.cn</span>
            </div>
            <div class="member-actions">
              <el-button size="small" type="primary" @click="copyEmail('10235501461@stu.ecnu.edu.cn')">复制邮箱</el-button>
              <el-button size="small" @click="openMail('10235501461@stu.ecnu.edu.cn')">邮件联系</el-button>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="12">
          <el-card shadow="hover" class="member-card">
            <div class="member-header">
              <el-avatar :size="54" class="member-avatar" :src="wkAvatar" />
              <div>
                <h3>王可楠</h3>
                <p class="member-id">ECNU学号：10235501466</p>
              </div>
            </div>
            <p class="member-role">(50%)职责方向：负责系统架构设计 + 前后端工程实现，系统整体架构设计，FastAPI 后端工程，Vue3 前端工程，Docker 容器化与部署，前后端接口设计，DEMO视频剪辑，最终交叉测试</p>
            <div class="member-contact">
              <el-tag type="info">邮箱</el-tag>
              <span class="email">10235501466@stu.ecnu.edu.cn</span>
            </div>
            <div class="member-actions">
              <el-button size="small" type="primary" @click="copyEmail('10235501466@stu.ecnu.edu.cn')">复制邮箱</el-button>
              <el-button size="small" @click="openMail('10235501466@stu.ecnu.edu.cn')">邮件联系</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="detail-card">
      <template #header>
        <PageTitle title="项目亮点" subtitle="协作与成果概览">
          <template #icon>
            <el-icon><CollectionTag /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-row :gutter="16">
        <el-col :xs="24" :md="14">
          <el-collapse v-model="activePanels" accordion>
            <el-collapse-item title="技术栈与实现重点(此处为概述，详见项目仓库技术文档)" name="stack">
              <ul class="bullet-list">
                <li>Vue 3 + Element Plus：统一的蓝色视觉规范与交互组件</li>
                <li>FastAPI + Redis + ChromaDB：高效解析与语义检索链路</li>
                <li>LLM 校验机制：输出质量评估与风险提示</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="协作方式(此处为概述，详见项目仓库分工文档)" name="collab">
              <ul class="bullet-list">
                <li>需求拆解与迭代式开发</li>
                <li>每日功能评审与对齐</li>
                <li>基于指标的体验优化与性能迭代</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="优势与特点(此处为概述，详见项目仓库计划文档)" name="plan">
              <ul class="bullet-list">
                <li>结构化解析模板</li>
                <li>用户学习画像与知识路径可视化</li>
                <li>独特的智能化讲义演示文稿处理体验</li>
              </ul>
            </el-collapse-item>
          </el-collapse>
        </el-col>
        <el-col :xs="24" :md="10">
          <el-timeline>
            <el-timeline-item timestamp="2026.01.17" placement="top">
              完成核心功能
            </el-timeline-item>
            <el-timeline-item timestamp="2026.01.19" placement="top">
              完成前端UI设计与主题展示升级
            </el-timeline-item>
            <el-timeline-item timestamp="2026.01.20" placement="top">
              功能细节调优与提交最终准备
            </el-timeline-item>
          </el-timeline>
        </el-col>
      </el-row>
    </el-card>
  </PageContainer>
</template>

<script setup>
import PageContainer from '@/components/PageContainer.vue'
import PageTitle from '@/components/PageTitle.vue'

import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UserFilled, CollectionTag } from '@element-plus/icons-vue'
import kyAvatar from '@/assets/KY.png'
import wkAvatar from '@/assets/WK.jpg'

const activePanels = ref('stack')

const copyEmail = async (email) => {
  try {
    await navigator.clipboard.writeText(email)
    ElMessage.success('邮箱已复制')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

const openMail = (email) => {
  window.open(`mailto:${email}`, '_blank')
}
</script>

<style scoped>
.overview-card,
.detail-card {
  margin-bottom: 20px;
}

.member-card {
  border: 1px solid rgba(37, 99, 235, 0.12);
}

.member-header {
  display: flex;
  gap: 14px;
  align-items: center;
}

.member-avatar {
  background: var(--el-color-primary-light-3);
  color: white;
  font-weight: 700;
}

.member-id {
  color: var(--el-text-color-secondary);
  margin: 2px 0 0;
}

.member-role {
  margin: 12px 0 8px;
  color: var(--el-text-color-secondary);
}

.member-contact {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.email {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.member-actions {
  display: flex;
  gap: 10px;
}

.bullet-list {
  margin: 8px 0 0 16px;
  color: var(--el-text-color-secondary);
}
</style>
