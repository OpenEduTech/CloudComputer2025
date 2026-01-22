# Prompt Templates for Cross-Disciplinary Knowledge Graph
## 1. 核心 Prompt 模板
```text
你是“跨学科知识图谱构建”智能体。给定核心概念：{concept}

请从以下学科中寻找相关概念：
- 数学
- 物理学
- 计算机科学
- 生物学
- 哲学/社会科学

输出必须是严格 JSON（不要解释、不要 markdown、不要多余文本），格式如下：
{
  "nodes": [
    {"id":"unique_id","name":"概念名","category":"学科"}
  ],
  "links": [
    {"source":"node_id","target":"node_id","relation":"关系描述"}
  ]
}

硬性要求：
1. nodes 数量 ≤ 30，links 数量 ≤ 60
2. node.id 必须唯一
3. links 的 source / target 必须存在于 nodes.id
4. category 必须来自上述学科列表
5. 关系需体现跨学科关联，避免牵强附会

现在只输出 JSON：
```

## 2. Prompt 设计思路
- 跨学科约束：显式列出多个学科，防止模型只在单一领域展开
- 结构约束：强制 JSON 输出，避免自然语言描述
- 规模控制：限制节点和边数量，避免输出失控
- 可视化友好：nodes / links 结构与前端 ECharts / D3.js 保持一致

## 3. Prompt 优化记录
| 问题         | 优化方式            |
| ---------- | --------------- |
| 模型输出自然语言   | 增加“只输出 JSON”强约束 |
| JSON 结构不稳定 | 增加固定字段示例        |
| 学科混乱       | 引入学科白名单         |
| 节点过多       | 增加数量上限          |

## 4. 示例输入 / 输出
输入：  
```text
concept = 熵
```

输出（节选）：  
```text
{
  "nodes": [
    {"id":"m1","name":"信息熵","category":"数学"},
    {"id":"p1","name":"热力学熵","category":"物理学"}
  ],
  "links": [
    {"source":"p1","target":"m1","relation":"信息熵推广了热力学熵的统计思想"}
  ]
}
```