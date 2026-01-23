"""
语义向量索引器
使用轻量语义模型将事实转为向量，通过向量相似度检索找到相似事实
支持分层检测：哈希去重 → 向量索引 → 精细比对
"""
import re
import hashlib
import logging
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# 尝试导入 sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("sentence-transformers 已加载")
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers 未安装，将使用 TF-IDF 向量化")

# 尝试导入 sklearn 用于 TF-IDF
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn 未安装，将使用简化的相似度计算")

# 尝试导入 jieba
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


@dataclass
class FactVector:
    """事实向量"""
    fact_id: str
    fact: Dict[str, Any]
    vector: np.ndarray
    content_hash: str


class SemanticIndexer:
    """
    语义向量索引器
    实现三层过滤：
    1. 哈希去重：完全相同的事实
    2. 向量相似度：语义相似的事实
    3. 返回候选对供 LLM 精细比对
    """
    
    # 轻量多语言模型（支持中文）
    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    
    def __init__(
        self,
        model_name: str = None,
        similarity_threshold: float = 0.5,
        use_gpu: bool = False
    ):
        """
        初始化语义索引器
        
        Args:
            model_name: sentence-transformers 模型名称
            similarity_threshold: 相似度阈值（0-1）
            use_gpu: 是否使用 GPU
        """
        self.similarity_threshold = similarity_threshold
        self.model = None
        self.tfidf_vectorizer = None
        self.use_sentence_transformers = False
        
        # 尝试加载 sentence-transformers 模型
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                model_name = model_name or self.DEFAULT_MODEL
                device = "cuda" if use_gpu else "cpu"
                self.model = SentenceTransformer(model_name, device=device)
                self.use_sentence_transformers = True
                logger.info(f"已加载语义模型: {model_name}")
            except Exception as e:
                logger.warning(f"加载语义模型失败: {e}，将使用 TF-IDF")
        
        # 如果没有 sentence-transformers，使用 TF-IDF
        if not self.use_sentence_transformers and SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                tokenizer=self._tokenize if JIEBA_AVAILABLE else None
            )
            logger.info("使用 TF-IDF 向量化")
    
    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        if JIEBA_AVAILABLE:
            return list(jieba.cut(text))
        return text.split()
    
    def _get_fact_text(self, fact: Dict[str, Any]) -> str:
        """获取事实的完整文本表示"""
        parts = []
        
        # 主要内容
        if fact.get("content"):
            parts.append(fact["content"])
        
        # 原文
        if fact.get("original_text"):
            parts.append(fact["original_text"])
        
        # 结构化字段
        if fact.get("subject"):
            parts.append(f"主体:{fact['subject']}")
        if fact.get("predicate"):
            parts.append(f"谓词:{fact['predicate']}")
        if fact.get("object"):
            parts.append(f"客体:{fact['object']}")
        if fact.get("value"):
            parts.append(f"数值:{fact['value']}")
        if fact.get("time"):
            parts.append(f"时间:{fact['time']}")
        
        return " ".join(parts)
    
    def _compute_hash(self, text: str) -> str:
        """计算文本哈希"""
        # 规范化文本
        normalized = re.sub(r'\s+', '', text.lower())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _compute_vectors(
        self,
        texts: List[str]
    ) -> np.ndarray:
        """计算文本向量"""
        if not texts:
            return np.array([])
        
        if self.use_sentence_transformers and self.model:
            # 使用 sentence-transformers
            vectors = self.model.encode(texts, show_progress_bar=False)
            return np.array(vectors)
        
        elif SKLEARN_AVAILABLE and self.tfidf_vectorizer:
            # 使用 TF-IDF
            try:
                vectors = self.tfidf_vectorizer.fit_transform(texts)
                return vectors.toarray()
            except Exception as e:
                logger.warning(f"TF-IDF 向量化失败: {e}")
        
        # 回退：使用简单的词袋向量
        return self._simple_vectorize(texts)
    
    def _simple_vectorize(self, texts: List[str]) -> np.ndarray:
        """简单的词袋向量化"""
        # 构建词表
        all_words = set()
        tokenized = []
        
        for text in texts:
            words = set(self._tokenize(text) if JIEBA_AVAILABLE else text.split())
            tokenized.append(words)
            all_words.update(words)
        
        # 转换为向量
        word_list = list(all_words)
        word_to_idx = {w: i for i, w in enumerate(word_list)}
        
        vectors = []
        for words in tokenized:
            vec = np.zeros(len(word_list))
            for w in words:
                if w in word_to_idx:
                    vec[word_to_idx[w]] = 1
            vectors.append(vec)
        
        return np.array(vectors)
    
    def _compute_similarity(
        self,
        vectors: np.ndarray
    ) -> np.ndarray:
        """计算相似度矩阵"""
        if len(vectors) == 0:
            return np.array([])
        
        if SKLEARN_AVAILABLE:
            return cosine_similarity(vectors)
        
        # 手动计算余弦相似度
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # 避免除零
        normalized = vectors / norms
        return np.dot(normalized, normalized.T)
    
    def find_similar_pairs(
        self,
        facts: List[Dict[str, Any]],
        max_pairs: int = 100
    ) -> List[Tuple[Dict, Dict, float]]:
        """
        查找相似的事实对（三层过滤）
        
        Args:
            facts: 事实列表
            max_pairs: 最大返回对数
        
        Returns:
            相似事实对列表，每对包含 (fact_a, fact_b, similarity_score)
        """
        if len(facts) < 2:
            return []
        
        logger.info(f"开始语义索引: {len(facts)} 条事实")
        
        # === 第一层：哈希去重 ===
        hash_groups: Dict[str, List[Tuple[int, Dict]]] = {}
        texts = []
        valid_indices = []
        
        for i, fact in enumerate(facts):
            text = self._get_fact_text(fact)
            content_hash = self._compute_hash(text)
            
            if content_hash not in hash_groups:
                hash_groups[content_hash] = []
            hash_groups[content_hash].append((i, fact))
            
            texts.append(text)
            valid_indices.append(i)
        
        # 完全重复的事实（哈希相同）
        duplicate_pairs = []
        for hash_val, group in hash_groups.items():
            if len(group) > 1:
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        duplicate_pairs.append((
                            group[i][1],
                            group[j][1],
                            1.0  # 完全相同
                        ))
        
        logger.info(f"哈希去重: 发现 {len(duplicate_pairs)} 对完全重复")
        
        # === 第二层：向量相似度 ===
        vectors = self._compute_vectors(texts)
        
        if len(vectors) == 0:
            return duplicate_pairs[:max_pairs]
        
        similarity_matrix = self._compute_similarity(vectors)
        
        # 找到高相似度的对
        semantic_pairs = []
        seen_pairs: Set[Tuple[str, str]] = set()
        
        # 添加已有的重复对到 seen_pairs
        for fa, fb, _ in duplicate_pairs:
            ida = str(fa.get("fact_id", id(fa)))
            idb = str(fb.get("fact_id", id(fb)))
            key = tuple(sorted([ida, idb]))
            seen_pairs.add(key)
        
        # 遍历相似度矩阵
        n = len(similarity_matrix)
        candidates = []
        
        for i in range(n):
            for j in range(i + 1, n):
                sim = similarity_matrix[i][j]
                
                if sim >= self.similarity_threshold:
                    fact_a = facts[valid_indices[i]]
                    fact_b = facts[valid_indices[j]]
                    
                    ida = str(fact_a.get("fact_id", id(fact_a)))
                    idb = str(fact_b.get("fact_id", id(fact_b)))
                    key = tuple(sorted([ida, idb]))
                    
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        
                        # 计算优先级分数
                        priority = self._calculate_priority(fact_a, fact_b, sim)
                        candidates.append((priority, fact_a, fact_b, sim))
        
        # 按优先级排序
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        for priority, fa, fb, sim in candidates:
            semantic_pairs.append((fa, fb, sim))
            if len(semantic_pairs) >= max_pairs - len(duplicate_pairs):
                break
        
        logger.info(f"语义相似: 发现 {len(semantic_pairs)} 对相似事实")
        
        # 合并结果
        all_pairs = duplicate_pairs + semantic_pairs
        
        return all_pairs[:max_pairs]
    
    def _calculate_priority(
        self,
        fact_a: Dict,
        fact_b: Dict,
        similarity: float
    ) -> float:
        """计算事实对的优先级"""
        priority = similarity * 2  # 基础分：相似度
        
        type_a = fact_a.get("type", "")
        type_b = fact_b.get("type", "")
        
        # 同类型加分
        if type_a == type_b:
            priority += 1.0
        
        # 高优先类型
        high_priority_types = {"数据", "日期", "结论", "百分比", "金额"}
        if type_a in high_priority_types:
            priority += 0.5
        if type_b in high_priority_types:
            priority += 0.5
        
        # 极性不同加分（更可能冲突）
        polarity_a = (fact_a.get("polarity") or "").lower()
        polarity_b = (fact_b.get("polarity") or "").lower()
        if polarity_a and polarity_b and polarity_a != polarity_b:
            priority += 1.5
        
        # 数值差异加分
        value_a = self._extract_number(fact_a.get("value"))
        value_b = self._extract_number(fact_b.get("value"))
        if value_a is not None and value_b is not None:
            if value_a != value_b:
                priority += 1.0
                # 差异越大，优先级越高
                if min(value_a, value_b) > 0:
                    diff_ratio = abs(value_a - value_b) / max(value_a, value_b)
                    priority += diff_ratio
        
        return priority
    
    def _extract_number(self, value: Any) -> Optional[float]:
        """从值中提取数字"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            nums = re.findall(r'(-?\d+(?:\.\d+)?)', value)
            if nums:
                try:
                    return float(nums[0])
                except:
                    return None
        return None
    
    def build_index(
        self,
        facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建事实索引（用于快速检索）
        
        Args:
            facts: 事实列表
        
        Returns:
            索引对象，包含向量和元数据
        """
        texts = [self._get_fact_text(f) for f in facts]
        vectors = self._compute_vectors(texts)
        
        # 构建哈希索引
        hash_index = {}
        for i, text in enumerate(texts):
            h = self._compute_hash(text)
            if h not in hash_index:
                hash_index[h] = []
            hash_index[h].append(i)
        
        return {
            "facts": facts,
            "vectors": vectors,
            "hash_index": hash_index,
            "fact_count": len(facts)
        }
    
    def query_similar(
        self,
        query_fact: Dict[str, Any],
        index: Dict[str, Any],
        top_k: int = 10
    ) -> List[Tuple[Dict, float]]:
        """
        查询与给定事实相似的事实
        
        Args:
            query_fact: 查询事实
            index: 事实索引
            top_k: 返回前 k 个结果
        
        Returns:
            相似事实列表，每项包含 (fact, similarity)
        """
        query_text = self._get_fact_text(query_fact)
        query_vector = self._compute_vectors([query_text])
        
        if len(query_vector) == 0:
            return []
        
        # 计算相似度
        facts = index["facts"]
        vectors = index["vectors"]
        
        if len(vectors) == 0:
            return []
        
        similarities = self._compute_similarity(
            np.vstack([query_vector, vectors])
        )[0][1:]  # 第一行与其他行的相似度
        
        # 排序并返回 top_k
        indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in indices:
            if similarities[idx] >= self.similarity_threshold:
                results.append((facts[idx], float(similarities[idx])))
        
        return results


