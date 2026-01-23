#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实节点生成器 - 使用LLM和语义相似度
"""

import os
import asyncio
import numpy as np
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 加载环境变量
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ==================== LLM客户端 ====================
_llm_client = None
_embedding_client = None
_last_embedding_time = 0  # 记录上次embedding请求时间
_embedding_min_interval = 0.2  # 最小请求间隔（秒）

def get_llm_client():
    """获取LLM客户端（用于文本生成）"""
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            _llm_client = AsyncOpenAI(
                api_key=api_key,
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            )
            print("[INFO] LLM客户端已初始化（文本生成）")
    return _llm_client


def get_embedding_client():
    """获取Embedding客户端（用于相似度计算）"""
    global _embedding_client
    if _embedding_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            import httpx
            # 配置HTTP客户端：增加超时和连接限制
            http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),  # 总超时60秒，连接超时10秒
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            _embedding_client = AsyncOpenAI(
                api_key=api_key,
                http_client=http_client
            )
            print("[INFO] Embedding客户端已初始化（OpenAI，超时60秒）")
        else:
            print("[WARNING] OPENAI_API_KEY未设置，相似度计算将使用默认值")
    return _embedding_client


# ==================== LLM生成相关概念 ====================

async def generate_related_concepts(
    parent_concept: str,
    existing_concepts: List[str],
    max_count: int = 5
) -> List[Dict[str, str]]:
    """
    使用LLM生成相关概念
    
    Args:
        parent_concept: 父概念名称
        existing_concepts: 已存在的概念列表
        max_count: 最大生成数量
        
    Returns:
        [{"name": "概念名", "discipline": "学科", "relation": "关系类型"}, ...]
    """
    client = get_llm_client()
    if not client:
        print("[WARNING] LLM客户端未初始化，使用预定义概念")
        return _get_fallback_concepts(parent_concept)
    
    # 构建跨学科提示词
    existing_str = "、".join(existing_concepts) if existing_concepts else "无"
    prompt = f"""为概念"{parent_concept}"生成{max_count}个跨学科强相关概念。

【核心要求】
1. 必须生成完整的{max_count}个概念（少一个都不行）
2. 每个概念来自不同学科领域
3. 与"{parent_concept}"必须有**直接且深刻**的原理关联

【任务目标】发现跨学科的"强关联概念" - 与"{parent_concept}"在本质、原理或机制上高度相关的概念

【强相关性判定标准（必须满足）】
✅ 优先级1 - 本质相同（最强关联）：
- 数学公式/定义完全相同（如：热力学熵与信息熵都用H=-Σp·log(p)）
- 物理机制一致（如：扩散过程在气体、热传导、信息传播中的统一性）
- 核心原理直接对应（如：梯度下降与水往低处流都遵循能量最小化原理）

✅ 优先级2 - 直接应用/扩展：
- A是B的直接理论基础（如：贝叶斯定理是朴素贝叶斯分类器的基础）
- A是B在某领域的具体实现（如：卷积神经网络是卷积运算在图像识别中的应用）
- A和B共享核心算法（如：K-means聚类与向量量化）

✅ 优先级3 - 同源机制：
- 由同一底层规律衍生（如：随机游走、布朗运动、马尔可夫链都源于随机过程）
- 解决相同类型问题（如：主成分分析与奇异值分解都用于降维）

❌ 必须避免的弱关联：
- 仅概念上类比（如：社交网络与神经网络仅因"网络"二字相似）
- 远距离联想（如：蝴蝶效应与混沌理论虽相关但联系不够直接）
- 应用场景相关但原理无关（如：深度学习用于医疗但与医学原理无关）

【学科覆盖要求】
从以下领域寻找**强相关**概念（每领域最多选1-2个最相关的）：
1. 数学/统计学：数学公式、理论基础、统计原理
2. 物理学：物理定律、能量原理、守恒定律
3. 计算机科学：算法实现、数据结构、计算模型
4. 信息论/通信：信息度量、编码理论、传输原理
5. 生物学：生物机制、神经科学、演化论
6. 经济学/博弈论：均衡理论、优化决策、资源分配

【约束条件】
- 不包含已存在的概念：{existing_str}
- 每个概念必须来自不同学科（避免扎堆）
- 跨学科原理必须清晰说明**直接关联**的机制

【输出格式】（每行一个概念，不要序号）
概念名|学科|关系类型|跨学科原理

