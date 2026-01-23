import { defineStore } from 'pinia'
import { api } from '../api'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
    isStreaming: false,
    currentConcept: '',  // 当前概念上下文
    contextNode: null,   // 当前上下文节点（用户点击的节点）
    contextEdge: null,   // 当前上下文边（用户点击的边）
  }),
  
  actions: {
    // 设置当前概念上下文
    setConcept(concept) {
      this.currentConcept = concept;
    },
    
    // 设置节点上下文（用户选中了某个节点时调用）
    setContextNode(node) {
      this.contextNode = node;
      this.contextEdge = null;
    },
    
    // 设置边上下文（用户选中了某条边时调用）
    setContextEdge(edge) {
      this.contextEdge = edge;
      this.contextNode = null;
    },
    
    // 清除上下文
    clearContext() {
      this.contextNode = null;
      this.contextEdge = null;
    },
    
    // 发送消息
    async sendMessage(text) {
      // User message
      this.messages.push({
        id: Date.now(),
        role: 'user',
        content: text
      });
      
      this.isStreaming = true;
      const botMsgId = Date.now() + 1;
      
      // Placeholder for bot message
      this.messages.push({
        id: botMsgId,
        role: 'assistant',
        content: ''
      });
      
      const botMsgIndex = this.messages.findIndex(m => m.id === botMsgId);
      
      try {
        // 根据上下文决定调用方式
        let sourceNode = null;
        let targetNode = null;
        
        if (this.contextEdge) {
          // 如果有边上下文，查询两个节点的关系
          sourceNode = this.contextEdge.source?.id || this.contextEdge.source;
          targetNode = this.contextEdge.target?.id || this.contextEdge.target;
        } else if (this.contextNode) {
          // 如果有节点上下文，以该节点为中心
          sourceNode = this.contextNode.id;
          targetNode = this.currentConcept || sourceNode;
        }
        
        const stream = api.streamAnswer(
          text, 
          this.currentConcept, 
          sourceNode, 
          targetNode
        );
        
        for await (const chunk of stream) {
          this.messages[botMsgIndex].content += chunk;
        }
      } catch (e) {
        this.messages[botMsgIndex].content += "\n[出错: 无法连接到知识引擎]";
        console.error('Chat error:', e);
      } finally {
        this.isStreaming = false;
      }
    },
    
    // 询问关于特定节点的问题
    async askAboutNode(node, question = null) {
      this.setContextNode(node);
      
      const defaultQuestion = question || `请详细介绍一下"${node.label || node.id}"这个概念，以及它在知识图谱中的重要性。`;
      await this.sendMessage(defaultQuestion);
    },
    
    // 询问关于特定边（关系）的问题
    async askAboutEdge(edge, question = null) {
      this.setContextEdge(edge);
      
      const sourceId = edge.source?.id || edge.source;
      const targetId = edge.target?.id || edge.target;
      const relation = edge.relation || '关联';
      
      const defaultQuestion = question || `请解释"${sourceId}"和"${targetId}"之间的"${relation}"关系。`;
      await this.sendMessage(defaultQuestion);
    },
    
    // 清空对话
    clearMessages() {
      this.messages = [];
    }
  }
})
