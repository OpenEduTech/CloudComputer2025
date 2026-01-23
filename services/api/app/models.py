from typing import List, Optional
from pydantic import BaseModel, Field


class MaterialCreate(BaseModel):
    user_id: str = Field(..., description="Logical owner of the material")
    topic: Optional[str] = Field(None, description="Optional topic tag")
    content: str = Field(..., description="Plain text content of the material")
    memory_title: Optional[str] = Field(None, description="Optional inline memory title")
    memory_content: Optional[str] = Field(None, description="Optional inline memory content")
    memory_tags: Optional[List[str]] = Field(None, description="Optional inline memory tags")


class MaterialUpdate(BaseModel):
    topic: Optional[str] = None
    content: Optional[str] = None


class MaterialItem(BaseModel):
    material_id: str
    user_id: str
    topic: Optional[str]
    content: str


class QuizQuestion(BaseModel):
    id: str
    type: str = Field(..., description="mcq or short")
    stem: str
    options: Optional[List[str]] = None
    answer_key: Optional[str] = None
    rationale: Optional[str] = None
    difficulty: str = Field(..., description="easy|medium|hard")


class Quiz(BaseModel):
    quiz_id: str
    user_id: str
    topic: Optional[str]
    questions: List[QuizQuestion]


class QuizRequest(BaseModel):
    user_id: str
    topic: Optional[str] = None
    difficulty_span: List[str] = Field(default_factory=lambda: ["easy", "medium", "hard"], description="Ordered difficulties to include")
    num_questions: int = Field(default=4, ge=2, le=10)


class AnswerItem(BaseModel):
    question_id: str
    answer: str


class GradeRequest(BaseModel):
    user_id: str
    quiz_id: str
    answers: List[AnswerItem]


class GradeFeedback(BaseModel):
    question_id: str
    correct: bool
    rationale: str
    suggested_review: Optional[str] = None


class GradeResponse(BaseModel):
    user_id: str
    quiz_id: str
    score: float
    feedback: List[GradeFeedback]


class WeaknessEntry(BaseModel):
    quiz_id: Optional[str] = None
    question_id: str
    stem: str
    last_incorrect_answer: str
    expected: Optional[str] = None
    suggested_review: Optional[str] = None
    appeal_status: Optional[str] = None  # pending | upheld | rejected
    appeal_rationale: Optional[str] = None
    appeal_updated_correct: Optional[bool] = None


class WeaknessBook(BaseModel):
    user_id: str
    entries: List[WeaknessEntry]


class MemoryCreate(BaseModel):
    user_id: str
    title: str
    content: str
    tags: Optional[List[str]] = None


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class MemoryItem(BaseModel):
    memory_id: str
    user_id: str
    title: str
    content: str
    tags: Optional[List[str]] = None


class QuizSubmission(BaseModel):
    submission_id: str
    user_id: str
    quiz_id: str
    answers: List[AnswerItem]
    feedback: List[GradeFeedback]
    score: float
    created_at: str


class AppealRequest(BaseModel):
    user_id: str
    quiz_id: str
    question_id: str


class AppealResult(BaseModel):
    quiz_id: str
    question_id: str
    correct: bool
    rationale: str
