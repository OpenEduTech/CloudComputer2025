"""
PatPat-Inconsistency-Hunter Redis 客户端
实现事实黑板和任务状态管理
"""

import json
from typing import Any, Dict, List, Optional
from datetime import timedelta
import redis.asyncio as redis

from ..config import settings
from .logger import logger


class RedisClient:
    """
    Redis 客户端
    
    用于实现事实黑板（Fact Blackboard）和任务状态管理
    支持并发状态下的统一事实注册
    """
    
    # Redis键前缀
    PREFIX_TASK = "patpat:task:"
    PREFIX_FACT = "patpat:fact:"
    PREFIX_CONFLICT = "patpat:conflict:"
    PREFIX_DOCUMENT = "patpat:document:"
    PREFIX_PROGRESS = "patpat:progress:"
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        password: str = None,
        db: int = None,
    ):
        """
        初始化Redis客户端
        
        Args:
            host: Redis主机
            port: Redis端口
            password: Redis密码
            db: Redis数据库
        """
        self._host = host or settings.REDIS_HOST
        self._port = port or settings.REDIS_PORT
        self._password = password or settings.REDIS_PASSWORD
        self._db = db or settings.REDIS_DB
        self._client: Optional[redis.Redis] = None
    
    async def connect(self):
        """建立Redis连接"""
        try:
            self._client = redis.Redis(
                host=self._host,
                port=self._port,
                password=self._password,
                db=self._db,
                decode_responses=True,
            )
            await self._client.ping()
            logger.info(f"Redis连接成功: {self._host}:{self._port}")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    async def disconnect(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            logger.info("Redis连接已关闭")
    
    @property
    def client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self._client is None:
            raise RuntimeError("Redis客户端未初始化，请先调用connect()")
        return self._client
    
    # ==================== 任务管理 ====================
    
    async def save_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        expire: int = 86400,  # 24小时
    ):
        """
        保存任务状态
        
        Args:
            task_id: 任务ID
            task_data: 任务数据
            expire: 过期时间（秒）
        """
        key = f"{self.PREFIX_TASK}{task_id}"
        await self.client.set(key, json.dumps(task_data, ensure_ascii=False), ex=expire)
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务数据或None
        """
        key = f"{self.PREFIX_TASK}{task_id}"
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def update_task_progress(
        self,
        task_id: str,
        progress: float,
        step: str,
        status: str = None,
    ):
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度百分比
            step: 当前步骤
            status: 任务状态
        """
        task_data = await self.get_task(task_id)
        if task_data:
            task_data["progress"] = progress
            task_data["current_step"] = step
            if status:
                task_data["status"] = status
            await self.save_task(task_id, task_data)
        
        # 同时发布进度更新事件
        await self.publish_progress(task_id, progress, step)
    
    async def delete_task(self, task_id: str):
        """删除任务"""
        key = f"{self.PREFIX_TASK}{task_id}"
        await self.client.delete(key)
    
    # ==================== 事实黑板 ====================
    
    async def register_fact(
        self,
        task_id: str,
        fact_id: str,
        fact_data: Dict[str, Any],
    ):
        """
        注册事实到黑板
        
        Args:
            task_id: 任务ID
            fact_id: 事实ID
            fact_data: 事实数据
        """
        # 存储事实详情
        fact_key = f"{self.PREFIX_FACT}{task_id}:{fact_id}"
        await self.client.set(fact_key, json.dumps(fact_data, ensure_ascii=False))
        
        # 添加到任务的事实集合
        set_key = f"{self.PREFIX_FACT}{task_id}:set"
        await self.client.sadd(set_key, fact_id)
    
    async def register_facts_batch(
        self,
        task_id: str,
        facts: List[Dict[str, Any]],
    ):
        """
        批量注册事实
        
        Args:
            task_id: 任务ID
            facts: 事实列表
        """
        pipe = self.client.pipeline()
        set_key = f"{self.PREFIX_FACT}{task_id}:set"
        
        for fact in facts:
            fact_id = fact.get("fact_id")
            if fact_id:
                fact_key = f"{self.PREFIX_FACT}{task_id}:{fact_id}"
                pipe.set(fact_key, json.dumps(fact, ensure_ascii=False))
                pipe.sadd(set_key, fact_id)
        
        await pipe.execute()
    
    async def get_fact(self, task_id: str, fact_id: str) -> Optional[Dict[str, Any]]:
        """获取单个事实"""
        key = f"{self.PREFIX_FACT}{task_id}:{fact_id}"
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def get_all_facts(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的所有事实"""
        set_key = f"{self.PREFIX_FACT}{task_id}:set"
        fact_ids = await self.client.smembers(set_key)
        
        facts = []
        for fact_id in fact_ids:
            fact = await self.get_fact(task_id, fact_id)
            if fact:
                facts.append(fact)
        
        return facts
    
    async def get_facts_count(self, task_id: str) -> int:
        """获取事实数量"""
        set_key = f"{self.PREFIX_FACT}{task_id}:set"
        return await self.client.scard(set_key)
    
    # ==================== 冲突管理 ====================
    
    async def register_conflict(
        self,
        task_id: str,
        conflict_id: str,
        conflict_data: Dict[str, Any],
    ):
        """注册冲突"""
        conflict_key = f"{self.PREFIX_CONFLICT}{task_id}:{conflict_id}"
        await self.client.set(conflict_key, json.dumps(conflict_data, ensure_ascii=False))
        
        set_key = f"{self.PREFIX_CONFLICT}{task_id}:set"
        await self.client.sadd(set_key, conflict_id)
    
    async def register_conflicts_batch(
        self,
        task_id: str,
        conflicts: List[Dict[str, Any]],
    ):
        """批量注册冲突"""
        pipe = self.client.pipeline()
        set_key = f"{self.PREFIX_CONFLICT}{task_id}:set"
        
        for conflict in conflicts:
            conflict_id = conflict.get("conflict_id")
            if conflict_id:
                conflict_key = f"{self.PREFIX_CONFLICT}{task_id}:{conflict_id}"
                pipe.set(conflict_key, json.dumps(conflict, ensure_ascii=False))
                pipe.sadd(set_key, conflict_id)
        
        await pipe.execute()
    
    async def get_all_conflicts(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的所有冲突"""
        set_key = f"{self.PREFIX_CONFLICT}{task_id}:set"
        conflict_ids = await self.client.smembers(set_key)
        
        conflicts = []
        for conflict_id in conflict_ids:
            key = f"{self.PREFIX_CONFLICT}{task_id}:{conflict_id}"
            data = await self.client.get(key)
            if data:
                conflicts.append(json.loads(data))
        
        return conflicts
    
    # ==================== 进度发布/订阅 ====================
    
    async def publish_progress(
        self,
        task_id: str,
        progress: float,
        step: str,
    ):
        """发布进度更新"""
        channel = f"{self.PREFIX_PROGRESS}{task_id}"
        message = json.dumps({
            "progress": progress,
            "step": step,
        })
        await self.client.publish(channel, message)
    
    async def subscribe_progress(self, task_id: str):
        """订阅进度更新"""
        channel = f"{self.PREFIX_PROGRESS}{task_id}"
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
    
    # ==================== 清理 ====================
    
    async def cleanup_task_data(self, task_id: str):
        """清理任务相关的所有数据"""
        patterns = [
            f"{self.PREFIX_TASK}{task_id}",
            f"{self.PREFIX_FACT}{task_id}:*",
            f"{self.PREFIX_CONFLICT}{task_id}:*",
        ]
        
        for pattern in patterns:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self.client.delete(*keys)


# 全局Redis客户端实例
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """获取Redis客户端单例"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client


async def close_redis_client():
    """关闭Redis客户端"""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.disconnect()
        _redis_client = None

