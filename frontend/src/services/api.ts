import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,  // 300秒超时，支持复杂LLM和相似度计算
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ConceptNode {
  id: string;
  label: string;
  discipline: string;
  definition: string;
  brief_summary?: string;  // LLM生成的一句话简介
  credibility: number;
  source?: 'Wikipedia' | 'LLM' | 'Arxiv' | 'Manual';  // 定义来源
  wiki_url?: string;  // 维基百科链接
  depth?: number;  // 节点深度（距离根节点的层级）
  parentId?: string;  // 父节点ID
}

export interface ConceptEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
  reasoning: string;
}

export interface ArxivPaper {
  title: string;
  authors: string[];
  summary: string;
  link: string;
  published: string;
}

export interface DiscoverResponse {
  status: string;
  request_id: string;
  data: {
    nodes: ConceptNode[];
    edges: ConceptEdge[];
    metadata: {
      total_nodes: number;
      total_edges: number;
      verified_nodes: number;
      avg_credibility: number;
      processing_time: number;
      mode: string;
      arxiv_papers?: ArxivPaper[];
      bridge_analysis?: {
        input_concepts: string[];
        total_bridges: number;
        bridges_by_type: {
          [key: string]: {
            name: string;
            connected: string[];
            principle: string;
          }[];
        };
        summary: string;
      };
    };
  };
}

export interface GraphResponse {
  status: string;
  data: {
    nodes: ConceptNode[];
    edges: ConceptEdge[];
  };
}

export interface ConceptDetailResponse {
  status: string;
  data: {
    concept: string;
    wiki_definition: string | null;
    wiki_url: string | null;
    wiki_source: string;
    detailed_introduction: string;
    related_papers: ArxivPaper[];
    papers_count: number;
  };
}

export interface ArxivSearchResponse {
  status: string;
  data: {
    query: string;
    total: number;
    papers: ArxivPaper[];
  };
}

export const conceptAPI = {
  /**
   * 功能1：自动跨学科发现
   */
  discover: async (concept: string, disciplines?: string[]) => {
    const response = await apiClient.post<DiscoverResponse>('/discover', {
      concept,
      disciplines,
      depth: 2,
      max_concepts: 30
    });
    return response.data;
  },

  /**
   * 功能2：限定学科的跨学科发现
   */
  discoverDisciplined: async (concept: string, disciplines: string[]) => {
    const response = await apiClient.post<DiscoverResponse>('/discover/disciplined', {
      concept,
      disciplines,
      max_concepts: 20
    });
    return response.data;
  },

  /**
   * 功能3：桥接概念发现
   */
  discoverBridge: async (concepts: string[], maxBridges: number = 5) => {
    const response = await apiClient.post<DiscoverResponse>('/discover/bridge', {
      concepts,
      max_bridges: maxBridges
    });
    return response.data;
  },

  /**
   * 查询图谱数据
   */
  getGraph: async (conceptId: string) => {
    const response = await apiClient.get<GraphResponse>(`/graph/${conceptId}`);
    return response.data;
  },

  /**
   * 展开节点 - 获取相关概念（使用专用expand端点）
   */
  expandNode: async (nodeId: string, nodeName: string, existingNodeIds: string[] = []) => {
    try {
      // 优先使用专用expand端点
      const response = await apiClient.post<{
        status: string;
        data: {
          nodes: ConceptNode[];
          edges: ConceptEdge[];
          parent_id: string;
        };
      }>('/expand', {
        node_id: nodeId,
        node_label: nodeName,
        existing_nodes: existingNodeIds,
        max_new_nodes: 10
      });
      
      return {
        status: response.data.status,
        request_id: '',
        data: {
          nodes: response.data.data.nodes,
          edges: response.data.data.edges,
          metadata: {
            total_nodes: response.data.data.nodes.length,
            total_edges: response.data.data.edges.length,
            verified_nodes: 0,
            avg_credibility: 0,
            processing_time: 0,
            mode: 'expand'
          }
        }
      } as DiscoverResponse;
    } catch (error) {
      // 回退：使用discover接口
      console.log('expand端点失败，使用discover接口');
      const response = await apiClient.post<DiscoverResponse>('/discover', {
        concept: nodeName,
        depth: 1,
        max_concepts: 10
      });
      return response.data;
    }
  },

  /**
   * 获取概念详细介绍（大模型生成的扩展信息）
   */
  getConceptDetail: async (conceptName: string) => {
    const response = await apiClient.get<ConceptDetailResponse>(`/concept/${encodeURIComponent(conceptName)}/detail`);
    return response.data;
  },

  /**
   * 搜索Arxiv论文
   */
  searchArxiv: async (query: string, maxResults: number = 10) => {
    const response = await apiClient.get<ArxivSearchResponse>('/arxiv/search', {
      params: { query, max_results: maxResults }
    });
    return response.data;
  },

  /**
   * 搜索概念
   */
  searchConcepts: async (keyword: string, limit: number = 10) => {
    const response = await apiClient.get('/concepts/search', {
      params: { keyword, limit }
    });
    return response.data;
  },

  /**
   * 获取学科列表
   */
  getDisciplines: async () => {
    const response = await apiClient.get('/disciplines');
    return response.data;
  },

  /**
   * AI问答接口
   */
  aiChat: async (concept: string, question: string, context?: string) => {
    const response = await apiClient.post('/ai/chat', {
      concept,
      question,
      context
    });
    return response.data;
  }
};