class HybridFilter:
    """
    混合过滤器
    结合 LSH（快速预过滤）和语义向量（精确匹配）
    """
    
    def __init__(
        self,
        semantic_threshold: float = 0.5,
        lsh_threshold: float = 0.3
    ):
        self.semantic_indexer = SemanticIndexer(
            similarity_threshold=semantic_threshold
        )
        self.lsh_threshold = lsh_threshold
        
        # 尝试导入 LSH 过滤器
        try:
            from .lsh_filter import lsh_filter
            self.lsh_filter = lsh_filter
            self.lsh_available = True
        except ImportError:
            self.lsh_filter = None
            self.lsh_available = False
    
    def filter_candidate_pairs(
        self,
        facts: List[Dict[str, Any]],
        max_pairs: int = 100,
        use_lsh_prefilter: bool = True
    ) -> List[Tuple[Dict, Dict, float]]:
        """
        综合过滤获取候选对
        
        流程：
        1. LSH 快速预过滤（如果可用）
        2. 语义向量精确匹配
        3. 合并去重
        
        Args:
            facts: 事实列表
            max_pairs: 最大返回对数
            use_lsh_prefilter: 是否使用 LSH 预过滤
        
        Returns:
            候选事实对列表
        """
        if len(facts) < 2:
            return []
        
        all_pairs = []
        seen_keys: Set[Tuple[str, str]] = set()
        
        # LSH 预过滤
        if use_lsh_prefilter and self.lsh_available and self.lsh_filter:
            lsh_pairs = self.lsh_filter.filter_similar_pairs(facts, max_pairs=max_pairs)
            
            for fa, fb in lsh_pairs:
                ida = str(fa.get("fact_id", id(fa)))
                idb = str(fb.get("fact_id", id(fb)))
                key = tuple(sorted([ida, idb]))
                
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_pairs.append((fa, fb, 0.5))  # LSH 不提供精确分数
        
        # 语义向量匹配
        semantic_pairs = self.semantic_indexer.find_similar_pairs(
            facts, max_pairs=max_pairs
        )
        
        for fa, fb, sim in semantic_pairs:
            ida = str(fa.get("fact_id", id(fa)))
            idb = str(fb.get("fact_id", id(fb)))
            key = tuple(sorted([ida, idb]))
            
            if key not in seen_keys:
                seen_keys.add(key)
                all_pairs.append((fa, fb, sim))
            else:
                # 更新已有对的相似度分数
                for i, (a, b, s) in enumerate(all_pairs):
                    a_id = str(a.get("fact_id", id(a)))
                    b_id = str(b.get("fact_id", id(b)))
                    if tuple(sorted([a_id, b_id])) == key:
                        all_pairs[i] = (a, b, max(s, sim))
                        break
        
        # 按相似度排序
        all_pairs.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"混合过滤: {len(facts)} 条事实 -> {len(all_pairs)} 对候选")
        
        return all_pairs[:max_pairs]


# 全局实例
semantic_indexer = SemanticIndexer()
hybrid_filter = HybridFilter()




