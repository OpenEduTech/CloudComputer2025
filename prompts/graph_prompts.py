"""图谱构建Prompt模板"""


class GraphPrompt:
    """图谱构建Prompt"""
    
    @staticmethod
    def get_graph_builder_prompt(verified_concepts: list) -> str:
        """
        生成图谱构建Prompt
        
        Args:
            verified_concepts: 已验证的概念列表
        """
        concepts_str = "\n".join([
            f"- {c.get('concept_name', 'Unknown')} ({c.get('discipline', 'Unknown')}): {c.get('definition', 'N/A')}"
            for c in verified_concepts
        ])
        
        return f"""你是一个图数据结构专家。请将验证后的概念关联转换为标准的图数据格式。

【已验证的概念列表】
{concepts_str}

【任务要求】

1. 提取节点信息：
   - id：唯一标识符（格式：概念名拼音_学科拼音，如：entropy_xinxilun）
   - label：概念名称
   - discipline：所属学科
   - definition：简短定义（1句话，不超过100字）
   - credibility：可信度分数（保留原有分数）

2. 提取边信息：
   - source：源节点id
   - target：目标节点id
   - relation：关系类型（is_foundation_of/similar_to/applied_in/generalizes/derived_from）
   - weight：关联强度（0-1）
   - reasoning：关联原因（简述，不超过200字）

3. 关系类型定义：
   - "is_foundation_of"：A是B的理论基础
   - "similar_to"：A和B在原理上相似
   - "applied_in"：A应用于B领域
   - "generalizes"：A是B的泛化
   - "derived_from"：A由B推导而来

【输出格式】（严格JSON）
{{
  "nodes": [
    {{
      "id": "entropy_xinxilun",
      "label": "熵",
      "discipline": "信息论",
      "definition": "信息的不确定性度量",
      "credibility": 0.95
    }}
  ],
  "edges": [
    {{
      "source": "entropy_xinxilun",
      "target": "shannon_entropy_xinxilun",
      "relation": "is_foundation_of",
      "weight": 0.92,
      "reasoning": "香农熵是信息论中熵的具体定义"
    }}
  ],
  "metadata": {{
    "total_nodes": 18,
    "total_edges": 24,
    "avg_credibility": 0.87
  }}
}}

【重要规则】
1. 节点ID必须唯一，使用小写字母和下划线
2. 所有边的source和target必须对应存在的节点ID
3. 关系类型必须从预定义的5种中选择
4. credibility和weight必须在[0.0, 1.0]范围内
5. 确保JSON格式严格有效，可以被Python json.loads()解析

现在开始构建图谱："""

    @staticmethod
    def get_merge_graphs_prompt(graph1: dict, graph2: dict) -> str:
        """
        生成图谱合并Prompt
        
        Args:
            graph1: 图谱1
            graph2: 图谱2
        """
        return f"""你是一个图数据结构专家。请合并两个知识图谱，去除重复节点和边。

【图谱1】
节点数: {len(graph1.get('nodes', []))}
边数: {len(graph1.get('edges', []))}

【图谱2】
节点数: {len(graph2.get('nodes', []))}
边数: {len(graph2.get('edges', []))}

【合并规则】
1. 节点去重：相同ID的节点保留可信度更高的
2. 边去重：相同source和target的边保留权重更高的
3. 保持所有节点和边的引用完整性
4. 重新计算元数据

【输出格式】（严格JSON）
{{
  "nodes": [...],
  "edges": [...],
  "metadata": {{
    "total_nodes": 数字,
    "total_edges": 数字,
    "avg_credibility": 数字,
    "merged_from": ["graph1", "graph2"]
  }}
}}

现在开始合并："""

    @staticmethod
    def get_format_validation_prompt(graph_json: str) -> str:
        """
        生成格式验证Prompt
        
        Args:
            graph_json: 图谱JSON字符串
        """
        return f"""你是一个JSON格式专家。请检查以下图谱JSON的格式是否符合规范。

【待检查的JSON】
{graph_json}

【检查项】
1. JSON语法是否正确？
2. 所有必需字段是否存在？
3. 数据类型是否正确？
4. 边的引用是否有效？

【输出格式】
{{
  "is_valid": true/false,
  "errors": [],
  "warnings": [],
  "suggestions": []
}}

现在开始检查："""
