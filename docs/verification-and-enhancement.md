# LLM幻觉校验机制与功能增强方案

## 问题2：现有LLM幻觉校验机制分析

### 当前多层校验架构 (Check Layer)

系统已实现 **3层校验机制** 防止LLM幻觉：

#### Layer 1: 学术概念过滤 (Academic Concept Filter)
**位置**: [`backend/api/real_node_generator.py:283`](../backend/api/real_node_generator.py#L283)

```python
async def is_academic_concept(concept: str) -> bool:
    """使用LLM二元分类判断是否为学术概念"""
    prompt = f'"{concept}"是学术概念吗？回答"是"或"否"'
    # 使用低temperature确保确定性输出
    temperature=0.1, max_tokens=10
```

**校验逻辑**:
- ✅ 过滤非学术内容（如"笨蛋"、"好玩"等）
- ✅ 使用极低temperature (0.1) 提高判断稳定性
- ✅ 二元输出减少幻觉空间

**局限性**:
- ⚠️ 未在主流程中强制调用（测试代码中存在但未启用）
- ⚠️ 对边缘学术概念可能误判

---

#### Layer 2: Wikipedia知识库验证 (Knowledge Base Validation)
**位置**: [`backend/api/routes.py:148`](../backend/api/routes.py#L148)

```python
async def get_wikipedia_definition(concept: str) -> Dict:
    """双语Wikipedia查询（中文→英文fallback）"""
    # 1. 查询中文Wikipedia
    # 2. 失败则查询英文Wikipedia
    # 3. 返回exists标志和权威定义
```

**校验逻辑**:
- ✅ **所有概念强制验证** - 中心节点和扩展节点均验证
- ✅ 双语查询 - 中文失败时自动尝试英文
- ✅ 处理歧义页面 - 自动选择第一个选项
- ✅ 可信度加权 - Wikipedia存在的概念基础可信度0.95，否则0.70

**效果**:
```python
# 有Wikipedia定义
credibility_base = 0.95  # 高可信度

# 无Wikipedia定义（LLM生成）
credibility_base = 0.70  # 降级可信度
```

---

#### Layer 3: 语义相似度排序 (Semantic Similarity Ranking)
**位置**: [`backend/api/routes.py:310-390`](../backend/api/routes.py#L310-L390)

```python
# 数据流:
# 1. LLM生成2倍候选概念
# 2. 计算每个候选与输入概念的语义相似度
# 3. 按相似度降序排列
# 4. 动态阈值筛选（保证3-9个节点）
SIMILARITY_THRESHOLD = 0.62
```

**校验逻辑**:
- ✅ **过度生成+排序筛选** - 生成20个候选，选择10个最相关
- ✅ **OpenAI Embeddings** - 使用text-embedding-3-small计算真实语义相似度
- ✅ **动态阈值** - 相似度<0.62的概念被过滤
- ✅ **数量控制** - 确保3-9个高质量节点

**防幻觉效果**:
```python
候选概念: 20个
↓ 语义相似度计算
↓ 排序 + 阈值筛选 (>0.62)
最终输出: 3-9个高相关性概念
```

---

### 现有机制的优势

| 校验层 | 防幻觉效果 | 性能开销 | 覆盖率 |
|-------|-----------|---------|--------|
| **学术概念过滤** | ⭐⭐⭐ | 低 (1次LLM调用) | 未启用 |
| **Wikipedia验证** | ⭐⭐⭐⭐⭐ | 中 (网络查询) | 100% |
| **语义相似度排序** | ⭐⭐⭐⭐ | 高 (Embedding计算) | 100% |

---

### 改进方案

#### 改进点1: 启用学术概念过滤器

**问题**: 目前`is_academic_concept()`仅存在于测试代码，未在主流程中调用

**方案**: 在生成概念后立即过滤

```python
# backend/api/real_node_generator.py 第157行后添加
if concepts:
    # 添加学术概念过滤
    filtered_concepts = []
    for concept in concepts:
        if await is_academic_concept(concept["name"]):
            filtered_concepts.append(concept)
        else:
            print(f"[FILTER] 非学术概念已过滤: {concept['name']}")
    concepts = filtered_concepts
    print(f"[SUCCESS] 学术过滤后剩余{len(concepts)}个概念")
```

**效果**: 
- 过滤"AI女友"、"量子炒股"等伪学术概念
- 防止LLM生成营销/娱乐内容

---

#### 改进点2: 跨域知识库验证

**问题**: 仅依赖Wikipedia，学术领域覆盖不足（如前沿研究、冷门学科）

**方案**: 集成学术数据库API

```python
async def verify_academic_concept(concept: str) -> Dict:
    """多源验证学术概念"""
    # 1. Wikipedia（通用知识）
    wiki_result = await get_wikipedia_definition(concept)
    
    # 2. arXiv API（前沿研究）
    arxiv_result = await search_arxiv(concept, max_results=1)
    
    # 3. Semantic Scholar（学术文献）
    scholar_result = await search_semantic_scholar(concept, limit=1)
    
    # 综合可信度
    exists = wiki_result["exists"] or len(arxiv_result) > 0 or len(scholar_result) > 0
    credibility = 0.95 if exists else 0.60  # 三源均无则降至0.60
    
    return {"exists": exists, "credibility": credibility, "sources": [...]}
```

**效果**:
- 覆盖前沿概念（如"扩散模型"、"量子纠错码"）
- 多源交叉验证，降低单一数据源偏差

---

#### 改进点3: LLM自校验（Self-Verification）

**问题**: 生成的跨学科关联可能过于牵强

**方案**: 二次LLM调用验证关联合理性

```python
async def verify_cross_discipline_relation(
    concept1: str, 
    concept2: str, 
    relation: str
) -> float:
    """使用LLM评估跨学科关联的合理性"""
    
    prompt = f"""
你是跨学科研究专家。评估以下跨学科关联的合理性：

概念1: {concept1}
概念2: {concept2}
关系: {relation}

合理性评分（0-10分）：
- 0-3分：关联牵强，缺乏学术依据
- 4-6分：关联存在，但较弱
- 7-10分：关联紧密，有明确学术依据

仅输出0-10的整数分数：
"""
    
    response = await llm_client.chat.completions.create(
        model="google/gemini-3-flash-preview",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=5
    )
    
    score = int(response.choices[0].message.content.strip())
    return score / 10.0  # 归一化到[0, 1]
```

**使用场景**:
```python
# 在生成概念后验证
for candidate in candidates:
    verification_score = await verify_cross_discipline_relation(
        concept, candidate["name"], candidate["relation"]
    )
    
    if verification_score < 0.4:  # 低于4分的关联丢弃
        print(f"[FILTER] 关联不合理: {candidate['name']} ({verification_score:.2f})")
        continue
    
    candidate["verification_score"] = verification_score
```

**效果**:
- 过滤"神经网络 → 社交网络"等弱关联
- LLM自我纠错机制

---

#### 改进点4: 人工反馈循环（Human-in-the-Loop）

**问题**: 完全自动化无法处理边缘案例

**方案**: 添加用户反馈机制

```python
# 前端交互
用户点击节点 → 标记为"不相关" → 后端记录 → 下次生成时降权

# 后端实现
class ConceptFeedback:
    async def mark_irrelevant(self, concept: str, parent: str):
        """用户标记不相关的概念对"""
        await redis_client.sadd(f"irrelevant:{parent}", concept)
    
    async def get_blacklist(self, parent: str) -> Set[str]:
        """获取用户标记的黑名单"""
        return await redis_client.smembers(f"irrelevant:{parent}")

# 在生成时过滤
blacklist = await feedback.get_blacklist(concept)
candidates = [c for c in candidates if c["name"] not in blacklist]
```

**效果**:
- 个性化过滤
- 持续学习，越用越准

---

### 推荐实施优先级

| 改进方案 | 优先级 | 实施难度 | 效果 | 建议 |
|---------|-------|---------|------|------|
| **启用学术概念过滤** | 🔴 高 | ⭐ 低 | ⭐⭐⭐ | **立即实施** |
| **LLM自校验** | 🟡 中 | ⭐⭐ 中 | ⭐⭐⭐⭐ | **推荐实施** |
| **多源知识库验证** | 🟢 低 | ⭐⭐⭐ 高 | ⭐⭐⭐⭐⭐ | 长期优化 |
| **人工反馈循环** | 🟢 低 | ⭐⭐ 中 | ⭐⭐⭐⭐ | 产品化后实施 |

---

## 总结

### 现有机制已经相当完善：
✅ Wikipedia权威验证（100%覆盖）  
✅ 语义相似度排序（防止离题）  
✅ 动态可信度计算（风险量化）  

### 改进空间：
⚠️ 学术概念过滤未启用（代码已存在）  
⚠️ 缺少LLM自校验机制  
⚠️ 单一知识源（仅Wikipedia）  

### 建议：
**短期**（本次迭代）：启用学术概念过滤  
**中期**（下个版本）：添加LLM自校验  
**长期**（产品化）：多源验证 + 用户反馈

---

## 问题3：功能2和功能3设计方案

详见下一节...
