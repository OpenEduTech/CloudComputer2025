import { defineStore } from 'pinia'
import { api } from '../api'

export const useGraphStore = defineStore('graph', {
  state: () => ({
    nodes: [],
    links: [],
    loading: false,
    error: null,  // 添加错误状态
    selectedNode: null,
    selectedEdge: null,  // 添加选中的边
    disciplines: [],
    concept: '',  // 当前概念
    totalNodes: 0,
    totalEdges: 0,
    availableConcepts: [],  // 已构建的概念列表
  }),
  
  actions: {
    async fetchGraph(concept) {
      this.loading = true;
      this.error = null;
      this.concept = concept;
      
      try {
        const data = await api.getGraph(concept);
        
        // Transform data for D3 (if needed, but usually D3 modifies objects in place)
        // We clone to avoid reactivity issues during simulation if necessary
        this.nodes = data.nodes.map(n => ({
          ...n,
          // 确保有group属性用于着色
          group: n.group || n.domains?.[0] || '未知'
        }));
        this.links = data.links.map(l => ({...l}));
        
        // 统计信息
        this.totalNodes = data.totalNodes || this.nodes.length;
        this.totalEdges = data.totalEdges || this.links.length;
        
        // Extract unique disciplines for coloring
        const groups = new Set(this.nodes.map(n => n.group));
        this.disciplines = Array.from(groups);
        
      } catch (error) {
        console.error("Failed to fetch graph:", error);
        this.error = error.message || '获取知识图谱失败';
        // 清空数据
        this.nodes = [];
        this.links = [];
        this.totalNodes = 0;
        this.totalEdges = 0;
        this.disciplines = [];
      } finally {
        this.loading = false;
      }
    },
    
    // 获取已有概念列表
    async fetchAvailableConcepts() {
      try {
        const result = await api.listConcepts();
        this.availableConcepts = result.concepts || [];
        return this.availableConcepts;
      } catch (error) {
        console.error("Failed to fetch concepts:", error);
        return [];
      }
    },
    
    selectNode(node) {
      this.selectedNode = node;
      this.selectedEdge = null;  // 取消边选择
    },
    
    selectEdge(edge) {
      this.selectedEdge = edge;
      this.selectedNode = null;  // 取消节点选择
    },
    
    clearSelection() {
      this.selectedNode = null;
      this.selectedEdge = null;
    },

    async fetchChunk(chunkId) {
      if (!chunkId) return null;
      try {
        return await api.getChunk(chunkId);
      } catch (error) {
        console.error(`Failed to fetch chunk ${chunkId}:`, error);
        return null;
      }
    }
  }
})
