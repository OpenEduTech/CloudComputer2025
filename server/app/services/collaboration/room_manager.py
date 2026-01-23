"""
PatPat-Inconsistency-Hunter 房间管理服务
管理协作文档的房间、成员和状态
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from pydantic import BaseModel, Field
import json

from ...utils.logger import logger
from ...utils.redis_client import RedisClient, get_redis_client


class CollaborationMode(str, Enum):
    """协作模式"""
    REALTIME = "realtime"      # 实时协同编辑
    CHAPTER_LOCK = "chapter_lock"  # 分章节锁定编辑


class RoomMember(BaseModel):
    """房间成员"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    color: str = Field(..., description="用户颜色标识")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    cursor_position: Optional[int] = Field(None, description="光标位置")
    selection_start: Optional[int] = Field(None, description="选区起始")
    selection_end: Optional[int] = Field(None, description="选区结束")
    mouse_x: Optional[float] = Field(None, description="鼠标X坐标(0-1)")
    mouse_y: Optional[float] = Field(None, description="鼠标Y坐标(0-1)")
    current_chapter: Optional[str] = Field(None, description="当前编辑的章节")
    joined_at: datetime = Field(default_factory=datetime.now, description="加入时间")
    last_active: datetime = Field(default_factory=datetime.now, description="最后活跃时间")
    is_online: bool = Field(default=True, description="是否在线")


