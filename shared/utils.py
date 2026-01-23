"""共享工具函数"""

import re
import uuid
from typing import List
from .constants import Discipline


def generate_request_id() -> str:
    """生成请求追踪ID"""
    return f"req_{uuid.uuid4().hex[:12]}"


def generate_node_id(concept: str, discipline: str) -> str:
    """
    生成节点ID
    格式: {概念名拼音}_{学科拼音}
    """
    # 简单处理：移除特殊字符，转小写
    concept_clean = re.sub(r'[^\w\s]', '', concept).replace(' ', '_').lower()
    discipline_pinyin = Discipline.PINYIN.get(discipline, "unknown")
    return f"{concept_clean}_{discipline_pinyin}"


def validate_disciplines(disciplines: List[str]) -> bool:
    """验证学科列表是否有效"""
    return all(d in Discipline.ALL for d in disciplines)


def calculate_avg_credibility(nodes: List) -> float:
    """计算平均可信度"""
    if not nodes:
        return 0.0
    
    total = sum(node.credibility if hasattr(node, 'credibility') else 0.0 for node in nodes)
    return round(total / len(nodes), 2)


def pinyin_to_chinese(pinyin: str) -> str:
    """拼音转中文学科名（反向映射）"""
    pinyin_to_discipline = {v: k for k, v in Discipline.PINYIN.items()}
    return pinyin_to_discipline.get(pinyin, "未知")
