from pydantic import BaseModel, Field
from typing import Optional, List, Union, Any
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    type: str # "multiple_choice" or "short_answer"
    content: str
    options: Optional[List[str]] = None # For MC
    correct_answer: str # The standard answer
    explanation: Optional[str] = None
    difficulty: str # "easy", "medium", "hard"
    knowledge_point: str

class QuizBase(BaseModel):
    title: str
    user_id: Optional[PyObjectId] = None

class QuizCreate(QuizBase):
    pass

class QuizInDB(QuizBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    questions: List[Question] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

class Answer(BaseModel):
    question_id: str
    user_answer: str # Text or Image URL

class QuizSubmission(BaseModel):
    quiz_id: str
    answers: List[Answer]

class GradingResult(BaseModel):
    question_id: str
    is_correct: bool
    score: float
    feedback: str
    error_type: Optional[str] = None # "concept", "logic", "expression"
    analysis: str

class QuizResult(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    quiz_id: PyObjectId
    user_id: PyObjectId
    submission: QuizSubmission
    results: List[GradingResult]
    overall_analysis: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
