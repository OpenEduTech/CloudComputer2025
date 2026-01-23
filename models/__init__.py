from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional

@dataclass
class Chunk:
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

@dataclass
class Question:
    question_id: str
    question_type: str
    content: str
    options: List[str]  # 选择题选项
    correct_answer: str
    explanation: str
    difficulty: str
    source_chunks: List[str]
    tags: List[str]
    metadata: Dict[str, Any]

@dataclass
class EvaluationResult:
    is_correct: bool
    score: float  # 0-100分
    feedback: str
    detailed_explanation: str
    suggested_improvement: str
    confidence_score: float  # 评估置信度
    mistakes: List[str]  # 具体错误点