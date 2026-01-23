#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能2和功能3的核心生成器
"""

import os
import asyncio
import re
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 加载环境变量
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ==================== LLM客户端 ====================
_llm_client = None

def get_llm_client():
    """获取LLM客户端"""
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            _llm_client = AsyncOpenAI(
                api_key=api_key,
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            )
            print("[INFO] 多功能LLM客户端已初始化")
    return _llm_client


# ==================== 功能2：指定学科的概念挖掘 ====================

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
        max_count: 每个学科生成的概念数
        
    Returns:
        概念列表，每个概念包含：name, discipline, relation, cross_principle
    """
    
    client = get_llm_client()
    if not client:
        print("[WARNING] LLM客户端未初始化")
        return []
    
    # 构建学科列表字符串
    discipline_list = "\n".join([f"- {d}" for d in disciplines])
    
    # 填充prompt
    prompt = f"""你是跨学科知识挖掘专家。

任务：为概念"{parent_concept}"在指定学科中生成**完整的{max_count}个**相关概念。

**仅在以下学科中寻找**：
{discipline_list}

【关键要求】
1. 必须生成完整的{max_count}个概念（少一个都不行）
2. 所有概念必须从上述指定学科中选择，不得跨越到其他领域
3. 可以在同一学科中找多个不同层次的概念（如数学中：概率论、微积分、线性代数等都与神经网络相关）
4. 必须解释每个概念与"{parent_concept}"的直接关联

【生成策略】
- 如果只有1个学科：在该学科内找{max_count}个不同方面的相关概念
  * 基础理论概念
  * 核心方法/算法
  * 重要定理/原理
  * 实用工具/技术
  * 扩展应用

- 如果有多个学科：平均分配到各学科（每学科约{max_count // max(len(disciplines), 1)}个）

输出格式（每行一个概念，不要序号）：
概念名|学科|关系类型|学科视角下的关联原理

示例（输入"神经网络"，指定学科"数学"，需要5个概念）：
梯度下降|数学|优化算法|神经网络训练的核心优化方法
反向传播|数学|微分链式法则|计算损失函数对参数的梯度
矩阵乘法|数学|线性变换|神经网络前向传播的基本运算
激活函数|数学|非线性映射|引入非线性以拟合复杂函数
损失函数|数学|度量工具|衡量预测值与真实值的差距

【最后强调】务必输出{max_count}个概念，每行一个，直接输出，不要解释和额外文字。"""
    
    system_prompt = f"你是跨学科知识挖掘专家。关键要求：必须严格生成{max_count}个概念，不能多也不能少。每个概念单独一行，格式：概念名|学科|关系类型|关联原理。不要任何解释、序号或额外内容。"
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2000,  # 增加到2000以支持20个概念
                extra_body={"reasoning": {"enabled": False}}  # 关闭推理模式提高速度
            ),
            timeout=40.0  # 增加超时到40秒
        )
        
        # 解析输出
        if response and response.choices:
            content = response.choices[0].message.content.strip()
            concepts = []
            
            for line in content.split('\n'):
                line = line.strip()
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        # 去除序号
                        concept_name = re.sub(r'^\d+\.\s*', '', parts[0].strip())
                        concept_discipline = parts[1].strip()
                        
                        # 验证学科是否在指定列表中
                        if concept_discipline not in disciplines:
                            print(f"[FILTER] 学科不匹配，已过滤: {concept_name} ({concept_discipline})")
                            continue
                        
                        concepts.append({
                            "name": concept_name,
                            "discipline": concept_discipline,
                            "relation": parts[2].strip(),
                            "cross_principle": parts[3].strip()
                        })
            
            # 学术过滤已禁用
            if concepts:
                print(f"[SUCCESS] 功能2生成了{len(concepts)}个概念（限定学科：{', '.join(disciplines)}）")
                return concepts
            
            return concepts
    
    except asyncio.TimeoutError:
        print(f"[WARNING] 功能2生成超时")
    except Exception as e:
        print(f"[WARNING] 功能2生成失败: {str(e)}")
    
    return []


