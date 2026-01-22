"""
知识扩充API
"""
from fastapi import APIRouter, HTTPException
import logging
import json
from datetime import datetime

from app.models.schemas import KnowledgeExpansionRequest, KnowledgeExpansion
from app.agents.knowledge_agent import KnowledgeExpansionAgent
from app.core.database import get_chroma_client, get_redis_client
from app.parsers.ppt_parser import DocumentIndexer

logger = logging.getLogger(__name__)
router = APIRouter()

knowledge_agent = KnowledgeExpansionAgent()


def _knowledge_expansion_to_markdown(expansion: KnowledgeExpansion) -> str:
    lines: list[str] = []
    title = (expansion.query or "知识扩充").strip() or "知识扩充"
    lines.append(f"# 知识扩充：{title}")
    lines.append("")

    if (expansion.expansion or "").strip():
        lines.append("## 详细解释")
        lines.append((expansion.expansion or "").strip())
        lines.append("")

    formulas = expansion.formulas or []
    if formulas:
        cleaned = [str(f).strip() for f in formulas if str(f).strip()]
        if cleaned:
            lines.append("## 相关公式")
            for f in cleaned:
                lines.append(f"- {f}")
            lines.append("")

    code_examples = expansion.code_examples or []
    if code_examples:
        lines.append("## 代码示例")
        for ex in code_examples:
            try:
                lang = (ex.get("language") if isinstance(ex, dict) else "") or ""
                desc = (ex.get("description") if isinstance(ex, dict) else "") or ""
                code = (ex.get("code") if isinstance(ex, dict) else "") or ""
                if desc.strip():
                    lines.append(f"### {desc.strip()}")
                fence_lang = lang.strip() if lang else ""
                lines.append(f"```{fence_lang}")
                lines.append(code.rstrip())
                lines.append("```")
                lines.append("")
            except Exception:
                continue

    related = expansion.related_topics or []
    if related:
        cleaned = [str(t).strip() for t in related if str(t).strip()]
        if cleaned:
            lines.append("## 相关主题")
            for t in cleaned:
                lines.append(f"- {t}")
            lines.append("")

    resources = expansion.external_resources or []
    if resources:
        lines.append("## 外部资源")
        for r in resources:
            try:
                source = (r.source or "").strip()
                title2 = (r.title or "").strip()
                url = (r.url or "").strip()
                summary = (r.summary or "").strip()
                head = f"[{title2}]({url})" if url and title2 else (url or title2)
                if source:
                    lines.append(f"- **{source}**：{head}")
                else:
                    lines.append(f"- {head}")
                if summary:
                    lines.append(f"  - {summary}")
            except Exception:
                continue
        lines.append("")

    return "\n".join(lines).strip() + "\n"


@router.post("/expand", response_model=KnowledgeExpansion)
async def expand_knowledge(request: KnowledgeExpansionRequest):
    """
    扩充知识点
    """
    try:
        # 从向量数据库检索相关内容作为上下文
        chroma_client = get_chroma_client()
        indexer = DocumentIndexer(chroma_client)
        
        search_results = await indexer.search_similar(
            query=request.query,
            file_id=request.file_id,
            top_k=3
        )
        
        # 构建上下文
        context = ""
        if search_results and search_results.get("documents"):
            context = "\n\n".join(search_results["documents"][0])
        
        # 调用Agent扩充知识
        expansion = await knowledge_agent.expand_knowledge(
            query=request.query,
            context=context,
            max_length=request.max_length,
            include_external=request.include_external
        )

        # 同步生成 Markdown 版本（用于下载/笔记留存）
        try:
            md = _knowledge_expansion_to_markdown(expansion)
            expansion = expansion.model_copy(update={"markdown": md})
        except Exception as e:
            logger.warning(f"生成知识扩充 Markdown 失败: {e}")
        
        logger.info(f"知识扩充成功: {request.query}")

        # 记录扩充历史
        try:
            redis_client = await get_redis_client()
            history_item = {
                "file_id": request.file_id,
                "query": request.query,
                "expansion": expansion.expansion[:300],
                "created_at": datetime.now().isoformat(),
                "user_id": request.user_id
            }
            await redis_client.lpush(
                f"history:knowledge:{request.user_id}",
                json.dumps(history_item, ensure_ascii=False)
            )
            await redis_client.ltrim(f"history:knowledge:{request.user_id}", 0, 49)
        except Exception as e:
            logger.warning(f"记录知识扩充历史失败: {e}")
        
        return expansion
        
    except Exception as e:
        logger.error(f"知识扩充失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_knowledge(file_id: str, query: str, top_k: int = 5):
    """
    语义搜索PPT内容
    """
    try:
        chroma_client = get_chroma_client()
        indexer = DocumentIndexer(chroma_client)
        
        results = await indexer.search_similar(
            query=query,
            file_id=file_id,
            top_k=top_k
        )
        
        # 格式化返回结果
        formatted_results = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                
                formatted_results.append({
                    "content": doc,
                    "metadata": metadata,
                    "relevance": 1 - distance  # 转换为相关度分数
                })
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results
        }
        
    except Exception as e:
        logger.error(f"语义搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/external-search")
async def external_search(query: str):
    """外部权威资源搜索（多维检索）"""
    try:
        resources = await knowledge_agent._fetch_external_resources(query)
        return {
            "success": True,
            "query": query,
            "resources": [r.model_dump() for r in resources]
        }
    except Exception as e:
        logger.error(f"外部搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_knowledge_history(limit: int = 20, user_id: str = "default"):
    """获取知识扩充历史"""
    try:
        redis_client = await get_redis_client()
        items = await redis_client.lrange(f"history:knowledge:{user_id}", 0, max(limit - 1, 0))
        history = []
        for item in items or []:
            try:
                history.append(json.loads(item))
            except Exception:
                continue
        return {"success": True, "items": history}
    except Exception as e:
        logger.error(f"获取知识扩充历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
