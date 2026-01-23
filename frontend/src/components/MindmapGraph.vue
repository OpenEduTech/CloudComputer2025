<script setup>
import {computed, onMounted, onUnmounted, ref, watch, nextTick} from 'vue'

const props = defineProps({
  root: {type: Object, required: true}
})

const containerRef = ref(null)
const svgRef = ref(null)
const selected = ref(null)
const isFullscreen = ref(false)

const pan = ref({x: 100, y: 100})
const zoom = ref(0.9)
const isPanning = ref(false)
const lastPos = ref({x: 0, y: 0})

const CONFIG = {
  nodeHeight: 40,
  levelGap: 240,
  siblingGap: 20,
  charWidth: 14,
  padding: 20
}


function computeMetrics(node) {
  const labelWidth = Math.max(100, (node.label?.length || 0) * CONFIG.charWidth + 30)
  node._width = labelWidth

  if (!node.children || node.children.length === 0) {
    node._areaHeight = CONFIG.nodeHeight
    return
  }

  let childrenHeight = 0
  node.children.forEach(child => {
    computeMetrics(child)
    childrenHeight += child._areaHeight + CONFIG.siblingGap
  })
  childrenHeight -= CONFIG.siblingGap

  node._areaHeight = Math.max(CONFIG.nodeHeight, childrenHeight)
}

function assignCoords(node, x, yStart) {
  const xPos = x
  const yPos = yStart + node._areaHeight / 2

  node._x = xPos
  node._y = yPos

  if (node.children && node.children.length > 0) {
    let currentY = yStart
    node.children.forEach(child => {
      assignCoords(child, x + CONFIG.levelGap, currentY)
      currentY += child._areaHeight + CONFIG.siblingGap
    })
  }
}

const layout = computed(() => {
  if (!props.root) return {nodes: [], edges: []}

  const rootCopy = JSON.parse(JSON.stringify(props.root))

  computeMetrics(rootCopy)
  assignCoords(rootCopy, 50, 50)

  const nodes = []
  const edges = []

  function flatten(node, parent = null) {
    nodes.push(node)
    if (parent) {
      edges.push({
        id: `${parent.id}-${node.id}`,
        x1: parent._x + parent._width,
        y1: parent._y,
        x2: node._x,
        y2: node._y
      })
    }
    (node.children || []).forEach(c => flatten(c, node))
  }

  flatten(rootCopy)
  return {nodes, edges}
})

const onWheel = (e) => {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.05 : 0.05
  const newZoom = zoom.value + delta
  zoom.value = Math.min(2, Math.max(0.2, newZoom))
}

const startPan = (e) => {

  const target = e.target
  if (target.closest('.toolbar') || target.closest('.toolbar-btn') || 
      target.closest('.node-group') || target.closest('.detail-panel')) {
    return
  }
  
  if (e.button !== 0) return // 仅限左键
  e.preventDefault()
  isPanning.value = true
  lastPos.value = {x: e.clientX, y: e.clientY}
}

const doPan = (e) => {
  if (!isPanning.value) return
  e.preventDefault()
  const dx = e.clientX - lastPos.value.x
  const dy = e.clientY - lastPos.value.y
  pan.value.x += dx
  pan.value.y += dy
  lastPos.value = {x: e.clientX, y: e.clientY}
}

const endPan = (e) => {
  if (isPanning.value) {
    e?.preventDefault()
  }
  isPanning.value = false
}

watch(() => props.root, () => {
  selected.value = null
  pan.value = {x: 80, y: window.innerHeight / 3}
  zoom.value = 0.8
}, {immediate: true})

onMounted(() => {
  containerRef.value?.addEventListener('wheel', onWheel, {passive: false})
  
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.addEventListener('mozfullscreenchange', handleFullscreenChange)
  document.addEventListener('MSFullscreenChange', handleFullscreenChange)
})

onUnmounted(() => {
  containerRef.value?.removeEventListener('wheel', onWheel)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.removeEventListener('mozfullscreenchange', handleFullscreenChange)
  document.removeEventListener('MSFullscreenChange', handleFullscreenChange)
})

const handleFullscreenChange = () => {
  isFullscreen.value = !!(
    document.fullscreenElement ||
    document.webkitFullscreenElement ||
    document.mozFullScreenElement ||
    document.msFullscreenElement
  )
}

