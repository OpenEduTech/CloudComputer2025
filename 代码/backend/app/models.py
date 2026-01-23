from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class PPTElement(BaseModel):
    """PPT元素"""
    type: str
    content: str
    position: Dict[str, float]

class PPTImage(BaseModel):
    """PPT图片"""
    format: str
    data: str  # base64编码
    width: Optional[int] = None
    height: Optional[int] = None

class PageContent(BaseModel):
    """单页内容"""
    page_num: int
    title: str = ""
    text: str = ""
    elements: List[PPTElement] = []
    images: List[PPTImage] = []
    extensions: Dict[str, Any] = Field(default_factory=dict)
    external_references: Dict[str, Any] = Field(default_factory=dict)
    vector_id: Optional[int] = None

class TOCItem(BaseModel):
    """目录项"""
    page: int
    title: str
    level: int = 1

class PPTStructure(BaseModel):
    """PPT结构"""
    filename: str
    total_pages: int
    toc: List[TOCItem] = []
    pages: List[PageContent]

class ExtensionSection(BaseModel):
    """扩展内容章节"""
    section_title: str
    content: str
    type: str = "text"  # text, code, formula, example

class PPTRequest(BaseModel):
    """PPT处理请求"""
    file_url: Optional[str] = None
    local_file: Optional[str] = None
    extension_depth: str = "normal"  # simple, normal, deep
    include_sources: List[str] = ["wikipedia", "arxiv"]
    generate_questions: bool = True

class ExtendResponse(BaseModel):
    """扩展响应"""
    ppt_id: str
    original_filename: str
    total_pages: int
    pages: List[PageContent]
    structure: PPTStructure
    processing_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

class SearchResult(BaseModel):
    """搜索结果"""
    id: str
    score: float
    content: str
    title: str
    page_num: int
    metadata: Dict[str, Any]

class LLMRequest(BaseModel):
    """LLM请求"""
    content: str
    task: str = "extend"  # extend, summarize, qa, check_facts
    parameters: Dict[str, Any] = Field(default_factory=dict)