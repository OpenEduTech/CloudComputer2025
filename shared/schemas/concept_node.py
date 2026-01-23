"""概念节点数据模型"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


class ConceptNode(BaseModel):
    """概念节点数据模型"""
    
    id: str = Field(
        ..., 
        description="唯一标识，格式: {概念名}_{学科拼音}",
        min_length=1,
        max_length=200
    )
    label: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="概念名称"
    )
    discipline: str = Field(
        ..., 
        description="所属学科"
    )
    definition: str = Field(
        ..., 
        max_length=500, 
        description="概念定义（最多500字）"
    )
    credibility: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="可信度分数"
    )
    source: Optional[Literal["Wikipedia", "LLM", "Arxiv", "Manual"]] = Field(
        default="LLM",
        description="定义来源：Wikipedia/LLM/Arxiv/Manual"
    )
    metadata: Optional[dict] = Field(
        default=None, 
        description="额外元数据"
    )
    
    @field_validator('definition', mode='before')
    @classmethod
    def truncate_definition(cls, v: str) -> str:
        """确保定义不超过500字符"""
        if v and len(v) > 500:
            return v[:497] + "..."
        return v or ""
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "entropy_xinxilun",
                "label": "熵",
                "discipline": "信息论",
                "definition": "信息的不确定性度量，由香农在1948年提出",
                "credibility": 0.95,
                "source": "Wikipedia",
                "metadata": {
                    "wikipedia_url": "https://zh.wikipedia.org/wiki/熵_(信息论)",
                    "keywords": ["信息", "不确定性", "香农"]
                }
            }
        }
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "entropy_xinxilun",
                "label": "熵",
                "discipline": "信息论",
                "definition": "信息的不确定性度量",
                "credibility": 0.95,
                "metadata": {
                    "wikipedia_url": "https://zh.wikipedia.org/wiki/熵_(信息论)",
                    "keywords": ["信息", "不确定性", "香农"]
                }
            }
        }
