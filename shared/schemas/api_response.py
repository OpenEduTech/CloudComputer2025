"""API响应数据模型"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from .concept_node import ConceptNode
from .concept_edge import ConceptEdge


class Metadata(BaseModel):
    """元数据模型"""
    total_nodes: int = Field(..., description="总节点数")
    total_edges: int = Field(..., description="总边数")
    verified_nodes: int = Field(..., description="通过验证的节点数")
    avg_credibility: float = Field(..., description="平均可信度")
    processing_time: float = Field(..., description="处理耗时（秒）")


class GraphData(BaseModel):
    """图谱数据模型"""
    nodes: List[ConceptNode] = Field(default_factory=list, description="节点列表")
    edges: List[ConceptEdge] = Field(default_factory=list, description="边列表")
    metadata: Metadata = Field(..., description="元数据")


class APIResponse(BaseModel):
    """通用API响应模型"""
    status: str = Field(..., description="状态: success/error")
    request_id: Optional[str] = Field(None, description="请求追踪ID")
    message: Optional[str] = Field(None, description="消息")
    error_code: Optional[str] = Field(None, description="错误码")
    details: Optional[Any] = Field(None, description="详细信息")


class DiscoverResponse(APIResponse):
    """概念挖掘响应模型"""
    data: Optional[GraphData] = Field(None, description="图谱数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "request_id": "req_123456",
                "data": {
                    "nodes": [],
                    "edges": [],
                    "metadata": {
                        "total_nodes": 18,
                        "total_edges": 24,
                        "verified_nodes": 16,
                        "avg_credibility": 0.87,
                        "processing_time": 12.5
                    }
                }
            }
        }


class Evidence(BaseModel):
    """证据模型"""
    source: str = Field(..., description="来源")
    url: str = Field(..., description="证据链接")
    snippet: str = Field(..., description="相关片段")


class VerificationData(BaseModel):
    """验证数据模型"""
    credibility_score: float = Field(..., description="可信度评分")
    is_valid: bool = Field(..., description="是否有效")
    evidence: List[Evidence] = Field(default_factory=list, description="证据列表")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


class VerifyResponse(APIResponse):
    """概念验证响应模型"""
    data: Optional[VerificationData] = Field(None, description="验证数据")
