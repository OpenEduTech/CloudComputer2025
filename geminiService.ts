
import { GraphData, KeywordAnalysis, DetailedExplanation, GraphNode, GraphEdge } from "./types";

// 后端API配置
const BACKEND_API_BASE = import.meta.env.REACT_APP_API_URL || 'http://localhost:8080';
const AGENT_API_BASE = import.meta.env.REACT_APP_AGENT_SERVICE_URL || 'http://localhost:8001';

// 调用后端API生成图谱
const callBackendAPI = async (concept: string, forceRefresh: boolean = false): Promise<GraphData> => {
  console.log(`正在调用后端API生成图谱: ${concept}, 强制刷新: ${forceRefresh}`);

  // 1. 提交图谱生成任务
  const buildResponse = await fetch(`${BACKEND_API_BASE}/api/graph/build`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      concept: concept,
      force_refresh: forceRefresh,
      domains: ["数学", "物理", "计算机/AI", "生物/神经科学", "社会科学/经济学"]
    })
  });

  if (!buildResponse.ok) {
    let errorMessage = `图谱生成请求失败: ${buildResponse.status}`;
    try {
      const errorData = await buildResponse.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {}
    throw new Error(errorMessage);
  }

  const taskInfo = await buildResponse.json();
  const taskId = taskInfo.task_id;

  console.log(`📡 API响应状态: ${buildResponse.status}`);
  console.log(`📝 任务响应: ${taskInfo.status}, 任务ID: ${taskId}，预计时间: ${taskInfo.estimated_time}秒`);
  console.log(`📦 完整响应数据:`, JSON.stringify(taskInfo, null, 2));

  // 如果有result数据，打印详细信息
  if (taskInfo.result) {
    console.log(`🎯 返回图谱数据: ${taskInfo.result.nodes?.length || 0} 个节点, ${taskInfo.result.edges?.length || 0} 条边`);
    console.log(`🏷️ 数据来源: ${taskInfo.result.meta?.source || 'unknown'}`);
    console.log(`🤖 生成方式: ${taskInfo.result.meta?.generated_at ? 'AI生成' : '静态数据'}`);
  }

  // 检查是否直接返回了结果（缓存命中或其他同步处理）
  if (taskInfo.status === 'success' && taskInfo.result) {
    console.log(`💾 缓存命中！直接返回结果`);
    console.log(`📊 缓存图谱数据: ${taskInfo.result?.nodes?.length || 0} 个节点, ${taskInfo.result?.edges?.length || 0} 条边`);
    console.log(`🏷️ 数据来源: ${taskInfo.result?.meta?.source || 'unknown'}`);
    console.log(`📅 缓存时间: ${taskInfo.result?.meta?.generated_at || 'unknown'}`);
    console.log(`📋 核心概念: ${taskInfo.result?.meta?.core_concept || 'unknown'}`);
    console.log(`🔍 缓存图谱JSON:`, JSON.stringify(taskInfo.result, null, 2));
    return taskInfo.result;
  }

  // 如果是缓存命中，直接返回结果（即使result字段不存在，也应该有数据）
  if (taskId === 'cached') {
    console.log('检测到缓存命中，尝试直接返回结果');
    if (taskInfo.result) {
      console.log(`返回缓存结果，节点数: ${taskInfo.result.nodes?.length || 0}`);
      return taskInfo.result;
    } else {
      console.warn('缓存命中但未返回result字段，尝试从其他字段获取数据');
      // 如果没有result字段，尝试从其他可能的字段获取
      const possibleData = taskInfo.data || taskInfo.graph;
      if (possibleData) {
        console.log(`从备用字段返回数据，节点数: ${possibleData.nodes?.length || 0}`);
        return possibleData;
      }
      throw new Error('缓存命中但数据格式异常');
    }
  }

  // 2. 轮询任务状态
  const maxAttempts = 60; // 最多等待60次（约5分钟）
  const pollInterval = 5000; // 每5秒检查一次

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));

    try {
      const statusResponse = await fetch(`${BACKEND_API_BASE}/api/task/status?task_id=${taskId}`);

      if (!statusResponse.ok) {
        console.warn(`检查任务状态失败 (${statusResponse.status})，继续等待...`);
        continue;
      }

      const statusData = await statusResponse.json();
      const task = statusData.task;

      console.log(`任务状态: ${task.status}, 进度: ${task.progress || 0}%`);

      if (task.status === 'success') {
        console.log(`✅ 图谱生成成功！`);
        console.log(`📊 图谱数据: ${task.result?.nodes?.length || 0} 个节点, ${task.result?.edges?.length || 0} 条边`);
        console.log(`🏷️ 数据来源: ${task.result?.meta?.source || 'unknown'}`);
        console.log(`🤖 AI生成时间: ${task.result?.meta?.generated_at || 'unknown'}`);
        console.log(`📋 核心概念: ${task.result?.meta?.core_concept || 'unknown'}`);
        console.log(`🔬 完整图谱JSON:`, JSON.stringify(task.result, null, 2));
        return task.result;
      } else if (task.status === 'failed') {
        throw new Error(`图谱生成失败: ${task.error_message || '未知错误'}`);
      }
      // 如果还是 pending 或 running，继续等待

    } catch (error) {
      console.warn(`检查任务状态时出错: ${error}，继续等待...`);
    }
  }

  throw new Error(`图谱生成超时，任务ID: ${taskId}`);
};

