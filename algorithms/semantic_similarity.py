"""
语义相似度计算模块 - 基于OpenAI Embeddings
使用OpenAI的text-embedding-3-small模型计算向量嵌入
这是最优方案：快速、便宜、精确
"""

import os
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class SemanticSimilarity:
    """基于OpenAI Embeddings的语义相似度计算器"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimension: int = 1536
    ):
        """
        初始化语义相似度计算器
        
        Args:
            api_key: OpenAI API密钥
            model: 嵌入模型名称
            dimension: 向量维度
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.dimension = dimension
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required! "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self._embedding_cache: Dict[str, np.ndarray] = {}
        
        logger.info(f"SemanticSimilarity initialized with {model}")
    
    async def get_embedding(self, text: str) -> np.ndarray:
        """获取文本的向量嵌入"""
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            embedding = np.array(response.data[0].embedding)
            self._embedding_cache[text] = embedding
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding for '{text}': {e}")
            raise
    
    async def compute_similarity(
        self,
        text1: str,
        text2: str,
        metric: str = "cosine"
    ) -> float:
        """
        计算两个文本的语义相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            metric: 相似度度量（cosine/euclidean/dot）
            
        Returns:
            相似度分数 [0.0-1.0]
        """
        try:
            emb1 = await self.get_embedding(text1)
            emb2 = await self.get_embedding(text2)
            
            if metric == "cosine":
                # 余弦相似度
                similarity = np.dot(emb1, emb2) / (
                    np.linalg.norm(emb1) * np.linalg.norm(emb2)
                )
                # 归一化到[0,1]
                similarity = (similarity + 1) / 2
                
            elif metric == "euclidean":
                # 欧氏距离转相似度
                distance = np.linalg.norm(emb1 - emb2)
                similarity = 1 / (1 + distance)
                
            elif metric == "dot":
                # 点积相似度
                similarity = np.dot(emb1, emb2)
                similarity = max(0.0, min(1.0, similarity))
            else:
                raise ValueError(f"Unknown metric: {metric}")
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            return 0.0
    
    async def find_most_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """在候选列表中找出最相似的k个"""
        query_emb = await self.get_embedding(query)
        similarities = []
        
        for candidate in candidates:
            cand_emb = await self.get_embedding(candidate)
            sim = np.dot(query_emb, cand_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(cand_emb)
            )
            sim = (sim + 1) / 2  # 归一化
            similarities.append((candidate, float(sim)))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    async def compute_concept_distance(
        self,
        concept_a: str,
        concept_b: str,
        discipline_a: str,
        discipline_b: str
    ) -> Dict[str, float]:
        """计算跨学科概念距离"""
        semantic_sim = await self.compute_similarity(concept_a, concept_b)
        discipline_sim = await self.compute_similarity(discipline_a, discipline_b)
        
        # 跨学科奖励
        discipline_diff = 1 - discipline_sim
        cross_discipline_boost = 1 + (discipline_diff * 0.3)
        
        # 综合评分
        if discipline_sim > 0.8:
            final_score = semantic_sim
        else:
            if semantic_sim > 0.5:
                final_score = semantic_sim * cross_discipline_boost
            else:
                final_score = semantic_sim * 0.8
        
        final_score = max(0.0, min(1.0, final_score))
        
        return {
            "semantic_similarity": semantic_sim,
            "discipline_similarity": discipline_sim,
            "cross_discipline_boost": cross_discipline_boost,
            "final_score": final_score
        }
    
    async def find_distant_relatives(
        self,
        core_concept: str,
        core_discipline: str,
        candidates: List[Tuple[str, str]],
        top_k: int = 5,
        similarity_threshold: float = 0.5,
        diversity_threshold: float = 0.3
    ) -> List[Tuple[str, str, float]]:
        """
        发现"远亲概念"：语义相关但学科不同的概念
        
        这是跨学科概念搜索的核心算法
        """
        distant_relatives = []
        
        for candidate_concept, candidate_discipline in candidates:
            # 跳过同学科
            discipline_sim = await self.compute_similarity(
                core_discipline,
                candidate_discipline
            )
            
            if discipline_sim > (1 - diversity_threshold):
                continue
            
            # 计算跨学科距离
            distance_info = await self.compute_concept_distance(
                core_concept,
                candidate_concept,
                core_discipline,
                candidate_discipline
            )
            
            # 过滤低相似度
            if distance_info["semantic_similarity"] < similarity_threshold:
                continue
            
            distant_relatives.append((
                candidate_concept,
                candidate_discipline,
                distance_info["final_score"]
            ))
        
        distant_relatives.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(
            f"Found {len(distant_relatives)} distant relatives for "
            f"'{core_concept}' ({core_discipline})"
        )
        
        return distant_relatives[:top_k]
    
    def clear_cache(self):
        """清空缓存"""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._embedding_cache)


# Alias for compatibility
SemanticSimilarityCalculator = SemanticSimilarity
