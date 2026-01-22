"""概念关系边数据模型"""

from pydantic import BaseModel, Field


class ConceptEdge(BaseModel):
    """概念关系边数据模型"""
    
    source: str = Field(
        ..., 
        description="源节点ID"
    )
    target: str = Field(
        ..., 
        description="目标节点ID"
    )
    relation: str = Field(
        ..., 
        description="关系类型"
    )
    weight: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="关联强度"
    )
    reasoning: str = Field(
        ..., 
        description="关联原因"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "entropy_xinxilun",
                "target": "shannon_entropy_xinxilun",
                "relation": "is_foundation_of",
                "weight": 0.92,
                "reasoning": "香农熵是信息论中熵的具体定义"
            }
        }
