def _fill(tpl: str, **kwargs) -> str:
    for k, v in kwargs.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl



"""
Prompt模板：跨学科知识图谱智能体（增强版）
目标：直接生成结构化 JSON（nodes/edges），支持多学科、多跳、桥梁概念，并附带置信度与证据。
"""

DISCIPLINES = [
  "数学", "物理", "计算机科学", "生物学", "神经科学", "统计学",
  "信号处理", "控制理论", "经济学", "社会学", "心理学", "哲学"
]

GRAPH_JSON_SCHEMA = r"""
输出必须是 **纯 JSON**（不要 Markdown，不要代码块，不要多余解释）。
顶层字段：
{
  "core_concept": str,
  "disciplines": [str],
  "nodes": [
    {
      "name": str,
      "discipline": str,
      "level": int,              // 0=核心概念; 1=一跳; 2=二跳
      "type": "concept"|"method"|"phenomenon"|"assumption"|"metric"|"application",
      "description": str,        // 1~2 句解释
      "confidence": float        // 0~1
    }
  ],
  "edges": [
    {
      "source": str,             // 使用 node.name
      "target": str,             // 使用 node.name
      "relation": "RELATES_TO"|"ENABLED_BY"|"INSPIRED_BY"|"FORMALIZED_BY"|"ASSUMES"|"APPLIED_TO",
      "logic": str,              // 1~2 句推理链路（强调跨学科桥梁）
      "confidence": float        // 0~1
    }
  ]
}

约束：
1) nodes 必须包含 core_concept（level=0, discipline="核心概念"）。
2) disciplines 至少 5 个且必须包含：数学、计算机科学、生物学（其余自选，但要多样）。
3) nodes 总数建议 18~35；edges 总数建议 25~60（不要太少）。
4) 必须包含“桥梁边”：至少 8 条 edges 的两端 discipline 不同。
5) 不能胡编：不要虚构论文/学者/年份；逻辑要自洽；置信度低的边要标低 confidence。
"""

MINING_GRAPH_PROMPT = f"""
你是“跨学科知识图谱智能体”，需要围绕用户给定的核心概念构建一张跨学科知识图谱。
你必须强制跨学科挖掘，并显式构建“桥梁概念”和“桥梁关系”。

核心概念：{{concept}}

请遵循 JSON Schema：
{GRAPH_JSON_SCHEMA}

生成策略（写入 logic 与 description 中）：
- 先给出每个学科的 2~4 个关键概念（level=1）
- 从其中挑 6~10 个最关键的概念继续扩展二跳概念（level=2），其中至少一半是跨学科映射（比如从生物学启发到数学形式化）
- 构建边时，除了 core->子概念，还要显式写“概念之间”的跨学科桥梁边（例如：生物->数学->工程）
- 每条 edge 的 logic 用“推理链路”表达（避免一句话空泛描述）

输出必须是纯 JSON。
"""

# 让模型根据证据进行修正（第二阶段）
REFINE_WITH_EVIDENCE_PROMPT = r"""
你将收到：
1) 初始图谱 JSON（来自模型）
2) 若干条 Web 搜索证据（每条包含 query + snippets）

任务：基于证据对图谱做“保守修正”，输出新的纯 JSON。
修正规则：
- 发现明显不靠谱或证据不足的节点/边：降低 confidence 或删除（优先降低，再删除）
- 发现同义重复节点：合并为一个（保留更常用名称）
- 对于跨学科桥梁边，若证据支持，可略提升 confidence（上调不超过 0.15）
- 不要新增大量节点（最多新增 3 个节点 + 5 条边），重点是“修正与稳健化”
- 仍需满足：至少 5 学科，nodes 18~35，edges 25~60，跨学科桥梁边 >= 8

输出必须是纯 JSON，不要任何解释文字。
"""

def get_mining_graph_prompt(concept: str) -> str:
    return _fill(MINING_GRAPH_PROMPT, concept=concept)


def get_refine_prompt(graph_json: str, evidence_text: str) -> str:
    return f"""初始图谱JSON：
{graph_json}

Web搜索证据：
{evidence_text}

{REFINE_WITH_EVIDENCE_PROMPT}
"""
