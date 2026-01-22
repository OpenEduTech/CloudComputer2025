"""
PatPat-Inconsistency-Hunter Pydantic 数据模式定义
定义API请求/响应和内部数据传输的数据结构
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待处理
    EXTRACTING = "extracting"    # 正在提取事实
    DETECTING = "detecting"      # 正在检测冲突
    VERIFYING = "verifying"      # 正在验证事实
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


class ConflictType(str, Enum):
    """冲突类型枚举"""
    NUMERICAL = "numerical"              # 数值冲突
    TEMPORAL = "temporal"                # 时间冲突
    ENTITY = "entity"                    # 实体冲突
    CATEGORICAL = "categorical"          # 类别冲突
    DEFINITION = "definition"            # 定义冲突
    LOGICAL = "logical"                  # 逻辑冲突
    SPATIAL = "spatial"                  # 空间冲突


class DocumentInput(BaseModel):
    """文档输入模型"""
    content: str = Field(..., description="文档内容", min_length=100)
    title: Optional[str] = Field(None, description="文档标题")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="文档元数据")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "这是一篇长文档的内容...",
                "title": "研究报告",
                "metadata": {"author": "张三", "date": "2024-01-01"}
            }
        }
    )


class DocumentChunk(BaseModel):
    """文档分块模型"""
    chunk_id: str = Field(..., description="分块唯一标识")
    content: str = Field(..., description="分块内容")
    start_position: int = Field(..., description="在原文中的起始位置")
    end_position: int = Field(..., description="在原文中的结束位置")
    chapter: Optional[str] = Field(None, description="所属章节")
    section: Optional[str] = Field(None, description="所属小节")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class Fact(BaseModel):
    """事实模型"""
    fact_id: str = Field(..., description="事实唯一标识")
    content: str = Field(..., description="事实内容")
    fact_type: str = Field(..., description="事实类型（数据/日期/结论/人名等）")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="提取置信度")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class FactWithSource(Fact):
    """带来源的事实模型"""
    source_chunk_id: str = Field(..., description="来源分块ID")
    source_text: str = Field(..., description="原文文本片段")
    source_position: tuple[int, int] = Field(..., description="在原文中的位置 (start, end)")
    chapter: Optional[str] = Field(None, description="所属章节")
    section: Optional[str] = Field(None, description="所属小节")
    is_image_source: bool = Field(False, description="是否来自图片")
    image_id: Optional[str] = Field(None, description="来源图片ID")
    image_description: Optional[str] = Field(None, description="图片描述")
    
    @property
    def location_description(self) -> str:
        """获取位置描述"""
        parts = []
        if self.chapter:
            parts.append(f"第{self.chapter}章")
        if self.section:
            parts.append(f"第{self.section}节")
        return " > ".join(parts) if parts else "文档开头"


class ConflictPair(BaseModel):
    """冲突对模型"""
    conflict_id: str = Field(..., description="冲突唯一标识")
    fact_a: FactWithSource = Field(..., description="冲突事实A")
    fact_b: FactWithSource = Field(..., description="冲突事实B")
    conflict_type: ConflictType = Field(..., description="冲突类型")
    severity: float = Field(..., ge=0.0, le=1.0, description="冲突严重程度 (0-1)")
    description: str = Field(..., description="冲突描述")
    suggestion: Optional[str] = Field(None, description="修正建议")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class VerificationResult(BaseModel):
    """溯源验证结果模型"""
    conflict_id: str = Field(..., description="关联的冲突ID")
    is_verified: bool = Field(..., description="是否已验证")
    correct_fact: Optional[str] = Field(None, description="正确的事实（如果能确定）")
    source_url: Optional[str] = Field(None, description="来源URL")
    source_description: Optional[str] = Field(None, description="来源描述")
    verification_reasoning: str = Field(..., description="验证推理过程")
    confidence: float = Field(..., ge=0.0, le=1.0, description="验证置信度")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class ConflictReport(BaseModel):
    """冲突报告模型"""
    conflict: ConflictPair = Field(..., description="冲突对信息")
    verification: Optional[VerificationResult] = Field(None, description="验证结果")
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class AnalysisTask(BaseModel):
    """分析任务模型"""
    task_id: str = Field(..., description="任务唯一标识")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="任务进度（百分比）")
    current_step: str = Field(default="初始化", description="当前步骤描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    model_config = ConfigDict(validate_assignment=True)


class AnalysisResult(BaseModel):
    """完整分析结果模型"""
    task_id: str = Field(..., description="任务ID")
    document_title: Optional[str] = Field(None, description="文档标题")
    document_length: int = Field(..., description="文档长度（字符数）")
    total_chunks: int = Field(..., description="文档分块数")
    total_facts: int = Field(..., description="提取的事实总数")
    total_conflicts: int = Field(..., description="检测到的冲突数")
    verified_conflicts: int = Field(default=0, description="已验证的冲突数")
    
    facts: List[FactWithSource] = Field(default_factory=list, description="所有提取的事实")
    conflicts: List[ConflictReport] = Field(default_factory=list, description="所有冲突报告")
    
    analysis_time: float = Field(..., description="分析耗时（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    # 统计信息
    conflict_type_distribution: Dict[str, int] = Field(
        default_factory=dict, 
        description="冲突类型分布"
    )
    severity_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="严重程度分布"
    )
    
    model_config = ConfigDict(validate_assignment=True)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        return {
            "document_title": self.document_title,
            "document_length": self.document_length,
            "total_facts": self.total_facts,
            "total_conflicts": self.total_conflicts,
            "conflict_rate": round(self.total_conflicts / max(self.total_facts, 1) * 100, 2),
            "analysis_time": round(self.analysis_time, 2),
        }


class FactExtractionResponse(BaseModel):
    """事实提取响应模型（LLM结构化输出）"""
    
    class FactItem(BaseModel):
        """单个事实项"""
        content: str = Field(..., description="事实内容")
        fact_type: str = Field(..., description="事实类型")
        source_text: str = Field(..., description="原文依据")
        confidence: float = Field(default=1.0, description="置信度")
    
    reasoning: str = Field(default="", description="提取推理过程")
    facts: List[FactItem] = Field(default_factory=list, description="提取的事实列表")
    
    @model_validator(mode='before')
    @classmethod
    def filter_invalid_facts(cls, data):
        """过滤掉无效的事实对象（空对象或缺少必要字段的对象）"""
        if isinstance(data, dict) and 'facts' in data:
            valid_facts = []
            for fact in data.get('facts', []):
                if isinstance(fact, dict) and fact.get('content') and fact.get('fact_type') and fact.get('source_text'):
                    valid_facts.append(fact)
            data['facts'] = valid_facts
        return data


class ConflictDetectionResponse(BaseModel):
    """冲突检测响应模型（LLM结构化输出）"""
    
    class ConflictItem(BaseModel):
        """单个冲突项"""
        fact_a_id: str = Field(..., description="事实A的ID")
        fact_b_id: str = Field(..., description="事实B的ID")
        conflict_type: str = Field(..., description="冲突类型")
        severity: float = Field(..., description="严重程度")
        description: str = Field(..., description="冲突描述")
        suggestion: str = Field(..., description="修正建议")
    
    reasoning: str = Field(..., description="检测推理过程")
    has_conflict: bool = Field(..., description="是否存在冲突")
    conflicts: List[ConflictItem] = Field(default_factory=list, description="冲突列表")


class VerificationResponse(BaseModel):
    """验证响应模型（LLM结构化输出）"""
    reasoning: str = Field(..., description="验证推理过程")
    is_verified: bool = Field(..., description="是否能够验证")
    correct_fact: Optional[str] = Field(None, description="正确的事实")
    confidence: float = Field(..., description="验证置信度")
    source_description: Optional[str] = Field(None, description="来源描述")

