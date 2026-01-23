"""
LSH (局部敏感哈希) 过滤器
使用 MinHash + LSH 快速过滤不相似的事实对，仅保留可能冲突的事实对进行 LLM 比对
"""
import re
import logging
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

# 先创建 logger
logger = logging.getLogger(__name__)

# 检查并导入 jieba
try:
    import jieba
    JIEBA_AVAILABLE = True
    # 初始化 jieba（首次导入时加载词典）
    try:
        jieba.initialize()
        logger.info("jieba 分词器初始化成功")
    except Exception as e:
        logger.warning(f"jieba 初始化失败: {e}")
        JIEBA_AVAILABLE = False
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba 未安装，将使用简化的分词")

# 检查并导入 datasketch
try:
    from datasketch import MinHash, MinHashLSH
    DATASKETCH_AVAILABLE = True
    logger.info("datasketch 已加载，将使用 MinHash LSH 加速过滤")
except ImportError:
    DATASKETCH_AVAILABLE = False
    logger.warning("datasketch 未安装，将使用简化的相似度过滤")

# 中文停用词表（精简版）
STOPWORDS = {
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '里', '来', '他', '她', '它', '们', '什么', '为', '与',
    '等', '或', '及', '之', '其', '而', '但', '如', '被', '将', '把', '从', '向',
    '对', '于', '以', '可', '能', '所', '这个', '那个', '这些', '那些', '因为',
    '所以', '如果', '虽然', '但是', '然而', '因此', '例如', '比如', '即', '且',
    '又', '还', '已', '已经', '正在', '可以', '应该', '必须', '需要', '进行',
    '通过', '根据', '按照', '关于', '对于', '以及', '并且', '或者', '而且',
}


