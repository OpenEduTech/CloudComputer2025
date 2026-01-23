"""
轻量 NLP 提取器
使用正则表达式和规则提取基础实体（数字、日期、人名、机构）
不依赖 LLM，速度快，适合预处理
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# 尝试导入 jieba
try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba 未安装，部分 NLP 功能受限")


@dataclass
class BasicEntity:
    """基础实体"""
    type: str           # 类型: 数字/日期/人名/机构/金额/百分比
    value: str          # 提取的值
    normalized: Any     # 标准化后的值
    original_text: str  # 原文
    start_pos: int      # 起始位置
    end_pos: int        # 结束位置
    confidence: float   # 置信度


class NLPExtractor:
    """
    轻量 NLP 提取器
    使用规则和正则表达式提取基础实体
    """
    
    # 中文数字映射
    CN_NUM = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000, '亿': 100000000,
        '两': 2
    }
    
    # 常见机构后缀
    ORG_SUFFIXES = [
        '公司', '集团', '银行', '医院', '学校', '大学', '学院', '研究院',
        '研究所', '协会', '基金会', '委员会', '局', '部', '厅', '处',
        '中心', '办公室', '街道', '社区', '村委会', '居委会'
    ]
    
    # 常见职位
    TITLES = [
        '总经理', '经理', '主任', '主管', '总监', '董事', '院长', '校长',
        '局长', '处长', '科长', '主席', '秘书长', '书记', '市长', '区长',
        '镇长', '村长', '负责人', '项目经理'
    ]
    
    def __init__(self):
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """编译所有正则表达式模式"""
        return {
            # 日期模式
            'date_ymd': re.compile(
                r'(\d{4})\s*[年\-/\.]\s*(\d{1,2})\s*[月\-/\.]\s*(\d{1,2})\s*[日号]?'
            ),
            'date_ym': re.compile(
                r'(\d{4})\s*[年\-/\.]\s*(\d{1,2})\s*月'
            ),
            'date_y': re.compile(
                r'(\d{4})\s*年'
            ),
            'date_cn': re.compile(
                r'([二〇零一二三四五六七八九]+)\s*年\s*([一二三四五六七八九十]+)\s*月(?:\s*([一二三四五六七八九十]+)\s*[日号])?'
            ),
            'date_relative': re.compile(
                r'(今年|去年|前年|明年|后年|本月|上月|下月|本周|上周|下周|本季度|上季度|下季度)'
            ),
            
            # 金额模式
            'money_cn': re.compile(
                r'(\d+(?:\.\d+)?)\s*(万|亿|千|百)?\s*(元|块|美元|欧元|日元|港币|人民币)'
            ),
            'money_unit': re.compile(
                r'([\d,]+(?:\.\d+)?)\s*(万元|亿元|千元|百元|元)'
            ),
            
            # 百分比模式
            'percent': re.compile(
                r'(\d+(?:\.\d+)?)\s*[%％]|百分之\s*([一二三四五六七八九十百零\d]+(?:\.\d+)?)'
            ),
            
            # 纯数字模式（带单位）
            'number_with_unit': re.compile(
                r'(\d+(?:\.\d+)?)\s*(个|人|户|家|套|项|件|次|天|周|月|年|平方米|平米|㎡|米|公里|km|吨|千克|kg|万|亿)'
            ),
            
            # 电话/身份证（用于过滤）
            'phone': re.compile(r'\d{11}|\d{3,4}[-\s]?\d{7,8}'),
            'id_card': re.compile(r'\d{17}[\dXx]'),
            
            # 时间范围
            'time_range': re.compile(
                r'(\d{4}[年\-/]\d{1,2}[月\-/]?\d{0,2}[日]?)\s*[至到\-~]\s*(\d{4}[年\-/]\d{1,2}[月\-/]?\d{0,2}[日]?)'
            ),
        }
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取所有基础实体
        
        Args:
            text: 输入文本
        
        Returns:
            实体列表，每个实体包含 type, value, normalized, original_text, position
        """
        if not text:
            return []
        
        entities = []
        
        # 提取日期
        entities.extend(self._extract_dates(text))
        
        # 提取金额
        entities.extend(self._extract_money(text))
        
        # 提取百分比
        entities.extend(self._extract_percentages(text))
        
        # 提取数字（带单位）
        entities.extend(self._extract_numbers(text))
        
        # 如果 jieba 可用，提取人名和机构
        if JIEBA_AVAILABLE:
            entities.extend(self._extract_names_and_orgs(text))
        else:
            # 使用规则提取机构
            entities.extend(self._extract_orgs_by_rules(text))
        
        # 去重和排序
        entities = self._deduplicate_entities(entities)
        
        return [asdict(e) for e in entities]
    
    def _extract_dates(self, text: str) -> List[BasicEntity]:
        """提取日期"""
        entities = []
        
        # 年月日格式
        for match in self.patterns['date_ymd'].finditer(text):
            year, month, day = match.groups()
            entities.append(BasicEntity(
                type='日期',
                value=f"{year}年{month}月{day}日",
                normalized={'year': int(year), 'month': int(month), 'day': int(day)},
                original_text=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))
        
        # 年月格式（排除已匹配的）
        matched_positions = {(e.start_pos, e.end_pos) for e in entities}
        for match in self.patterns['date_ym'].finditer(text):
            if not self._overlaps_any(match.start(), match.end(), matched_positions):
                year, month = match.groups()
                entities.append(BasicEntity(
                    type='日期',
                    value=f"{year}年{month}月",
                    normalized={'year': int(year), 'month': int(month)},
                    original_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.90
                ))
        
        # 时间范围
        for match in self.patterns['time_range'].finditer(text):
            start_date, end_date = match.groups()
            entities.append(BasicEntity(
                type='时间范围',
                value=f"{start_date} 至 {end_date}",
                normalized={'start': start_date, 'end': end_date},
                original_text=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.92
            ))
        
        # 相对日期
        for match in self.patterns['date_relative'].finditer(text):
            entities.append(BasicEntity(
                type='相对日期',
                value=match.group(),
                normalized=match.group(),
                original_text=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.85
            ))
        
        return entities
    
    def _extract_money(self, text: str) -> List[BasicEntity]:
        """提取金额"""
        entities = []
        
        # 带单位的金额
        for match in self.patterns['money_unit'].finditer(text):
            num_str, unit = match.groups()
            num = float(num_str.replace(',', ''))
            
            # 转换为统一单位（元）
            multiplier = 1
            if '万' in unit:
                multiplier = 10000
            elif '亿' in unit:
                multiplier = 100000000
            elif '千' in unit:
                multiplier = 1000
            elif '百' in unit:
                multiplier = 100
            
            normalized_value = num * multiplier
            
            entities.append(BasicEntity(
                type='金额',
                value=f"{num}{unit}",
                normalized=normalized_value,
                original_text=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))
        
        # 中文金额表述
        for match in self.patterns['money_cn'].finditer(text):
            num_str, unit_prefix, currency = match.groups()
            num = float(num_str)
            
            multiplier = 1
            if unit_prefix == '万':
                multiplier = 10000
            elif unit_prefix == '亿':
                multiplier = 100000000
            elif unit_prefix == '千':
                multiplier = 1000
            elif unit_prefix == '百':
                multiplier = 100
            
            normalized_value = num * multiplier
            
            entities.append(BasicEntity(
                type='金额',
                value=match.group(),
                normalized={'amount': normalized_value, 'currency': currency},
                original_text=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.90
            ))
        
        return entities
    
    def _extract_percentages(self, text: str) -> List[BasicEntity]:
        """提取百分比"""
        entities = []
        
        for match in self.patterns['percent'].finditer(text):
            arabic_num, cn_num = match.groups()
            
            if arabic_num:
                value = float(arabic_num)
            elif cn_num:
                # 尝试转换中文数字
                try:
                    value = self._cn_to_arabic(cn_num)
                except:
                    value = cn_num
            else:
                continue
            
            entities.append(BasicEntity(
                type='百分比',
                value=f"{value}%",
                normalized=value if isinstance(value, (int, float)) else None,
                original_text=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))
        
        return entities
    
    def _extract_numbers(self, text: str) -> List[BasicEntity]:
        """提取带单位的数字"""
        entities = []
        
        # 过滤电话号码和身份证号
        phone_matches = set()
        for match in self.patterns['phone'].finditer(text):
            phone_matches.add((match.start(), match.end()))
        for match in self.patterns['id_card'].finditer(text):
            phone_matches.add((match.start(), match.end()))
        
        for match in self.patterns['number_with_unit'].finditer(text):
            if self._overlaps_any(match.start(), match.end(), phone_matches):
                continue
            
            num_str, unit = match.groups()
            num = float(num_str)
            
            entities.append(BasicEntity(
                type='数量',
                value=f"{num}{unit}",
                normalized={'value': num, 'unit': unit},
                original_text=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.90
            ))
        
        return entities
    
    def _extract_names_and_orgs(self, text: str) -> List[BasicEntity]:
        """使用 jieba 提取人名和机构"""
        entities = []
        
        words = pseg.cut(text)
        current_pos = 0
        
        for word, flag in words:
            start_pos = text.find(word, current_pos)
            end_pos = start_pos + len(word)
            current_pos = end_pos
            
            # nr: 人名, nt: 机构名
            if flag == 'nr' and len(word) >= 2:
                entities.append(BasicEntity(
                    type='人名',
                    value=word,
                    normalized=word,
                    original_text=word,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    confidence=0.80
                ))
            elif flag == 'nt' or flag == 'ns':
                entities.append(BasicEntity(
                    type='机构',
                    value=word,
                    normalized=word,
                    original_text=word,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    confidence=0.75
                ))
        
        return entities
    
    def _extract_orgs_by_rules(self, text: str) -> List[BasicEntity]:
        """使用规则提取机构"""
        entities = []
        
        for suffix in self.ORG_SUFFIXES:
            pattern = re.compile(rf'([\u4e00-\u9fa5]{{2,15}}{suffix})')
            for match in pattern.finditer(text):
                entities.append(BasicEntity(
                    type='机构',
                    value=match.group(),
                    normalized=match.group(),
                    original_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.70
                ))
        
        return entities
    
    def _cn_to_arabic(self, cn_str: str) -> float:
        """中文数字转阿拉伯数字"""
        if cn_str.isdigit():
            return float(cn_str)
        
        result = 0
        temp = 0
        
        for char in cn_str:
            if char in self.CN_NUM:
                num = self.CN_NUM[char]
                if num >= 10:
                    if temp == 0:
                        temp = 1
                    result += temp * num
                    temp = 0
                else:
                    temp = temp * 10 + num if temp else num
        
        result += temp
        return float(result) if result else float(cn_str)
    
    def _overlaps_any(
        self,
        start: int,
        end: int,
        positions: set
    ) -> bool:
        """检查位置是否与已有位置重叠"""
        for pos_start, pos_end in positions:
            if start < pos_end and end > pos_start:
                return True
        return False
    
    def _deduplicate_entities(
        self,
        entities: List[BasicEntity]
    ) -> List[BasicEntity]:
        """去重实体（优先保留置信度高的）"""
        # 按位置排序
        entities.sort(key=lambda e: (e.start_pos, -e.confidence))
        
        # 去除重叠的实体
        result = []
        last_end = -1
        
        for entity in entities:
            if entity.start_pos >= last_end:
                result.append(entity)
                last_end = entity.end_pos
        
        return result
    
    def extract_with_context(
        self,
        text: str,
        context_window: int = 50
    ) -> List[Dict[str, Any]]:
        """
        提取实体并附带上下文
        
        Args:
            text: 输入文本
            context_window: 上下文窗口大小
        
        Returns:
            带上下文的实体列表
        """
        entities = self.extract_entities(text)
        
        for entity in entities:
            start = max(0, entity['start_pos'] - context_window)
            end = min(len(text), entity['end_pos'] + context_window)
            entity['context'] = text[start:end]
        
        return entities


