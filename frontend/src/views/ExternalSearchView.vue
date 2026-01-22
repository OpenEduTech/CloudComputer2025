<template>
  <PageContainer>
    <el-card>
      <template #header>
        <PageTitle title="外部资源搜索" subtitle="按关键词聚合多来源的延伸阅读">
          <template #icon>
            <el-icon><Search /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-form :model="form" label-width="100px">
        <el-form-item label="关键词">
          <el-input v-model="form.query" placeholder="例如：Transformer、链式法则" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">
            {{ loading ? '搜索中...' : '开始搜索' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="results.length" class="results-card">
      <template #header>
        <PageTitle :title="`搜索结果 (${results.length})`" subtitle="按来源分组展示">
          <template #icon>
            <el-icon><Search /></el-icon>
          </template>
        </PageTitle>
      </template>

      <el-tabs v-model="activeSource">
        <el-tab-pane
          v-for="group in groupedResults"
          :key="group.source"
          :label="group.source"
          :name="group.source"
        >
          <el-card
            v-for="(item, idx) in group.items"
            :key="idx"
            class="resource-card"
            shadow="hover"
          >
            <p><strong>{{ item.title }}</strong></p>
            <p class="summary">{{ item.summary }}</p>
            <el-link :href="item.url" target="_blank" type="primary">查看详情</el-link>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-empty v-else-if="searched" description="暂无结果" />
  </PageContainer>
</template>

<script setup>
import PageContainer from '@/components/PageContainer.vue'
import PageTitle from '@/components/PageTitle.vue'

import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { externalSearch } from '@/api'

const form = ref({
  query: '',
})

const loading = ref(false)
const searched = ref(false)
const results = ref([])
const activeSource = ref('')

const groupedResults = computed(() => {
  const groups = {}
  for (const item of results.value) {
    const source = item.source || '其他'
    if (!groups[source]) groups[source] = []
    groups[source].push(item)
  }
  return Object.entries(groups).map(([source, items]) => ({ source, items }))
})

const handleSearch = async () => {
  if (!form.value.query) {
    ElMessage.warning('请输入关键词')
    return
  }

  loading.value = true
  searched.value = false
  results.value = []

  try {
    const res = await externalSearch(form.value.query)
    results.value = res.resources || []
    if (results.value.length) {
      activeSource.value = groupedResults.value[0]?.source || ''
    }
    searched.value = true
  } catch (error) {
    console.error('外部搜索失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.results-card {
  margin-top: 20px;
}

.resource-card {
  margin-bottom: 12px;
}

.summary {
  color: var(--el-text-color-secondary);
  margin: 8px 0;
}
</style>
