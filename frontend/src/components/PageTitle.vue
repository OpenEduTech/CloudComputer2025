<template>
  <div class="page-title">
    <div class="page-title__row">
      <div v-if="$slots.icon" class="page-title__icon">
        <slot name="icon" />
      </div>
      <div class="page-title__text">
        <div class="page-title__main">{{ title }}</div>
        <div v-if="subtitle" class="page-title__sub">{{ subtitle }}</div>
      </div>
    </div>
    <div v-if="$slots.extra" class="page-title__extra">
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<style scoped>
.page-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.page-title__row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title__icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.page-title__main {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.page-title__sub {
  margin-top: 3px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.page-title__extra {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