# ==================== 功能3：多概念桥梁发现 ====================

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
    
    client = get_llm_client()
    if not client:
        print("[WARNING] LLM客户端未初始化")
        return []
    
    # 构建概念列表字符串
    concept_list = "\n".join([f"- {c}" for c in concepts])
    
    # 填充prompt
    prompt = f"""你是跨学科概念连接专家，擅长发现看似无关概念之间的深层联系。

任务：分析以下多个概念之间的跨学科联系，找到连接它们的"桥梁概念"。

输入概念：
{concept_list}

【关键要求】
1. **必须生成至少{max_bridges}个桥梁概念**（不能少！）
2. 即使输入概念非常相关，也要从不同角度挖掘多个桥梁
3. 可以包括：理论基础、技术方法、数学工具、应用领域、发展历程等

【挖掘策略】
如果输入概念高度相关（如"神经网络"和"深度学习"），从以下角度寻找桥梁：
- **技术层面**：反向传播、梯度下降、激活函数、损失函数
- **架构层面**：卷积神经网络、循环神经网络、Transformer
- **数学基础**：线性代数、微积分、概率论、优化理论
- **应用领域**：计算机视觉、自然语言处理、强化学习
- **历史发展**：感知机、多层感知机、预训练模型

如果输入概念跨度较大，寻找：
- **共同原理**：优化、概率、信息论
- **共同方法**：统计推断、数值计算
- **哲学基础**：还原论、涌现性

桥梁概念的三个层次：
- **直接桥梁**：核心技术或理论基础
- **间接桥梁**：共同的应用工具或方法
- **原理性桥梁**：底层数学或哲学原理

输出格式（每行一个桥梁概念，不要序号）：
概念名|桥梁类型|关联的输入概念|连接原理

示例1（高度相关的概念：神经网络、深度学习）：
反向传播|直接桥梁|神经网络,深度学习|神经网络训练的核心算法，深度学习的基础技术
梯度下降|直接桥梁|神经网络,深度学习|两者共同的参数优化方法
激活函数|直接桥梁|神经网络,深度学习|引入非线性的关键组件
损失函数|直接桥梁|神经网络,深度学习|衡量模型性能的度量标准
卷积神经网络|间接桥梁|神经网络,深度学习|深度学习中特殊的神经网络架构
Transformer|间接桥梁|神经网络,深度学习|深度学习的新型神经网络架构
优化理论|原理性桥梁|神经网络,深度学习|两者都依赖参数优化算法
矩阵运算|原理性桥梁|神经网络,深度学习|底层数学计算的共同基础
特征学习|直接桥梁|神经网络,深度学习|自动提取特征的核心能力
预训练模型|间接桥梁|神经网络,深度学习|深度神经网络的迁移学习范式

示例2（跨度较大的概念：熵、最小二乘法）：
信息论|直接桥梁|熵,最小二乘法|熵度量信息不确定性，最小二乘基于信息损失最小化
统计推断|直接桥梁|熵,最小二乘法|最大熵原理和最小二乘估计都是统计推断方法
优化理论|原理性桥梁|熵,最小二乘法|熵最大化和误差最小化都是优化问题
概率分布|间接桥梁|熵,最小二乘法|熵描述分布不确定性，最小二乘假设正态分布
贝叶斯推理|直接桥梁|熵,最小二乘法|最大熵先验+最小二乘似然=后验估计

【最后强调】务必输出至少{max_bridges}个桥梁概念，直接输出，不要解释："""
    
    system_prompt = f"你是跨学科概念连接专家。关键要求：必须严格生成至少{max_bridges}个桥梁概念，不能少！每个概念单独一行，格式：概念名|桥梁类型|关联的输入概念|连接原理。不要任何解释、序号或额外内容。"
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # 提高temperature鼓励更多样化的输出
                max_tokens=2000,  # 增加token限制以容纳更多概念
                extra_body={"reasoning": {"enabled": True}}
            ),
            timeout=40.0  # 增加超时时间
        )
        
        # 解析输出
        if response and response.choices:
            content = response.choices[0].message.content.strip()
            print(f"[DEBUG] 功能3 LLM原始响应:\n{content}\n")
            bridges = []
            
            for line in content.split('\n'):
                line = line.strip()
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 4:
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
                        print(f"[DEBUG] 解析到桥梁概念: {bridge_name} ({bridge_type})")
            
            print(f"[DEBUG] 共解析出 {len(bridges)} 个桥梁概念")
            
            # 按桥梁类型排序：直接桥梁 > 间接桥梁 > 原理性桥梁
            priority = {"直接桥梁": 1, "间接桥梁": 2, "原理性桥梁": 3}
            bridges.sort(key=lambda x: priority.get(x["bridge_type"], 999))
            
            print(f"[SUCCESS] 功能3找到了{len(bridges)}个桥梁概念")
            return bridges[:max_bridges]
    
    except asyncio.TimeoutError:
        print(f"[WARNING] 功能3生成超时")
    except Exception as e:
        print(f"[WARNING] 功能3生成失败: {str(e)}")
    
    return []


# ==================== 测试代码 ====================

async def test_function_2():
    """测试功能2：指定学科挖掘"""
    print("\n" + "="*70)
    print("测试功能2：指定学科的概念挖掘")
    print("="*70)
    
    concepts = await generate_concepts_with_disciplines(
        parent_concept="神经网络",
        disciplines=["生物学", "数学"],
        max_count=10
    )
    
    print(f"\n生成结果（{len(concepts)}个）：")
    for concept in concepts:
        print(f"  - {concept['name']} ({concept['discipline']})")
        print(f"    关系: {concept['relation']}")
        print(f"    原理: {concept['cross_principle']}")


async def test_function_3():
    """测试功能3：多概念桥梁发现"""
    print("\n" + "="*70)
    print("测试功能3：多概念桥梁发现")
    print("="*70)
    
    bridges = await find_bridge_concepts(
        concepts=["熵", "最小二乘法"],
        max_bridges=10
    )
    
    print(f"\n桥梁概念（{len(bridges)}个）：")
    for bridge in bridges:
        print(f"  - {bridge['name']} ({bridge['bridge_type']})")
        print(f"    连接: {', '.join(bridge['connected_concepts'])}")
        print(f"    原理: {bridge['connection_principle']}")


if __name__ == "__main__":
    print(__doc__)
    
    # 测试功能2
    asyncio.run(test_function_2())
    
    # 测试功能3
    asyncio.run(test_function_3())