class SmartChunker:
    """
    智能文本分块器
    基于语义边界和实体密度进行分块
    """
    
    def __init__(self, nlp_extractor: NLPExtractor = None):
        self.nlp = nlp_extractor or NLPExtractor()
    
    def chunk_text(
        self,
        text: str,
        max_chunk_size: int = 1000,
        min_chunk_size: int = 200,
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        智能分块文本
        
        Args:
            text: 输入文本
            max_chunk_size: 最大块大小
            min_chunk_size: 最小块大小
            overlap: 块之间的重叠
        
        Returns:
            分块列表，每块包含 text, start, end, entities
        """
        if len(text) <= max_chunk_size:
            entities = self.nlp.extract_entities(text)
            return [{
                'text': text,
                'start': 0,
                'end': len(text),
                'entities': entities,
                'entity_count': len(entities)
            }]
        
        chunks = []
        
        # 找到自然分割点（段落、句号等）
        split_points = self._find_split_points(text, max_chunk_size, min_chunk_size)
        
        prev_end = 0
        for split_point in split_points:
            chunk_text = text[prev_end:split_point]
            entities = self.nlp.extract_entities(chunk_text)
            
            chunks.append({
                'text': chunk_text,
                'start': prev_end,
                'end': split_point,
                'entities': entities,
                'entity_count': len(entities)
            })
            
            prev_end = max(prev_end, split_point - overlap)
        
        # 处理最后一块
        if prev_end < len(text):
            chunk_text = text[prev_end:]
            entities = self.nlp.extract_entities(chunk_text)
            chunks.append({
                'text': chunk_text,
                'start': prev_end,
                'end': len(text),
                'entities': entities,
                'entity_count': len(entities)
            })
        
        return chunks
    
    def _find_split_points(
        self,
        text: str,
        max_size: int,
        min_size: int
    ) -> List[int]:
        """找到自然分割点"""
        split_points = []
        current_pos = 0
        
        # 分割符优先级：段落 > 句号 > 分号 > 逗号
        separators = ['\n\n', '\n', '。', '；', '，', ' ']
        
        while current_pos < len(text):
            target_pos = current_pos + max_size
            
            if target_pos >= len(text):
                break
            
            # 在目标位置附近找分割点
            best_split = target_pos
            
            for sep in separators:
                # 在目标位置前后寻找分割符
                search_start = max(current_pos + min_size, target_pos - 200)
                search_end = min(len(text), target_pos + 100)
                
                search_text = text[search_start:search_end]
                sep_pos = search_text.rfind(sep)
                
                if sep_pos != -1:
                    best_split = search_start + sep_pos + len(sep)
                    break
            
            split_points.append(best_split)
            current_pos = best_split
        
        return split_points


# 全局实例
nlp_extractor = NLPExtractor()
smart_chunker = SmartChunker(nlp_extractor)




