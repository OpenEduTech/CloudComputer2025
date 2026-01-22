<template>
  <el-menu
    class="sidenav"
    :default-active="activeIndex"
    router
    :collapse="collapsed"
  >
    <el-menu-item index="/">
      <el-icon><House /></el-icon>
      <span>首页</span>
    </el-menu-item>
    <el-menu-item index="/upload">
      <el-icon><Upload /></el-icon>
      <span>上传与解析</span>
    </el-menu-item>
    <el-menu-item index="/knowledge">
      <el-icon><DataAnalysis /></el-icon>
      <span>知识扩充</span>
    </el-menu-item>
    <el-menu-item index="/external-search">
      <el-icon><Search /></el-icon>
      <span>外部搜索</span>
    </el-menu-item>
    <el-menu-item index="/practice">
      <el-icon><EditPen /></el-icon>
      <span>练习测验</span>
    </el-menu-item>
    <el-menu-item index="/mistakes">
      <el-icon><Notebook /></el-icon>
      <span>错题本</span>
    </el-menu-item>
    <el-menu-item index="/team">
      <el-icon><User /></el-icon>
      <span>项目组介绍</span>
    </el-menu-item>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { House, Upload, DataAnalysis, Search, EditPen, Notebook, User } from '@element-plus/icons-vue'

defineProps({
  collapsed: { type: Boolean, default: false },
})

const route = useRoute()
const activeIndex = computed(() => route.path)
</script>

<style scoped>
.sidenav {
  height: 100%;
  border-right: none;
}
</style>
