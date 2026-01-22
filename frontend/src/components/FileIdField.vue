<template>
  <div class="fileid">
    <el-input
      :model-value="modelValue"
      :readonly="readonly"
      :placeholder="placeholder"
      @update:model-value="onUpdate"
      clearable
    >
      <template #append>
        <el-button :disabled="!modelValue" @click="copy">复制</el-button>
      </template>
    </el-input>
    <div v-if="showActions" class="fileid__actions">
      <el-button
        size="small"
        type="success"
        :disabled="!modelValue"
        @click="$router.push({ path: '/knowledge', query: { file_id: modelValue } })"
      >
        去知识扩充
      </el-button>
      <el-button
        size="small"
        type="warning"
        :disabled="!modelValue"
        @click="$router.push({ path: '/practice', query: { file_id: modelValue } })"
      >
        去练习测验
      </el-button>
      <el-button
        v-if="allowClear"
        size="small"
        :disabled="!modelValue"
        @click="onUpdate('')"
      >
        清空
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: String, default: '' },
  readonly: { type: Boolean, default: false },
  placeholder: { type: String, default: '请输入文件ID' },
  showActions: { type: Boolean, default: true },
  allowClear: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue'])

const onUpdate = (val) => {
  emit('update:modelValue', val)
}

const copy = async () => {
  if (!props.modelValue) return
  try {
    await navigator.clipboard.writeText(String(props.modelValue))
    ElMessage.success('已复制文件ID')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.fileid__actions {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
