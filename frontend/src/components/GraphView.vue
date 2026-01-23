<template>
  <div ref="container" class="graph-container">
    <div v-if="graphStore.loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>正在加载知识图谱...</p>
    </div>

    <div v-else-if="graphStore.error" class="error-overlay">
      <p class="error-message">{{ graphStore.error }}</p>
      <p class="error-hint">请先搜索并构建知识图谱，或点击刷新按钮重试</p>
      <button @click="refreshGraph" class="refresh-btn">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
        刷新图谱
      </button>
    </div>

    <div v-else-if="graphStore.nodes.length === 0" class="empty-overlay">
      <p>暂无图谱数据</p>
      <p class="empty-hint">搜索一个概念来构建知识图谱，或点击刷新按钮加载已有图谱</p>
      <button @click="refreshGraph" class="refresh-btn">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
        刷新图谱
      </button>
    </div>

    <!-- Controls -->
    <div class="graph-controls" v-if="!graphStore.loading">
      <button @click="refreshGraph" class="control-btn" title="刷新图谱" :disabled="isRefreshing">
        <span :class="{ 'spinning': isRefreshing }">↻</span>
      </button>
      <button @click="resetZoom" class="control-btn" title="重置视图" v-if="graphStore.nodes.length > 0">
        <span>⤢</span>
      </button>
    </div>

    <svg ref="svgRef"></svg>
    
    <NodeDetail />

    <!-- Legend -->
    <div class="legend" v-if="graphStore.disciplines.length > 0">
      <div class="legend-title">学科分布 (点击筛选)</div>
      <div 
        v-for="disc in graphStore.disciplines" 
        :key="disc" 
        class="legend-item"
        :class="{ inactive: hiddenGroups.has(disc) }"
        @click="toggleGroup(disc)"
      >
        <span class="dot" :style="{ backgroundColor: colorScale(disc) }"></span>
        <span>{{ disc }}</span>
      </div>
    </div>

    <div class="graph-hint" v-if="!graphStore.loading && graphStore.nodes.length > 0">
      悬停高亮 | 拖拽固定 | 点击节点/连线询问AI
    </div>
  </div>
</template>


<script setup>
import { onMounted, ref, watch, onUnmounted } from 'vue';
import * as d3 from 'd3';
import { useGraphStore } from '../stores/graphStore';
import { useChatStore } from '../stores/chatStore';
import { useSearchStore } from '../stores/searchStore';
import NodeDetail from './NodeDetail.vue';

const graphStore = useGraphStore();
const chatStore = useChatStore();
const searchStore = useSearchStore();
const container = ref(null);
const svgRef = ref(null);

// Interactive state
const hiddenGroups = ref(new Set());
const hoverNode = ref(null);
const isRefreshing = ref(false);
let zoomBehavior = null;
let svgSelection = null; // Store d3 selection

let simulation = null;
let width = 0;
let height = 0;

// Google/Gemini inspired palette
const colors = [
  "#4285F4", // Blue
  "#34A853", // Green
  "#EA4335", // Red
  "#FBBC05", // Yellow
  "#AB47BC", // Purple
  "#00ACC1", // Cyan
  "#FF7043", // Orange
  "#9E9D24"  // Olive
];

const colorScale = d3.scaleOrdinal(colors);

// 刷新图谱
async function refreshGraph() {
  if (isRefreshing.value) return;
  
  const concept = searchStore.currentConcept || graphStore.concept;
  if (!concept) {
    console.warn('没有可用的概念');
    return;
  }
  
  isRefreshing.value = true;
  
  try {
    await graphStore.fetchGraph(concept);
    
    // 如果图谱加载成功，初始化聊天连接
    if (graphStore.nodes.length > 0 && !graphStore.error) {
      chatStore.setConcept(concept);
      console.log(`图谱加载成功，已连接聊天服务: ${concept}`);
    }
  } catch (error) {
    console.error('刷新图谱失败:', error);
  } finally {
    isRefreshing.value = false;
  }
}

function toggleGroup(group) {
  if (hiddenGroups.value.has(group)) {
    hiddenGroups.value.delete(group);
  } else {
    hiddenGroups.value.add(group);
  }
  // 数据过滤并重新布局，而不是仅仅改变透明度
  initGraph();
}

function resetZoom() {
  if (svgSelection && zoomBehavior) {
    svgSelection.transition().duration(750).call(zoomBehavior.transform, d3.zoomIdentity);
  }
}

