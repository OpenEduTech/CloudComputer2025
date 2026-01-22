<template>
  <div id="app">
    <AppShell>
      <router-view />
    </AppShell>
  </div>
</template>

<script setup>
import AppShell from './components/AppShell.vue'
</script>

<style scoped>
#app {
  min-height: 100vh;
}

.el-container {
  min-height: 100vh;
}


</style>
