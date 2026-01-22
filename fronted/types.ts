
// 根据graph.schema.json更新类型定义，支持LLM返回的数据格式
export interface GraphMeta {
  // LLM返回的字段
  concept?: string;
  trace_id?: string;

  // 传统字段
  core_concept?: string;
  normalized_concept?: string;
  domains: string[];
  version?: string;
  generated_at: string;
  stats: {
    num_nodes: number;
    num_edges: number;
    num_domains_covered: number;
    // LLM额外统计字段
    num_cross_domain_edges?: number;
    num_cross_domain_edges_all?: number;
    num_cross_domain_edges_highlight?: number;
  };
  notes?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  field: string;
  type: 'core' | 'bridge' | 'normal';
  aliases?: string[];
  summary?: string;
  importance?: number;
  confidence?: number;

  // LLM额外返回的字段
  details?: string;
  key_points?: string[];
  reading_hint?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  relation_type: string;
  confidence: number;
  evidence: string;
  reasoning_chain?: string[];
  bridge_concepts?: string[];
  sources?: Array<{
    title: string;
    url?: string;
    note?: string;
  }>;
  direction?: 'directed' | 'undirected';
  tags?: string[];
}

export interface GraphData {
  meta: GraphMeta;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface KeywordAnalysisResult {
  analysis: KeywordAnalysis;
  graphData: GraphData;
}

// 为兼容前端现有代码，保留旧类型并添加转换函数
export interface Discipline {
  id: string;
  name: string;
  icon: string; // Emoji or SVG key
  shortSummary: string;
  color: string;
}

export interface KeywordAnalysis {
  keyword: string;
  disciplines: Discipline[];
}

export interface DetailedExplanation {
  definition: string;
  historicalContext: string;
  keyExample: string;
  crossDisciplinaryLink: string;
  // From GraphNode
  details?: string;
  key_points?: string[];
  aliases?: string[];
  reading_hint?: string;
  importance?: number;
  confidence?: number;
}

export enum AppScreen {
  SEARCH = 'SEARCH',
  CONTEXT = 'CONTEXT',
  DETAIL = 'DETAIL'
}