// 移除不再使用的 getCachedGraph 函数

// 生成模拟数据（后备方案）
const generateMockGraphData = (keyword: string): GraphData => {
  const domains = ["数学", "物理", "计算机/AI", "生物/神经科学", "社会科学/经济学"];

  // 为不同关键词生成不同的模拟数据
  const mockDataMap: Record<string, GraphData> = {
    "拓扑": {
      meta: {
        core_concept: "拓扑",
        normalized_concept: "topology",
        domains: ["数学", "物理", "计算机/AI"],
        version: "mock-v1",
        generated_at: new Date().toISOString(),
        stats: {
          num_nodes: 12,
          num_edges: 18,
          num_domains_covered: 3
        }
      },
      nodes: [
        {
          id: "topology_core",
          label: "拓扑学",
          field: "数学",
          type: "core",
          summary: "研究几何图形在连续变形下的不变性质",
          importance: 1.0,
          confidence: 0.95
        },
        {
          id: "continuous_deformation",
          label: "连续变形",
          field: "数学",
          type: "bridge",
          summary: "不撕裂、不粘连的变换",
          aliases: ["同胚", "homeomorphism"]
        },
        {
          id: "manifold",
          label: "流形",
          field: "数学",
          type: "normal",
          summary: "局部欧几里德空间的高维几何对象"
        },
        {
          id: "quantum_topology",
          label: "量子拓扑学",
          field: "物理",
          type: "bridge",
          summary: "量子力学中的拓扑不变量"
        },
        {
          id: "knot_theory",
          label: "纽结理论",
          field: "数学",
          type: "normal",
          summary: "研究三维空间中纽结的拓扑性质"
        },
        {
          id: "graph_topology",
          label: "图论拓扑",
          field: "计算机/AI",
          type: "normal",
          summary: "网络结构中的拓扑分析"
        },
        {
          id: "neural_network_topology",
          label: "神经网络拓扑",
          field: "计算机/AI",
          type: "normal",
          summary: "神经网络连接结构的拓扑性质"
        },
        {
          id: "topological_insulator",
          label: "拓扑绝缘体",
          field: "物理",
          type: "normal",
          summary: "具有拓扑保护的量子态材料"
        },
        {
          id: "persistent_homology",
          label: "持续同调",
          field: "计算机/AI",
          type: "normal",
          summary: "数据分析中的拓扑特征提取"
        },
        {
          id: "social_network_topology",
          label: "社交网络拓扑",
          field: "社会科学/经济学",
          type: "normal",
          summary: "社会关系网络的拓扑结构分析"
        },
        {
          id: "economic_networks",
          label: "经济网络",
          field: "社会科学/经济学",
          type: "normal",
          summary: "经济系统中交易关系的网络拓扑"
        },
        {
          id: "phase_transition",
          label: "相变",
          field: "物理",
          type: "bridge",
          summary: "物质状态变化的临界现象"
        }
      ],
      edges: [
        {
          source: "topology_core",
          target: "continuous_deformation",
          relation: "基于",
          relation_type: "直接关联",
          confidence: 0.95,
          evidence: "拓扑学核心概念建立在连续变形不变量的基础上"
        },
        {
          source: "continuous_deformation",
          target: "manifold",
          relation: "定义",
          relation_type: "数学关联",
          confidence: 0.90,
          evidence: "流形通过局部欧几里德性质刻画连续变形"
        },
        {
          source: "topology_core",
          target: "quantum_topology",
          relation: "扩展到",
          relation_type: "应用关联",
          confidence: 0.85,
          evidence: "拓扑概念在量子物理中发现新的应用"
        },
        {
          source: "topology_core",
          target: "knot_theory",
          relation: "包含",
          relation_type: "直接关联",
          confidence: 0.95,
          evidence: "纽结理论是拓扑学的重要分支"
        },
        {
          source: "quantum_topology",
          target: "topological_insulator",
          relation: "应用于",
          relation_type: "应用关联",
          confidence: 0.88,
          evidence: "量子拓扑原理解释拓扑绝缘体的导电性质"
        },
        {
          source: "topology_core",
          target: "graph_topology",
          relation: "应用于",
          relation_type: "应用关联",
          confidence: 0.82,
          evidence: "图论中借用拓扑学的连通性概念"
        },
        {
          source: "graph_topology",
          target: "neural_network_topology",
          relation: "应用于",
          relation_type: "应用关联",
          confidence: 0.80,
          evidence: "神经网络结构分析使用图论拓扑方法"
        },
        {
          source: "topology_core",
          target: "persistent_homology",
          relation: "发展出",
          relation_type: "应用关联",
          confidence: 0.85,
          evidence: "持续同调是拓扑学在数据科学中的应用"
        },
        {
          source: "persistent_homology",
          target: "neural_network_topology",
          relation: "相关于",
          relation_type: "类比关联",
          confidence: 0.75,
          evidence: "两种方法都用于分析复杂系统的结构特征"
        },
        {
          source: "topology_core",
          target: "social_network_topology",
          relation: "应用于",
          relation_type: "应用关联",
          confidence: 0.78,
          evidence: "社会网络分析借用拓扑学的连通性概念"
        },
        {
          source: "social_network_topology",
          target: "economic_networks",
          relation: "应用于",
          relation_type: "应用关联",
          confidence: 0.80,
          evidence: "经济网络是社会网络拓扑在经济学中的应用"
        },
        {
          source: "quantum_topology",
          target: "phase_transition",
          relation: "相关于",
          relation_type: "因果/机制",
          confidence: 0.85,
          evidence: "拓扑相变是量子相变的一种特殊形式"
        },
        {
          source: "phase_transition",
          target: "topological_insulator",
          relation: "解释",
          relation_type: "因果/机制",
          confidence: 0.90,
          evidence: "相变理论帮助理解拓扑绝缘体的相变行为"
        }
      ]
    }
  };

  return mockDataMap[keyword] || mockDataMap["拓扑"];
};

