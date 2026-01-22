"""
功能2和功能3的Prompt设计
三大功能的统一实现
"""

# ============================================================
# 功能1：搜索单一概念（不选学科）- 现有实现
# ============================================================
# 输入：concept="神经网络"
# 逻辑：跨学科挖掘，自动发现所有学科的关联
# Prompt：见 backend/api/real_node_generator.py generate_related_concepts()
# 已实现，保持不变

FUNCTION_1_PROMPT = """
你是跨学科知识挖掘专家，专门识别不同学科间的"远亲概念"。

任务：为概念"{parent_concept}"生成{max_count}个跨学科相关概念。

要求：
1. **强制跨学科多样性**：必须从以下至少4个不同领域寻找：
   - 数学/统计学
   - 计算机科学
   - 物理学
   - 生物学
   - 经济学/社会科学
   - 工程学

2. **寻找"远亲概念"而非"近亲概念"**：
   ✓ 好的例子：神经网络 → 热力学系统（物理学，能量最小化原理）
   ✗ 坏的例子：神经网络 → 卷积神经网络（同一领域的子类）

3. **每个概念必须包含跨学科原理**（核心！）

输出格式（每行一个概念，不要序号）：
概念名|学科|关系类型|跨学科原理

示例：
反向传播|数学|算法|梯度下降优化链式法则
突触可塑性|生物学|灵感|Hebbian学习规则的生物基础
玻尔兹曼机|物理学|类比|统计力学中的能量函数
图神经网络|计算机科学|扩展|拓扑结构的泛化
"""


# ============================================================
# 功能2：搜索单一概念 + 选学科
# ============================================================
# 输入：concept="神经网络", disciplines=["生物学", "数学"]
# 逻辑：只在指定学科中挖掘关联概念
# 新增功能

FUNCTION_2_PROMPT_TEMPLATE = """
你是跨学科知识挖掘专家。

任务：为概念"{parent_concept}"在指定学科中生成{max_count}个相关概念。

**仅在以下学科中寻找**：
{discipline_list}

严格要求：
1. **只能从上述指定学科中选择概念**，不得跨越到其他领域
2. 如果某个学科与该概念关联性弱，可以选择该学科中的"桥梁概念"（即连接性概念）
3. 必须解释每个概念与"{parent_concept}"在该学科视角下的关联

输出格式（每行一个概念，不要序号）：
概念名|学科|关系类型|跨学科原理

示例（假设指定学科为"生物学"和"数学"）：
输入：神经网络
输出：
突触传递|生物学|生物灵感|神经元间信号传递机制
Hebbian学习|生物学|学习规则|同步激活的神经元连接增强
梯度下降|数学|优化算法|损失函数最小化的迭代方法
反向传播|数学|计算方法|链式法则求导数传播误差
"""


# ============================================================
# 功能3：搜索多个概念
# ============================================================
# 输入：concepts=["熵", "最小二乘法"]
# 逻辑：寻找连接这些概念的"桥梁概念"
# 新增功能，最复杂

FUNCTION_3_PROMPT_TEMPLATE = """
你是跨学科概念连接专家，擅长发现看似无关概念之间的深层联系。

任务：分析以下多个概念之间的跨学科联系，找到连接它们的"桥梁概念"。

输入概念：
{concept_list}

核心要求：
1. **寻找桥梁概念**：能够同时关联多个输入概念的中间概念
2. **跨学科路径**：优先选择能够跨越不同学科的连接
3. **原理性关联**：必须基于共同的数学原理、物理规律或方法论

桥梁概念的三个层次：
- **直接桥梁**（优先）：与所有输入概念都有明确关联
  例：熵 + 最小二乘法 → 信息论（两者都涉及不确定性度量）
  
- **间接桥梁**（次选）：通过1-2步可连接所有概念
  例：熵 + 最小二乘法 → 概率论 → 统计推断
  
- **原理性桥梁**（补充）：体现相同的数学/哲学原理
  例：熵 + 最小二乘法 → 优化理论（两者都涉及最优化）

输出格式（每行一个桥梁概念，不要序号）：
概念名|桥梁类型|关联的输入概念|连接原理

桥梁类型：直接桥梁/间接桥梁/原理性桥梁

示例：
输入概念：["熵", "最小二乘法"]

输出：
信息论|直接桥梁|熵,最小二乘法|熵度量信息不确定性，最小二乘基于信息损失最小化
统计推断|直接桥梁|熵,最小二乘法|最大熵原理和最小二乘估计都是统计推断方法
优化理论|原理性桥梁|熵,最小二乘法|熵最大化和误差最小化都是优化问题
概率分布|间接桥梁|熵,最小二乘法|熵描述分布不确定性，最小二乘假设正态分布
贝叶斯推理|直接桥梁|熵,最小二乘法|最大熵先验+最小二乘似然=后验估计
"""


# ============================================================
# 功能2的具体实现逻辑
# ============================================================

