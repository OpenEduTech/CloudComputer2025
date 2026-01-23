<template>
  <div class="progress-indicator">
    <template v-for="(step, index) in steps" :key="step.key">
      <span 
        class="step" 
        :class="{ 
          'active': currentStep === index + 1,
          'completed': currentStep > index + 1
        }"
      >
        {{ index + 1 }}. {{ step.label }}
      </span>
      <span v-if="index < steps.length - 1" class="separator">→</span>
    </template>
  </div>
</template>

<script setup>
const props = defineProps({
  currentStep: {
    type: Number,
    required: true
  }
});

const steps = [
  { key: 'input', label: '输入' },
  { key: 'select', label: '学科选择' },
  { key: 'explore', label: '探索' } // Changed '探索中' to '探索' for consistency
];
</script>

<style scoped>
.progress-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.step {
  transition: color 0.3s;
}

.step.active {
  color: var(--color-text-primary);
  font-weight: 600;
}

.step.completed {
  color: var(--color-text-primary);
  opacity: 0.6;
}

.separator {
  color: var(--color-border);
}
</style>
