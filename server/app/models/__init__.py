"""
PatPat-Inconsistency-Hunter 数据模型模块
定义系统中使用的所有数据结构
"""

from .schemas import (
    DocumentInput,
    DocumentChunk,
    Fact,
    FactWithSource,
    ConflictPair,
    ConflictReport,
    VerificationResult,
    AnalysisResult,
    AnalysisTask,
    TaskStatus,
)

from .database import (
    Base,
    Document,
    FactRecord,
    ConflictRecord,
    AnalysisHistory,
)

__all__ = [
    # Schemas
    "DocumentInput",
    "DocumentChunk",
    "Fact",
    "FactWithSource",
    "ConflictPair",
    "ConflictReport",
    "VerificationResult",
    "AnalysisResult",
    "AnalysisTask",
    "TaskStatus",
    # Database Models
    "Base",
    "Document",
    "FactRecord",
    "ConflictRecord",
    "AnalysisHistory",
]

