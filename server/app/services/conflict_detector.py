"""
PatPat-Inconsistency-Hunter 冲突检测模块
负责检测文档中事实之间的不一致性
优化版本 - 支持图片事实、语义相似度和更完备的检测逻辑
"""

import asyncio
import uuid
import re
from typing import List, Optional, Dict, Any, Tuple, Set
from itertools import combinations
from collections import defaultdict

from ..config import settings
from ..models.schemas import (
    FactWithSource,
    ConflictPair,
    ConflictType,
    ConflictDetectionResponse,
)
from ..utils.logger import logger
from .llm_client import DeepSeekClient, get_llm_client
from .prompts import (
    CONFLICT_DETECTION_SYSTEM_PROMPT,
    CONFLICT_DETECTION_USER_PROMPT,
    BATCH_CONFLICT_DETECTION_SYSTEM_PROMPT,
    BATCH_CONFLICT_DETECTION_USER_PROMPT,
)


class ConflictDetector:
    """
    冲突检测器
    
    负责检测文档中事实之间的冲突和不一致性
    """
    
    def __init__(
        self,
        llm_client: Optional[DeepSeekClient] = None,
        max_concurrency: int = 5,
        similarity_threshold: float = 0.3,
    ):
        """
        初始化冲突检测器
        
        Args:
            llm_client: LLM客户端实例
            max_concurrency: 最大并发数
            similarity_threshold: 相似度阈值，用于预过滤可能相关的事实对
        """
        self._client = llm_client or get_llm_client()
        self._max_concurrency = max_concurrency
        self._similarity_threshold = similarity_threshold
    
    async def detect_conflicts(
        self,
        facts: List[FactWithSource],
        progress_callback: Optional[callable] = None,
    ) -> List[ConflictPair]:
        """
        检测事实列表中的所有冲突
        
        Args:
            facts: 事实列表
            progress_callback: 进度回调函数
        
        Returns:
            冲突对列表
        """
        if len(facts) < 2:
            logger.info("事实数量少于2，无需检测冲突")
            return []
        
        logger.info(f"开始检测 {len(facts)} 个事实之间的冲突...")
        
        # 第一步：预过滤可能相关的事实对
        candidate_pairs = self._get_candidate_pairs(facts)
        logger.info(f"预过滤后得到 {len(candidate_pairs)} 对候选事实对")
        
        if not candidate_pairs:
            logger.info("没有找到可能相关的事实对")
            return []
        
        # 第二步：使用LLM检测冲突
        conflicts = await self._detect_conflicts_in_pairs(
            candidate_pairs,
            progress_callback,
        )
        
        # 第三步：去重和合并
        conflicts = self._merge_conflicts(conflicts)
        
        logger.info(f"冲突检测完成，发现 {len(conflicts)} 个冲突")
        return conflicts
    
    def _get_candidate_pairs(
        self,
        facts: List[FactWithSource],
    ) -> List[Tuple[FactWithSource, FactWithSource]]:
        """
        获取可能相关的事实对（增强版预过滤）
        
        使用多种策略减少需要检测的事实对数量：
        1. 同类型事实配对（基础类型匹配）
        2. 实体重叠检测（共享关键实体）
        3. 数值相似性检测（数值接近但可能不同）
        4. 图片与文本交叉检测
        5. 章节交叉检测
        
        Args:
            facts: 事实列表
        
        Returns:
            候选事实对列表
        """
        candidate_pairs = []
        seen: Set[Tuple[str, str]] = set()
        
        def add_pair(fact_a: FactWithSource, fact_b: FactWithSource):
            """添加候选对（自动去重）"""
            pair_key = tuple(sorted([fact_a.fact_id, fact_b.fact_id]))
            if pair_key not in seen:
                seen.add(pair_key)
                candidate_pairs.append((fact_a, fact_b))
        
        # 策略1: 按基础类型分组（去除image_前缀）
        type_groups: Dict[str, List[FactWithSource]] = defaultdict(list)
        for fact in facts:
            base_type = fact.fact_type.replace("image_", "")
            type_groups[base_type].append(fact)
        
        # 同类型事实之间的组合
        for fact_type, type_facts in type_groups.items():
            if len(type_facts) >= 2:
                for pair in combinations(type_facts, 2):
                    add_pair(pair[0], pair[1])
        
        # 策略2: 提取实体并构建索引
        entity_to_facts: Dict[str, List[FactWithSource]] = defaultdict(list)
        fact_entities: Dict[str, Set[str]] = {}
        
        for fact in facts:
            entities = self._extract_entities_advanced(fact.content)
            fact_entities[fact.fact_id] = entities
            for entity in entities:
                entity_to_facts[entity].append(fact)
        
        # 共享实体的事实配对
        for entity, entity_facts in entity_to_facts.items():
            if len(entity_facts) >= 2:
                for pair in combinations(entity_facts, 2):
                    add_pair(pair[0], pair[1])
        
        # 策略3: 图片事实与文本事实交叉检测
        image_facts = [f for f in facts if f.fact_type.startswith("image_")]
        text_facts = [f for f in facts if not f.fact_type.startswith("image_")]
        
        for img_fact in image_facts:
            img_entities = fact_entities.get(img_fact.fact_id, set())
            for txt_fact in text_facts:
                txt_entities = fact_entities.get(txt_fact.fact_id, set())
                # 检查实体重叠
                if len(img_entities & txt_entities) >= 1:
                    add_pair(img_fact, txt_fact)
                # 检查数值相似性
                elif self._has_similar_numbers(img_fact.content, txt_fact.content):
                    add_pair(img_fact, txt_fact)
        
        # 策略4: 跨章节的事实检测（同一主题在不同章节可能有冲突）
        chapter_facts: Dict[str, List[FactWithSource]] = defaultdict(list)
        for fact in facts:
            chapter = fact.chapter or "unknown"
            chapter_facts[chapter].append(fact)
        
        chapters = list(chapter_facts.keys())
        if len(chapters) >= 2:
            for i, chapter_a in enumerate(chapters):
                for chapter_b in chapters[i+1:]:
                    for fact_a in chapter_facts[chapter_a]:
                        for fact_b in chapter_facts[chapter_b]:
                            # 只检查有实体重叠的
                            entities_a = fact_entities.get(fact_a.fact_id, set())
                            entities_b = fact_entities.get(fact_b.fact_id, set())
                            if len(entities_a & entities_b) >= 1:
                                add_pair(fact_a, fact_b)
        
        # 策略5: 高优先级类型的交叉检测
        high_priority_types = {"numerical", "temporal", "entity"}
        high_priority_facts = [
            f for f in facts 
            if f.fact_type.replace("image_", "") in high_priority_types
        ]
        
        for i, fact_a in enumerate(high_priority_facts):
            for fact_b in high_priority_facts[i+1:]:
                if self._are_potentially_related(fact_a, fact_b):
                    add_pair(fact_a, fact_b)
        
        logger.info(f"候选对生成: {len(facts)} 个事实 -> {len(candidate_pairs)} 个候选对")
        return candidate_pairs
    
    def _extract_entities_advanced(self, text: str) -> Set[str]:
        """
        高级实体提取
        
        提取文本中的关键实体：数字、日期、名称等
        """
        entities = set()
        
        # 数字（包括带单位的）
        numbers = re.findall(r'\d+(?:\.\d+)?(?:\s*[%万亿元年月日号人个项])?', text)
        entities.update(n.strip() for n in numbers)
        
        # 日期格式
        dates = re.findall(r'\d{4}[年/-]\d{1,2}[月/-]?\d{0,2}[日号]?', text)
        entities.update(dates)
        
        # 中文名称（2-4字，常见姓名长度）
        names = re.findall(r'[\u4e00-\u9fa5]{2,4}(?:公司|集团|项目|系统|负责人|经理|总监)?', text)
        entities.update(names)
        
        # 英文缩写和专有名词
        english = re.findall(r'\b[A-Z][a-zA-Z]{1,}(?:\s+[A-Z][a-zA-Z]+)*\b', text)
        entities.update(e.lower() for e in english)
        
        # 百分比
        percentages = re.findall(r'\d+(?:\.\d+)?%', text)
        entities.update(percentages)
        
        return entities
    
    def _has_similar_numbers(self, text_a: str, text_b: str) -> bool:
        """
        检查两段文本是否包含相似但可能不同的数字
        
        用于发现潜在的数值冲突
        """
        # 提取所有数字
        numbers_a = set(re.findall(r'\d+(?:\.\d+)?', text_a))
        numbers_b = set(re.findall(r'\d+(?:\.\d+)?', text_b))
        
        if not numbers_a or not numbers_b:
            return False
        
        # 检查是否有相似但不完全相同的数字
        for num_a in numbers_a:
            try:
                val_a = float(num_a)
                for num_b in numbers_b:
                    try:
                        val_b = float(num_b)
                        # 如果数值接近但不相同，可能是冲突
                        if val_a != val_b:
                            ratio = max(val_a, val_b) / max(min(val_a, val_b), 0.001)
                            # 在10%到200%范围内的差异值得检查
                            if 0.8 <= ratio <= 2.0:
                                return True
                    except ValueError:
                        continue
            except ValueError:
                continue
        
        return False
    
    def _are_potentially_related(
        self,
        fact_a: FactWithSource,
        fact_b: FactWithSource,
    ) -> bool:
        """
        判断两个事实是否可能相关
        
        使用简单的关键词匹配来判断
        
        Args:
            fact_a: 事实A
            fact_b: 事实B
        
        Returns:
            是否可能相关
        """
        # 提取关键词（简单实现）
        def extract_keywords(text: str) -> set:
            import re
            # 提取中文词汇和英文单词
            words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text.lower())
            # 过滤掉太短的词
            return {w for w in words if len(w) > 1}
        
        keywords_a = extract_keywords(fact_a.content)
        keywords_b = extract_keywords(fact_b.content)
        
        # 计算Jaccard相似度
        if not keywords_a or not keywords_b:
            return False
        
        intersection = len(keywords_a & keywords_b)
        union = len(keywords_a | keywords_b)
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= self._similarity_threshold
    
    async def _detect_conflicts_in_pairs(
        self,
        pairs: List[Tuple[FactWithSource, FactWithSource]],
        progress_callback: Optional[callable] = None,
    ) -> List[ConflictPair]:
        """
        检测事实对之间的冲突
        
        Args:
            pairs: 事实对列表
            progress_callback: 进度回调函数
        
        Returns:
            冲突对列表
        """
        semaphore = asyncio.Semaphore(self._max_concurrency)
        completed = 0
        conflicts = []
        
        async def detect_single_pair(
            pair: Tuple[FactWithSource, FactWithSource]
        ) -> Optional[ConflictPair]:
            nonlocal completed
            async with semaphore:
                result = await self._detect_conflict_between(pair[0], pair[1])
                completed += 1
                if progress_callback:
                    await progress_callback(completed / len(pairs) * 100)
                return result
        
        # 并行检测
        tasks = [detect_single_pair(pair) for pair in pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集冲突
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"冲突检测任务失败: {result}")
                continue
            if result is not None:
                conflicts.append(result)
        
        return conflicts
    
    async def _detect_conflict_between(
        self,
        fact_a: FactWithSource,
        fact_b: FactWithSource,
    ) -> Optional[ConflictPair]:
        """
        检测两个事实之间的冲突
        
        Args:
            fact_a: 事实A
            fact_b: 事实B
        
        Returns:
            冲突对（如果存在冲突）或None
        """
        messages = [
            {"role": "system", "content": CONFLICT_DETECTION_SYSTEM_PROMPT},
            {"role": "user", "content": CONFLICT_DETECTION_USER_PROMPT.format(
                fact_a_id=fact_a.fact_id,
                fact_a_content=fact_a.content,
                fact_a_type=fact_a.fact_type,
                fact_a_location=fact_a.location_description,
                fact_a_source=fact_a.source_text,
                fact_b_id=fact_b.fact_id,
                fact_b_content=fact_b.content,
                fact_b_type=fact_b.fact_type,
                fact_b_location=fact_b.location_description,
                fact_b_source=fact_b.source_text,
            )},
        ]
        
        try:
            response = await self._client.chat_structured(
                messages=messages,
                response_model=ConflictDetectionResponse,
            )
            
            if not response.has_conflict or not response.conflicts:
                return None
            
            # 取第一个冲突（因为我们是两两比对）
            conflict_item = response.conflicts[0]
            
            # 映射冲突类型
            conflict_type = self._map_conflict_type(conflict_item.conflict_type)
            
            return ConflictPair(
                conflict_id=f"conflict_{uuid.uuid4().hex[:12]}",
                fact_a=fact_a,
                fact_b=fact_b,
                conflict_type=conflict_type,
                severity=conflict_item.severity,
                description=conflict_item.description,
                suggestion=conflict_item.suggestion,
            )
            
        except Exception as e:
            logger.error(f"检测事实对冲突失败: {e}")
            return None
    
    def _map_conflict_type(self, type_str: str) -> ConflictType:
        """
        将字符串映射到ConflictType枚举
        
        Args:
            type_str: 类型字符串
        
        Returns:
            ConflictType枚举值
        """
        type_mapping = {
            "numerical": ConflictType.NUMERICAL,
            "temporal": ConflictType.TEMPORAL,
            "entity": ConflictType.ENTITY,
            "categorical": ConflictType.CATEGORICAL,
            "definition": ConflictType.DEFINITION,
            "logical": ConflictType.LOGICAL,
            "spatial": ConflictType.SPATIAL,
        }
        return type_mapping.get(type_str.lower(), ConflictType.LOGICAL)
    
    def _merge_conflicts(self, conflicts: List[ConflictPair]) -> List[ConflictPair]:
        """
        合并和去重冲突
        
        Args:
            conflicts: 冲突列表
        
        Returns:
            去重后的冲突列表
        """
        # 使用事实对ID作为去重键
        seen = set()
        unique_conflicts = []
        
        for conflict in conflicts:
            pair_key = tuple(sorted([conflict.fact_a.fact_id, conflict.fact_b.fact_id]))
            if pair_key not in seen:
                seen.add(pair_key)
                unique_conflicts.append(conflict)
        
        # 按严重程度排序
        unique_conflicts.sort(key=lambda c: c.severity, reverse=True)
        
        return unique_conflicts
    
    async def detect_conflicts_batch(
        self,
        facts: List[FactWithSource],
        batch_size: int = 10,
        progress_callback: Optional[callable] = None,
    ) -> List[ConflictPair]:
        """
        批量检测冲突（将事实分组后一起发送给LLM）
        
        适用于事实数量较多时的优化检测
        
        Args:
            facts: 事实列表
            batch_size: 每批事实数量
            progress_callback: 进度回调函数
        
        Returns:
            冲突对列表
        """
        if len(facts) < 2:
            return []
        
        logger.info(f"开始批量检测 {len(facts)} 个事实之间的冲突...")
        
        all_conflicts = []
        total_batches = (len(facts) + batch_size - 1) // batch_size
        
        for i in range(0, len(facts), batch_size):
            batch = facts[i:i + batch_size]
            batch_conflicts = await self._detect_conflicts_in_batch(batch)
            all_conflicts.extend(batch_conflicts)
            
            if progress_callback:
                await progress_callback((i + len(batch)) / len(facts) * 100)
        
        return self._merge_conflicts(all_conflicts)
    
    async def _detect_conflicts_in_batch(
        self,
        facts: List[FactWithSource],
    ) -> List[ConflictPair]:
        """
        在一批事实中检测冲突
        
        Args:
            facts: 事实批次
        
        Returns:
            冲突对列表
        """
        if len(facts) < 2:
            return []
        
        # 构建事实列表字符串
        facts_list_str = "\n\n".join([
            f"[{i+1}] ID: {f.fact_id}\n"
            f"    内容: {f.content}\n"
            f"    类型: {f.fact_type}\n"
            f"    位置: {f.location_description}\n"
            f"    原文: {f.source_text}"
            for i, f in enumerate(facts)
        ])
        
        messages = [
            {"role": "system", "content": BATCH_CONFLICT_DETECTION_SYSTEM_PROMPT},
            {"role": "user", "content": BATCH_CONFLICT_DETECTION_USER_PROMPT.format(
                facts_list=facts_list_str,
            )},
        ]
        
        try:
            response = await self._client.chat_structured(
                messages=messages,
                response_model=ConflictDetectionResponse,
            )
            
            if not response.has_conflict or not response.conflicts:
                return []
            
            # 构建事实ID到事实的映射
            fact_map = {f.fact_id: f for f in facts}
            
            conflicts = []
            for conflict_item in response.conflicts:
                fact_a = fact_map.get(conflict_item.fact_a_id)
                fact_b = fact_map.get(conflict_item.fact_b_id)
                
                if not fact_a or not fact_b:
                    continue
                
                conflict = ConflictPair(
                    conflict_id=f"conflict_{uuid.uuid4().hex[:12]}",
                    fact_a=fact_a,
                    fact_b=fact_b,
                    conflict_type=self._map_conflict_type(conflict_item.conflict_type),
                    severity=conflict_item.severity,
                    description=conflict_item.description,
                    suggestion=conflict_item.suggestion,
                )
                conflicts.append(conflict)
            
            return conflicts
            
        except Exception as e:
            logger.error(f"批量冲突检测失败: {e}")
            return []

