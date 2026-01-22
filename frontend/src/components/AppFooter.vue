<template>
  <footer class="app-footer">
    <div class="app-footer__inner">
      <span>© 2026 SmartLecPPTKiller: A Smart Knowledge Extractor and Quiz Generator</span>
      <span class="dot">·</span>
      <span>云计算期末项目：基于云原生与LLM Agents</span>
      <span class="dot">·</span>
      <span>BY KEYU(BronsonLau) & Wang Kenan</span>
    </div>
  </footer>
</template>

<script setup>
</script>

<style scoped>
.app-footer {
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--app-surface);
}

.app-footer__inner {
  max-width: var(--app-max-width);
  margin: 0 auto;
  padding: 14px 16px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.dot {
  opacity: 0.6;
}
</style>
