"""
学科领域分类器
使用LLM和规则匹配对概念进行学科分类
"""

import os
import logging
import re
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI
from shared.constants import Discipline

logger = logging.getLogger(__name__)


class DisciplineClassifier:
    """学科领域分类器"""
    
    # 学科关键词词典（用于规则匹配）
    DISCIPLINE_KEYWORDS = {
        Discipline.MATH: [
            "数学", "代数", "几何", "微积分", "拓扑", "概率", "统计",
            "矩阵", "函数", "方程", "定理", "证明", "集合", "向量",
            "积分", "微分", "数论", "逻辑", "组合",
            "math", "algebra", "geometry", "calculus", "theorem", "mathematical"
        ],
        Discipline.PHYSICS: [
            "物理", "力学", "热力学", "电磁", "量子", "相对论", "波",
            "能量", "粒子", "场", "牛顿", "爱因斯坦", "薛定谔", "熵",
            "温度", "压力", "热", "动力学", "静力学", "光学",
            "physics", "mechanics", "quantum", "relativity", "energy", "entropy", "thermodynamics"
        ],
        Discipline.CHEMISTRY: [
            "化学", "分子", "原子", "化合物", "反应", "催化", "合成",
            "有机", "无机", "元素", "离子", "键", "酸碱", "氧化",
            "化学键", "电子", "周期表",
            "chemistry", "molecule", "atom", "reaction", "compound", "chemical"
        ],
        Discipline.BIOLOGY: [
            "生物", "细胞", "基因", "进化", "生态", "神经", "免疫",
            "蛋白质", "DNA", "RNA", "酶", "代谢", "遗传", "物种",
            "生命", "有机体", "染色体",
            "biology", "cell", "gene", "evolution", "protein", "DNA", "biological"
        ],
        Discipline.COMPUTER: [
            "计算机", "算法", "数据结构", "编程", "网络", "数据库",
            "人工智能", "机器学习", "深度学习", "神经网络", "图灵",
            "信息", "信息论", "信息量", "比特", "编码", "香农",
            "computer", "algorithm", "programming", "AI", "neural", "information", "shannon"
        ],
        Discipline.SOCIOLOGY: [
            "社会", "经济", "政治", "文化", "心理", "哲学", "历史",
            "伦理", "法律", "教育", "人类", "行为", "制度", "组织",
            "sociology", "economy", "culture", "psychology", "philosophy"
        ]
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        use_llm: bool = True,
        confidence_threshold: float = 0.6
    ):
        """
        初始化学科分类器
        
        Args:
            api_key: OpenAI API密钥
            use_llm: 是否使用LLM进行分类（否则仅用规则）
            confidence_threshold: 置信度阈值
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.use_llm = use_llm and self.api_key is not None
        self.confidence_threshold = confidence_threshold
        
        if self.use_llm:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("LLM not available, using rule-based classification only")
        
        logger.info(f"DisciplineClassifier initialized (use_llm={use_llm})")
    
    def _rule_based_classify(
        self,
        concept: str,
        definition: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        基于规则的学科分类
        
        Args:
            concept: 概念名称
            definition: 概念定义（可选）
            
        Returns:
            [(学科, 置信度), ...] 列表
        """
        text = f"{concept} {definition or ''}".lower()
        
        scores = {}
        for discipline, keywords in self.DISCIPLINE_KEYWORDS.items():
            score = 0.0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in text:
                    # 概念名精确匹配给更高权重
                    if keyword.lower() == concept.lower():
                        score += 3.0
                    # 在概念名中出现给中等权重
                    elif keyword.lower() in concept.lower():
                        score += 2.0
                    # 在定义中出现给基础权重
                    else:
                        score += 1.0
                    matched_keywords.append(keyword)
            
            if score > 0:
                # 归一化：使用对数缩放避免过大
                import math
                confidence = min(1.0, math.log(score + 1) / math.log(len(keywords) + 1) * 1.5)
                scores[discipline] = confidence
        
        # 如果没有匹配，返回空列表
        if not scores:
            return []
        
        # 按置信度降序排序
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_scores
    
    async def _llm_classify(
        self,
        concept: str,
        definition: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        使用LLM进行学科分类
        
        Args:
            concept: 概念名称
            definition: 概念定义（可选）
            
        Returns:
            [(学科, 置信度), ...] 列表
        """
        if not self.client:
            return []
        
        prompt = f"""请判断以下概念主要属于哪些学科领域，可以选择多个。

概念：{concept}
{f'定义：{definition}' if definition else ''}

可选学科：
- 数学
- 物理
- 化学
- 生物
- 计算机
- 社会学

请按照以下JSON格式返回，包含所有相关学科及其相关度（0-1之间的浮点数）：
{{
  "classifications": [
    {{"discipline": "学科名", "confidence": 0.95}},
    {{"discipline": "学科名", "confidence": 0.7}}
  ],
  "reasoning": "简短解释为什么属于这些学科"
}}

只返回JSON，不要其他文字。"""
        
        try:
            response = await self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                messages=[
                    {"role": "system", "content": "你是一个学科分类专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 解析JSON
            import json
            result = json.loads(result_text)
            
            classifications = []
            for item in result.get("classifications", []):
                discipline = item.get("discipline")
                confidence = item.get("confidence", 0.5)
                
                # 映射到标准学科名称
                if discipline in Discipline.ALL:
                    classifications.append((discipline, float(confidence)))
            
            return classifications
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return []
    
    async def classify(
        self,
        concept: str,
        definition: Optional[str] = None,
        return_all: bool = False
    ) -> List[Tuple[str, float]]:
        """
        对概念进行学科分类
        
        Args:
            concept: 概念名称
            definition: 概念定义（可选）
            return_all: 是否返回所有学科（否则只返回置信度>阈值的）
            
        Returns:
            [(学科, 置信度), ...] 列表，按置信度降序排列
        """
        # 1. 规则分类
        rule_results = self._rule_based_classify(concept, definition)
        
        # 2. LLM分类（如果启用）
        if self.use_llm:
            llm_results = await self._llm_classify(concept, definition)
        else:
            llm_results = []
        
        # 3. 融合结果
        # 如果两种方法都有结果，取平均；否则使用有结果的那个
        combined = {}
        
        for discipline, confidence in rule_results:
            combined[discipline] = confidence
        
        for discipline, confidence in llm_results:
            if discipline in combined:
                # 加权平均：LLM权重更高
                combined[discipline] = combined[discipline] * 0.3 + confidence * 0.7
            else:
                combined[discipline] = confidence
        
        # 转换为列表并排序
        results = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        
        # 过滤置信度
        if not return_all:
            results = [(d, c) for d, c in results if c >= self.confidence_threshold]
        
        logger.info(f"Classified '{concept}': {results}")
        return results
    
    async def classify_batch(
        self,
        concepts: List[Dict[str, str]]
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        批量分类
        
        Args:
            concepts: [{"concept": str, "definition": str}, ...] 列表
            
        Returns:
            {概念: [(学科, 置信度), ...], ...}
        """
        results = {}
        
        for item in concepts:
            concept = item.get("concept")
            definition = item.get("definition")
            
            if not concept:
                continue
            
            classifications = await self.classify(concept, definition)
            results[concept] = classifications
        
        return results
    
    def get_primary_discipline(
        self,
        concept: str,
        definition: Optional[str] = None
    ) -> Optional[str]:
        """
        获取概念的主要学科（同步方法）
        
        Args:
            concept: 概念名称
            definition: 概念定义（可选）
            
        Returns:
            主要学科名称，如果无法分类则返回None
        """
        # 仅使用规则分类（同步）
        results = self._rule_based_classify(concept, definition)
        
        if not results:
            return None
        
        # 返回置信度最高的学科
        return results[0][0] if results[0][1] >= self.confidence_threshold else None
    
    async def is_cross_discipline(
        self,
        concept: str,
        definition: Optional[str] = None,
        min_disciplines: int = 2
    ) -> bool:
        """
        判断概念是否为跨学科概念
        
        Args:
            concept: 概念名称
            definition: 概念定义（可选）
            min_disciplines: 最少涉及的学科数量
            
        Returns:
            True如果是跨学科概念
        """
        classifications = await self.classify(concept, definition, return_all=True)
        
        # 对跨学科判断使用更低的阈值（0.3）
        cross_discipline_threshold = 0.3
        valid_disciplines = [d for d, c in classifications if c >= cross_discipline_threshold]
        
        return len(valid_disciplines) >= min_disciplines
    
    async def find_discipline_bridge(
        self,
        concept: str,
        definition: Optional[str] = None
    ) -> Dict[str, any]:
        """
        分析概念作为学科桥梁的潜力
        
        Args:
            concept: 概念名称
            definition: 概念定义（可选）
            
        Returns:
            {
                "is_bridge": bool,
                "disciplines": [(学科, 置信度), ...],
                "bridge_score": float,  # 桥梁指数
                "description": str
            }
        """
        classifications = await self.classify(concept, definition, return_all=True)
        
        # 过滤高置信度的学科
        high_conf_disciplines = [(d, c) for d, c in classifications if c >= self.confidence_threshold]
        
        # 计算桥梁指数
        # 因素1：涉及的学科数量
        num_disciplines = len(high_conf_disciplines)
        
        # 因素2：置信度分布的均匀性（方差越小越好）
        if num_disciplines >= 2:
            confidences = [c for _, c in high_conf_disciplines]
            avg_conf = sum(confidences) / len(confidences)
            variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)
            uniformity = 1 - variance  # 方差越小，均匀性越高
            
            bridge_score = (num_disciplines / len(Discipline.ALL)) * 0.6 + uniformity * 0.4
        else:
            bridge_score = 0.0
        
        is_bridge = num_disciplines >= 2 and bridge_score >= 0.4
        
        description = ""
        if is_bridge:
            disciplines_str = "、".join([d for d, _ in high_conf_disciplines])
            description = f"'{concept}'是连接{disciplines_str}等{num_disciplines}个学科的桥梁概念"
        else:
            description = f"'{concept}'主要属于单一学科"
        
        return {
            "is_bridge": is_bridge,
            "disciplines": high_conf_disciplines,
            "bridge_score": bridge_score,
            "description": description
        }
