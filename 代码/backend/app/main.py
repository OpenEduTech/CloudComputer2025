from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from typing import List, Dict, Any
import uuid
import json

from app.ppt_parser import PPTParser
from app.vector_store import VectorStore
from app.llm_client import LLMClient
from app.search_client import SearchClient
from app.models import PPTRequest, ExtendResponse, PageContent

app = FastAPI(title="PPT知识扩展智能体", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局组件
ppt_parser = PPTParser()
vector_store = VectorStore()
llm_client = LLMClient()
search_client = SearchClient()

@app.post("/api/ppt/upload", response_model=ExtendResponse)
async def upload_and_extend_ppt(file: UploadFile = File(...)):
    """
    上传PPT文件并自动扩展知识
    """
    try:
        # 1. 保存上传文件
        file_id = str(uuid.uuid4())
        file_path = f"temp/{file_id}_{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 2. 解析PPT结构
        ppt_structure = await ppt_parser.parse_ppt(file_path)
        
        # 3. 逐页处理（异步并行）
        tasks = []
        for page in ppt_structure["pages"]:
            task = process_page_content(page, file_id)
            tasks.append(task)
        
        extended_pages = await asyncio.gather(*tasks)
        
        # 4. 构建响应
        response = ExtendResponse(
            ppt_id=file_id,
            original_filename=file.filename,
            total_pages=len(extended_pages),
            pages=extended_pages,
            structure=ppt_structure
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_page_content(page_data: Dict, file_id: str) -> PageContent:
    """
    处理单页PPT内容
    """
    # 1. 提取文本内容
    text_content = page_data.get("text", "")
    if not text_content:
        return PageContent(**page_data)
    
    # 2. 存入向量数据库
    vector_id = vector_store.add_document(
        text=text_content,
        metadata={
            "ppt_id": file_id,
            "page_num": page_data["page_num"],
            "title": page_data.get("title", "")
        }
    )
    
    # 3. 获取相似内容（用于扩展）
    similar_chunks = vector_store.search_similar(text_content, top_k=3)
    
    # 4. 调用LLM进行知识扩展
    llm_extensions = await llm_client.extend_knowledge(
        content=text_content,
        context=similar_chunks
    )
    
    # 5. 外部搜索补充
    search_results = await search_client.search_external(
        query=page_data.get("title", text_content[:50])
    )
    
    # 6. 合并结果
    return PageContent(
        **page_data,
        extensions=llm_extensions,
        external_references=search_results,
        vector_id=vector_id
    )

@app.get("/api/ppt/{ppt_id}")
async def get_ppt_details(ppt_id: str):
    """获取PPT处理详情"""
    # 从数据库或缓存获取
    return {"ppt_id": ppt_id, "status": "processed"}

@app.get("/api/search/semantic")
async def semantic_search(query: str, top_k: int = 5):
    """语义搜索PPT内容"""
    results = vector_store.search_similar(query, top_k=top_k)
    return {"query": query, "results": results}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "ppt-knowledge-extender"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)