// 将GraphData转换为前端期望的KeywordAnalysis格式
const convertToKeywordAnalysis = (graphData: GraphData): KeywordAnalysis => {
  const iconMap: Record<string, string> = {
    "数学": "scale",
    "物理": "car",
    "计算机/AI": "laptop",
    "生物/神经科学": "tree",
    "社会科学/经济学": "book"
  };

  const colorPalette = [
    '#b8c2bb', '#c5aeb1', '#aebdc5', '#d5c8b8', '#c1b8c5',
    '#cad1b8', '#b8c5c5', '#a8b5c1', '#c1b8a8', '#b8c1c5'
  ];

  // 从节点中提取学科信息
  const disciplines = graphData.nodes
    .filter(node => node.type === 'core' || node.type === 'bridge')
    .slice(0, 12) // 限制数量
    .map((node, index) => ({
      id: node.id,
      name: node.label,
      icon: iconMap[node.field] || 'book',
      shortSummary: node.summary || `${node.label}在${node.field}中的应用`,
      color: colorPalette[index % colorPalette.length]
    }));

  return {
    keyword: graphData.meta.core_concept || graphData.meta.concept || "未知概念",
    disciplines
  };
};

// 模拟API延迟
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// 修改返回类型，包含analysis和graphData
export interface KeywordAnalysisResult {
  analysis: KeywordAnalysis;
  graphData: GraphData;
}

