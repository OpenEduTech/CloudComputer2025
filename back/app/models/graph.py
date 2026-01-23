from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Node(BaseModel):
    """节点模型"""
    id: str = Field(..., description="节点唯一ID")
    label: str = Field(..., description="显示名称")
    field: str = Field(..., description="所属学科域")
    type: str = Field(..., description="节点类型")
    aliases: Optional[List[str]] = None
    summary: Optional[str] = None
    importance: Optional[float] = None
    confidence: Optional[float] = None

class Edge(BaseModel):
    """边模型"""
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    relation: str = Field(..., description="关系短语")
    relation_type: str = Field(..., description="关系类型")
    confidence: float = Field(..., ge=0, le=1, description="可信度")
    evidence: str = Field(..., description="关系依据")

class GraphMeta(BaseModel):
    """图谱元数据"""
    core_concept: str
    normalized_concept: str
    domains: List[str]
    version: str
    generated_at: datetime
    stats: Dict[str, int]
    notes: Optional[str] = None

class GraphData(BaseModel):
    """图谱数据"""
    meta: GraphMeta
    nodes: List[Node]
    edges: List[Edge]

class GraphBuildRequest(BaseModel):
    """生成图谱请求"""
    concept: str = Field(..., min_length=1, max_length=50, description="核心概念词")
    force_refresh: bool = Field(False, description="强制重新生成")
    domains: Optional[List[str]] = Field(None, description="指定学科域")

class GraphBuildResponse(BaseModel):
    """生成图谱响应"""
    task_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None
    result: Optional[Dict[str, Any]] = None  # 添加result字段用于缓存命中

class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending, running, success, failed
    progress: Optional[int] = None  # 0-100
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime