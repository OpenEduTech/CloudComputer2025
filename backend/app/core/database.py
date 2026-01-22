"""
数据库连接管理
"""
import asyncio
import chromadb
from chromadb.config import Settings as ChromaSettings
import redis.asyncio as redis
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# 全局连接实例
chroma_client: Optional[chromadb.Client] = None
redis_client: Optional[redis.Redis] = None


async def init_db():
    """初始化数据库连接"""
    global chroma_client, redis_client
    
    try:
        # 初始化ChromaDB
        logger.info("初始化ChromaDB连接...")
        chroma_client = None
        for attempt in range(1, 31):
            try:
                # 连接到 docker-compose 中的 chromadb 服务（HTTP API）
                candidate = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                # 触发一次轻量请求，尽早暴露连接问题
                candidate.heartbeat()
                chroma_client = candidate
                logger.info("ChromaDB连接成功")
                break
            except Exception as e:
                logger.warning(f"ChromaDB连接失败(第{attempt}/30次): {e}")
                await asyncio.sleep(min(2 * attempt, 10))
        if chroma_client is None:
            logger.error("ChromaDB多次重试仍不可用，服务将以降级模式启动（相关接口可能不可用）")
        
        # 初始化Redis
        logger.info("初始化Redis连接...")
        redis_client = None
        for attempt in range(1, 31):
            try:
                candidate = await redis.from_url(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await candidate.ping()
                redis_client = candidate
                logger.info("Redis连接成功")
                break
            except Exception as e:
                logger.warning(f"Redis连接失败(第{attempt}/30次): {e}")
                await asyncio.sleep(min(2 * attempt, 10))
        if redis_client is None:
            logger.error("Redis多次重试仍不可用，服务将以降级模式启动（相关接口可能不可用）")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        # 避免因外部依赖偶发不可用导致 API 进程直接退出
        return


async def close_db():
    """关闭数据库连接"""
    global redis_client
    
    try:
        if redis_client:
            await redis_client.close()
            logger.info("Redis连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")


def get_chroma_client() -> chromadb.Client:
    """获取ChromaDB客户端"""
    if chroma_client is None:
        raise RuntimeError("ChromaDB未初始化")
    return chroma_client


async def get_redis_client() -> redis.Redis:
    """获取Redis客户端"""
    if redis_client is None:
        raise RuntimeError("Redis未初始化")
    return redis_client