onMounted(() => {
  // Initial size
  updateDimensions();
  window.addEventListener('resize', handleResize);
  
  if (graphStore.nodes.length > 0) {
    initGraph();
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (simulation) simulation.stop();
});

watch(() => graphStore.nodes, (newNodes) => {
  if (newNodes.length > 0) {
    initGraph();
  }
}, { deep: true });

watch(() => graphStore.selectedNode, () => {
  updateGraphVisibility();
});

function updateDimensions() {
  if (container.value) {
    width = container.value.clientWidth;
    height = container.value.clientHeight;
  }
}

function handleResize() {
  updateDimensions();
  if (svgRef.value) {
    d3.select(svgRef.value)
      .attr("width", width)
      .attr("height", height);
    
    if (simulation) {
      simulation.force("center", d3.forceCenter(width / 2, height / 2));
      simulation.alpha(1).restart();
    }
  }
}

function initGraph() {
  if (!svgRef.value) return;
  
  // 保存当前的 Zoom 状态，避免筛选时重置视角体验不佳
  let currentTransform = d3.zoomIdentity;
  if(svgSelection) {
      currentTransform = d3.zoomTransform(svgSelection.node());
  }

  // Clear previous
  const svg = d3.select(svgRef.value);
  svg.selectAll("*").remove();
  svgSelection = svg; // Store for resetZoom
  
  svg.attr("width", width).attr("height", height);
  
  // Add zoom group
  const g = svg.append("g");
  
  zoomBehavior = d3.zoom()
      .extent([[0, 0], [width, height]])
      .scaleExtent([0.1, 8])
      .on("zoom", ({transform}) => {
        g.attr("transform", transform);
      });
      
  svg.call(zoomBehavior);
  // Restore zoom
  svg.call(zoomBehavior.transform, currentTransform);

  // Filter nodes based on hiddenGroups
  // Always keep center concept node visible
  const nodes = graphStore.nodes
    .filter(d => !hiddenGroups.value.has(d.group) || d.id === graphStore.concept)
    .map(d => ({...d}));
    
  // Filter links: keep only if both source and target are visible
  const visibleNodeIds = new Set(nodes.map(n => n.id));
  const links = graphStore.links
    .filter(d => visibleNodeIds.has(d.source) && visibleNodeIds.has(d.target))
    .map(d => ({...d}));

  // 1. 预处理数据范围，建立比例尺，避免节点过大
  const valExtent = d3.extent(nodes, d => d.val || 1);
  // 使用开方比例尺，使面积与数值成正比，避免巨大节点
  const radiusScale = d3.scaleSqrt()
    .domain([0, valExtent[1] || 10])
    .range([8, 25])
    .clamp(true); // 限制最大最小值
    
  const fontSizeScale = d3.scaleLinear()
    .domain([0, valExtent[1] || 10])
    .range([11, 14])
    .clamp(true);

  // 辅助函数：获取节点半径
  function getNodeRadius(d) {
    if (d.id === graphStore.concept) return 35; // 中心节点稍大
    return radiusScale(d.val || 1);
  }

  // Neighbor index for fast lookup
  const linkedByIndex = {};
  const adj = {};

  // Build Adjacency List for BFS
  links.forEach(d => {
    // d.source and d.target are initially strings (IDs), but d3 force will mutate them to objects.
    // We should use strings for our maps before simulation starts, or handle objects if later.
    // At this point (before simulation), they are objects because I did .map(d => ({...d}))? 
    // Wait, in previous fetchGraph, I did map(...).
    // Let's assume they are strings initially if fetchGraph is standard. 
    // BUT d3.forceLink(links) happens later.
    // IF initGraph is called multiple times, be careful. 
    // We are mapping from graphStore.nodes/links which are fresh objects each time initGraph calls map?
    // graphStore.links are from API response.
    
    // Safety check: handle if they are objects (re-rendering)
    const s = (typeof d.source === 'object') ? d.source.id : d.source;
    const t = (typeof d.target === 'object') ? d.target.id : d.target;

    linkedByIndex[`${s},${t}`] = 1;
    linkedByIndex[`${t},${s}`] = 1;
    
    if (!adj[s]) adj[s] = [];
    if (!adj[t]) adj[t] = [];
    adj[s].push(t);
    adj[t].push(s);
  });

  // Calculate levels (hops from center) & Predecessors for Path Finding
  const levelMap = new Map();
  const parentMap = new Map(); // For reconstructing path to center
  const startNodeId = graphStore.concept;
  
  if (startNodeId) {
    const queue = [[startNodeId, 0]];
    levelMap.set(startNodeId, 0);
    const visited = new Set([startNodeId]);
    
    let head = 0;
    while(head < queue.length) {
      const [curr, level] = queue[head++];
      if (adj[curr]) {
        for (const neighbor of adj[curr]) {
          if (!visited.has(neighbor)) {
            visited.add(neighbor);
            levelMap.set(neighbor, level + 1);
            parentMap.set(neighbor, curr); // Store parent
            queue.push([neighbor, level + 1]);
          }
        }
      }
    }
  }

  nodes.forEach(n => {
    n.level = levelMap.has(n.id) ? levelMap.get(n.id) : 4; // Default outer ring
  });

  // Calculate path from node to center
  function getPathToCenter(nodeId) {
    const pathNodes = new Set([nodeId]);
    const pathEdges = new Set();
    let curr = nodeId;
    
    // Safety break
    let count = 0;
    while(curr !== startNodeId && count < 100) {
      const parent = parentMap.get(curr);
      if (!parent) break;
      
      pathNodes.add(parent);
      
      // Edge key depends on ID sort or just verify both
      // We will check validity in visibility function
      // But creating a deterministic key for edges in path is useful
      // Or just check if edge endpoints are (curr, parent)
      
      curr = parent;
      count++;
    }
    return { nodes: pathNodes, edges: pathEdges }; // we only need node set for now, edge check is dynamically done
  }

  function isConnected(a, b) {
    return linkedByIndex[`${a.id},${b.id}`] || linkedByIndex[`${b.id},${a.id}`] || a.id === b.id;
  }

  // 中心节点定位
  const conceptNode = nodes.find(n => n.id === graphStore.concept);
  if (conceptNode) {
    // 固定中心节点位置
    conceptNode.fx = width / 2;
    conceptNode.fy = height / 2;
    conceptNode.val = 30; // 确保中心节点足够大
    conceptNode.level = 0;
  }

  simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(d => {
       // 根据层级动态调整连线长度，内层稍微紧凑，外层松散
       const sourceLevel = d.source.level || 0;
       const targetLevel = d.target.level || 0;
       if (sourceLevel === 0 || targetLevel === 0) return 120;
       return 80;
    })) 
    .force("charge", d3.forceManyBody().strength(d => {
      // 动态斥力，大节点斥力更大，避免重叠
      const r = getNodeRadius(d);
      return -200 - (r * 15); 
    }))
    .force("collide", d3.forceCollide().radius(d => {
      // 碰撞半径包含文字标签的一定空间预留
      return getNodeRadius(d) * 1.2 + 15; 
    }).iterations(3))
    .force("radial", d3.forceRadial(
      d => {
         // 层级布局半径
         const level = d.level || 0;
         if (level === 0) return 0;
         return 120 + (level - 1) * 100; // 第一层120，后续每层递增100
      }, 
      width / 2, 
      height / 2
    ).strength(0.6)); // 降低一点强度，允许物理模拟微调位置

  // Arrow marker & Filters
  const defs = svg.append("defs");
  
  defs.append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 18) // Moved back slightly to account for node stroke
    .attr("refY", 0)
    .attr("markerWidth", 5)
    .attr("markerHeight", 5)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#bdc1c6");

  // Drop Shadow Filter
  const filter = defs.append("filter")
    .attr("id", "shadow")
    .attr("x", "-50%")
    .attr("y", "-50%")
    .attr("width", "200%")
    .attr("height", "200%");
    
  filter.append("feDropShadow")
    .attr("dx", 0)
    .attr("dy", 2)
    .attr("stdDeviation", 3)
    .attr("flood-color", "#000000")
    .attr("flood-opacity", 0.15);

  // Edges
  const link = g.append("g")
    .attr("class", "links")
    .selectAll("path") // Changed to path for curves if desired, or stay line
    .data(links)
    .join("line")
    .attr("stroke", "#e0e0e0") // Lighter default
    .attr("stroke-width", 1.5)
    .attr("stroke-opacity", 0.6)
    .attr("class", "link")
    .style("cursor", "pointer")
    .on("click", (event, d) => {
      // 点击边，选择并询问关系
      graphStore.selectEdge(d);
      chatStore.askAboutEdge(d);
      event.stopPropagation();
    });
    
     // ... mouseover/out ... moved to updateGraphVisibility or keep simple hover effect?
     // We rely on updateGraphVisibility mostly, but can add simple hover stroke width increase locally if needed.
     // But updateGraphVisibility handles Logic better.

  // Center Pulse Effect (under nodes)
  const centerNodeData = nodes.find(n => n.id === graphStore.concept);
  let pulseGroup;
  
  if (centerNodeData) {
    pulseGroup = g.append("g").attr("class", "pulse-group");
    pulseGroup.append("circle")
        .attr("class", "pulse-circle")
        .attr("r", 30)
        .attr("fill", "var(--color-primary)")
        .attr("opacity", 0.2);
  }

  // Nodes
  const node = g.append("g")
    .attr("class", "nodes")
    .selectAll("g") 
    .data(nodes)
    .join("g")
    .attr("class", "node")
    .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

  // Node Circle
  node.append("circle")
    .attr("r", d => getNodeRadius(d))
    .attr("fill", d => d.id === graphStore.concept ? "white" : colorScale(d.group))
    .attr("stroke", d => d.id === graphStore.concept ? "var(--color-primary)" : "#fff")
    .attr("stroke-width", d => d.id === graphStore.concept ? 4 : 2)
    .style("filter", "url(#shadow)")
    .style("cursor", "pointer")
    .style("transition", "fill 0.3s, stroke-width 0.3s")
    .on("click", (event, d) => {
      graphStore.selectNode(d);
      event.stopPropagation();
    })
    .on("mouseover", (event, d) => {
      hoverNode.value = d;
      updateGraphVisibility();
    })
    .on("mouseout", () => {
      hoverNode.value = null;
      updateGraphVisibility();
    });

  // Labels with Halo
  const labelGroup = node.append("g")
    .style("pointer-events", "none");

  // Helper for label positioning
  const getLabelDx = d => d.id === graphStore.concept ? 0 : getNodeRadius(d) + 6;
  const getLabelDy = d => d.id === graphStore.concept ? 0 : 4;
  const getFontSize = d => d.id === graphStore.concept ? "15px" : fontSizeScale(d.val || 1) + "px";

  labelGroup.append("text")
    .text(d => d.id)
    .attr("font-size", getFontSize)
    .attr("fill", "#202124")
    .attr("dx", getLabelDx)
    .attr("dy", getLabelDy)
    .attr("text-anchor", d => d.id === graphStore.concept ? "middle" : "start")
    .attr("dominant-baseline", d => d.id === graphStore.concept ? "middle" : "auto")
    .attr("stroke", "white")
    .attr("stroke-width", 3)
    .attr("stroke-linejoin", "round")
    .attr("stroke-opacity", 0.8)
    .style("font-weight", "600");

  labelGroup.append("text")
    .text(d => d.id)
    .attr("font-size", getFontSize)
    .attr("fill", "#202124")
    .attr("dx", getLabelDx)
    .attr("dy", getLabelDy)
    .attr("text-anchor", d => d.id === graphStore.concept ? "middle" : "start")
    .attr("dominant-baseline", d => d.id === graphStore.concept ? "middle" : "auto")
    .style("font-weight", "600");

  simulation.on("tick", () => {
    link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

    node
        .attr("transform", d => `translate(${d.x},${d.y})`);
        
    if (pulseGroup && centerNodeData) {
        pulseGroup.attr("transform", `translate(${centerNodeData.x},${centerNodeData.y})`);
    }
  });

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    // d.fx = null; // Comment out to allow "sticky" nodes - one of the interactive features
    // d.fy = null;
    
    // Check if user wants to release? Maybe single click releases?
    // For now keep sticky behavior as it's useful for organizing
  }

  // Update function for visibility
  window.updateGraphVisibility = () => {
    const hidden = hiddenGroups.value;
    const isHovering = hoverNode.value !== null;
    const isSelected = graphStore.selectedNode !== null;
    const centerId = graphStore.concept;
    
    // Determine target node for Path Logic
    // Priority: Hover > Selected
    let targetNode = null;
    if (isHovering) {
        targetNode = hoverNode.value;
    } else if (isSelected) {
        targetNode = graphStore.selectedNode;
    }

    // Calculate path if a valid target is present
    let activeNodes = null; // Set of IDs
    let isPathActive = false;
    
    if (targetNode && targetNode.id !== centerId) {
       // Highlight path from targetNode to center
       const pathData = getPathToCenter(targetNode.id);
       activeNodes = pathData.nodes;
       isPathActive = true;
    }

    node.transition().duration(200).style('opacity', d => {
      // 1. Group filtering
      if (hidden.has(d.group)) return 0.1;
      
      // 2. Interaction filtering
      if (isPathActive) {
        if (activeNodes && activeNodes.has(d.id)) return 1;
        return 0.1;
      }
      
      return 1;
    });

    link.transition().duration(200).style('stroke-opacity', d => {
       const sourceHidden = hidden.has(d.source.group);
       const targetHidden = hidden.has(d.target.group);
       if (sourceHidden || targetHidden) return 0.05;

       if (isPathActive) {
         if (activeNodes) {
           const s = d.source.id;
           const t = d.target.id;
           if (activeNodes.has(s) && activeNodes.has(t)) {
             const p_s = parentMap.get(s);
             const p_t = parentMap.get(t);
             if (p_s === t || p_t === s) return 1.0; 
           }
         }
         return 0.1; 
       }
       return 0.6;
    });
    
    // 统一样式处理，增强高亮效果
    link.transition().duration(200)
      .style('stroke', d => {
        if (isPathActive && activeNodes) {
            const s = d.source.id;
            const t = d.target.id;
            if (activeNodes.has(s) && activeNodes.has(t)) {
               const p_s = parentMap.get(s);
               const p_t = parentMap.get(t);
               if (p_s === t || p_t === s) return "var(--color-primary)"; 
            }
        }
        return "#dadce0";
      })
      .style('stroke-width', d => {
        if (isPathActive && activeNodes) {
            const s = d.source.id;
            const t = d.target.id;
            if (activeNodes.has(s) && activeNodes.has(t)) {
               const p_s = parentMap.get(s);
               const p_t = parentMap.get(t);
               if (p_s === t || p_t === s) return 4;
            }
        }
        return 2;
      });
    
    node.selectAll("circle")
      .attr("stroke", d => {
          if (isPathActive && activeNodes && activeNodes.has(d.id)) return "#000"; 
          return "#fff";
      })
      .attr("stroke-width", d => {
           if (isPathActive && activeNodes && activeNodes.has(d.id)) return 3;
           return 2;
      });
  };
}

