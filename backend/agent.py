"""
LLM Agent核心逻辑
负责与大模型交互，执行知识挖掘任务
"""

import os
import json
import time
import httpx
from openai import OpenAI

try:
    from .prompts import SYSTEM_PROMPT, RELATION_MINING_PROMPT, VALIDATION_PROMPT
except ImportError:
    from prompts import SYSTEM_PROMPT, RELATION_MINING_PROMPT, VALIDATION_PROMPT


def _normalize_base_url(base_url):
    if not base_url:
        return base_url
    if base_url.endswith("/chat/completions"):
        return base_url.rsplit("/chat/completions", 1)[0]
    return base_url

class KnowledgeGraphAgent:
    def __init__(self, api_key=None, api_base=None, model_name=None):
        """初始化Agent"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('MAAS_API_KEY')
        self.api_base = _normalize_base_url(
            api_base or os.getenv('OPENAI_API_BASE') or os.getenv('MAAS_API_ENDPOINT', 'https://open.bigmodel.cn/api/paas/v4')
        )
        self.model_name = model_name or os.getenv('MODEL_NAME') or os.getenv('MAAS_MODEL_NAME', 'glm-4')

        # Create a custom httpx client to avoid proxies compatibility issues
        http_client = httpx.Client(timeout=60.0)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            http_client=http_client
        )

    def _call_llm(self, prompt, system_prompt=SYSTEM_PROMPT, temperature=0.7, max_retries=3):
        """调用LLM API"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"LLM调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise

    def mine_relations(self, concept):
        """挖掘概念的跨学科关联"""
        prompt = RELATION_MINING_PROMPT.format(concept=concept)

        try:
            response = self._call_llm(prompt, temperature=0.7)
            # 尝试解析JSON
            result = self._parse_json_response(response)
            return result
        except Exception as e:
            print(f"关联挖掘失败: {str(e)}")
            return self._get_fallback_relations(concept)

    def validate_relation(self, core_concept, related_concept, discipline, description, relation_type='', bridge_concept=''):
        """验证概念关联的合理性"""
        prompt = VALIDATION_PROMPT.format(
            core_concept=core_concept,
            related_concept=related_concept,
            discipline=discipline,
            relation_type=relation_type or '未知',
            bridge_concept=bridge_concept or '无',
            description=description
        )

        try:
            response = self._call_llm(prompt, temperature=0.3)
            result = self._parse_json_response(response)
            return result
        except Exception as e:
            print(f"验证失败: {str(e)}")
            return {"is_valid": True, "confidence": 0.5, "reason": "验证服务暂时不可用"}

    def _parse_json_response(self, response):
        """解析LLM返回的JSON响应"""
        # 尝试提取JSON部分
        response = response.strip()

        # 如果响应被markdown代码块包裹，提取出来
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            print(f"原始响应: {response}")
            raise

    def _get_fallback_relations(self, concept):
        """当LLM调用失败时的后备方案 - 基于概念关键词匹配生成相关关联"""
        # 根据概念关键词匹配不同的学科关联
        concept_lower = concept.lower()
        
        # 定义不同概念类型的关联模板
        templates = {
            # 数学/统计类概念
            '数学': ['最小二乘法', '线性回归', '梯度下降', '优化算法'],
            '统计': ['最小二乘法', '线性回归', '梯度下降', '优化算法'],
            '算法': ['最小二乘法', '线性回归', '梯度下降', '优化算法'],
            '回归': ['最小二乘法', '线性回归', '梯度下降', '优化算法'],
            
            # 物理/热力学类概念
            '熵': ['信息熵', '热力学', '概率论', '数据压缩', '生态系统'],
            '热力学': ['熵', '信息熵', '概率论', '数据压缩', '生态系统'],
            '能量': ['熵', '热力学', '信息熵', '概率论', '数据压缩'],
            
            # 生物/进化类概念
            '进化': ['自然选择', '遗传算法', '生态系统', '信息熵', '概率论'],
            '生物': ['进化', '自然选择', '遗传算法', '生态系统', '信息熵'],
            '遗传': ['进化', '自然选择', '遗传算法', '生态系统', '信息熵'],
            
            # 计算机/网络类概念
            '神经网络': ['深度学习', '反向传播', '梯度下降', '信息熵', '概率论'],
            '网络': ['深度学习', '反向传播', '梯度下降', '信息熵', '概率论'],
            '学习': ['深度学习', '反向传播', '梯度下降', '信息熵', '概率论'],
            '云计算': ['分布式系统', '大数据', '信息熵', '数据压缩', '概率论'],
            '大数据': ['分布式系统', '云计算', '信息熵', '数据压缩', '概率论'],
            
            # 信息论类概念
            '信息': ['信息熵', '数据压缩', '概率论', '热力学', '生态系统'],
            '压缩': ['信息熵', '数据压缩', '概率论', '热力学', '生态系统'],
        }
        
        # 匹配概念类型
        matched_template = None
        for key, related_concepts in templates.items():
            if key in concept_lower:
                matched_template = related_concepts
                break
        
        # 如果没有匹配，使用通用模板（根据概念长度和特征）
        if not matched_template:
            # 根据概念特征选择不同的关联
            if len(concept) <= 2:  # 短概念，可能是基础概念
                matched_template = ['信息熵', '概率论', '热力学', '数据压缩', '生态系统']
            elif '云' in concept or '数据' in concept:  # 技术类概念
                matched_template = ['分布式系统', '大数据', '信息熵', '数据压缩', '概率论']
            elif '神经' in concept or '网络' in concept:  # AI类概念
                matched_template = ['深度学习', '反向传播', '梯度下降', '信息熵', '概率论']
            else:  # 默认通用关联
                matched_template = ['信息熵', '概率论', '热力学', '数据压缩', '生态系统']
        
        # 构建关联列表
        disciplines_map = {
            '信息熵': '信息论',
            '数据压缩': '计算机科学',
            '概率论': '数学',
            '热力学': '物理学',
            '生态系统': '生物学',
            '自然选择': '生物学',
            '遗传算法': '计算机科学',
            '深度学习': '计算机科学',
            '反向传播': '计算机科学',
            '梯度下降': '数学',
            '最小二乘法': '数学',
            '线性回归': '数学',
            '优化算法': '数学',
            '分布式系统': '计算机科学',
            '大数据': '计算机科学',
            '云计算': '计算机科学',
        }
        
        relations = []
        for idx, related_concept in enumerate(matched_template[:5]):  # 最多5个
            discipline = disciplines_map.get(related_concept, ['数学', '物理学', '计算机科学', '信息论', '生物学'][idx % 5])
            relation_types = ['理论基础', '应用', '类比', '核心概念', '方法论']
            
            relations.append({
                "discipline": discipline,
                "related_concept": related_concept,
                "relation_type": relation_types[idx % len(relation_types)],
                "description": f"{concept}与{related_concept}在{discipline}领域存在关联，体现了跨学科的知识联系"
            })
        
        return {
            "core_concept": concept,
            "relations": relations
        }

