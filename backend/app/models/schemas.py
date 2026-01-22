"""
数据模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class QuestionType(str, Enum):
    """题目类型"""
    CHOICE = "choice"  # 选择题
    SHORT_ANSWER = "short_answer"  # 简答题
    TRUE_FALSE = "true_false"  # 判断题


class DifficultyLevel(str, Enum):
    """难度等级"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ========== PPT相关模型 ==========

class PPTUploadResponse(BaseModel):
    """PPT上传响应"""
    file_id: str
    filename: str
    file_size: int
    upload_time: datetime
    message: str


class PPTSlide(BaseModel):
    """PPT单页内容"""
    slide_number: int
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: List[str] = []
    body: List[str] = []
    images: List[str] = []
    image_descriptions: List[str] = []
    ocr_texts: List[str] = []
    notes: Optional[str] = None


class PPTParseResponse(BaseModel):
    """PPT解析响应"""
    file_id: str
    total_slides: int
    slides: List[PPTSlide]
    metadata: Dict[str, Any] = {}
    markdown: str | None = None


# ========== 知识扩充相关模型 ==========

class KnowledgeExpansionRequest(BaseModel):
    """知识扩充请求"""
    file_id: str
    slide_number: Optional[int] = None
    query: str = Field(..., description="要扩充的知识点")
    max_length: int = Field(500, description="扩充内容最大长度")
    include_external: bool = Field(True, description="是否包含外部资源")
    user_id: str = "default"


class ExternalResource(BaseModel):
    """外部资源"""
    source: str  # Wikipedia, Arxiv等
    title: str
    url: str
    summary: str


class KnowledgeExpansion(BaseModel):
    """知识扩充结果"""
    query: str
    expansion: str
    formulas: List[str] = []
    code_examples: List[Dict[str, str]] = []
    external_resources: List[ExternalResource] = []
    related_topics: List[str] = []
    llm_validation: Dict[str, Any] | None = None
    markdown: str | None = None


# ========== 题目相关模型 ==========

class QuestionOption(BaseModel):
    """选择题选项"""
    key: str  # A, B, C, D
    value: str


class Question(BaseModel):
    """题目"""
    question_id: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    content: str
    options: Optional[List[QuestionOption]] = None  # 选择题选项
    correct_answer: str
    explanation: str
    related_slide: Optional[int] = None
    tags: List[str] = []


class GenerateQuestionsRequest(BaseModel):
    """生成题目请求"""
    file_id: str
    num_questions: int = Field(5, ge=1, le=20, description="生成题目数量")
    question_types: List[QuestionType] = [QuestionType.CHOICE]
    difficulty_levels: List[DifficultyLevel] = [DifficultyLevel.MEDIUM]
    slide_numbers: Optional[List[int]] = None
    focus_query: Optional[str] = Field(None, description="知识点定位查询")
    top_k: int = Field(3, ge=1, le=10, description="向量检索返回数量")
    strict_context: bool = Field(True, description="是否严格基于上下文出题")


class GenerateQuestionsResponse(BaseModel):
    """生成题目响应"""
    file_id: str
    questions: List[Question]
    llm_validation: Dict[str, Any] | None = None


class SubmitAnswerRequest(BaseModel):
    """提交答案请求"""
    question_id: str
    user_answer: str
    user_id: str = "default"


class AnswerEvaluation(BaseModel):
    """答案评估"""
    question_id: str
    is_correct: bool
    score: float  # 0-100
    user_answer: str
    correct_answer: str
    detailed_feedback: str
    improvement_suggestions: List[str] = []
    semantic_similarity: Optional[float] = None
    error_type: Optional[str] = None
    alignment_score: Optional[float] = None
    alignment_summary: Optional[str] = None
    llm_validation: Dict[str, Any] | None = None


# ========== 错题本相关模型 ==========

class MistakeRecord(BaseModel):
    """错题记录"""
    mistake_id: str
    user_id: str
    question: Question
    user_answer: str
    evaluation: AnswerEvaluation
    created_at: datetime
    reviewed: bool = False
    review_count: int = 0


class MistakeStats(BaseModel):
    """错题统计"""
    user_id: str
    total_mistakes: int
    by_difficulty: Dict[str, int]
    by_type: Dict[str, int]
    weak_topics: List[str]
    improvement_rate: float


# ========== 小灶纠偏相关模型 ==========

class RemediationRequest(BaseModel):
    """小灶纠偏请求"""
    question_id: str
    user_id: str = "default"
    # 兼容旧字段（前端不再传）
    user_profile: Optional[str] = None
    focus_topic: Optional[str] = None


class RemediationResponse(BaseModel):
    """小灶纠偏响应"""
    explain: str
    contrast: str
    practice: Dict[str, str]
    transfer: Dict[str, str]
    tips: List[str] = []
    markdown: str | None = None


# ========== 通用响应模型 ==========

class StandardResponse(BaseModel):
    """标准响应"""
    success: bool
    message: str
    data: Optional[Any] = None