class LSHFilter:
    """
    LSH 过滤器
    使用 MinHash 生成事实的哈希签名，通过 LSH 快速找到相似的事实对
    """
    
    def __init__(
        self,
        num_perm: int = 128,
        threshold: float = 0.3,
        num_shingles: int = 2
    ):
        """
        初始化 LSH 过滤器
        
        Args:
            num_perm: MinHash 排列数量（越大越精确，但越慢）
            threshold: LSH 相似度阈值（0-1，越低越宽松）
            num_shingles: n-gram 的 n 值
        """
        self.num_perm = num_perm
        self.threshold = threshold
        self.num_shingles = num_shingles
        
        if not DATASKETCH_AVAILABLE:
            logger.warning("datasketch 未安装，将使用简化的相似度过滤")
        if not JIEBA_AVAILABLE:
            logger.warning("jieba 未安装，将使用简化的分词")
    
    def filter_similar_pairs(
        self,
        facts: List[Dict[str, Any]],
        max_pairs: int = 50
    ) -> List[Tuple[Dict, Dict]]:
        """
        过滤出可能存在冲突的事实对
        
        Args:
            facts: 事实列表
            max_pairs: 最大返回对数
        
        Returns:
            可能冲突的事实对列表
        """
        if len(facts) < 2:
            return []
        
        # 如果 datasketch 可用，使用 MinHash LSH
        if DATASKETCH_AVAILABLE:
            return self._filter_with_minhash_lsh(facts, max_pairs)
        else:
            return self._filter_with_simple_similarity(facts, max_pairs)
    
    def _filter_with_minhash_lsh(
        self,
        facts: List[Dict[str, Any]],
        max_pairs: int
    ) -> List[Tuple[Dict, Dict]]:
        """使用 MinHash LSH 过滤"""
        # 创建 LSH 索引
        lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        
        # 为每个事实生成 MinHash
        minhashes = {}
        for i, fact in enumerate(facts):
            fact_id = f"fact_{i}"
            text = self._get_fact_text(fact)
            tokens = self._tokenize(text)
            
            if not tokens:
                continue
            
            # 生成 n-gram shingles
            shingles = self._get_shingles(tokens, self.num_shingles)
            
            if not shingles:
                continue
            
            # 创建 MinHash
            m = MinHash(num_perm=self.num_perm)
            for shingle in shingles:
                m.update(shingle.encode('utf-8'))
            
            minhashes[fact_id] = (m, fact, i)
            
            try:
                lsh.insert(fact_id, m)
            except ValueError:
                # 重复的 key，跳过
                pass
        
        # 查找相似对
        pairs = []
        seen_pairs = set()
        
        for fact_id, (m, fact, idx) in minhashes.items():
            # 查询相似的事实
            similar_ids = lsh.query(m)
            
            for sim_id in similar_ids:
                if sim_id == fact_id:
                    continue
                
                # 确保每对只添加一次
                pair_key = tuple(sorted([fact_id, sim_id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                
                # 获取对应的事实
                if sim_id in minhashes:
                    _, sim_fact, _ = minhashes[sim_id]
                    
                    # 优先添加同类型事实
                    fact_type = fact.get("type", "")
                    sim_type = sim_fact.get("type", "")
                    
                    # 计算优先级分数
                    priority = self._calculate_priority(fact, sim_fact)
                    pairs.append((priority, fact, sim_fact))
        
        # 按优先级排序，取前 max_pairs 对
        pairs.sort(key=lambda x: x[0], reverse=True)
        
        result = [(p[1], p[2]) for p in pairs[:max_pairs]]
        
        logger.info(f"LSH 过滤: {len(facts)} 条事实 -> {len(result)} 对候选冲突")
        
        return result
    
    def _filter_with_simple_similarity(
        self,
        facts: List[Dict[str, Any]],
        max_pairs: int
    ) -> List[Tuple[Dict, Dict]]:
        """简化的相似度过滤（不依赖 datasketch）"""
        pairs = []
        
        # 为每个事实生成特征词集合
        fact_tokens = []
        for fact in facts:
            text = self._get_fact_text(fact)
            tokens = set(self._tokenize(text))
            fact_tokens.append(tokens)
        
        # 计算所有对的 Jaccard 相似度
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                tokens_i = fact_tokens[i]
                tokens_j = fact_tokens[j]
                
                if not tokens_i or not tokens_j:
                    continue
                
                # 计算 Jaccard 相似度
                intersection = len(tokens_i & tokens_j)
                union = len(tokens_i | tokens_j)
                
                if union == 0:
                    continue
                
                similarity = intersection / union
                
                # 只保留相似度高于阈值的对
                if similarity >= self.threshold:
                    priority = self._calculate_priority(facts[i], facts[j])
                    pairs.append((priority + similarity, facts[i], facts[j]))
        
        # 按优先级排序
        pairs.sort(key=lambda x: x[0], reverse=True)
        
        result = [(p[1], p[2]) for p in pairs[:max_pairs]]
        
        logger.info(f"简单过滤: {len(facts)} 条事实 -> {len(result)} 对候选冲突")
        
        return result
    
    def _get_fact_text(self, fact: Dict[str, Any]) -> str:
        """获取事实的文本内容"""
        content = fact.get("content", "")
        original = fact.get("original_text", "")
        return f"{content} {original}"
    
    def _tokenize(self, text: str) -> List[str]:
        """分词并去停用词"""
        if not text:
            return []
        
        # 清理文本
        text = re.sub(r'[^\w\u4e00-\u9fff]', ' ', text)
        
        if JIEBA_AVAILABLE:
            # 使用 jieba 分词
            tokens = list(jieba.cut(text))
        else:
            # 简单的字符级分词（针对中文）
            tokens = []
            current_word = []
            for char in text:
                if '\u4e00' <= char <= '\u9fff':
                    # 中文字符
                    if current_word:
                        tokens.append(''.join(current_word))
                        current_word = []
                    tokens.append(char)
                elif char.isalnum():
                    current_word.append(char)
                else:
                    if current_word:
                        tokens.append(''.join(current_word))
                        current_word = []
            if current_word:
                tokens.append(''.join(current_word))
        
        # 去停用词和过短的词
        tokens = [
            t.lower().strip()
            for t in tokens
            if t.strip() and len(t.strip()) > 1 and t.strip() not in STOPWORDS
        ]
        
        return tokens
    
    def _get_shingles(self, tokens: List[str], n: int) -> Set[str]:
        """生成 n-gram shingles"""
        if len(tokens) < n:
            return set(tokens)
        
        shingles = set()
        for i in range(len(tokens) - n + 1):
            shingle = ' '.join(tokens[i:i + n])
            shingles.add(shingle)
        
        return shingles
    
    def _calculate_priority(self, fact_a: Dict, fact_b: Dict) -> float:
        """
        计算事实对的优先级分数
        同类型事实优先级更高
        """
        priority = 0.0
        
        type_a = fact_a.get("type", "")
        type_b = fact_b.get("type", "")
        
        # 同类型加分
        if type_a == type_b:
            priority += 2.0
        
        # 数据类型优先
        high_priority_types = {"数据", "日期", "结论"}
        if type_a in high_priority_types:
            priority += 1.0
        if type_b in high_priority_types:
            priority += 1.0
        
        # 高置信度事实优先
        conf_a = fact_a.get("confidence", 0.5)
        conf_b = fact_b.get("confidence", 0.5)
        priority += (conf_a + conf_b) / 2
        
        return priority


# 全局 LSH 过滤器实例
lsh_filter = LSHFilter()

