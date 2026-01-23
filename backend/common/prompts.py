CLASSIFY_PROMPT = """\
你是一个跨学科知识专家。给定一个核心概念，分析它在不同学科领域中的应用和关联。

核心概念: {concept}

请只返回 JSON（不要解释、不要 Markdown），格式如下：
{{
  "concept": "{concept}",
  "primary_discipline": "学科名",
  "disciplines": [
    {{
      "name": "学科名称",
      "relevance_score": 0.95,
      "reason": "关联理由（具体、有学术价值）",
      "search_keywords": ["关键词1","关键词2","关键词3"]
    }}
  ],
  "suggested_additions": [
    {{
      "name": "可选学科",
      "reason": "为什么可能相关"
    }}
  ]
}}

要求：
- disciplines 至少 3 个；尽量包含“远亲概念”学科
- relevance_score ∈ [0,1]，按相关性降序
"""

VALIDATE_PROMPT = """\
你是检索结果的质量审核员。根据核心概念判断每条结果是否值得用于后续知识图谱构建。

核心概念：{concept}

候选结果（JSON数组）：{items_json}

请只返回 JSON，格式：
{{
  "validated": [
    {{
      "url": "...",
      "relevance_score": 0.0,
      "academic_value": 0.0,
      "is_valid": true,
      "notes": "简短原因"
    }}
  ],
  "rejected": [
    {{
      "url": "...",
      "reason": "简短原因"
    }}
  ]
}}

规则：
- 明显广告/论坛灌水/与概念无关 => rejected
- validated 中给出 relevance_score 与 academic_value ∈ [0,1]
"""