export const analyzeKeyword = async (keyword: string, forceRefresh: boolean = false): Promise<KeywordAnalysisResult> => {
  try {
    // 调用后端API（可选择强制刷新缓存）
    console.log(`${forceRefresh ? '强制刷新' : '调用'}后端API生成:`, keyword);
    const graphData = await callBackendAPI(keyword, forceRefresh);
    const analysis = convertToKeywordAnalysis(graphData);
    return { analysis, graphData };

  } catch (error) {
    console.warn('❌ 后端API调用失败，使用模拟数据:', error);
    console.log('📝 使用静态模拟数据作为后备方案');
    // 后端API失败时，使用模拟数据作为后备
    const graphData = generateMockGraphData(keyword);
    console.log(`🎭 模拟数据: ${graphData.nodes?.length || 0} 个节点, ${graphData.edges?.length || 0} 条边`);
    console.log(`🏷️ 数据来源: ${graphData.meta?.source || 'mock'}`);
    const analysis = convertToKeywordAnalysis(graphData);
    return { analysis, graphData };
  }
};

export const fetchDisciplineDetail = async (keyword: string, discipline: string): Promise<DetailedExplanation> => {
  try {
    // 获取图谱数据（自动处理缓存）
    let graphData;
    try {
      graphData = await callBackendAPI(keyword);
    } catch (apiError) {
      console.warn('❌ 获取最新数据失败，使用模拟数据:', apiError);
      console.log('📝 学科详情使用静态模拟数据');
      graphData = generateMockGraphData(keyword);
    }

    const node = graphData.nodes.find(n => n.label === discipline) || graphData.nodes[0];

    // 基于节点信息生成详细解释
    const definition = node.summary || `${discipline}是${keyword}概念在${node.field}领域的重要体现。`;

    // 查找相关的边来构建上下文
    const relatedEdges = graphData.edges.filter(edge =>
      edge.source === node.id || edge.target === node.id
    );

    const historicalContext = `在${node.field}领域，${discipline}作为${keyword}概念的关键应用，体现了跨学科研究的价值。${relatedEdges.length > 0 ? `该概念与其他${relatedEdges.length}个相关概念建立了联系。` : ''}`;

    const keyExample = `典型应用包括：${relatedEdges.slice(0, 2).map(edge =>
      `${edge.relation} ${edge.source === node.id ? edge.target : edge.source}`
    ).join('、') || '与相关领域概念的深入关联'}`;

    const crossDisciplinaryLink = `${discipline}不仅在${node.field}中发挥作用，还与其他学科领域如${graphData.meta.domains.filter(d => d !== node.field).slice(0, 2).join('、')}等建立了广泛的联系，形成跨学科知识网络。`;

  return {
    definition,
    historicalContext,
    keyExample,
    crossDisciplinaryLink,
    // include node-level enrichments so UI can show details
    details: node.details,
    key_points: node.key_points,
    aliases: node.aliases,
    reading_hint: node.reading_hint,
    importance: node.importance,
    confidence: node.confidence
  };

  } catch (e) {
    console.error("Failed to fetch discipline details", e);
    throw new Error("获取详情失败");
  }
};

// 导出GraphData类型供其他地方使用
export { generateMockGraphData, convertToKeywordAnalysis };