// Helper access for the updateGraphVisibility which needs to be called from toggleGroup & watchers
function updateGraphVisibility() {
  if (window.updateGraphVisibility) window.updateGraphVisibility();
}
</script>

<style scoped>
.graph-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.02);
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  backdrop-filter: blur(4px);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.legend {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 16px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(12px);
  border: 1px solid var(--color-border);
  max-width: 260px; 
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 10;
  transition: all 0.3s;
}

.legend:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

.legend-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  margin-bottom: 8px;
  text-transform: uppercase;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: opacity 0.2s;
  user-select: none;
}

.legend-item:hover {
  opacity: 0.8;
}

.legend-item.inactive {
  opacity: 0.4;
  text-decoration: line-through;
}

.graph-controls {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 5;
  display: flex;
  gap: 8px;
}

.control-btn {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s;
}

.control-btn:hover {
  background: var(--color-bg-secondary);
  transform: translateY(-1px);
}

.control-btn span {
  font-size: 18px;
  line-height: 1;
}

.graph-hint {
  position: absolute;
  bottom: 20px;
  right: 20px;
  font-size: 12px;
  color: var(--color-text-tertiary);
  background: rgba(255,255,255,0.8);
  padding: 4px 8px;
  border-radius: 4px;
  pointer-events: none;
}

.error-overlay,
.empty-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  text-align: center;
  padding: 20px;
}

.error-message {
  color: #ef4444;
  font-size: 16px;
  margin-bottom: 8px;
}

.error-hint,
.empty-hint {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin-bottom: 16px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: var(--color-primary-hover, #3b82f6);
  transform: translateY(-1px);
}

.refresh-btn svg {
  width: 16px;
  height: 16px;
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.control-btn .spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 8px;
}

.pulse-circle {
  animation: pulse 2s infinite;
  transform-origin: center;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.5; }
  70% { transform: scale(1.3); opacity: 0; }
  100% { transform: scale(0.95); opacity: 0; }
}
</style>