const toggleFullscreen = async () => {
  if (!containerRef.value) return
  
  try {
    if (!isFullscreen.value) {
      if (containerRef.value.requestFullscreen) {
        await containerRef.value.requestFullscreen()
      } else if (containerRef.value.webkitRequestFullscreen) {
        await containerRef.value.webkitRequestFullscreen()
      } else if (containerRef.value.mozRequestFullScreen) {
        await containerRef.value.mozRequestFullScreen()
      } else if (containerRef.value.msRequestFullscreen) {
        await containerRef.value.msRequestFullscreen()
      }
    } else {
      if (document.exitFullscreen) {
        await document.exitFullscreen()
      } else if (document.webkitExitFullscreen) {
        await document.webkitExitFullscreen()
      } else if (document.mozCancelFullScreen) {
        await document.mozCancelFullScreen()
      } else if (document.msExitFullscreen) {
        await document.msExitFullscreen()
      }
    }
  } catch (err) {
    console.error('全屏操作失败:', err)
  }
}

const exportAsSVG = () => {
  if (!svgRef.value || !layout.value.nodes.length) return
  
  try {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    layout.value.nodes.forEach(node => {
      const x = node._x
      const y = node._y
      const width = node._width || 100
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x + width)
      maxY = Math.max(maxY, y + 40)
    })
    
    const padding = 50
    const svgWidth = maxX - minX + padding * 2
    const svgHeight = maxY - minY + padding * 2
    
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    svg.setAttribute('width', svgWidth.toString())
    svg.setAttribute('height', svgHeight.toString())
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
    bg.setAttribute('width', '100%')
    bg.setAttribute('height', '100%')
    bg.setAttribute('fill', '#fcfcfd')
    svg.appendChild(bg)
    
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs')
    const filter = document.createElementNS('http://www.w3.org/2000/svg', 'filter')
    filter.setAttribute('id', 'nodeShadow')
    filter.setAttribute('x', '-20%')
    filter.setAttribute('y', '-20%')
    filter.setAttribute('width', '140%')
    filter.setAttribute('height', '140%')
    const dropShadow = document.createElementNS('http://www.w3.org/2000/svg', 'feDropShadow')
    dropShadow.setAttribute('dx', '0')
    dropShadow.setAttribute('dy', '2')
    dropShadow.setAttribute('stdDeviation', '3')
    dropShadow.setAttribute('flood-opacity', '0.1')
    filter.appendChild(dropShadow)
    defs.appendChild(filter)
    svg.appendChild(defs)
    
    layout.value.edges.forEach(edge => {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
      const x1 = edge.x1 - minX + padding
      const y1 = edge.y1 - minY + padding
      const x2 = edge.x2 - minX + padding
      const y2 = edge.y2 - minY + padding
      const midX = (x1 + x2) / 2
      path.setAttribute('d', `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`)
      path.setAttribute('fill', 'none')
      path.setAttribute('stroke', '#cbd5e1')
      path.setAttribute('stroke-width', '1.5')
      svg.appendChild(path)
    })
    
    layout.value.nodes.forEach(node => {
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
      const x = node._x - minX + padding
      const y = node._y - minY + padding
      g.setAttribute('transform', `translate(${x}, ${y - 20})`)
      
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
      rect.setAttribute('width', (node._width || 100).toString())
      rect.setAttribute('height', '40')
      rect.setAttribute('rx', '8')
      rect.setAttribute('fill', '#ffffff')
      rect.setAttribute('stroke', '#e2e8f0')
      rect.setAttribute('stroke-width', '1')
      rect.setAttribute('filter', 'url(#nodeShadow)')
      g.appendChild(rect)
      
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
      text.setAttribute('x', '15')
      text.setAttribute('y', '25')
      text.setAttribute('font-size', '13')
      text.setAttribute('font-weight', '500')
      text.setAttribute('fill', '#1e293b')
      text.textContent = node.label || ''
      g.appendChild(text)
      
      svg.appendChild(g)
    })
    
    const svgData = new XMLSerializer().serializeToString(svg)
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const svgUrl = URL.createObjectURL(svgBlob)
    
    const downloadLink = document.createElement('a')
    downloadLink.href = svgUrl
    downloadLink.download = 'mindmap.svg'
    document.body.appendChild(downloadLink)
    downloadLink.click()
    document.body.removeChild(downloadLink)
    URL.revokeObjectURL(svgUrl)
  } catch (err) {
    console.error('导出SVG失败:', err)
    alert('导出SVG失败: ' + err.message)
  }
}

