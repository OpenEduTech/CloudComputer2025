"""关联挖掘Prompt模板（带CoT推理）"""


class DiscoveryPrompt:
    """概念关联挖掘Prompt"""
    
    @staticmethod
    def get_discovery_prompt(concept: str, disciplines: list, depth: int = 2) -> str:
        """
        生成概念挖掘Prompt
        
        Args:
            concept: 核心概念
            disciplines: 目标学科列表
            depth: 挖掘深度
        """
        disciplines_str = "、".join(disciplines)
        
        return f"""你是一个跨学科知识专家。请使用Chain-of-Thought推理，系统性地分析概念关联。

【步骤1：概念本质分析】
核心概念：{concept}

请回答：
1. 这个概念的核心定义是什么？
2. 它的数学/物理本质是什么？
3. 它解决了什么根本问题？

【步骤2：跨学科映射】
在以下学科中寻找相关概念：
{disciplines_str}

对于每个学科，请思考：
- 该学科中是否有类似的概念或原理？
- 底层机制是否相通？（如：优化、不确定性、信息传递、能量守恒等）
- 是否存在历史上的类比或启发关系？

【步骤3：关联强度量化】
根据以下标准评分（0-1）：
- 0.8-1.0：底层数学/物理原理完全相同
- 0.5-0.8：存在明确的类比关系或理论桥梁
- 0.2-0.5：概念间接相关，需要多步推理
- 0.0-0.2：几乎无关或牵强附会

【输出格式】（严格JSON数组）
[
  {{
    "discipline": "学科名称",
    "concept_name": "相关概念名称",
    "definition": "概念定义（不超过100字）",
    "reasoning": "为什么这些概念相关的推理（80-120字，使用空格不要换行）",
    "common_principle": "共同的底层原理",
    "relation_type": "关系类型（is_foundation_of/similar_to/applied_in/generalizes/derived_from）",
    "strength": 0.85
  }}
]

【JSON格式要求】⚠️ 严格遵守
- 必须是有效的JSON数组格式
- 所有字符串值不能包含换行符，使用空格代替
- reasoning字段严格控制在80-120字
- 不要使用```json```或```代码块
- 直接返回纯JSON数组，不要有其他文字
- 检查所有引号、逗号、括号是否匹配

【重要提示】
- 必须在每个学科至少找出1-2个相关概念
- 避免表面的文字联系，要找深层原理
- 如果某个学科确实没有强关联，strength可以设为0.1-0.3并说明原因
- 每个学科最多返回{3 if depth == 1 else 5 if depth == 2 else 8}个概念

现在开始推理："""

    @staticmethod
    def get_expansion_prompt(parent_concept: str, parent_discipline: str, target_disciplines: list) -> str:
        """
        生成节点扩展Prompt
        
        Args:
            parent_concept: 父节点概念
            parent_discipline: 父节点学科
            target_disciplines: 目标扩展学科
        """
        disciplines_str = "、".join(target_disciplines)
        
        return f"""你是一个跨学科知识专家。现在需要扩展一个已存在的概念节点。

【父节点信息】
概念：{parent_concept}
学科：{parent_discipline}

【任务】
在以下学科中寻找与"{parent_concept}"直接相关的子概念或应用：
{disciplines_str}

【扩展策略】
1. 寻找更具体的子概念（如：神经网络 → 卷积神经网络）
2. 寻找实际应用场景（如：熵 → 机器学习中的交叉熵损失）
3. 寻找相关理论（如：牛顿力学 → 拉格朗日力学）

【输出格式】（严格JSON数组）
[
  {{
    "discipline": "学科名称",
    "concept_name": "相关概念名称",
    "definition": "概念定义（不超过100字）",
    "reasoning": "与父节点的关系说明（80-120字，不要换行）",
    "relation_type": "关系类型",
    "strength": 0.85
  }}
]

【要求】
- 每个学科返回1-3个最相关的概念
- 关系必须直接且明确
- 避免重复父节点已有的关联

现在开始扩展："""

    @staticmethod
    def get_cot_example() -> str:
        """返回CoT推理示例（用于few-shot learning）"""
        return """
【示例：分析"熵"概念】

步骤1 - 概念本质分析：
- 核心定义：熵是对系统无序程度或不确定性的度量
- 数学本质：概率分布的期望对数
- 根本问题：量化信息量、混乱度、能量可用性

步骤2 - 跨学科映射：

【信息论】
- 相关概念：香农熵、信息增益
- 底层机制：都使用概率分布描述不确定性
- 历史关系：香农受热力学第二定律启发
- 关联强度：0.95（数学公式完全一致）

【热力学】
- 相关概念：热力学熵、玻尔兹曼熵公式
- 底层机制：都描述微观状态数与宏观状态的关系
- 历史关系：信息熵从热力学熵类比而来
- 关联强度：0.92（理论基础）

【机器学习】
- 相关概念：交叉熵损失、KL散度
- 底层机制：用熵衡量预测分布与真实分布的差异
- 应用关系：信息论工具在ML中的直接应用
- 关联强度：0.88（应用层面）

【生物学】
- 相关概念：生态多样性指数、遗传多样性
- 底层机制：用熵的思想度量种群的复杂性
- 间接关系：概念类比，数学形式相似
- 关联强度：0.45（类比应用）

步骤3 - 输出JSON：
[
  {
    "discipline": "信息论",
    "concept_name": "香农熵",
    "definition": "香农熵是信息论中对信息量的度量，H(X) = -Σ p(x)log p(x)",
    "reasoning": "香农熵与热力学熵在数学形式上完全一致，都用于度量系统的不确定性。香农在1948年的论文中明确指出受到热力学第二定律的启发。",
    "common_principle": "概率分布的对数期望，度量不确定性",
    "relation_type": "similar_to",
    "strength": 0.95
  }
]

⚠️ JSON格式要求：
1. reasoning字段必须简洁（80-120字），只能使用单行文本，不能包含任何换行符
2. 所有字符串字段必须：不能包含换行符（\n, \r）、不能包含未转义的引号（"）、不能包含制表符（\t）
3. 直接输出JSON，不要使用```json```包裹
4. 输出的JSON必须可以直接被标准JSON解析器解析，不能有任何格式错误
"""
