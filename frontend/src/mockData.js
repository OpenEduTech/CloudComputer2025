// 模拟 API 1：
export const mockRelations = {
  categories: [
    { name: "核心关键词", itemStyle: { color: "#ff7070" } }, // 红色
    { name: "所属学科", itemStyle: { color: "#5470c6" } },   // 蓝色
    { name: "具体概念", itemStyle: { color: "#91cc75" } }    // 绿色
  ],
  nodes: [
    // 1. 核心关键词
    { id: "0", name: "熵", category: 0, symbolSize: 80, value: "核心检索词" },
    
    // 2. 学科层 
    { id: "1", name: "热力学", category: 1, symbolSize: 60, value: "基础学科" },
    { id: "2", name: "信息论", category: 1, symbolSize: 60, value: "应用学科" },
    { id: "3", name: "统计力学", category: 1, symbolSize: 60, value: "微观解释" },

    // 3. 具体概念层
    { id: "11", name: "热力学熵", category: 2, symbolSize: 45, value: "物理量" },
    { id: "21", name: "信息熵", category: 2, symbolSize: 45, value: "不确定性度量" },
    { id: "31", name: "玻尔兹曼熵", category: 2, symbolSize: 45, value: "微观状态数" }
  ],
  edges: [
    // 核心 -> 学科
    { source: "0", target: "1", label: { show: true, formatter: "属于" } },
    { source: "0", target: "2", label: { show: true, formatter: "引入" } },
    { source: "0", target: "3", label: { show: true, formatter: "解释" } },

    // 学科 -> 概念
    { source: "1", target: "11", label: { show: true, formatter: "定义" } },
    { source: "2", target: "21", label: { show: true, formatter: "提出" } },
    { source: "3", target: "31", label: { show: true, formatter: "公式化" } },

    // 概念 -> 概念 
    { 
      source: "11", 
      target: "21", 
      label: { show: true, formatter: "启发/衍生" },
      lineStyle: { type: "dashed", width: 2, curveness: 0.2 } // 虚线表示跨学科关联
    },
    {
      source: "31",
      target: "11",
      label: { show: true, formatter: "等价于" }
    }
  ]
};

// 模拟 API 2：
export const mockDefinition = {
  concept: "信息熵 (Information Entropy)",
  domain: "信息论 / 计算机科学",
  definition: "信息熵是香农（Shannon）借用热力学熵的概念，用来描述信源的不确定度。一个系统越是有序，信息熵就越低；反之，越是混乱，信息熵就越高。",
  key_points: [
    "📌 核心思想：消除不确定性所需的信息量。",
    "🧮 公式：H(x) = -Σ p(x) log(p(x))",
    "🔗 关联：与热力学熵在数学形式上完全一致（只差一个常数k）。"
  ],
  reference: "C. E. Shannon, 'A Mathematical Theory of Communication', 1948."
};

// 模拟 API 3：问答
export const mockQA = {
  answer: "这确实是一个深刻的问题。虽然热力学熵描述的是能量分布的混乱度，而信息熵描述的是数据的不确定性，但冯·诺依曼曾建议香农使用'熵'这个词，因为两者的数学公式在统计力学层面是同构的。本质上，它们都在描述系统状态的'可能性数量'。",
};