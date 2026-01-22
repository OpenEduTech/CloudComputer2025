"""
PatPat-Inconsistency-Hunter 章节锁定服务
实现分章节锁定编辑的功能
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import json

from ...utils.logger import logger
from ...utils.redis_client import RedisClient, get_redis_client


class ChapterLock(BaseModel):
    """章节锁"""
    chapter_id: str = Field(..., description="章节ID")
    room_id: str = Field(..., description="房间ID")
    user_id: str = Field(..., description="锁定用户ID")
    username: str = Field(..., description="锁定用户名")
    locked_at: datetime = Field(default_factory=datetime.now, description="锁定时间")
    expires_at: datetime = Field(..., description="过期时间")
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        return datetime.now() > self.expires_at


class ChapterLockService:
    """
    章节锁定服务
    
    实现分章节锁定编辑的功能，确保同一章节同一时间只能被一个人编辑
    """
    
    PREFIX_LOCK = "patpat:chapter_lock:"
    DEFAULT_LOCK_DURATION = 300  # 默认锁定5分钟
    MAX_LOCK_DURATION = 1800     # 最长锁定30分钟
    
    def __init__(self):
        self._redis: Optional[RedisClient] = None
        self._local_locks: Dict[str, ChapterLock] = {}
    
    async def _get_redis(self) -> RedisClient:
        """获取Redis客户端"""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    def _get_lock_key(self, room_id: str, chapter_id: str) -> str:
        """获取锁的Redis键"""
        return f"{self.PREFIX_LOCK}{room_id}:{chapter_id}"
    
    async def acquire_lock(
        self,
        room_id: str,
        chapter_id: str,
        user_id: str,
        username: str,
        duration: int = None,
    ) -> Optional[ChapterLock]:
        """
        获取章节锁
        
        Args:
            room_id: 房间ID
            chapter_id: 章节ID
            user_id: 用户ID
            username: 用户名
            duration: 锁定时长（秒）
        
        Returns:
            锁对象或None（如果获取失败）
        """
        duration = min(duration or self.DEFAULT_LOCK_DURATION, self.MAX_LOCK_DURATION)
        
        redis = await self._get_redis()
        key = self._get_lock_key(room_id, chapter_id)
        
        # 检查是否已被锁定
        existing_lock = await self.get_lock(room_id, chapter_id)
        if existing_lock:
            if existing_lock.user_id == user_id:
                # 续期
                return await self.renew_lock(room_id, chapter_id, user_id, duration)
            elif not existing_lock.is_expired:
                # 被其他人锁定
                logger.warning(f"章节 {chapter_id} 已被 {existing_lock.username} 锁定")
                return None
        
        # 创建新锁
        now = datetime.now()
        lock = ChapterLock(
            chapter_id=chapter_id,
            room_id=room_id,
            user_id=user_id,
            username=username,
            locked_at=now,
            expires_at=now + timedelta(seconds=duration),
        )
        
        # 使用Redis事务确保原子性
        lock_data = {
            "chapter_id": chapter_id,
            "room_id": room_id,
            "user_id": user_id,
            "username": username,
            "locked_at": lock.locked_at.isoformat(),
            "expires_at": lock.expires_at.isoformat(),
        }
        
        # 使用SETNX确保原子性
        success = await redis.client.set(
            key,
            json.dumps(lock_data, ensure_ascii=False),
            nx=True,  # 仅当键不存在时设置
            ex=duration,
        )
        
        if success:
            self._local_locks[key] = lock
            logger.info(f"用户 {username} 获取章节 {chapter_id} 的锁")
            return lock
        
        # 再次检查，可能是过期的锁
        existing = await redis.client.get(key)
        if existing:
            existing_data = json.loads(existing)
            if existing_data["user_id"] == user_id:
                # 是自己的锁，更新
                await redis.client.set(
                    key,
                    json.dumps(lock_data, ensure_ascii=False),
                    ex=duration,
                )
                self._local_locks[key] = lock
                return lock
        
        return None
    
    async def release_lock(
        self,
        room_id: str,
        chapter_id: str,
        user_id: str,
    ) -> bool:
        """
        释放章节锁
        
        Args:
            room_id: 房间ID
            chapter_id: 章节ID
            user_id: 用户ID
        
        Returns:
            是否成功释放
        """
        redis = await self._get_redis()
        key = self._get_lock_key(room_id, chapter_id)
        
        # 检查锁是否属于该用户
        existing = await redis.client.get(key)
        if existing:
            lock_data = json.loads(existing)
            if lock_data["user_id"] != user_id:
                logger.warning(f"用户 {user_id} 无权释放章节 {chapter_id} 的锁")
                return False
        
        # 删除锁
        await redis.client.delete(key)
        if key in self._local_locks:
            del self._local_locks[key]
        
        logger.info(f"用户 {user_id} 释放章节 {chapter_id} 的锁")
        return True
    
    async def renew_lock(
        self,
        room_id: str,
        chapter_id: str,
        user_id: str,
        duration: int = None,
    ) -> Optional[ChapterLock]:
        """
        续期章节锁
        
        Args:
            room_id: 房间ID
            chapter_id: 章节ID
            user_id: 用户ID
            duration: 续期时长（秒）
        
        Returns:
            更新后的锁对象或None
        """
        duration = min(duration or self.DEFAULT_LOCK_DURATION, self.MAX_LOCK_DURATION)
        
        redis = await self._get_redis()
        key = self._get_lock_key(room_id, chapter_id)
        
        existing = await redis.client.get(key)
        if not existing:
            return None
        
        lock_data = json.loads(existing)
        if lock_data["user_id"] != user_id:
            return None
        
        # 更新过期时间
        now = datetime.now()
        lock_data["expires_at"] = (now + timedelta(seconds=duration)).isoformat()
        
        await redis.client.set(
            key,
            json.dumps(lock_data, ensure_ascii=False),
            ex=duration,
        )
        
        lock = ChapterLock(
            chapter_id=chapter_id,
            room_id=room_id,
            user_id=user_id,
            username=lock_data["username"],
            locked_at=datetime.fromisoformat(lock_data["locked_at"]),
            expires_at=datetime.fromisoformat(lock_data["expires_at"]),
        )
        self._local_locks[key] = lock
        
        return lock
    
    async def get_lock(
        self,
        room_id: str,
        chapter_id: str,
    ) -> Optional[ChapterLock]:
        """
        获取章节锁信息
        
        Args:
            room_id: 房间ID
            chapter_id: 章节ID
        
        Returns:
            锁对象或None
        """
        redis = await self._get_redis()
        key = self._get_lock_key(room_id, chapter_id)
        
        data = await redis.client.get(key)
        if not data:
            return None
        
        lock_data = json.loads(data)
        return ChapterLock(
            chapter_id=lock_data["chapter_id"],
            room_id=lock_data["room_id"],
            user_id=lock_data["user_id"],
            username=lock_data["username"],
            locked_at=datetime.fromisoformat(lock_data["locked_at"]),
            expires_at=datetime.fromisoformat(lock_data["expires_at"]),
        )
    
    # 别名方法，兼容不同调用
    async def get_chapter_lock(
        self,
        room_id: str,
        chapter_id: str,
    ) -> Optional[ChapterLock]:
        """get_lock的别名"""
        return await self.get_lock(room_id, chapter_id)
    
    async def get_room_locks(self, room_id: str) -> List[ChapterLock]:
        """
        获取房间内所有章节锁
        
        Args:
            room_id: 房间ID
        
        Returns:
            锁列表
        """
        redis = await self._get_redis()
        pattern = f"{self.PREFIX_LOCK}{room_id}:*"
        
        locks = []
        async for key in redis.client.scan_iter(match=pattern):
            data = await redis.client.get(key)
            if data:
                lock_data = json.loads(data)
                lock = ChapterLock(
                    chapter_id=lock_data["chapter_id"],
                    room_id=lock_data["room_id"],
                    user_id=lock_data["user_id"],
                    username=lock_data["username"],
                    locked_at=datetime.fromisoformat(lock_data["locked_at"]),
                    expires_at=datetime.fromisoformat(lock_data["expires_at"]),
                )
                if not lock.is_expired:
                    locks.append(lock)
        
        return locks
    
    async def release_user_locks(self, room_id: str, user_id: str) -> int:
        """
        释放用户在房间内的所有锁
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
        
        Returns:
            释放的锁数量
        """
        locks = await self.get_room_locks(room_id)
        released = 0
        
        for lock in locks:
            if lock.user_id == user_id:
                await self.release_lock(room_id, lock.chapter_id, user_id)
                released += 1
        
        return released
    
    async def can_edit_chapter(
        self,
        room_id: str,
        chapter_id: str,
        user_id: str,
    ) -> bool:
        """
        检查用户是否可以编辑章节
        
        Args:
            room_id: 房间ID
            chapter_id: 章节ID
            user_id: 用户ID
        
        Returns:
            是否可以编辑
        """
        lock = await self.get_lock(room_id, chapter_id)
        if not lock:
            return True
        if lock.is_expired:
            return True
        return lock.user_id == user_id


# 全局章节锁定服务实例
_chapter_lock_service: Optional[ChapterLockService] = None


def get_chapter_lock_service() -> ChapterLockService:
    """获取章节锁定服务单例"""
    global _chapter_lock_service
    if _chapter_lock_service is None:
        _chapter_lock_service = ChapterLockService()
    return _chapter_lock_service

