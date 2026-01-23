from __future__ import annotations
from typing import List

DISCIPLINES: List[str] = ["数学", "物理学", "计算机科学", "生物学", "哲学/社会科学"]

def build_prompt(concept: str, max_nodes: int, max_links: int) -> str:
    return f"""
你是“跨学科知识图谱构建”智能体。给定核心概念：{concept}

任务：从不同学科（{", ".join(DISCIPLINES)}）挖掘相关概念，并构建知识图谱。

【必须严格输出 JSON】（不要 markdown，不要解释，不要多余文本），格式如下：
{{
  "nodes": [
    {{
      "id": "unique_id",
      "name": "概念名",
      "category": "学科",
      "description": "用1~2句话解释该概念，并说明它与核心概念{concept}的关系（尽量具体）"
    }}
  ],
  "links": [
    {{
      "source": "node_id",
      "target": "node_id",
      "relation": "6~12字动词短语（尽量具体）",
      "description": "用1~2句话解释source与target的关系机制/用途，并点明与{concept}的联系"
    }}
  ]
}}

硬性约束：
1) nodes 数量 <= {max_nodes}；links 数量 <= {max_links}
2) node.id 必须唯一；links 的 source/target 必须存在于 nodes.id
3) category 必须来自：{DISCIPLINES}
4) 尽量避免“有关/相关/联系/影响/作用/涉及”等空泛表述
5) 图谱尽量“连通”：避免孤立节点（每个节点最好至少出现在一条边中）
6) 至少输出 8 个节点、8 条边（概念很冷门可略少，但尽量满足）
7) 只输出 JSON

现在开始输出 JSON：
""".strip()

def stronger_prompt_for_regen(concept: str, reason: str, min_disciplines: int, max_nodes: int, max_links: int) -> str:
    return f"""
你刚才生成的知识图谱质量不达标（原因：{reason}）。

请重新生成更高质量的跨学科知识图谱，并严格满足：
- 必须覆盖至少 {min_disciplines} 个不同学科（从 {DISCIPLINES} 中选）
- links 的 relation 必须具体、有信息量，尽量6~12字动词短语
- nodes/links 都必须提供 description（1~2句话，说明与核心概念 {concept} 的关系）
- 尽量连通：避免孤立节点；每个节点最好至少连接一条边
- nodes <= {max_nodes}, links <= {max_links}
- node.id 唯一；links 的 source/target 必须存在于 nodes.id
- 只输出严格 JSON，不要任何解释

核心概念：{concept}

现在只输出 JSON：
""".strip()

def force_json_repair_prompt(bad_text: str, concept: str, max_nodes: int, max_links: int) -> str:
    return f"""
你刚才的输出不是严格 JSON，导致程序解析失败。

请把下面内容“改写”为严格 JSON，只允许输出 JSON（不要解释，不要 markdown）。
JSON 格式必须是：
{{
  "nodes": [{{"id":"...","name":"...","category":"数学/物理学/计算机科学/生物学/哲学/社会科学","description":"..."}}],
  "links": [{{"source":"...","target":"...","relation":"...","description":"..."}}]
}}
并满足：nodes<={max_nodes}，links<={max_links}，id唯一，source/target必须存在于nodes。

核心概念：{concept}

下面是刚才的原始输出（请基于它改写）：
{bad_text}
""".strip()