优质示例（强相关）：
信息熵|信息论|mathematical_identity|与热力学熵数学定义完全一致：H=-Σp·log(p)，都度量不确定性
最大似然估计|统计学|theoretical_foundation|熵最大化原理的统计推断实现，直接用于参数估计
吉布斯分布|统计物理|energy_based_model|用玻尔兹曼因子e^(-E/kT)描述热平衡，与最大熵分布等价
交叉熵损失|机器学习|direct_application|信息熵在分类任务中的直接应用，用于衡量预测分布与真实分布的差异

❌ 避免示例（弱相关）：
社会流动性|社会学|metaphorical|仅概念上类比社会变化的"无序度"（关联不够直接）
蝴蝶效应|混沌理论|distant_analogy|与熵增有间接关系但机制不直接（过于宽泛）

【最后强调】务必输出{max_count}个概念，每个概念必须与"{parent_concept}"有**清晰可验证**的直接关联。直接输出，不要解释和额外文字。"""

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {"role": "system", "content": f"你是跨学科知识挖掘专家。关键要求：必须严格生成{max_count}个概念，不能多也不能少。每个概念单独一行，格式：概念名|学科|关系类型|跨学科原理。不要任何解释、序号或额外内容。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2000,
                extra_body={"reasoning": {"enabled": False}}
            ),
            timeout=40.0
        )
        
        if response and response.choices:
            content = response.choices[0].message.content.strip()
            concepts = []
            
            for line in content.split('\n'):
                line = line.strip()
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        # 新格式：概念名|学科|关系类型|跨学科原理
                        # 去除概念名前的序号（如"1. 反向传播" -> "反向传播"）
                        concept_name = parts[0].strip()
                        # 移除开头的数字+点号模式
                        import re
                        concept_name = re.sub(r'^\d+\.\s*', '', concept_name)
                        
                        concepts.append({
                            "name": concept_name,
                            "discipline": parts[1].strip(),
                            "relation": parts[2].strip(),
                            "cross_principle": parts[3].strip()
                        })
                    elif len(parts) >= 3:
                        # 兼容旧格式：概念名|学科|关系类型
                        concept_name = parts[0].strip()
                        import re
                        concept_name = re.sub(r'^\d+\.\s*', '', concept_name)
                        
                        concepts.append({
                            "name": concept_name,
                            "discipline": parts[1].strip(),
                            "relation": parts[2].strip(),
                            "cross_principle": "学科交叉概念"
                        })
            
            if concepts:
                print(f"[SUCCESS] LLM生成了{len(concepts)}个相关概念")
                # 学术过滤已禁用，直接返回LLM生成的概念
                return concepts[:max_count]
    
    except asyncio.TimeoutError:
        print(f"[WARNING] LLM生成超时，使用预定义概念")
    except Exception as e:
        print(f"[WARNING] LLM生成失败: {str(e)}，使用预定义概念")
    
    return _get_fallback_concepts(parent_concept)


def _get_fallback_concepts(parent_concept: str) -> List[Dict[str, str]]:
    """预定义概念映射（作为回退方案）"""
    domain_mapping = {
        "机器学习": [
            {"name": "深度学习", "discipline": "计算机科学", "relation": "sub_field"},
            {"name": "神经网络", "discipline": "人工智能", "relation": "foundation"},
            {"name": "监督学习", "discipline": "方法论", "relation": "methodology"},
        ],
        "深度学习": [
            {"name": "卷积神经网络", "discipline": "计算机科学", "relation": "sub_field"},
            {"name": "反向传播", "discipline": "算法", "relation": "methodology"},
            {"name": "计算机视觉", "discipline": "应用领域", "relation": "application"},
        ],
    }
    
    if parent_concept in domain_mapping:
        return domain_mapping[parent_concept]
    
    # 通用回退
    return [
        {"name": f"{parent_concept}理论", "discipline": "理论基础", "relation": "theoretical_foundation"},
        {"name": f"{parent_concept}方法", "discipline": "方法论", "relation": "methodology"},
        {"name": f"{parent_concept}应用", "discipline": "应用领域", "relation": "application"},
    ]


# ==================== 语义相似度计算 ====================

async def compute_similarity(concept1: str, concept2: str) -> float:
    """
    计算两个概念的语义相似度（带智能重试和请求控制）
    
    Args:
        concept1: 概念1
        concept2: 概念2
        
    Returns:
        相似度分数 [0, 1]
    """
    global _last_embedding_time
    
    client = get_embedding_client()
    if not client:
        print("[WARNING] Embedding客户端未初始化，返回默认相似度")
        return 0.75
    
    # 请求速率控制：避免并发请求过多
    import time
    current_time = time.time()
    time_since_last = current_time - _last_embedding_time
    if time_since_last < _embedding_min_interval:
        wait_time = _embedding_min_interval - time_since_last
        await asyncio.sleep(wait_time)
    
    _last_embedding_time = time.time()
    
    # 智能重试：最多2次
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            # 获取embeddings
            response = await asyncio.wait_for(
                client.embeddings.create(
                    model="text-embedding-3-small",
                    input=[concept1, concept2]
                ),
                timeout=30.0  # 增加超时到30秒
            )
            
            emb1 = np.array(response.data[0].embedding)
            emb2 = np.array(response.data[1].embedding)
            
            # 计算余弦相似度
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            
            # 归一化到 [0, 1]
            normalized = (similarity + 1) / 2
            
            print(f"[SUCCESS] 相似度计算: {concept1} <-> {concept2} = {normalized:.3f}")
            return float(normalized)
        
        except asyncio.TimeoutError:
            if attempt < max_retries:
                print(f"[RETRY] 超时重试...（第{attempt + 1}次）")
                await asyncio.sleep(0.5)
            else:
                print(f"[FALLBACK] 使用默认相似度0.75（超时）")
                return 0.75
        except Exception as e:
            error_msg = str(e)
            # 详细的错误分类
            if "Connection error" in error_msg or "connection" in error_msg.lower():
                if attempt < max_retries:
                    print(f"[RETRY] 网络错误，重试...（第{attempt + 1}次）")
                    await asyncio.sleep(1.0)  # 网络错误等待更长时间
                else:
                    print(f"[FALLBACK] 使用默认相似度0.75（网络问题）")
                    return 0.75
            elif "rate_limit" in error_msg.lower() or "429" in error_msg:
                print(f"[FALLBACK] API速率限制，使用默认相似度0.75")
                await asyncio.sleep(2.0)  # 速率限制等待2秒
                return 0.75
            elif "invalid" in error_msg.lower() or "key" in error_msg.lower():
                print(f"[ERROR] API Key问题: {error_msg}")
                return 0.75
            else:
                if attempt < max_retries:
                    print(f"[RETRY] 未知错误，重试: {error_msg}（第{attempt + 1}次）")
                    await asyncio.sleep(0.5)
                else:
                    print(f"[FALLBACK] 使用默认相似度0.75（{error_msg}）")
                    return 0.75
    
    return 0.75


async def compute_similarities_batch(concepts: list[str], reference_concept: str) -> list[float]:
    """
    批量计算多个概念与参考概念的相似度（减少API调用）
    
    Args:
        concepts: 待计算的概念列表
        reference_concept: 参考概念
        
    Returns:
        相似度列表，与concepts顺序对应
    """
    if not concepts:
        return []
    
    # 如果只有少量概念，逐个计算
    if len(concepts) <= 3:
        results = []
        for concept in concepts:
            sim = await compute_similarity(concept, reference_concept)
            results.append(sim)
        return results
    
    # 批量计算：减少请求次数
    client = get_embedding_client()
    if not client:
        print("[WARNING] Embedding客户端未初始化，返回默认相似度")
        return [0.75] * len(concepts)
    
    try:
        # 一次性获取所有概念的embedding
        all_texts = [reference_concept] + concepts
        
        print(f"[INFO] 批量计算{len(concepts)}个概念的相似度（超时60秒）...")
        
        response = await asyncio.wait_for(
            client.embeddings.create(
                model="text-embedding-3-small",
                input=all_texts
            ),
            timeout=60.0  # 增加批量计算超时到60秒
        )
        
        # 参考概念的embedding
        ref_emb = np.array(response.data[0].embedding)
        
        # 计算所有相似度
        similarities = []
        for i in range(len(concepts)):
            concept_emb = np.array(response.data[i + 1].embedding)
            similarity = np.dot(ref_emb, concept_emb) / (np.linalg.norm(ref_emb) * np.linalg.norm(concept_emb))
            normalized = (similarity + 1) / 2
            similarities.append(float(normalized))
        
        print(f"[SUCCESS] 批量相似度计算完成: 平均相似度 = {np.mean(similarities):.3f}")
        return similarities
        
    except asyncio.TimeoutError:
        print(f"[WARNING] 批量相似度计算超时（60秒），回退到逐个计算")
        # 回退到逐个计算
        results = []
        for concept in concepts:
            sim = await compute_similarity(concept, reference_concept)
            results.append(sim)
        return results
    except Exception as e:
        print(f"[WARNING] 批量相似度计算失败: {type(e).__name__}: {str(e)}，回退到逐个计算")
        # 回退到逐个计算
        results = []
        for concept in concepts:
            sim = await compute_similarity(concept, reference_concept)
            results.append(sim)
        return results


async def compute_credibility(
    concept: str,
    parent_concept: str,
    has_wikipedia: bool = False,
    similarity: float = None  # 新增：直接传入已计算的相似度
) -> float:
    """
    计算节点可信度
    
    公式: base_credibility * (0.7 + 0.3 * similarity)
    
    Args:
        concept: 当前概念
        parent_concept: 父概念
        has_wikipedia: 是否有Wikipedia定义
        similarity: 已计算的相似度（可选，如果提供则不重新计算）
        
    Returns:
        可信度分数 [0, 1]
    """
    # 基础可信度
    base = 0.95 if has_wikipedia else 0.70
    
    # 使用已有相似度或重新计算
    if similarity is None:
        similarity = await compute_similarity(concept, parent_concept)
    
    # 动态可信度
    credibility = base * (0.7 + 0.3 * similarity)
    
    print(f"[INFO] 可信度: {concept} = {credibility:.3f} (base={base}, similarity={similarity:.3f})")
    
    return credibility


# ==================== 学术概念过滤 ====================

async def is_academic_concept(concept: str) -> bool:
    """
    判断是否为学术概念
    
    Args:
        concept: 概念名称
        
    Returns:
        True表示是学术概念，False表示非学术
    """
    client = get_llm_client()
    if not client:
        return True  # 默认允许
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {
                        "role": "system",
                        "content": "你是学术概念过滤器。判断输入是否为学术概念。只回答'是'或'否'。"
                    },
                    {
                        "role": "user",
                        "content": f"'{concept}' 是学术概念吗？"
                    }
                ],
                temperature=0.1,
                max_tokens=10,
                extra_body={"reasoning": {"enabled": True}}
            ),
            timeout=5.0
        )
        
        if response and response.choices:
            answer = response.choices[0].message.content.strip()
            is_academic = "是" in answer or "yes" in answer.lower()
            print(f"[INFO] 学术过滤: {concept} = {'学术概念' if is_academic else '非学术'}")
            return is_academic
    
    except Exception as e:
        print(f"[WARNING] 学术过滤失败: {str(e)}")
    
    return True  # 默认允许


# ==================== 测试函数 ====================

async def test_real_generator():
    """测试真实生成器"""
    print("=" * 60)
    print("测试真实节点生成器")
    print("=" * 60)
    
    # 1. 测试LLM生成概念
    print("\n[1] 测试LLM生成相关概念...")
    concepts = await generate_related_concepts("机器学习", [], max_count=3)
    for c in concepts:
        print(f"   - {c['name']} ({c['discipline']}) - {c['relation']}")
    
    # 2. 测试相似度计算
    print("\n[2] 测试相似度计算...")
    sim1 = await compute_similarity("机器学习", "深度学习")
    sim2 = await compute_similarity("机器学习", "笨蛋")
    print(f"   机器学习 <-> 深度学习: {sim1:.3f}")
    print(f"   机器学习 <-> 笨蛋: {sim2:.3f}")
    
    # 3. 测试可信度计算
    print("\n[3] 测试可信度计算...")
    cred1 = await compute_credibility("深度学习", "机器学习", has_wikipedia=True)
    cred2 = await compute_credibility("未知概念", "机器学习", has_wikipedia=False)
    print(f"   深度学习 (有Wiki): {cred1:.3f}")
    print(f"   未知概念 (无Wiki): {cred2:.3f}")
    
    # 4. 测试学术过滤
    print("\n[4] 测试学术概念过滤...")
    is_ac1 = await is_academic_concept("熵")
    is_ac2 = await is_academic_concept("笨蛋")
    print(f"   熵: {'学术' if is_ac1 else '非学术'}")
    print(f"   笨蛋: {'学术' if is_ac2 else '非学术'}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_real_generator())
