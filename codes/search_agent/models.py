from typing import List
from pydantic import BaseModel, Field

class QueryRewrite(BaseModel):
    queries: List[str] = Field(description="改写后的查询列表")

class ArticleScore(BaseModel):
    title: str = Field(description="文章标题")
    url: str = Field(description="文章链接")
    snippet: str = Field(description="文章摘要")
    score: float = Field(description="相关性评分(0-10)")

class ContentChunk(BaseModel):
    title: str = Field(description="文章标题")
    url: str = Field(description="文章链接")
    chunks: List[str] = Field(description="文章内容块")