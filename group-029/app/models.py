import json
from pydantic import BaseModel, Field, field_validator


# 会话创建返回
class SessionCreateResponse(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    chunk_count: int = Field(..., description="切分后的片段数量")
    name: str = Field(..., description="会话名称")
    source_type: str = Field(..., description="数据来源类型（pdf/text）")


class SessionItem(BaseModel):
    session_id: str
    name: str
    created_at: str
    last_accessed: str
    chunk_count: int


class SessionListResponse(BaseModel):
    sessions: list[SessionItem]


class SessionDeleteResponse(BaseModel):
    session_id: str
    deleted: bool


class SessionRenameRequest(BaseModel):
    name: str = Field(..., description="新的会话名称")


class SessionRenameResponse(BaseModel):
    session_id: str
    name: str
    updated: bool


class SessionTextCreateRequest(BaseModel):
    text: str = Field(..., description="原始文本内容")
    name: str | None = Field(None, description="可选会话名称")


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    message: str = Field(..., description="用户问题")


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


# 出题请求
class QuestionGenerateRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    num_mcq: int = Field(3, description="选择题数量")
    num_short: int = Field(2, description="简答题数量")
    difficulty_ratio: str = Field("4:4:2", description="难度梯度比例（易:中:难）")


# 题目结构
class QuestionItem(BaseModel):
    qid: str
    qtype: str
    question: str
    options: list[str] | None = None
    answer: str
    explanation: str
    evidence: list[str]
    difficulty: str | None = None

    @field_validator("options", mode="before")
    @classmethod
    def _coerce_options(cls, v):
        # 兼容模型将 options 输出成字符串的情况
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return v

    @field_validator("evidence", mode="before")
    @classmethod
    def _coerce_evidence(cls, v):
        # 兼容 evidence 被输出为 JSON 字符串的情况
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return v


# 出题结果
class QuestionGenerateResponse(BaseModel):
    session_id: str
    questions: list[QuestionItem]


# 判卷请求
class GradeRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    questions: list[QuestionItem] = Field(..., description="题目列表")
    answers: list[dict] = Field(..., description="答案列表，元素包含 qid 与 answer")


# 判卷结果项
class GradeItem(BaseModel):
    qid: str
    is_correct: bool
    score: float
    explanation: str


# 判卷结果
class GradeResponse(BaseModel):
    session_id: str
    total_score: float
    items: list[GradeItem]


class RecordResponse(BaseModel):
    session_id: str
    questions: list[dict]
    answers: list[dict]
    grade: dict | None = None


# 错题本查询结果
class WrongbookResponse(BaseModel):
    session_id: str
    total_wrong: int
    items: list[dict]
    summary: dict


class WrongbookDeleteResponse(BaseModel):
    record_id: str
    deleted: bool
