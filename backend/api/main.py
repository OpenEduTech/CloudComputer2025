"""
FastAPI主应用
提供REST API接口
"""
import os
import logging
import hashlib
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis.asyncio as redis
from datetime import datetime

from agent_service.agent import AgentService
from graph_service.neo4j_client import Neo4jClient

# 配置日志
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
agent_service: Optional[AgentService] = None
neo4j_client: Optional[Neo4jClient] = None
redis_client: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global agent_service, neo4j_client, redis_client
    
    # 启动时初始化
    logger.info("Initializing services...")
    
    agent_service = AgentService()
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    # 初始化Redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_client = await redis.from_url(
        f"redis://{redis_host}:{redis_port}",
        encoding="utf-8",
        decode_responses=True
    )
    
    logger.info("All services initialized successfully")
    
    yield
    
    # 关闭时清理
    logger.info("Shutting down services...")
    if neo4j_client:
        await neo4j_client.close()
    if redis_client:
        await redis_client.close()
    logger.info("All services shut down")


# 创建FastAPI应用
app = FastAPI(
    title="跨学科知识图谱智能体 API",
    description="基于LLM的跨学科知识图谱生成系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 数据模型 ============

class GenerateGraphRequest(BaseModel):
    """生成图谱请求"""
    concept: str = Field(..., description="核心概念", min_length=1, max_length=100)
    enable_validation: bool = Field(True, description="是否启用校验层")
    fast_mode: bool = Field(True, description="快速模式（只做直接验证，速度更快）")


class ExpandNodeRequest(BaseModel):
    """扩展节点请求"""
    graph_id: str = Field(..., description="图谱ID")
    node_id: str = Field(..., description="节点ID")
    enable_validation: bool = Field(True, description="是否启用校验层")
    fast_mode: bool = Field(True, description="快速模式")


class GraphResponse(BaseModel):
    """图谱响应"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None


# ============ API端点 ============

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "跨学科知识图谱智能体 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # 检查Neo4j
    try:
        if neo4j_client and neo4j_client.driver:
            await neo4j_client.driver.verify_connectivity()
            health_status["services"]["neo4j"] = "connected"
        else:
            health_status["services"]["neo4j"] = "not initialized"
    except Exception as e:
        health_status["services"]["neo4j"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # 检查Redis
    try:
        if redis_client:
            await redis_client.ping()
            health_status["services"]["redis"] = "connected"
        else:
            health_status["services"]["redis"] = "not initialized"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


@app.post("/api/graph/generate", response_model=GraphResponse)
async def generate_graph(request: GenerateGraphRequest):
    """
    生成知识图谱
    
    - **concept**: 核心概念（如"熵"、"神经网络"）
    - **enable_validation**: 是否启用校验层（推荐开启）
    - **fast_mode**: 快速模式（只做直接验证，速度提升50%）
    """
    try:
        logger.info(f"Received request to generate graph for: {request.concept}")
        
        # 生成图谱ID
        graph_id = hashlib.md5(request.concept.encode()).hexdigest()
        
        # 检查缓存
        cache_key = f"graph:{graph_id}:{request.fast_mode}"
        logger.info(f"🔍 Checking cache with key: {cache_key}")
        cached_data = await redis_client.get(cache_key)
        logger.info(f"🔍 Cache data type: {type(cached_data)}, is None: {cached_data is None}, bool: {bool(cached_data)}")
        
        if cached_data:
            logger.info(f"✅ Cache HIT! Returning cached graph for: {request.concept}")
            import json
            cached_result = json.loads(cached_data)
            # 确保返回的数据包含 graph_id，这样前端才能进行节点扩展
            return GraphResponse(
                success=True,
                message="从缓存返回",
                data={
                    "graph_id": graph_id,
                    **cached_result
                }
            )
        else:
            logger.info(f"❌ Cache MISS! Generating new graph for: {request.concept}")
        
        # 生成图谱
        result = await agent_service.generate_knowledge_graph(
            concept=request.concept,
            enable_validation=request.enable_validation,
            fast_mode=request.fast_mode
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        # 保存到Neo4j
        graph_data = result.get("graph", {})
        await neo4j_client.create_graph(
            graph_id=graph_id,
            nodes=graph_data.get("nodes", []),
            edges=graph_data.get("edges", [])
        )
        
        # 缓存结果
        import json
        cache_ttl = int(os.getenv("CACHE_TTL", "3600"))
        await redis_client.setex(
            cache_key,
            cache_ttl,
            json.dumps(result)
        )
        logger.info(f"💾 Cached graph with key: {cache_key}, TTL: {cache_ttl}s")
        
        return GraphResponse(
            success=True,
            message="图谱生成成功",
            data={
                "graph_id": graph_id,
                **result
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/{graph_id}", response_model=GraphResponse)
async def get_graph(graph_id: str):
    """
    获取已生成的知识图谱
    
    - **graph_id**: 图谱ID
    """
    try:
        logger.info(f"Fetching graph: {graph_id}")
        
        # 从Neo4j获取
        graph_data = await neo4j_client.get_graph(graph_id)
        
        if not graph_data:
            raise HTTPException(status_code=404, detail="Graph not found")
        
        return GraphResponse(
            success=True,
            message="图谱获取成功",
            data={
                "graph_id": graph_id,
                "graph": graph_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/expand", response_model=GraphResponse)
async def expand_node(request: ExpandNodeRequest):
    """
    扩展图谱节点
    
    - **graph_id**: 图谱ID
    - **node_id**: 要扩展的节点ID
    - **enable_validation**: 是否启用校验层
    - **fast_mode**: 快速模式
    """
    try:
        logger.info(f"Expanding node {request.node_id} in graph {request.graph_id}")
        
        # 获取节点信息
        graph_data = await neo4j_client.get_graph(request.graph_id)
        if not graph_data:
            raise HTTPException(status_code=404, detail="Graph not found")
        
        # 找到目标节点
        target_node = None
        for node in graph_data.get("nodes", []):
            if node["id"] == request.node_id:
                target_node = node
                break
        
        if not target_node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # 扩展概念
        expansion_result = await agent_service.expand_concept(
            concept=target_node["id"],
            domain=target_node.get("domain", "Unknown"),
            enable_validation=request.enable_validation,
            fast_mode=request.fast_mode
        )
        
        if not expansion_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=expansion_result.get("error", "Expansion failed")
            )
        
        # 构建新节点和边
        new_nodes = []
        new_edges = []
        
        for idx, relation in enumerate(expansion_result.get("expansions", [])):
            target_id = relation.get("target_concept")
            
            # 检查节点是否已存在
            node_exists = any(n["id"] == target_id for n in graph_data.get("nodes", []))
            
            if not node_exists:
                new_nodes.append({
                    "id": target_id,
                    "label": target_id,
                    "domain": relation.get("target_domain", ""),
                    "type": "related"
                })
            
            new_edges.append({
                "id": f"edge_exp_{request.node_id}_{idx}",
                "source": request.node_id,
                "target": target_id,
                "relation_type": relation.get("relation_type", ""),
                "strength": relation.get("relation_strength", 5),
                "explanation": relation.get("explanation", ""),
                "confidence": relation.get("confidence", 1.0)
            })
        
        # 保存到Neo4j
        await neo4j_client.expand_node(
            graph_id=request.graph_id,
            node_id=request.node_id,
            new_nodes=new_nodes,
            new_edges=new_edges
        )
        
        # 清除所有相关缓存（包括不同 fast_mode 的缓存）
        cache_keys = [
            f"graph:{request.graph_id}:True",
            f"graph:{request.graph_id}:False",
            f"graph:{request.graph_id}"
        ]
        for cache_key in cache_keys:
            deleted = await redis_client.delete(cache_key)
            logger.info(f"🗑️  Deleted cache key: {cache_key}, result: {deleted}")
        
        return GraphResponse(
            success=True,
            message="节点扩展成功",
            data={
                "new_nodes": new_nodes,
                "new_edges": new_edges,
                "count": len(new_nodes)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error expanding node: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/graph/{graph_id}")
async def delete_graph(graph_id: str):
    """
    删除知识图谱
    
    - **graph_id**: 图谱ID
    """
    try:
        logger.info(f"Deleting graph: {graph_id}")
        
        await neo4j_client.delete_graph(graph_id)
        
        # 清除所有相关缓存（包括不同 fast_mode 的缓存）
        cache_keys = [
            f"graph:{graph_id}:True",
            f"graph:{graph_id}:False",
            f"graph:{graph_id}"
        ]
        for cache_key in cache_keys:
            deleted = await redis_client.delete(cache_key)
            logger.info(f"🗑️  Deleted cache key: {cache_key}, result: {deleted}")
        
        return GraphResponse(
            success=True,
            message="图谱删除成功"
        )
        
    except Exception as e:
        logger.error(f"Error deleting graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graphs")
async def list_graphs():
    """列出所有图谱"""
    try:
        graph_ids = await neo4j_client.list_graphs()
        
        return GraphResponse(
            success=True,
            message=f"找到 {len(graph_ids)} 个图谱",
            data={
                "graphs": graph_ids,
                "count": len(graph_ids)
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing graphs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/export/markdown")
async def export_markdown(request: dict):
    """
    导出图谱为 Markdown 报告
    
    - **graph_data**: 图谱数据
    - **concept**: 核心概念
    """
    try:
        graph_data = request.get("graph_data", {})
        concept = request.get("concept", "未知概念")
        
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        # 统计信息
        domains = set(n.get("domain", "未知") for n in nodes)
        center_node = next((n for n in nodes if n.get("type") == "center"), None)
        
        # 生成 Markdown 报告
        markdown = f"""# 跨学科知识图谱报告

## 核心概念：{concept}

---

## 📊 图谱统计

- **节点总数**：{len(nodes)}
- **关系总数**：{len(edges)}
- **涉及学科**：{len(domains)}
- **生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 🎯 核心概念信息

"""
        
        if center_node:
            markdown += f"""**概念名称**：{center_node.get('label', center_node.get('id', ''))}

**所属学科**：{center_node.get('domain', '未知')}

**定义**：{center_node.get('definition', '暂无定义')}

"""
            if center_node.get('keywords'):
                markdown += f"**关键词**：{', '.join(center_node.get('keywords', []))}\n\n"
        
        markdown += "---\n\n## 🌍 涉及学科领域\n\n"
        
        for domain in sorted(domains):
            domain_nodes = [n for n in nodes if n.get("domain") == domain]
            markdown += f"### {domain} ({len(domain_nodes)} 个概念)\n\n"
            for node in domain_nodes:
                if node.get("type") != "center":
                    markdown += f"- **{node.get('label', node.get('id', ''))}**\n"
            markdown += "\n"
        
        markdown += "---\n\n## 🔗 跨学科关联关系\n\n"
        
        # 按源节点分组
        edges_by_source = {}
        for edge in edges:
            source = edge.get("source", "")
            if source not in edges_by_source:
                edges_by_source[source] = []
            edges_by_source[source].append(edge)
        
        for source, source_edges in edges_by_source.items():
            source_node = next((n for n in nodes if n.get("id") == source), None)
            if source_node:
                markdown += f"### {source_node.get('label', source)}\n\n"
                for edge in source_edges:
                    target_node = next((n for n in nodes if n.get("id") == edge.get("target")), None)
                    if target_node:
                        markdown += f"**→ {target_node.get('label', edge.get('target'))}** ({target_node.get('domain', '未知')})\n\n"
                        markdown += f"- **关系类型**：{edge.get('relation_type', '未知')}\n"
                        markdown += f"- **关系强度**：{edge.get('strength', 0)}/10\n"
                        markdown += f"- **置信度**：{edge.get('confidence', 0):.2f}\n"
                        markdown += f"- **说明**：{edge.get('explanation', '暂无说明')}\n\n"
                markdown += "---\n\n"
        
        markdown += """## 📌 使用说明

本报告由跨学科知识图谱智能体自动生成，展示了不同学科领域之间的概念关联。

- 关系强度范围：1-10，数值越大表示关联越紧密
- 置信度范围：0-1，表示关系的可靠程度
- 所有关系均经过 AI 验证层校验

---

*生成工具：跨学科知识图谱智能体*  
*技术栈：FastAPI + Neo4j + Redis + React*
"""
        
        return {
            "success": True,
            "data": {
                "markdown": markdown,
                "filename": f"{concept}_知识图谱报告.md"
            }
        }
        
    except Exception as e:
        logger.error(f"Error exporting markdown: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/api/graph/summary")
async def generate_summary(request: dict):
    """
    生成图谱智能摘要
    
    - **graph_data**: 图谱数据
    - **concept**: 核心概念
    """
    try:
        graph_data = request.get("graph_data", {})
        concept = request.get("concept", "未知概念")
        
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        # 统计信息
        domains = list(set(n.get("domain", "未知") for n in nodes))
        center_node = next((n for n in nodes if n.get("type") == "center"), None)
        
        # 构建提示词
        prompt = f"""你是一个跨学科知识专家。请为以下知识图谱生成一个简洁而富有洞察力的摘要。

核心概念：{concept}
所属学科：{center_node.get('domain', '未知') if center_node else '未知'}
定义：{center_node.get('definition', '暂无') if center_node else '暂无'}

图谱统计：
- 节点总数：{len(nodes)}
- 关系总数：{len(edges)}
- 涉及学科：{', '.join(domains)}

关联的概念：
{chr(10).join([f"- {n.get('label', n.get('id', ''))} ({n.get('domain', '未知')})" for n in nodes if n.get('type') != 'center'][:10])}

请生成一个包含以下内容的摘要（200字以内）：
1. 核心概念的简要说明
2. 主要的跨学科关联特点
3. 最有价值的洞察或发现

请用自然、流畅的语言，避免列表式表达。直接输出摘要文本，不要其他内容。
"""
        
        # 调用 LLM 生成摘要
        from agent_service.llm_client import LLMClient
        llm_client = LLMClient()
        
        summary = await llm_client.call_llm(
            prompt=prompt,
            system_prompt="你是一个专业的知识图谱分析专家，擅长提炼跨学科知识的核心洞察。",
            temperature=0.7
        )
        
        # 提取关键节点（度最高的节点）
        node_degrees = {}
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            node_degrees[source] = node_degrees.get(source, 0) + 1
            node_degrees[target] = node_degrees.get(target, 0) + 1
        
        # 排序获取前3个关键节点
        sorted_nodes = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[:3]
        key_concepts = []
        for node_id, degree in sorted_nodes:
            node = next((n for n in nodes if n.get("id") == node_id), None)
            if node:
                key_concepts.append({
                    "concept": node.get("label", node_id),
                    "domain": node.get("domain", "未知"),
                    "connections": degree
                })
        
        return {
            "success": True,
            "data": {
                "summary": summary.strip(),
                "key_concepts": key_concepts,
                "stats": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "domains_count": len(domains),
                    "domains": domains
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/wikipedia/{concept}")
async def get_wikipedia_summary(concept: str):
    """
    获取维基百科摘要
    
    - **concept**: 概念名称
    """
    try:
        import aiohttp
        import urllib.parse
        import traceback
        
        # URL 编码概念名称
        encoded_concept = urllib.parse.quote(concept)
        
        # 维基百科 API 端点
        wiki_url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{encoded_concept}"
        
        logger.info(f"Fetching Wikipedia summary for: {concept}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(wiki_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    logger.info(f"Wikipedia API response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # 提取关键信息
                        result = {
                            "title": data.get("title", concept),
                            "extract": data.get("extract", ""),
                            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                            "thumbnail": data.get("thumbnail", {}).get("source", "") if "thumbnail" in data else "",
                            "description": data.get("description", "")
                        }
                        
                        return {
                            "success": True,
                            "data": result
                        }
                    elif response.status == 404:
                        return {
                            "success": False,
                            "message": "未找到相关维基百科条目"
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"维基百科 API 返回错误: {response.status}"
                        }
            except aiohttp.ClientError as ce:
                logger.error(f"aiohttp ClientError: {str(ce)}")
                return {
                    "success": False,
                    "message": f"网络请求失败: {str(ce)}"
                }
                    
    except Exception as e:
        logger.error(f"Error fetching Wikipedia summary: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": str(e) if str(e) else "未知错误"
        }



@app.post("/api/graph/rate")
async def rate_graph(request: dict):
    """
    为图谱评分
    
    - **concept**: 概念名称
    - **rating**: 评分（1-5）
    """
    try:
        concept = request.get("concept")
        rating = request.get("rating")
        
        if not concept or not rating:
            return {
                "success": False,
                "message": "缺少必要参数"
            }
        
        if not (1 <= rating <= 5):
            return {
                "success": False,
                "message": "评分必须在 1-5 之间"
            }
        
        import json
        
        # 获取当前评分数据
        rating_key = f"rating:{concept}"
        rating_data = await redis_client.get(rating_key)
        
        if rating_data:
            data = json.loads(rating_data)
            total_rating = data["total_rating"] + rating
            vote_count = data["vote_count"] + 1
        else:
            total_rating = rating
            vote_count = 1
        
        avg_rating = round(total_rating / vote_count, 1)
        
        # 保存评分数据
        new_data = {
            "total_rating": total_rating,
            "vote_count": vote_count,
            "avg_rating": avg_rating
        }
        
        await redis_client.set(rating_key, json.dumps(new_data))
        
        logger.info(f"⭐ Graph rated: {concept} - {rating} stars (avg: {avg_rating}, votes: {vote_count})")
        
        return {
            "success": True,
            "data": {
                "avg_rating": avg_rating,
                "vote_count": vote_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error rating graph: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": str(e)
        }


@app.get("/api/graph/rating/{concept}")
async def get_graph_rating(concept: str):
    """
    获取图谱评分
    
    - **concept**: 概念名称
    """
    try:
        import json
        
        rating_key = f"rating:{concept}"
        rating_data = await redis_client.get(rating_key)
        
        if rating_data:
            data = json.loads(rating_data)
            return {
                "success": True,
                "data": data
            }
        else:
            return {
                "success": True,
                "data": {
                    "avg_rating": 0,
                    "vote_count": 0
                }
            }
        
    except Exception as e:
        logger.error(f"Error getting graph rating: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/api/literature/{concept}")
async def get_literature_recommendations(concept: str):
    """
    获取文献推荐（学术论文）
    
    - **concept**: 概念名称
    """
    try:
        import aiohttp
        import urllib.parse
        
        # URL 编码概念名称
        encoded_concept = urllib.parse.quote(concept)
        
        # Semantic Scholar API（免费，无需Key）
        api_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded_concept}&limit=5&fields=title,authors,year,abstract,url,citationCount,venue"
        
        # 检查缓存
        import json
        cache_key = f"literature:{concept}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            logger.info(f"✅ Literature Cache HIT for: {concept}")
            return json.loads(cached_data)
        
        logger.info(f"❌ Literature Cache MISS for: {concept}")
        logger.info(f"Fetching literature for: {concept}")
        
        # 添加请求头
        headers = {
            'User-Agent': 'KnowledgeGraphAgent/1.0 (Educational Project)',
            'Accept': 'application/json'
        }
        
        papers = []
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    logger.info(f"Semantic Scholar API response status: {response.status}")
                    
                    if response.status == 429:
                        return {
                            "success": False,
                            "message": "学术API请求过于频繁，请稍后再试（建议等待1-2分钟）"
                        }
                    elif response.status == 200:
                        data = await response.json()
                        
                        # 提取论文信息
                        for paper in data.get("data", [])[:5]:
                            authors = [author.get("name", "") for author in paper.get("authors", [])]
                            
                            papers.append({
                                "title": paper.get("title", ""),
                                "authors": authors,
                                "year": paper.get("year"),
                                "abstract": paper.get("abstract", "")[:300] + "..." if paper.get("abstract") else "暂无摘要",
                                "url": paper.get("url", ""),
                                "citations": paper.get("citationCount", 0),
                                "venue": paper.get("venue", "")
                            })
                        
                        result = {
                            "success": True,
                            "data": {
                                "papers": papers,
                                "count": len(papers)
                            }
                        }
                        
                        # 缓存结果（24小时）
                        import json
                        await redis_client.setex(
                            cache_key,
                            86400,  # 24小时
                            json.dumps(result)
                        )
                        logger.info(f"💾 Cached literature for: {concept}")
                        
                        return result
                    else:
                        return {
                            "success": False,
                            "message": f"API 返回错误: {response.status}"
                        }
            except aiohttp.ClientError as ce:
                logger.error(f"aiohttp ClientError: {str(ce)}")
                return {
                    "success": False,
                    "message": f"网络请求失败: {str(ce)}"
                }
                    
    except Exception as e:
        logger.error(f"Error fetching literature: {str(e)}")
        return {
            "success": False,
            "message": str(e) if str(e) else "未知错误"
        }