class Room(BaseModel):
    """协作房间"""
    room_id: str = Field(..., description="房间ID")
    room_name: str = Field(..., description="房间名称")
    document_title: str = Field(default="未命名文档", description="文档标题")
    mode: CollaborationMode = Field(..., description="协作模式")
    content: str = Field(default="", description="文档内容")
    content_json: Optional[Dict] = Field(default=None, description="富文本内容JSON")
    chapters: List[Dict] = Field(default_factory=list, description="章节列表")
    members: Dict[str, RoomMember] = Field(default_factory=dict, description="成员列表")
    owner_id: str = Field(..., description="房主ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    max_members: int = Field(default=10, description="最大成员数")
    is_detecting: bool = Field(default=False, description="是否正在检测冲突")
    last_detection_time: Optional[datetime] = Field(None, description="上次检测时间")
    invite_code: Optional[str] = Field(default=None, description="邀请码")
    description: str = Field(default="", description="房间描述")
    is_ended: bool = Field(default=False, description="房间是否已结束")
    status: str = Field(default="active", description="房间状态: active, ended")
    version: int = Field(default=0, description="文档版本号，用于一致性检查")
    
    class Config:
        arbitrary_types_allowed = True


class RoomManager:
    """
    房间管理器
    
    负责创建、管理和销毁协作房间
    """
    
    PREFIX_ROOM = "patpat:room:"
    PREFIX_ROOM_MEMBERS = "patpat:room_members:"
    PREFIX_USER_ROOM = "patpat:user_room:"
    
    # 用户颜色池
    USER_COLORS = [
        "#ef4444", "#f97316", "#eab308", "#22c55e", 
        "#14b8a6", "#0ea5e9", "#6366f1", "#a855f7",
        "#ec4899", "#f43f5e",
    ]
    
    def __init__(self):
        self._local_rooms: Dict[str, Room] = {}
        self._redis: Optional[RedisClient] = None
    
    async def _get_redis(self) -> RedisClient:
        """获取Redis客户端"""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def create_room(
        self,
        room_name: str,
        owner_id: str,
        owner_name: str,
        mode: CollaborationMode,
        document_title: str = "未命名文档",
        initial_content: str = "",
        owner_avatar_url: Optional[str] = None,
    ) -> Room:
        """
        创建协作房间
        
        Args:
            room_name: 房间名称
            owner_id: 房主ID
            owner_name: 房主名称
            mode: 协作模式
            document_title: 文档标题
            initial_content: 初始内容
        
        Returns:
            创建的房间对象
        """
        room_id = f"room_{uuid.uuid4().hex[:12]}"
        
        # 创建房主成员
        owner_member = RoomMember(
            user_id=owner_id,
            username=owner_name,
            color=self.USER_COLORS[0],
            avatar_url=owner_avatar_url,
        )
        
        # 解析章节（如果有内容）
        chapters = self._parse_chapters(initial_content) if initial_content else []
        
        room = Room(
            room_id=room_id,
            room_name=room_name,
            document_title=document_title,
            mode=mode,
            content=initial_content,
            chapters=chapters,
            members={owner_id: owner_member},
            owner_id=owner_id,
        )
        
        # 保存到Redis和本地缓存
        await self._save_room(room)
        self._local_rooms[room_id] = room
        
        # 记录用户所在房间
        await self._set_user_room(owner_id, room_id)
        
        logger.info(f"创建协作房间: {room_id}, 模式: {mode.value}, 房主: {owner_name}")
        return room
    
    async def get_room(self, room_id: str) -> Optional[Room]:
        """获取房间信息"""
        # 先查本地缓存
        if room_id in self._local_rooms:
            return self._local_rooms[room_id]
        
        # 从Redis获取
        redis = await self._get_redis()
        key = f"{self.PREFIX_ROOM}{room_id}"
        data = await redis.client.get(key)
        
        if data:
            room_dict = json.loads(data)
            room = Room(**room_dict)
            self._local_rooms[room_id] = room
            return room
        
        # 如果 Redis 中没有，尝试从数据库恢复
        room = await self._restore_room_from_db(room_id)
        if room:
            await self._save_room(room)  # 重新缓存到 Redis
            self._local_rooms[room_id] = room
            return room
        
        return None
    
    async def _restore_room_from_db(self, room_id: str) -> Optional[Room]:
        """从数据库恢复房间数据"""
        try:
            from ...utils.db_session import async_session_maker
            from ...models.database import CollaborationRoom, RoomMembership, User
            from sqlalchemy import select
            
            async with async_session_maker() as db:
                # 获取房间数据
                result = await db.execute(
                    select(CollaborationRoom).where(
                        CollaborationRoom.room_id == room_id,
                        CollaborationRoom.is_active == True
                    )
                )
                db_room = result.scalar_one_or_none()
                
                if not db_room:
                    return None
                
                # 获取房间成员
                members_result = await db.execute(
                    select(RoomMembership, User)
                    .join(User, RoomMembership.user_id == User.id, isouter=True)
                    .where(RoomMembership.room_id == db_room.id)
                )
                
                members = {}
                owner_user_id = None
                
                # 获取房主信息
                if db_room.owner_id:
                    owner_result = await db.execute(
                        select(User).where(User.id == db_room.owner_id)
                    )
                    owner_user = owner_result.scalar_one_or_none()
                    if owner_user:
                        owner_user_id = owner_user.user_id
                        members[owner_user.user_id] = RoomMember(
                            user_id=owner_user.user_id,
                            username=owner_user.display_name or owner_user.username,
                            color=self.USER_COLORS[0],
                            avatar_url=owner_user.avatar_url,
                            is_online=False,
                        )
                
                # 添加其他成员
                for membership, user in members_result.all():
                    if user and user.user_id not in members:
                        color_idx = len(members) % len(self.USER_COLORS)
                        members[user.user_id] = RoomMember(
                            user_id=user.user_id,
                            username=user.display_name or user.username,
                            color=membership.color or self.USER_COLORS[color_idx],
                            avatar_url=user.avatar_url,
                            is_online=False,
                        )
                
                # 构建 Room 对象
                room = Room(
                    room_id=db_room.room_id,
                    room_name=db_room.room_name,
                    document_title=db_room.document_title,
                    mode=CollaborationMode(db_room.mode),
                    content=db_room.content or "",
                    content_json=db_room.content_json,
                    chapters=db_room.chapters or [],
                    members=members,
                    owner_id=owner_user_id or "",
                    created_at=db_room.created_at,
                    updated_at=db_room.updated_at,
                    max_members=db_room.max_members,
                    invite_code=db_room.invite_code,
                    description=db_room.description or "",
                    is_ended=db_room.is_ended,
                    status="ended" if db_room.is_ended else "active",
                )
                
                logger.info(f"从数据库恢复房间: {room_id}")
                return room
                
        except Exception as e:
            logger.error(f"从数据库恢复房间失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def join_room(
        self,
        room_id: str,
        user_id: str,
        username: str,
        avatar_url: Optional[str] = None,
    ) -> Optional[Room]:
        """
        加入房间
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            username: 用户名
        
        Returns:
            房间对象或None
        """
        room = await self.get_room(room_id)
        if not room:
            logger.warning(f"房间不存在: {room_id}")
            return None
        
        if len(room.members) >= room.max_members:
            logger.warning(f"房间已满: {room_id}")
            return None
        
        # 如果用户已在房间中，更新状态
        if user_id in room.members:
            room.members[user_id].is_online = True
            room.members[user_id].last_active = datetime.now()
            if avatar_url is not None:
                room.members[user_id].avatar_url = avatar_url
        else:
            # 分配颜色
            used_colors = {m.color for m in room.members.values()}
            available_colors = [c for c in self.USER_COLORS if c not in used_colors]
            color = available_colors[0] if available_colors else self.USER_COLORS[len(room.members) % len(self.USER_COLORS)]
            
            member = RoomMember(
                user_id=user_id,
                username=username,
                color=color,
                avatar_url=avatar_url,
            )
            room.members[user_id] = member
        
        room.updated_at = datetime.now()
        await self._save_room(room)
        await self._set_user_room(user_id, room_id)
        
        logger.info(f"用户 {username} 加入房间 {room_id}")
        return room
    
    async def leave_room(self, room_id: str, user_id: str) -> bool:
        """离开房间"""
        room = await self.get_room(room_id)
        if not room or user_id not in room.members:
            return False
        
        # 标记为离线而不是删除
        room.members[user_id].is_online = False
        room.updated_at = datetime.now()
        
        # 如果是房主且所有人都离线，删除房间
        online_members = [m for m in room.members.values() if m.is_online]
        if not online_members:
            await self._delete_room(room_id)
            logger.info(f"房间 {room_id} 已删除（所有成员离开）")
        else:
            await self._save_room(room)
        
        await self._clear_user_room(user_id)
        logger.info(f"用户 {user_id} 离开房间 {room_id}")
        return True
    
    async def update_content(
        self,
        room_id: str,
        content: str,
        user_id: str,
        base_version: Optional[int] = None,
        content_json: Optional[Dict] = None,
    ) -> Tuple[bool, int]:
        """
        更新文档内容
        
        Args:
            room_id: 房间ID
            content: 新内容
            user_id: 操作用户ID
            base_version: 基础版本号（用于一致性检查）
        
        Returns:
            (是否成功, 新版本号)
        """
        room = await self.get_room(room_id)
        if not room:
            return (False, 0)
        
        # 版本一致性检查（简化的 Last-Write-Wins 策略）
        # 如果提供了 base_version 且不匹配当前版本，记录冲突但仍然接受更新
        if base_version is not None and base_version != room.version:
            logger.warning(
                f"版本冲突: room={room_id}, base={base_version}, current={room.version}, "
                f"将使用 Last-Write-Wins 策略接受更新"
            )
        
        room.content = content
        if content_json is not None:
            room.content_json = content_json
        room.version += 1  # 增加版本号
        
        # 只有实时协同模式才重新解析章节
        # 分章节锁定模式由房主手动管理章节结构，不自动覆盖
        if room.mode == CollaborationMode.REALTIME:
            room.chapters = self._parse_chapters(content)
        room.updated_at = datetime.now()
        
        if user_id in room.members:
            room.members[user_id].last_active = datetime.now()
        
        await self._save_room(room)
        return (True, room.version)
    
    async def update_chapter_content(
        self,
        room_id: str,
        chapter_id: str,
        content: str,
        user_id: str,
    ) -> bool:
        """
        更新章节内容（分章节模式）
        
        Args:
            room_id: 房间ID
            chapter_id: 章节ID
            content: 新内容
            user_id: 操作用户ID
        
        Returns:
            是否成功
        """
        room = await self.get_room(room_id)
        if not room:
            return False
        
        # 更新章节
        for chapter in room.chapters:
            if chapter["id"] == chapter_id:
                chapter["content"] = content
                break
        
        # 重建完整内容
        room.content = self._build_content_from_chapters(room.chapters)
        room.updated_at = datetime.now()
        
        if user_id in room.members:
            room.members[user_id].last_active = datetime.now()
        
        await self._save_room(room)
        return True
    
    async def update_member_cursor(
        self,
        room_id: str,
        user_id: str,
        position: int,
        selection_start: Optional[int] = None,
        selection_end: Optional[int] = None,
    ) -> bool:
        """更新成员光标位置"""
        room = await self.get_room(room_id)
        if not room or user_id not in room.members:
            return False
        
        room.members[user_id].cursor_position = position
        room.members[user_id].selection_start = selection_start
        room.members[user_id].selection_end = selection_end
        room.members[user_id].last_active = datetime.now()
        
        await self._save_room(room)
        return True
    
    async def list_rooms(self, limit: int = 20) -> List[Room]:
        """列出所有房间"""
        redis = await self._get_redis()
        rooms = []
        
        async for key in redis.client.scan_iter(match=f"{self.PREFIX_ROOM}*"):
            if len(rooms) >= limit:
                break
            data = await redis.client.get(key)
            if data:
                room_dict = json.loads(data)
                rooms.append(Room(**room_dict))
        
        return rooms
    
    def _parse_chapters(self, content: str) -> List[Dict]:
        """解析文档章节"""
        import re
        
        chapters = []
        
        # 中文章节模式
        chapter_pattern = r'^(第[一二三四五六七八九十百千\d]+章[\s:：]*.+?)$'
        
        lines = content.split('\n')
        current_chapter = None
        current_content = []
        chapter_start = 0
        
        for i, line in enumerate(lines):
            match = re.match(chapter_pattern, line.strip(), re.MULTILINE)
            if match:
                # 保存上一章
                if current_chapter:
                    chapters.append({
                        "id": f"chapter_{len(chapters) + 1}",
                        "title": current_chapter,
                        "content": '\n'.join(current_content).strip(),
                        "start_line": chapter_start,
                        "end_line": i - 1,
                    })
                
                current_chapter = match.group(1).strip()
                current_content = []
                chapter_start = i
            else:
                current_content.append(line)
        
        # 保存最后一章
        if current_chapter:
            chapters.append({
                "id": f"chapter_{len(chapters) + 1}",
                "title": current_chapter,
                "content": '\n'.join(current_content).strip(),
                "start_line": chapter_start,
                "end_line": len(lines) - 1,
            })
        
        # 如果没有识别到章节，整体作为一个章节
        if not chapters and content.strip():
            chapters.append({
                "id": "chapter_1",
                "title": "全文",
                "content": content.strip(),
                "start_line": 0,
                "end_line": len(lines) - 1,
            })
        
        return chapters
    
    def _build_content_from_chapters(self, chapters: List[Dict]) -> str:
        """从章节重建完整内容"""
        parts = []
        for chapter in chapters:
            if chapter["title"] != "全文":
                parts.append(chapter["title"])
            parts.append(chapter["content"])
        return '\n\n'.join(parts)
    
    async def _save_room(self, room: Room):
        """保存房间到Redis"""
        redis = await self._get_redis()
        key = f"{self.PREFIX_ROOM}{room.room_id}"
        
        # 转换为可序列化的字典
        room_dict = room.model_dump()
        room_dict['created_at'] = room.created_at.isoformat()
        room_dict['updated_at'] = room.updated_at.isoformat()
        if room_dict.get('last_detection_time'):
            room_dict['last_detection_time'] = room.last_detection_time.isoformat()
        
        # 转换成员
        for user_id, member in room_dict['members'].items():
            member['joined_at'] = room.members[user_id].joined_at.isoformat()
            member['last_active'] = room.members[user_id].last_active.isoformat()
        
        await redis.client.set(key, json.dumps(room_dict, ensure_ascii=False), ex=86400 * 7)
        self._local_rooms[room.room_id] = room
    
    async def _delete_room(self, room_id: str):
        """删除房间"""
        redis = await self._get_redis()
        key = f"{self.PREFIX_ROOM}{room_id}"
        await redis.client.delete(key)
        
        if room_id in self._local_rooms:
            del self._local_rooms[room_id]
    
    async def _set_user_room(self, user_id: str, room_id: str):
        """设置用户所在房间"""
        redis = await self._get_redis()
        key = f"{self.PREFIX_USER_ROOM}{user_id}"
        await redis.client.set(key, room_id, ex=86400)
    
    async def _clear_user_room(self, user_id: str):
        """清除用户所在房间"""
        redis = await self._get_redis()
        key = f"{self.PREFIX_USER_ROOM}{user_id}"
        await redis.client.delete(key)
    
    async def get_user_room(self, user_id: str) -> Optional[str]:
        """获取用户所在房间"""
        redis = await self._get_redis()
        key = f"{self.PREFIX_USER_ROOM}{user_id}"
        return await redis.client.get(key)


# 全局房间管理器实例
_room_manager: Optional[RoomManager] = None


def get_room_manager() -> RoomManager:
    """获取房间管理器单例"""
    global _room_manager
    if _room_manager is None:
        _room_manager = RoomManager()
    return _room_manager

