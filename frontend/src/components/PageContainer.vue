<template>
  <div class="page">
    <div class="page__inner">
      <slot />
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.page {
  padding: 12px 0 20px;
}

.page__inner {
  max-width: var(--app-max-width);
  margin: 0 auto;
  padding: 0 20px;
}
</style>