async def generate_concepts_with_disciplines(
    parent_concept: str,
    disciplines: List[str],
    max_count: int = 10
) -> List[Dict]:
    """
    功能2：生成指定学科的相关概念
    
    Args:
        parent_concept: 输入概念，如"神经网络"
        disciplines: 学科列表，如["生物学", "数学"]
        max_count: 每个学科生成的概念数（总数=len(disciplines)*max_count）
        
    Returns:
        概念列表，每个概念包含：name, discipline, relation, cross_principle
    """
    
    # 构建学科列表字符串
    discipline_list = "\n".join([f"- {d}" for d in disciplines])
    
    # 填充prompt
    prompt = FUNCTION_2_PROMPT_TEMPLATE.format(
        parent_concept=parent_concept,
        max_count=max_count,
        discipline_list=discipline_list
    )
    
    system_prompt = "你是跨学科知识挖掘专家，严格按照指定学科范围生成概念。"
    
    response = await llm_client.chat.completions.create(
        model="google/gemini-3-flash-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=800,
        extra_body={"reasoning": {"enabled": True}}
    )
    
    # 解析输出（与功能1相同的解析逻辑）
    content = response.choices[0].message.content.strip()
    concepts = []
    
    for line in content.split('\n'):
        line = line.strip()
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 4:
                import re
                concept_name = re.sub(r'^\d+\.\s*', '', parts[0].strip())
                
                # 验证学科是否在指定列表中
                concept_discipline = parts[1].strip()
                if concept_discipline not in disciplines:
                    print(f"[FILTER] 学科不匹配，已过滤: {concept_name} ({concept_discipline})")
                    continue
                
                concepts.append({
                    "name": concept_name,
                    "discipline": concept_discipline,
                    "relation": parts[2].strip(),
                    "cross_principle": parts[3].strip()
                })
    
    return concepts


# ============================================================
# 功能3的具体实现逻辑
# ============================================================

async def find_bridge_concepts(
    concepts: List[str],
    max_bridges: int = 10
) -> List[Dict]:
    """
    功能3：寻找多个概念之间的桥梁概念
    
    Args:
        concepts: 输入概念列表，如["熵", "最小二乘法"]
        max_bridges: 最大桥梁概念数
        
    Returns:
        桥梁概念列表，每个包含：
        - name: 桥梁概念名
        - bridge_type: 桥梁类型（直接/间接/原理性）
        - connected_concepts: 关联的输入概念列表
        - connection_principle: 连接原理
    """
    
    # 构建概念列表字符串
    concept_list = "\n".join([f"- {c}" for c in concepts])
    
    # 填充prompt
    prompt = FUNCTION_3_PROMPT_TEMPLATE.format(
        concept_list=concept_list
    )
    
    system_prompt = "你是跨学科概念连接专家，擅长发现看似无关概念之间的深层联系。"
    
    response = await llm_client.chat.completions.create(
        model="google/gemini-3-flash-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,  # 稍高的temperature鼓励创造性连接
        max_tokens=1000,
        extra_body={"reasoning": {"enabled": True}}
    )
    
    # 解析输出
    content = response.choices[0].message.content.strip()
    bridges = []
    
    for line in content.split('\n'):
        line = line.strip()
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 4:
                import re
                bridge_name = re.sub(r'^\d+\.\s*', '', parts[0].strip())
                bridge_type = parts[1].strip()
                connected = [c.strip() for c in parts[2].split(',')]
                principle = parts[3].strip()
                
                bridges.append({
                    "name": bridge_name,
                    "bridge_type": bridge_type,
                    "connected_concepts": connected,
                    "connection_principle": principle
                })
    
    # 按桥梁类型排序：直接桥梁 > 间接桥梁 > 原理性桥梁
    priority = {"直接桥梁": 1, "间接桥梁": 2, "原理性桥梁": 3}
    bridges.sort(key=lambda x: priority.get(x["bridge_type"], 999))
    
    return bridges[:max_bridges]


# ============================================================
# API接口设计
# ============================================================

"""
三个功能的统一API接口设计：

POST /api/discover
功能1：不选学科的自动跨学科挖掘
{
    "concept": "神经网络",
    "max_concepts": 10
}

POST /api/discover/disciplined
功能2：指定学科的概念挖掘
{
    "concept": "神经网络",
    "disciplines": ["生物学", "数学"],
    "max_concepts": 10
}

POST /api/discover/bridge
功能3：多概念桥梁发现
{
    "concepts": ["熵", "最小二乘法"],
    "max_bridges": 10
}
"""


# ============================================================
# 数据流对比
# ============================================================

"""
功能1 数据流:
用户输入 → LLM生成跨学科候选 → 语义相似度排序 → Wikipedia验证 → 返回图谱

功能2 数据流:
用户输入+学科列表 → LLM生成指定学科候选 → 学科过滤 → 语义相似度排序 → Wikipedia验证 → 返回图谱

功能3 数据流:
用户输入多概念 → LLM生成桥梁概念 → 桥梁类型排序 → 验证每个桥梁与输入概念的关联 → 返回桥梁图谱

关键区别:
- 功能1: 自动跨学科（最大自由度）
- 功能2: 约束跨学科（用户指定）
- 功能3: 连接性挖掘（寻找中间节点）
"""


# ============================================================
# 图谱结构对比
# ============================================================

"""
功能1 图谱结构:
        [神经网络]
           /  |  \\
    [反向传播][突触可塑性][玻尔兹曼机]
    (数学)    (生物学)    (物理学)

功能2 图谱结构（指定"生物学"和"数学"）:
        [神经网络]
           /    \\
    [突触传递] [梯度下降]
    (生物学)    (数学)

功能3 图谱结构（输入["熵", "最小二乘法"]）:
    [熵]              [最小二乘法]
      \\              /
       [信息论]
      /       \\
    [统计推断] [优化理论]
              /
    [最小二乘法]

特点:
- 功能1/2: 星形图（中心节点+扩展节点）
- 功能3: 网状图（多个中心+桥梁节点）
"""