const exportAsPNG = async () => {
  if (!svgRef.value || !layout.value.nodes.length) return
  
  try {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    layout.value.nodes.forEach(node => {
      const x = node._x
      const y = node._y
      const width = node._width || 100
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x + width)
      maxY = Math.max(maxY, y + 40)
    })
    
    const padding = 50
    const svgWidth = maxX - minX + padding * 2
    const svgHeight = maxY - minY + padding * 2
    

    let svgString = `<svg width="${svgWidth}" height="${svgHeight}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="nodeShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.1"/>
        </filter>
      </defs>
      <rect width="100%" height="100%" fill="#fcfcfd"/>
    `
    
    layout.value.edges.forEach(edge => {
      const x1 = edge.x1 - minX + padding
      const y1 = edge.y1 - minY + padding
      const x2 = edge.x2 - minX + padding
      const y2 = edge.y2 - minY + padding
      const midX = (x1 + x2) / 2
      svgString += `<path d="M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}" fill="none" stroke="#cbd5e1" stroke-width="1.5"/>`
    })
    
    layout.value.nodes.forEach(node => {
      const x = node._x - minX + padding
      const y = node._y - minY + padding
      const width = node._width || 100
      svgString += `<g transform="translate(${x}, ${y - 20})">
        <rect width="${width}" height="40" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1" filter="url(#nodeShadow)"/>
        <text x="15" y="25" font-size="13" font-weight="500" fill="#1e293b">${(node.label || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</text>
      </g>`
    })
    
    svgString += '</svg>'
    
    const img = new Image()
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(svgBlob)
    
    await new Promise((resolve, reject) => {
      img.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width = svgWidth
        canvas.height = svgHeight
        const ctx = canvas.getContext('2d')
        
        ctx.fillStyle = '#fcfcfd'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        
        ctx.drawImage(img, 0, 0)
        URL.revokeObjectURL(url)
        

        canvas.toBlob((blob) => {
          if (!blob) {
            reject(new Error('无法创建PNG blob'))
            return
          }
          const pngUrl = URL.createObjectURL(blob)
          const downloadLink = document.createElement('a')
          downloadLink.href = pngUrl
          downloadLink.download = 'mindmap.png'
          document.body.appendChild(downloadLink)
          downloadLink.click()
          document.body.removeChild(downloadLink)
          URL.revokeObjectURL(pngUrl)
          resolve()
        }, 'image/png')
      }
      img.onerror = () => {
        URL.revokeObjectURL(url)
        reject(new Error('图片加载失败'))
      }
      img.src = url
    })
  } catch (err) {
    console.error('导出PNG失败:', err)
    alert('导出PNG失败: ' + err.message)
  }
}
</script>

