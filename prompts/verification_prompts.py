"""知识校验Prompt模板"""


class VerificationPrompt:
    """概念验证Prompt"""
    
    @staticmethod
    def get_verification_prompt(concept_a: str, concept_b: str, claimed_relation: str, strength: float) -> str:
        """
        生成知识校验Prompt
        
        Args:
            concept_a: 概念A
            concept_b: 概念B
            claimed_relation: 声称的关联
            strength: 声称的关联强度
        """
        return f"""你是一个严谨的知识验证专家。请验证以下概念关联的准确性。

【待验证的关联】
概念A：{concept_a}
概念B：{concept_b}
声称的关联：{claimed_relation}
声称强度：{strength}

【验证步骤】

1. 定义核查
   - 查阅权威来源（如学术定义、教科书定义）确认两个概念的标准定义
   - 检查定义中是否提到彼此或共同原理
   - 判断：定义是否支持这种关联？

2. 文献支持
   - 是否有学术论文、教科书明确提到这种关联？
   - 支持文献的数量和权威性如何？
   - 判断：文献证据是否充分？

3. 逻辑一致性
   - 该关联在逻辑上是否成立？
   - 是否存在反例或矛盾？
   - 是否过度类比或牵强附会？

【可信度评分标准】
- 0.9-1.0：学术界公认，有教材级支持
- 0.7-0.9：有多篇高质量论文支持
- 0.5-0.7：有一定依据但不充分
- 0.3-0.5：逻辑上成立但缺乏文献支持
- 0.0-0.3：可能错误或过度类比

【输出格式】（严格JSON）
{{
  "credibility_score": 0.87,
  "is_valid": true,
  "evidence": [
    {{
      "source": "Wikipedia",
      "url": "https://zh.wikipedia.org/wiki/...",
      "snippet": "具体段落引用（不超过200字）"
    }},
    {{
      "source": "学术论文",
      "url": "论文DOI或链接",
      "snippet": "论文中的相关描述"
    }}
  ],
  "logical_reasoning": "详细的逻辑分析（200-400字）",
  "warnings": []
}}

【重要原则】
- 宁可严格，不可放松
- 低于0.5的关联必须在warnings中说明问题
- 如果无法验证，在warnings中明确说明原因
- evidence数组至少包含1个证据，如果找不到证据，credibility_score不能超过0.4

现在开始验证："""

    @staticmethod
    def get_batch_verification_prompt(relations: list) -> str:
        """
        生成批量验证Prompt
        
        Args:
            relations: 待验证的关系列表
        """
        relations_str = "\n".join([
            f"{i+1}. {r['concept_a']} → {r['concept_b']}: {r['claimed_relation']}"
            for i, r in enumerate(relations)
        ])
        
        return f"""你是一个严谨的知识验证专家。请批量验证以下概念关联的准确性。

【待验证的关联列表】
{relations_str}

【任务】
对每个关联进行快速验证，重点检查：
1. 是否存在明显的事实错误？
2. 关联是否过于牵强？
3. 是否有基本的文献或定义支持？

【输出格式】（严格JSON数组）
[
  {{
    "index": 1,
    "concept_a": "概念A",
    "concept_b": "概念B",
    "credibility_score": 0.85,
    "is_valid": true,
    "quick_reasoning": "简短的验证理由（50-100字）",
    "warnings": []
  }}
]

【快速评分标准】
- 0.8-1.0：关联明确且广为人知
- 0.5-0.8：关联合理但需要更多验证
- 0.3-0.5：关联较弱或证据不足
- 0.0-0.3：可能错误

现在开始批量验证："""

    @staticmethod
    def get_fact_check_prompt(statement: str) -> str:
        """
        生成事实核查Prompt
        
        Args:
            statement: 待核查的陈述
        """
        return f"""你是一个事实核查专家。请验证以下陈述的准确性。

【待核查陈述】
{statement}

【核查要点】
1. 陈述中的关键事实是否准确？
2. 是否存在常见的误解或谬误？
3. 表述是否严谨？

【输出格式】（严格JSON）
{{
  "is_accurate": true,
  "confidence": 0.9,
  "issues": [],
  "corrections": "",
  "sources": []
}}

现在开始核查："""
