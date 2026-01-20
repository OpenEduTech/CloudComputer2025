from pydantic import BaseModel, Field


# 会话创建返回
class SessionCreateResponse(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    chunk_count: int = Field(..., description="切分后的片段数量")


# 出题请求
class QuestionGenerateRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    num_mcq: int = Field(3, description="选择题数量")
    num_short: int = Field(2, description="简答题数量")


# 题目结构
class QuestionItem(BaseModel):
    qid: str
    qtype: str
    question: str
    options: list[str] | None = None
    answer: str
    explanation: str
    evidence: list[str]


# 出题结果
class QuestionGenerateResponse(BaseModel):
    session_id: str
    questions: list[QuestionItem]
