// Central Agent API Client (整合 Search Agent & Knowledge Engine)

// API Base URL - uses Vite proxy in development
const API_BASE = '/api';

// Helper to simulate delay (for streaming simulation)
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * 统一请求处理函数
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}



export const api = {
  /**
   * 健康检查
   */
  health: async () => {
    const res = await request('/health');
    return res.data;
  },

  /**
   * 概念分类 - 获取概念相关的学科领域
   * @param {string} concept - 要分类的概念
   * @param {number} maxDisciplines - 最大返回学科数
   * @param {number} minRelevance - 最小相关度阈值
   * @param {number} defaultSelected - 默认选中数量
   * @param {Object} options - 请求选项（如 signal）
   * @returns {Promise<{concept, primary_discipline, defaults, disciplines, suggested_additions}>}
   */
  classifyConcept: async (concept, maxDisciplines = 8, minRelevance = 0.3, defaultSelected = 3, options = {}) => {
    const res = await request('/search/plan', {
      method: 'POST',
      body: JSON.stringify({
        concept,
        max_disciplines: maxDisciplines,
        min_relevance: minRelevance,
        default_selected: defaultSelected,
      }),
      ...options
    });
    return res.data;
  },

  /**
   * 开始搜索任务
   * @param {string} concept - 搜索的概念
   * @param {Array<{name: string, search_keywords: string[]}>} disciplines - 学科列表
   * @param {Object} searchConfig - 搜索配置
   * @returns {Promise<{task_id, status, created_at, estimated_duration_seconds}>}
   */
  startSearch: async (concept, disciplines, searchConfig = {}) => {
    const res = await request('/search/start', {
      method: 'POST',
      body: JSON.stringify({
        concept,
        disciplines: disciplines.map(d => 
          typeof d === 'string' 
            ? { name: d, search_keywords: [] } 
            : d
        ),
        search_config: {
          depth: searchConfig.depth || 'medium',
          max_results_per_discipline: searchConfig.maxResultsPerDiscipline || 10,
          enable_validation: searchConfig.enableValidation !== false,
        },
      }),
    });
    return res.data;
  },

  /**
   * 获取搜索任务状态
   * @param {string} taskId - 任务ID
   * @returns {Promise<{task_id, status, progress, partial_results, started_at, updated_at}>}
   */
  getSearchStatus: async (taskId) => {
    const res = await request(`/search/status/${taskId}`);
    return res.data;
  },

  /**
   * 获取搜索结果
   * @param {string} taskId - 任务ID
   * @param {Object} options - 分页和过滤选项
   * @returns {Promise<{task_id, concept, summary, chunks, pagination}>}
   */
  getSearchResults: async (taskId, options = {}) => {
    const params = new URLSearchParams();
    if (options.page) params.set('page', options.page);
    if (options.pageSize) params.set('page_size', options.pageSize);
    if (options.discipline) params.set('discipline', options.discipline);
    if (options.minRelevance !== undefined) params.set('min_relevance', options.minRelevance);

    const queryString = params.toString();
    const endpoint = `/search/results/${taskId}${queryString ? `?${queryString}` : ''}`;
    const res = await request(endpoint);
    return res.data;
  },

  /**
   * 取消搜索任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<{task_id, status}>}
   */
  cancelSearch: async (taskId) => {
    const res = await request(`/search/tasks/${taskId}`, {
      method: 'DELETE',
    });
    return res.data;
  },

  /**
   * 轮询搜索状态直到完成
   * @param {string} taskId - 任务ID
   * @param {Function} onProgress - 进度回调
   * @param {number} interval - 轮询间隔(ms)
   * @returns {Promise<{task_id, concept, summary, chunks, pagination}>}
   */
  pollSearchUntilComplete: async (taskId, onProgress, interval = 2000) => {
    while (true) {
      const status = await api.getSearchStatus(taskId);
      
      if (onProgress) {
        onProgress(status);
      }

      if (status.status === 'completed') {
        return api.getSearchResults(taskId);
      }

      if (status.status === 'failed') {
        throw new Error('搜索任务失败');
      }

      if (status.status === 'cancelled') {
        throw new Error('搜索任务已取消');
      }

      await delay(interval);
    }
  },

  // ============ 图谱相关 (接入knowledge-engine) ============
  
  /**
   * 获取已有概念列表
   * @returns {Promise<{concepts: string[]}>}
   */
  listConcepts: async () => {
    try {
      const res = await request('/graph/concepts');
      return res.data;
    } catch (error) {
      console.error('获取概念列表失败:', error);
      return { concepts: [] };
    }
  },

  /**
   * 获取知识图谱数据 (从 central-agent 获取)
   * @param {string} concept - 概念名称
   * @returns {Promise<{concept, nodes, edges, total_nodes, total_edges}>}
   */
  getGraph: async (concept) => {
    const res = await request(`/graph/${encodeURIComponent(concept)}`);
    const data = res.data;
    
    // 转换为前端需要的格式
    return {
      nodes: data.nodes.map(n => ({
        id: n.id,
        label: n.label,
        description: n.description,
        group: n.domains?.[0] || '未知',
        domains: n.domains || [],
        val: n.size || 15,
        sourceChunks: n.source_chunks || []
      })),
      links: data.edges.map(e => ({
        source: e.source,
        target: e.target,
        relation: e.relation,
        description: e.description || ''
      })),
      totalNodes: data.total_nodes,
      totalEdges: data.total_edges
    };
  },

  /**
   * 获取原始文档片段
   * @param {string} chunkId - 片段ID
   * @returns {Promise<{doc_id, domain, content}>}
   */
  getChunk: async (chunkId) => {
    const res = await request(`/graph/chunk/${encodeURIComponent(chunkId)}`);
    return res.data;
  },

  /**
   * 获取图谱构建任务状态
   * @param {string} taskId - 任务ID
   * @returns {Promise<{task_id, status}>}
   */
  getGraphTaskStatus: async (taskId) => {
    const res = await request(`/task/${taskId}`);
    return res.data;
  },

  // ============ 知识问答相关 (接入knowledge-engine的LightRAG) ============
  
  /**
   * 知识问答 - 查询节点之间的关系
   * @param {string} concept - 核心概念
   * @param {string} sourceNode - 源节点ID
   * @param {string} targetNode - 目标节点ID
   * @param {string} question - 用户问题（可选）
   * @returns {Promise<{concept, source_node, target_node, question, answer}>}
   */
  queryNodeRelation: async (concept, sourceNode, targetNode, question = null) => {
    const body = {
      concept,
      source_node: sourceNode,
      target_node: targetNode,
    };
    if (question) {
      body.question = question;
    }
    
    const res = await request('/qa', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return res.data;
  },

  /**
   * 通用知识问答
   * @param {string} concept - 核心概念
   * @param {string} question - 用户问题
   * @returns {Promise<{answer: string}>}
   */
  askQuestion: async (concept, question) => {
    const res = await request('/qa', {
      method: 'POST',
      body: JSON.stringify({
        concept,
        source_node: concept,  // 使用concept作为source
        target_node: concept,  // 使用concept作为target
        question,
      }),
    });
    return res.data;
  },

  // ============ 聊天相关 (接入knowledge-engine的QA) ============
  
  /**
   * 流式回答 (目前knowledge-engine不支持流式，模拟流式输出)
   * @param {string} question - 用户问题
   * @param {string} concept - 当前概念
   * @param {string} sourceNode - 源节点（可选）
   * @param {string} targetNode - 目标节点（可选）
   */
  async *streamAnswer(question, concept = null, sourceNode = null, targetNode = null) {
    try {
      let answer;
      
      if (sourceNode && targetNode && sourceNode !== targetNode) {
        // 查询节点关系
        const result = await api.queryNodeRelation(concept, sourceNode, targetNode, question);
        answer = result.answer;
      } else if (concept) {
        // 通用问答
        const result = await api.askQuestion(concept, question);
        answer = result.answer;
      } else {
        // 没有概念时使用mock
        answer = "请先选择一个概念进行探索，或者开始搜索来构建知识图谱。";
      }
      
      // 模拟流式输出
      const chunks = answer.split(/(?<=[。！？\n])/);
      for (const chunk of chunks) {
        if (chunk.trim()) {
          await delay(100 + Math.random() * 200);
          yield chunk;
        }
      }
    } catch (error) {
      console.error('问答失败:', error);
      yield `抱歉，查询失败: ${error.message}`;
    }
  }
};
