"""
冲突检测服务
检测文档内部事实之间的矛盾和冲突
使用 LSH (局部敏感哈希) 快速过滤不相似的事实对，提高效率
"""
import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from itertools import combinations

from .llm_client import llm_client
from .redis_client import redis_client
from .lsh_filter import lsh_filter
from .progress_manager import progress_manager, ProgressStage

logger = logging.getLogger(__name__)

# 冲突检测 Prompt 模板
CONFLICT_DETECTION_PROMPT = """以下是从同一文档不同位置提取的两个事实，请判断它们是否存在冲突或矛盾。

事实A：{fact_a_content}
（类型：{fact_a_type} | 位置：{fact_a_location}）

事实B：{fact_b_content}
（类型：{fact_b_type} | 位置：{fact_b_location}）

请仔细分析这两个事实，判断是否存在冲突（数据不一致、逻辑矛盾、时间冲突等）。

只返回单行JSON（不要换行、不要缩进、不要多余空白）：
{{"has_conflict": true或false, "conflict_type": "无冲突/数据不一致/逻辑矛盾/时间冲突", "severity": "无/低/中/高", "explanation": "简短说明", "confidence": 0.5}}"""


class ConflictDetector:
    """冲突检测器"""
    
    def __init__(self):
        self.llm = llm_client
        self.redis = redis_client
        self.lsh = lsh_filter
    
    async def detect_conflicts(
        self,
        document_id: str,
        facts: List[Dict[str, Any]] = None,
        save_to_redis: bool = True,
        use_lsh: bool = False,
        max_pairs: int = 300,
        report_progress: bool = True,
        sections: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检测文档中事实之间的冲突及内容重复
        
        Args:
            document_id: 文档ID
            facts: 事实列表（如果为空，从 Redis 获取）
            save_to_redis: 是否保存结果到 Redis
            use_lsh: 是否使用 LSH 预过滤（默认False，因LSH会漏掉数值/时间冲突）
            max_pairs: 最大比对对数（默认300，结构化字段智能过滤后的高风险对）
            report_progress: 是否报告进度
            sections: 文档章节列表，用于检测重复段落（可选）
        
        Returns:
            冲突检测结果
        """
        # 如果没有提供事实列表，从 Redis 获取
        if facts is None:
            facts = self.redis.get_facts(document_id)
            if facts is None:
                raise ValueError(f"文档 {document_id} 的事实数据不存在")
        
        if len(facts) < 2:
            return {
                "document_id": document_id,
                "total_facts": len(facts),
                "total_comparisons": 0,
                "conflicts_found": 0,
                "conflicts": [],
                "message": "事实数量不足，无法进行冲突检测"
            }
        
        logger.info(f"开始冲突检测: 文档 {document_id}, 共 {len(facts)} 条事实")
        
        # 初始化进度 - 标记上一阶段完成，进入冲突检测阶段
        if report_progress:
            await progress_manager.update_progress(
                document_id,
                stage=ProgressStage.DETECT_CONFLICTS,
                stage_label="冲突检测",
                current=0,
                total=1,
                message="正在生成事实对比对列表...",
                sub_message="准备中...",
                mark_stage_complete=True
            )
        
        # 使用 LSH 预过滤或传统方法生成事实对
        if use_lsh:
            # 使用 LSH 预过滤；若结果过少，则回退到全量生成
            fact_pairs = self.lsh.filter_similar_pairs(facts, max_pairs=max_pairs)
            logger.info(f"LSH 过滤后: {len(fact_pairs)} 对事实进行比对 (原始可能 {len(facts) * (len(facts) - 1) // 2} 对)")
            if not fact_pairs:
                fact_pairs = self._generate_comparison_pairs(facts, max_pairs=max_pairs)
                logger.info(f"LSH 未命中，回退生成 {len(fact_pairs)} 对事实进行比对")
        else:
            # 直接全量/按类型生成，确保覆盖潜在矛盾
            fact_pairs = self._generate_comparison_pairs(facts, max_pairs=max_pairs)
            logger.info(f"生成 {len(fact_pairs)} 对事实进行比对")
        
        total_pairs = len(fact_pairs)
        
        # 更新进度 - 设置总比对数
        if report_progress:
            await progress_manager.update_progress(
                document_id,
                total=total_pairs,
                message=f"正在进行全文档逻辑矛盾检测 (0/{total_pairs})",
                sub_message=f"共 {total_pairs} 对事实需要比对"
            )
        
        # 检测冲突
        conflicts = []
        comparison_count = 0
        
        # 并行化优化：批量处理 LLM 调用
        batch_size = 10  # 每批并行处理10对
        
        for i in range(0, len(fact_pairs), batch_size):
            batch = fact_pairs[i:i + batch_size]
            
            # 并行调用 LLM 比对
            tasks = [self._compare_facts(fa, fb) for fa, fb in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for (fact_a, fact_b), result in zip(batch, results):
                comparison_count += 1
                
                # 更新进度
                if report_progress and comparison_count % 5 == 0:  # 每5次更新一次，减少更新频率
                    await progress_manager.update_progress(
                        document_id,
                        current=comparison_count,
                        message=f"正在进行全文档逻辑矛盾检测 ({comparison_count}/{total_pairs})",
                        sub_message=f"已发现 {len(conflicts)} 个冲突"
                    )
                
                # 处理异常
                if isinstance(result, Exception):
                    logger.error(f"比对事实时出错: {str(result)}")
                    continue
                
                if result and result.get("has_conflict"):
                    conflict = {
                        "conflict_id": f"conflict_{document_id}_{len(conflicts)}",
                        "fact_a": {
                            "fact_id": fact_a.get("fact_id"),
                            "type": fact_a.get("type"),
                            "content": fact_a.get("content"),
                            "original_text": fact_a.get("original_text"),
                            "location": fact_a.get("location")
                        },
                        "fact_b": {
                            "fact_id": fact_b.get("fact_id"),
                            "type": fact_b.get("type"),
                            "content": fact_b.get("content"),
                            "original_text": fact_b.get("original_text"),
                            "location": fact_b.get("location")
                        },
                        "conflict_type": result.get("conflict_type", "未知"),
                        "severity": result.get("severity", "中"),
                        "explanation": result.get("explanation", ""),
                        "confidence": result.get("confidence", 0.5)
                    }
                    conflicts.append(conflict)
                    logger.info(f"发现冲突: {conflict['conflict_type']} - {conflict['explanation'][:50]}")
        
        # 检测重复内容
        repetitions = []
        if sections:
            repetitions = self._detect_repetitions(sections)
        
        # 按严重程度排序
        severity_map = {"高": 0, "中": 1, "低": 2, "无": 3}
        # 确保 severity 字段存在且在 map 中，否则默认为 "中"
        conflicts.sort(key=lambda x: severity_map.get(x.get("severity", "中"), 1))
        
        # 统计信息
        severity_stats = {}
        type_stats = {}
        for conflict in conflicts:
            severity = conflict.get("severity", "中")
            severity_stats[severity] = severity_stats.get(severity, 0) + 1
            
            conflict_type = conflict.get("conflict_type", "未知")
            type_stats[conflict_type] = type_stats.get(conflict_type, 0) + 1
        
        result = {
            "document_id": document_id,
            "total_facts": len(facts),
            "total_comparisons": comparison_count,
            "conflicts_found": len(conflicts),
            "conflicts": conflicts,
            "repetitions": repetitions,  # 单独返回重复内容
            "statistics": {
                "by_severity": severity_stats,
                "by_type": type_stats
            }
        }
        
        # 保存到 Redis
        if save_to_redis and conflicts:
            try:
                self.redis.save_conflicts(document_id, conflicts)
                result["saved_to_redis"] = True
            except Exception as e:
                logger.error(f"保存冲突到 Redis 失败: {str(e)}")
                result["saved_to_redis"] = False
        
        logger.info(f"冲突检测完成: 文档 {document_id}, 发现 {len(conflicts)} 个冲突")
        
        return result
    
    def _generate_comparison_pairs(
        self,
        facts: List[Dict[str, Any]],
        max_pairs: int = 30
    ) -> List[Tuple[Dict, Dict]]:
        """
        生成需要比对的事实对
        
        优先比对同类型的事实（更可能存在冲突）
        """
        pairs: List[Tuple[Dict, Dict]] = []
        seen: Set[Tuple[str, str]] = set()
        
        # 先添加结构化字段驱动的候选（主体/谓词/客体/数值/时间/极性）
        structured_pairs = self._generate_structured_pairs(facts, limit=max_pairs)
        for fa, fb in structured_pairs:
            if self._add_pair((fa, fb), pairs, seen):
                if len(pairs) >= max_pairs:
                    return pairs

        # 再添加关键词/模式驱动的候选（覆盖常见矛盾点）
        keyword_pairs = self._generate_keyword_based_pairs(facts, limit=max_pairs)
        for fa, fb in keyword_pairs:
            if self._add_pair((fa, fb), pairs, seen):
                if len(pairs) >= max_pairs:
                    return pairs

        # 再按类型分组补充
        facts_by_type = {}
        for fact in facts:
            fact_type = fact.get("type", "未知")
            if fact_type not in facts_by_type:
                facts_by_type[fact_type] = []
            facts_by_type[fact_type].append(fact)
        
        # 优先添加同类型事实对
        for fact_type, type_facts in facts_by_type.items():
            if len(type_facts) >= 2:
                for pair in combinations(type_facts, 2):
                    if self._add_pair(pair, pairs, seen):
                        if len(pairs) >= max_pairs:
                            return pairs
                    if len(pairs) >= max_pairs:
                        return pairs
        
        # 如果同类型比对不够，添加跨类型比对（数据类型优先）
        data_types = ["数据", "日期", "结论"]
        for type_a in data_types:
            for type_b in data_types:
                if type_a != type_b:
                    facts_a = facts_by_type.get(type_a, [])
                    facts_b = facts_by_type.get(type_b, [])
                    for fa in facts_a:
                        for fb in facts_b:
                            if self._add_pair((fa, fb), pairs, seen):
                                if len(pairs) >= max_pairs:
                                    return pairs
                            if len(pairs) >= max_pairs:
                                return pairs
        
        
        return pairs

    def _generate_structured_pairs(self, facts: List[Dict[str, Any]], limit: int) -> List[Tuple[Dict, Dict]]:
        """
        基于结构化字段生成候选对：
        - 同一 (subject, predicate, object) 分组内：
          * 极性相反 → 逻辑矛盾候选
          * 数值冲突 → 数据不一致候选（数值/比例差异显著）
          * 时间冲突 → 时间不一致候选
        """
        def key_of(f: Dict[str, Any]) -> Tuple[str, str, str]:
            return (
                (f.get("subject") or "").strip(),
                (f.get("predicate") or "").strip(),
                (f.get("object") or "").strip(),
            )

        def num_of(v: Any) -> Optional[float]:
            if v is None:
                return None
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                m = re.findall(r"(-?\d+(?:\.\d+)?)", v)
                if m:
                    try:
                        return float(m[0])
                    except:
                        return None
            return None

        groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        for f in facts:
            k = key_of(f)
            groups.setdefault(k, []).append(f)

        pairs: List[Tuple[Dict, Dict]] = []
        for k, items in groups.items():
            if len(items) < 2:
                continue
            # 两两组合比较
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    fa, fb = items[i], items[j]
                    # 极性相反
                    pa = (fa.get("polarity") or "affirmative").lower()
                    pb = (fb.get("polarity") or "affirmative").lower()
                    if pa != pb:
                        pairs.append((fa, fb))
                        if len(pairs) >= limit:
                            return pairs
                    # 数值冲突（如果两者具有数值）
                    va = num_of(fa.get("value"))
                    vb = num_of(fb.get("value"))
                    if va is not None and vb is not None:
                        # 若是比例/百分比，差异阈值稍宽；否则比较绝对差异和相对差异
                        has_percent_a = "%" in str(fa.get("value")) or "%" in (fa.get("original_text") or "")
                        has_percent_b = "%" in str(fb.get("value")) or "%" in (fb.get("original_text") or "")
                        if has_percent_a or has_percent_b:
                            if abs(va - vb) >= 10.0:
                                pairs.append((fa, fb))
                                if len(pairs) >= limit:
                                    return pairs
                        else:
                            # 一般数值，比较相对差异 > 0.2 或绝对差异明显
                            if (min(va, vb) > 0 and abs(va - vb) / max(va, vb) > 0.2) or abs(va - vb) > 1.0:
                                pairs.append((fa, fb))
                                if len(pairs) >= limit:
                                    return pairs
                    # 时间冲突（时间字符串不一致）
                    ta = (fa.get("time") or "").strip()
                    tb = (fb.get("time") or "").strip()
                    if ta and tb and ta != tb:
                        pairs.append((fa, fb))
                        if len(pairs) >= limit:
                            return pairs
        return pairs

    def _add_pair(self, pair: Tuple[Dict, Dict], pairs: List[Tuple[Dict, Dict]], seen: Set[Tuple[str, str]]) -> bool:
        """将事实对加入列表并去重（基于 fact_id 或内容哈希）"""
        fa, fb = pair
        ida = str(fa.get("fact_id") or hash(fa.get("content", "")))
        idb = str(fb.get("fact_id") or hash(fb.get("content", "")))
        key = (ida, idb) if ida <= idb else (idb, ida)
        if key in seen:
            return False
        seen.add(key)
        pairs.append(pair)
        return True

    def _generate_keyword_based_pairs(self, facts: List[Dict[str, Any]], limit: int) -> List[Tuple[Dict, Dict]]:
        """
        基于关键词与模式的候选对生成，针对用户列出的典型矛盾：
        - 合规/不合规（落实政策 vs 不符合新版指南）
        - 居民协调完成 vs 居民反对/延迟
        - 资金缺口（无缺口 vs 停工风险/仅到位/阶段性缺口可控）
        - 竣工时间（可能延迟至4月 vs 调整为3月20日/3月底试运行）
        - 医疗预约闭环 vs 无法对接/仍需线下
        - 前期筹备全部完成 vs 未办理施工许可证/未办结
        - 装修进度/费用比例不匹配（装修进度70% vs 支出50%）
        - 安全目标 vs 技术问题（全方位防护/覆盖 vs 识别率低/无法实时传输）
        """
        text_list = [(f, (f.get("content") or "") + " " + (f.get("original_text") or "")) for f in facts]
        def has_any(s: str, kws: List[str]) -> bool:
            return any(kw in s for kw in kws)
        def find(kws: List[str]) -> List[Dict]:
            return [f for f, t in text_list if has_any(t, kws)]
        def pairs_for(kws_a: List[str], kws_b: List[str]) -> List[Tuple[Dict, Dict]]:
            A = find(kws_a)
            B = find(kws_b)
            return [(fa, fb) for fa in A for fb in B]
        
        candidates: List[Tuple[Dict, Dict]] = []
        
        # 合规性：落实政策/符合要求 vs 不符新版指南/未达到要求
        candidates += pairs_for([
            "落实国家及省级政策", "符合政策", "落实政策", "符合要求"
        ], [
            "不符", "未达到指南要求", "修订版", "2024年修订版"
        ])
        
        # 居民协调：已完成协调 vs 居民反对/延迟/隐私
        candidates += pairs_for([
            "已完成协调", "协调工作已完成"
        ], [
            "居民反对", "延迟推进", "隐私", "延迟安装"
        ])
        
        # 资金缺口：无资金缺口 vs 停工风险/仅到位/阶段性缺口可控
        candidates += pairs_for([
            "无资金缺口", "资金周转正常"
        ], [
            "停工风险", "仅到位", "资金缺口", "阶段性资金缺口可控"
        ])
        
        # 竣工时间：可能延迟至4月 vs 调整为3月20日/3月底试运行
        candidates += pairs_for([
            "可能导致项目整体竣工时间延迟至2026年4月", "可能延迟至2026年4月"
        ], [
            "调整为2026年3月20日", "3月底前投入试运行", "2026年3月20日"
        ])
        
        # 医疗预约：闭环服务 vs 无法对接/仍需线下
        candidates += pairs_for([
            "医疗预约闭环服务", "闭环服务"
        ], [
            "无法与", "无法对接", "仍需线下排队"
        ])
        
        # --- 新增通用企业年报场景 ---
        
        # 1. 总部地点冲突
        candidates += pairs_for([
            "总部位于", "总部设在", "注册地"
        ], [
            "总部", "地点", "位于", "迁往"
        ])

        # 2. 裁员承诺 vs 裁员事实
        candidates += pairs_for([
            "零裁员", "不裁员", "增加员工", "招聘"
        ], [
            "裁员", "裁撤", "离职", "减少岗位", "重组"
        ])

        # 3. 财务数据冲突 (营收/利润)
        candidates += pairs_for([
            "营收", "收入", "利润", "亏损", "财务", "业绩"
        ], [
            "营收", "收入", "利润", "亏损", "财务", "业绩"
        ])

        # 4. 环保承诺 vs 排放事实
        candidates += pairs_for([
            "零排放", "碳中和", "环保", "绿色", "减少排放"
        ], [
            "排放增加", "污染", "未达到", "推迟", "增加废弃物"
        ])

        # 5. 产地冲突 (制造地)
        candidates += pairs_for([
            "制造", "产地", "生产线", "工厂"
        ], [
            "制造", "产地", "生产线", "工厂", "转移"
        ])

        # 6. 趋势矛盾 (定性描述 vs 定量数据)
        # 例如："稳步增长" vs "下降了"
        candidates += pairs_for([
            "增长", "上升", "提高", "增加", "攀升"
        ], [
            "下降", "下滑", "减少", "降低", "缩减", "跌落"
        ])

        # 7. 合规与安全矛盾
        # 例如："从未发生泄露" vs "违规传输"
        candidates += pairs_for([
            "未发生", "零事故", "合规", "遵守", "安全", "保护"
        ], [
            "泄露", "违规", "事故", "失败", "违反", "被罚"
        ])
        
        # 前期筹备：全部完成 vs 未办理施工许可证/未办结
        candidates += pairs_for([
            "前期筹备工作已全部完成"
        ], [
            "未办理施工许可证", "未办结"
        ])
        
        # 装修进度/费用：包含“装修”且存在百分比
        def percent_values(text: str) -> List[float]:
            return [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)%", text)]
        deco_facts = [f for f, t in text_list if "装修" in t]
        for i in range(len(deco_facts)):
            for j in range(i + 1, len(deco_facts)):
                ta = (deco_facts[i].get("content") or "") + " " + (deco_facts[i].get("original_text") or "")
                tb = (deco_facts[j].get("content") or "") + " " + (deco_facts[j].get("original_text") or "")
                pa = percent_values(ta)
                pb = percent_values(tb)
                if pa and pb and any(abs(a - b) >= 15.0 for a in pa for b in pb):
                    candidates.append((deco_facts[i], deco_facts[j]))
        
        # 安全目标 vs 技术问题（识别率低/无法实时传输）
        candidates += pairs_for([
            "全方位安全防护网络", "覆盖社区出入口、楼道、停车场"
        ], [
            "识别成功率仅", "无法实现实时画面传输", "无法实时传输"
        ])
        
        # 去重并限量
        unique: List[Tuple[Dict, Dict]] = []
        seen: Set[Tuple[str, str]] = set()
        for fa, fb in candidates:
            ida = str(fa.get("fact_id") or hash(fa.get("content", "")))
            idb = str(fb.get("fact_id") or hash(fb.get("content", "")))
            key = (ida, idb) if ida <= idb else (idb, ida)
            if key in seen:
                continue
            seen.add(key)
            unique.append((fa, fb))
            if len(unique) >= limit:
                break
        return unique
    
    async def _compare_facts(
        self,
        fact_a: Dict[str, Any],
        fact_b: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 比对两个事实是否冲突
        """
        if not self.llm.is_available():
            raise ValueError("LLM 服务不可用")
        
        # 构建提示词
        prompt = CONFLICT_DETECTION_PROMPT.format(
            fact_a_content=fact_a.get("content", ""),
            fact_a_type=fact_a.get("type", "未知"),
            fact_a_subject=fact_a.get("subject", ""),
            fact_a_predicate=fact_a.get("predicate", ""),
            fact_a_object=fact_a.get("object", ""),
            fact_a_value=str(fact_a.get("value", "")),
            fact_a_time=fact_a.get("time", ""),
            fact_a_polarity=fact_a.get("polarity", ""),
            fact_a_original=fact_a.get("original_text", ""),
            fact_a_location=self._format_location(fact_a.get("location")),
            fact_b_content=fact_b.get("content", ""),
            fact_b_type=fact_b.get("type", "未知"),
            fact_b_subject=fact_b.get("subject", ""),
            fact_b_predicate=fact_b.get("predicate", ""),
            fact_b_object=fact_b.get("object", ""),
            fact_b_value=str(fact_b.get("value", "")),
            fact_b_time=fact_b.get("time", ""),
            fact_b_polarity=fact_b.get("polarity", ""),
            fact_b_original=fact_b.get("original_text", ""),
            fact_b_location=self._format_location(fact_b.get("location"))
        )
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的文档审核助手，擅长发现文档中的事实冲突和逻辑矛盾。请准确判断两个事实是否存在冲突，避免误报。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self.llm.chat(messages, temperature=0.1)
            return self._parse_conflict_response(response)
        except Exception as e:
            logger.error(f"LLM 比对失败: {str(e)}")
            return None
    
    def _format_location(self, location: Optional[Dict]) -> str:
        """格式化位置信息"""
        if not location:
            return "未知位置"
        
        section_title = location.get("section_title", "")
        section_index = location.get("section_index", 0)
        
        if section_title:
            return f"章节 {section_index + 1}: {section_title}"
        return f"章节 {section_index + 1}"
    
    def _parse_conflict_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的冲突检测结果"""
        try:
            response = response.strip()
            
            # 第一步：移除可能的 markdown 代码块
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # 第二步：将所有whitespace（包括换行、制表、多余空格）压缩为单一空格
            # 这样形如 '\n    "has_conflict"' 的错误格式会被规范化
            response = ' '.join(response.split())
            
            # 第三步：尝试 JSON 解析
            result = json.loads(response)
            
            # 第四步：验证必需字段，确保返回格式统一
            if "has_conflict" not in result:
                result["has_conflict"] = False
            
            if "conflict_type" not in result:
                result["conflict_type"] = "无冲突"
            
            if "severity" not in result:
                result["severity"] = "无" if not result.get("has_conflict") else "中"
            
            if "explanation" not in result:
                result["explanation"] = ""
            
            if "confidence" not in result:
                result["confidence"] = 0.5 if result.get("has_conflict") else 0.3
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析冲突检测 JSON 失败: {e}")
            logger.debug(f"原始响应 (前200字): {response[:200]}")
            return None
        except Exception as e:
            logger.error(f"处理冲突检测响应出错: {str(e)}")
            return None

    def _detect_repetitions(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测文档中的高频重复段落（完全匹配或高度相似）
        
        Args:
            sections: 章节列表
            
        Returns:
            重复内容作为冲突对象的列表
        """
        if not sections:
            logger.warning("No sections provided for repetition detection")
            return []
            
        # Map: normalized_content -> {original_content, count, locations: []}
        content_map = {}
        
        logger.info(f"Detecting repetitions in {len(sections)} sections")
        
        for section in sections:
            sec_title = section.get('title', '未知章节')
            content = section.get('content', '')
            if not content:
                continue

            # 改进分割逻辑：不仅按换行符，还按句子结束符分割
            # 这样可以捕获嵌入在段落中的重复核心语句
            # 使用正则是最好的: re.split(r'[。！？\n.!?;]+', content)
            segments = re.split(r'[。！？\n.!?;]+', content)
            
            for p in segments:
                # 归一化：去除两端空白
                normalized = p.strip()
                # 忽略短句（标题、短语等），通常核心段落长度较长
                # 调低阈值到 20 以捕获中等长度的标语/使命
                if len(normalized) < 20:
                    continue
                    
                if normalized not in content_map:
                    content_map[normalized] = {
                        'content': normalized,
                        'count': 0,
                        'locations': []
                    }
                
                content_map[normalized]['count'] += 1
                content_map[normalized]['locations'].append(sec_title)
        
        logger.info(f"Processed {len(content_map)} unique segments")
        
        repetitions = []
        # 筛选重复次数 >= 3 的段落
        for content, data in content_map.items():
            if data['count'] >= 3:
                # 整理位置信息
                unique_locs = sorted(list(set(data['locations'])))
                
                rep_entry = {
                    "conflict_id": f"rep_{abs(hash(content))}",
                    "has_conflict": True,
                    "conflict_type": "核心高频重复",
                    "severity": "中", 
                    "fact_a": {
                        "fact_id": "rep_source",
                        "type": "段落内容",
                        "content": content[:100] + "..." if len(content) > 100 else content,
                        "original_text": content,  # 添加完整原文用于前端高亮
                        "location": {"section_title": unique_locs[0] if unique_locs else "未知"}
                    },
                    "fact_b": {
                        "fact_id": "rep_target",
                        "type": "重复统计",
                        "content": f"重复次数: {data['count']}",
                        "location": {"section_title": "全文多处"}
                    },
                    "explanation": f"检测到核心段落高频重复（出现 {data['count']} 次）。\n内容摘要：“{content[:30]}...”\n出现位置：{', '.join(unique_locs[:5])}{' 等' if len(unique_locs)>5 else ''}。",
                    "confidence": 1.0
                }
                repetitions.append(rep_entry)
                logger.info(f"发现重复段落: {data['count']} 次 - {content[:20]}...")
                
        return repetitions
    
    def get_conflicts(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """从 Redis 获取已保存的冲突"""
        return self.redis.get_conflicts(document_id)


# 全局冲突检测器实例
conflict_detector = ConflictDetector()

