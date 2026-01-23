<script setup>
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'

const props = defineProps({
  slides: Array,
  currentIndex: Number
})

const emit = defineEmits(['select'])

const hasSlides = computed(() => props.slides && props.slides.length > 0)
const mainStageRef = ref(null)
const thumbnailListRef = ref(null)

const selectPrev = () => {
  if (!hasSlides.value) return
  const next = (props.currentIndex - 1 + props.slides.length) % props.slides.length
  emit('select', next)
}

const selectNext = () => {
  if (!hasSlides.value) return
  const next = (props.currentIndex + 1) % props.slides.length
  emit('select', next)
}

let wheelTimeout = null
const handleWheel = (e) => {
  e.preventDefault()

  if (wheelTimeout) {
    clearTimeout(wheelTimeout)
  }
  
  wheelTimeout = setTimeout(() => {
    const delta = e.deltaY
    if (delta > 0) {
      // 向下滚动，切换到下一页
      selectNext()
    } else if (delta < 0) {
      // 向上滚动，切换到上一页
      selectPrev()
    }
  }, 100)
}

// 滚动到当前激活的缩略图
const scrollToActiveThumb = () => {
  nextTick(() => {
    if (thumbnailListRef.value && props.currentIndex !== undefined && props.currentIndex >= 0) {
      const activeThumb = thumbnailListRef.value.querySelector(`.thumb-item:nth-child(${props.currentIndex + 1})`)
      if (activeThumb) {
        activeThumb.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'center'
        })
      }
    }
  })
}

// 监听 currentIndex 变化，自动滚动缩略图
watch(() => props.currentIndex, () => {
  scrollToActiveThumb()
}, { immediate: true })

onMounted(() => {
  if (mainStageRef.value) {
    mainStageRef.value.addEventListener('wheel', handleWheel, { passive: false })
  }
  scrollToActiveThumb()
})

onUnmounted(() => {
  if (mainStageRef.value) {
    mainStageRef.value.removeEventListener('wheel', handleWheel)
  }
  if (wheelTimeout) {
    clearTimeout(wheelTimeout)
  }
})
</script>

<template>
  <div class="ppt-preview-container" v-if="hasSlides">
    <div class="main-stage" ref="mainStageRef">
      <button class="nav-btn prev" @click="selectPrev">‹</button>
      <div class="slide-number-badge">Slide {{ (currentIndex || 0) + 1 }} / {{ slides.length }}</div>
      <div class="slide-image-wrapper">
        <template v-if="slides[currentIndex]?.image">
          <img :src="slides[currentIndex]?.image" alt="Slide Preview" class="slide-image" />
        </template>
        <template v-else>
          <div class="slide-placeholder">
            <span class="placeholder-icon">📄</span>
            <span class="placeholder-text">{{ slides[currentIndex]?.title || '无标题幻灯片' }}</span>
            <ul class="placeholder-points">
              <li v-for="(point, idx) in (slides[currentIndex]?.raw_points || []).slice(0, 3)" :key="idx">
                {{ point }}
              </li>
            </ul>
          </div>
        </template>
      </div>
      <div class="slide-caption">
        {{ slides[currentIndex]?.title }}
      </div>
      <button class="nav-btn next" @click="selectNext">›</button>
    </div>

    <div class="thumbnail-list" ref="thumbnailListRef">
      <div
        v-for="(slide, index) in slides"
        :key="slide.page_num"
        :class="['thumb-item', { active: index === currentIndex }]"
        @click="$emit('select', index)"
      >
        <template v-if="slide.image">
          <img :src="slide.image" class="thumb-img" />
        </template>
        <template v-else>
          <div class="thumb-placeholder">
            <span class="mini-icon">📄</span>
          </div>
        </template>
        <span class="thumb-num">{{ slide.page_num }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ppt-preview-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #e2e8f0;
}

.main-stage {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid #cbd5e1;
  position: relative;
  background: #cbd5e1;
  overflow: hidden;
  cursor: pointer;
}

.slide-number-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(0,0,0,0.6);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
}

.slide-image-wrapper {
  width: 100%;
  max-width: 600px;
  aspect-ratio: 16/9;
  background: white;
  box-shadow: 0 10px 25px rgba(0,0,0,0.3);
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slide-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.slide-caption {
  margin-top: 1rem;
  font-weight: 600;
  color: #334155;
  text-align: center;
  padding: 0 1rem;
  font-size: 0.9rem;
}

.wheel-hint {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #64748b;
  opacity: 0.7;
  text-align: center;
  animation: fadeInOut 3s ease-in-out infinite;
}

@keyframes fadeInOut {
  0%, 100% {
    opacity: 0.5;
  }
  50% {
    opacity: 0.9;
  }
}

.nav-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: none;
  background: rgba(0,0,0,0.35);
  color: white;
  font-size: 1.4rem;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.nav-btn:hover {
  background: rgba(0,0,0,0.55);
  transform: translateY(-50%) scale(1.03);
}

.nav-btn.prev {
  left: 12px;
}

.nav-btn.next {
  right: 12px;
}

.thumbnail-list {
  height: 140px;
  min-height: 140px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 12px 16px;
  display: flex;
  gap: 10px;
  background: #f8fafc;
  scroll-snap-type: x mandatory;
  border-top: 1px solid #e2e8f0;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
}

/* 优化滚动条样式 */
.thumbnail-list::-webkit-scrollbar {
  height: 6px;
}

.thumbnail-list::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.thumbnail-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s;
}

.thumbnail-list::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.thumb-item {
  position: relative;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 3px solid transparent;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  aspect-ratio: 16/9;
  width: 120px;
  height: 68px;
  flex: 0 0 auto;
  scroll-snap-align: start;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.thumb-item:hover {
  border-color: #64748b;
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.thumb-item.active {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2), 0 4px 12px rgba(59, 130, 246, 0.3);
  transform: translateY(-2px) scale(1.03);
}

.slide-placeholder {
  width: 100%;
  aspect-ratio: 16/9;
  background: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  box-sizing: border-box;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.placeholder-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.placeholder-text {
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 1rem;
  text-align: center;
  max-width: 80%;
}

.placeholder-points {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 0.9rem;
  text-align: left;
  opacity: 0.8;
  width: 80%;
}

.placeholder-points li {
  margin-bottom: 0.5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.placeholder-points li::before {
  content: "•";
  margin-right: 0.5rem;
  color: #3b82f6;
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mini-icon {
  font-size: 1.5rem;
  opacity: 0.3;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.25s;
}

.thumb-item:hover .thumb-img {
  transform: scale(1.05);
}

.thumb-num {
  position: absolute;
  bottom: 4px;
  right: 4px;
  background: linear-gradient(135deg, rgba(0,0,0,0.8), rgba(0,0,0,0.6));
  color: white;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 3px 6px;
  border-radius: 4px;
  backdrop-filter: blur(4px);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}
</style>