<template>
  <div class="mindmap-container" ref="containerRef"
       @mousemove="doPan" @mouseup="endPan" @mouseleave="endPan">

    <!-- 工具栏 -->
    <div class="toolbar" @mousedown.stop @click.stop>
      <button @click.stop="toggleFullscreen" class="toolbar-btn" title="全屏显示">
        <span v-if="!isFullscreen">⛶</span>
        <span v-else>⛶</span>
        全屏
      </button>
      <button @click.stop="exportAsSVG" class="toolbar-btn" title="导出为SVG">
        📥 SVG
      </button>
      <button @click.stop="exportAsPNG" class="toolbar-btn" title="导出为PNG">
        📥 PNG
      </button>
    </div>

    <!-- 画布主体 -->
    <svg class="mindmap-svg" ref="svgRef" @mousedown="startPan">
      <defs>
        <filter id="nodeShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.1"/>
        </filter>
      </defs>

      <g :transform="`translate(${pan.x}, ${pan.y}) scale(${zoom})`">
        <path v-for="edge in layout.edges" :key="edge.id" class="edge-line"
              :d="`M ${edge.x1} ${edge.y1} C ${(edge.x1 + edge.x2)/2} ${edge.y1}, ${(edge.x1 + edge.x2)/2} ${edge.y2}, ${edge.x2} ${edge.y2}`"/>

        <g v-for="node in layout.nodes" :key="node.id"
           class="node-group" :class="{ 'is-selected': selected?.id === node.id }"
           :transform="`translate(${node._x}, ${node._y - 20})`"
           @mousedown.stop
           @click.stop="selected = node">

          <rect class="node-card" :width="node._width" height="40" rx="8"/>
          <text class="node-label" :x="15" :y="25">{{ node.label }}</text>

          <circle v-if="node.meta?.kind === 'slide'" cx="5" cy="20" r="3" fill="#3b82f6"/>
        </g>
      </g>
    </svg>

    <!-- 底部操作提示 -->
    <div class="controls-hint">
      滚轮缩放 · 左键按住拖拽
    </div>

    <!-- 悬浮详情面板 (不再挤占空间) -->
    <Transition name="slide">
      <div v-if="selected" class="detail-panel">
        <div class="detail-header">
          <h3>节点详情</h3>
          <button @click="selected = null" class="close-btn">✕</button>
        </div>
        <div class="detail-content">
          <div class="info-row">
            <label>标题</label>
            <p>{{ selected.label }}</p>
          </div>
          <div v-if="selected.meta?.kind" class="info-row">
            <label>类型</label>
            <span class="badge">{{ selected.meta.kind }}</span>
          </div>
          <div v-if="selected.meta?.page_num" class="info-row">
            <label>对应页码</label>
            <p>第 {{ selected.meta.page_num }} 页</p>
          </div>

          <div v-if="selected.meta?.images?.length" class="detail-section">
            <label>视觉素材</label>
            <div class="image-placeholder" v-for="img in selected.meta.images" :key="img">
              <span class="icon">🖼️</span> {{ img.split('/').pop() }}
            </div>
          </div>

          <div v-if="selected.meta?.references?.length" class="detail-section">
            <label>参考引用</label>
            <a v-for="ref in selected.meta.references" :key="ref.url" :href="ref.url" target="_blank" class="ref-link">
              {{ ref.title }} <small>{{ ref.source }}</small>
            </a>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.mindmap-container {
  position: relative;
  width: 100%;
  height: 650px;
  background-color: #fcfcfd;
  background-image: radial-gradient(#e5e7eb 1px, transparent 1px);
  background-size: 30px 30px;
  overflow: hidden;
  cursor: grab;
}

.mindmap-container:active {
  cursor: grabbing;
}

.mindmap-svg {
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: all;
}

/* 连线样式 */
.edge-line {
  fill: none;
  stroke: #cbd5e1;
  stroke-width: 1.5;
  transition: all 0.3s;
}

/* 节点样式 */
.node-group {
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.node-card {
  fill: #ffffff;
  stroke: #e2e8f0;
  stroke-width: 1;
  filter: url(#nodeShadow);
}

.node-group:hover .node-card {
  stroke: #94a3b8;
  fill: #f8fafc;
}

.node-group.is-selected .node-card {
  stroke: #3b82f6;
  stroke-width: 2;
  fill: #eff6ff;
}

.node-label {
  font-size: 13px;
  font-weight: 500;
  fill: #1e293b;
  pointer-events: none;
  user-select: none;
}

/* 详情面板 (浮动) */
.detail-panel {
  position: absolute;
  top: 70px;
  right: 10px;
  width: 320px;
  max-height: calc(100% - 80px);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(226, 232, 240, 0.8);
  display: flex;
  flex-direction: column;
  z-index: 40;
  pointer-events: auto;
}

.detail-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #0f172a;
}

.close-btn {
  background: #f1f5f9;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  color: #64748b;
}

.detail-content {
  padding: 20px;
  overflow-y: auto;
}

.info-row {
  margin-bottom: 16px;
}

.info-row label {
  display: block;
  font-size: 11px;
  text-transform: uppercase;
  color: #94a3b8;
  margin-bottom: 4px;
  letter-spacing: 0.05em;
}

.info-row p {
  margin: 0;
  color: #1e293b;
  line-height: 1.5;
  font-size: 14px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.detail-section {
  margin-top: 20px;
}

.detail-section label {
  display: block;
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 8px;
}

.image-placeholder {
  background: #f8fafc;
  border: 1px dashed #e2e8f0;
  padding: 8px;
  border-radius: 6px;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.ref-link {
  display: block;
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
  text-decoration: none;
  color: #3b82f6;
  font-size: 13px;
  margin-bottom: 8px;
}

.controls-hint {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(15, 23, 42, 0.7);
  color: white;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 12px;
  backdrop-filter: blur(4px);
  pointer-events: none;
  z-index: 30;
}

.toolbar {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 8px;
  z-index: 50;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 8px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(226, 232, 240, 0.8);
  pointer-events: auto;
}

.toolbar-btn {
  padding: 8px 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #1e293b;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.toolbar-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.toolbar-btn:active {
  transform: translateY(0);
}

/* 动画 */
.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from, .slide-leave-to {
  transform: translateX(50px);
  opacity: 0;
}
</style>