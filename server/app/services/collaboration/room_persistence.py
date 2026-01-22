"""
PatPat-Inconsistency-Hunter 房间数据持久化服务
将协作房间数据同步到PostgreSQL数据库
"""

import json
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...utils.logger import logger
from ...models.database import (
    User,
    CollaborationRoom,
    RoomMembership,
    EditHistory,
    ChapterLockRecord,
)
from .room_manager import Room, RoomMember, CollaborationMode


class RoomPersistenceService:
    """
    房间持久化服务
    
    负责将Redis中的房间数据同步到PostgreSQL数据库
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def save_room(self, room: Room, owner_db_id: int = None) -> CollaborationRoom:
        """
        保存房间到数据库
        
        Args:
            room: 房间对象
            owner_db_id: 房主的数据库ID（可选）
        
        Returns:
            数据库房间对象
        """
        # 查找现有房间
        db_room = await self.get_room_by_room_id(room.room_id)
        
        if db_room:
            # 更新现有房间
            db_room.room_name = room.room_name
            db_room.document_title = room.document_title
            db_room.mode = room.mode.value
            db_room.content = room.content
            db_room.content_json = getattr(room, "content_json", None)
            db_room.chapters = room.chapters
            db_room.max_members = room.max_members
            db_room.last_activity_at = datetime.now()
            db_room.updated_at = datetime.now()
            # 更新邀请码和描述
            if hasattr(room, 'invite_code') and room.invite_code:
                db_room.invite_code = room.invite_code
            if hasattr(room, 'description') and room.description:
                db_room.description = room.description
        else:
            # 创建新房间
            db_room = CollaborationRoom(
                room_id=room.room_id,
                room_name=room.room_name,
                document_title=room.document_title,
                mode=room.mode.value,
                content=room.content,
                content_json=getattr(room, "content_json", None),
                chapters=room.chapters,
                owner_id=owner_db_id,
                max_members=room.max_members,
                invite_code=room.invite_code if hasattr(room, 'invite_code') else None,
                description=room.description if hasattr(room, 'description') else "",
            )
            self.db.add(db_room)
        
        await self.db.commit()
        await self.db.refresh(db_room)
        
        logger.info(f"房间已保存到数据库: {room.room_id}")
        return db_room
    
    async def get_room_by_room_id(self, room_id: str) -> Optional[CollaborationRoom]:
        """根据房间ID获取数据库房间"""
        result = await self.db.execute(
            select(CollaborationRoom).where(CollaborationRoom.room_id == room_id)
        )
        return result.scalar_one_or_none()
    
    async def get_room_by_id(self, db_id: int) -> Optional[CollaborationRoom]:
        """根据数据库ID获取房间"""
        result = await self.db.execute(
            select(CollaborationRoom).where(CollaborationRoom.id == db_id)
        )
        return result.scalar_one_or_none()
    
    async def list_user_rooms(self, user_db_id: int) -> List[CollaborationRoom]:
        """
        获取用户参与的所有房间
        
        Args:
            user_db_id: 用户数据库ID
        
        Returns:
            房间列表
        """
        # 用户拥有的房间
        owned_result = await self.db.execute(
            select(CollaborationRoom)
            .where(CollaborationRoom.owner_id == user_db_id)
            .where(CollaborationRoom.is_active == True)
        )
        owned_rooms = list(owned_result.scalars().all())
        
        # 用户参与的房间
        membership_result = await self.db.execute(
            select(RoomMembership)
            .where(RoomMembership.user_id == user_db_id)
        )
        memberships = membership_result.scalars().all()
        
        member_room_ids = [m.room_id for m in memberships]
        if member_room_ids:
            member_rooms_result = await self.db.execute(
                select(CollaborationRoom)
                .where(CollaborationRoom.id.in_(member_room_ids))
                .where(CollaborationRoom.is_active == True)
            )
            member_rooms = list(member_rooms_result.scalars().all())
        else:
            member_rooms = []
        
        # 合并去重
        all_rooms = {r.room_id: r for r in owned_rooms}
        for r in member_rooms:
            if r.room_id not in all_rooms:
                all_rooms[r.room_id] = r
        
        return list(all_rooms.values())
    
    async def list_public_rooms(self, limit: int = 20) -> List[CollaborationRoom]:
        """获取公开房间列表"""
        result = await self.db.execute(
            select(CollaborationRoom)
            .where(CollaborationRoom.is_public == True)
            .where(CollaborationRoom.is_active == True)
            .order_by(CollaborationRoom.last_activity_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_all_active_rooms(self, limit: int = 50) -> List[CollaborationRoom]:
        """获取所有活跃房间"""
        result = await self.db.execute(
            select(CollaborationRoom)
            .where(CollaborationRoom.is_active == True)
            .order_by(CollaborationRoom.last_activity_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def deactivate_room(self, room_id: str) -> bool:
        """停用房间（软删除）"""
        db_room = await self.get_room_by_room_id(room_id)
        if not db_room:
            return False
        
        db_room.is_active = False
        await self.db.commit()
        
        logger.info(f"房间已停用: {room_id}")
        return True
    
    async def delete_room(self, room_id: str) -> bool:
        """删除房间（硬删除）"""
        db_room = await self.get_room_by_room_id(room_id)
        if not db_room:
            return False
        
        await self.db.delete(db_room)
        await self.db.commit()
        
        logger.info(f"房间已删除: {room_id}")
        return True
    
    # ==================== 成员管理 ====================
    
    async def add_member(
        self,
        room_db_id: int,
        user_db_id: int,
        role: str = "editor",
        color: str = "#6366f1",
    ) -> RoomMembership:
        """
        添加房间成员
        
        Args:
            room_db_id: 房间数据库ID
            user_db_id: 用户数据库ID
            role: 角色
            color: 用户颜色
        
        Returns:
            成员关系对象
        """
        # 检查是否已是成员
        existing = await self.get_membership(room_db_id, user_db_id)
        if existing:
            existing.is_online = True
            existing.last_active_at = datetime.now()
            await self.db.commit()
            return existing
        
        membership = RoomMembership(
            room_id=room_db_id,
            user_id=user_db_id,
            role=role,
            color=color,
        )
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        
        return membership
    
    async def get_membership(
        self,
        room_db_id: int,
        user_db_id: int,
    ) -> Optional[RoomMembership]:
        """获取成员关系"""
        result = await self.db.execute(
            select(RoomMembership)
            .where(RoomMembership.room_id == room_db_id)
            .where(RoomMembership.user_id == user_db_id)
        )
        return result.scalar_one_or_none()
    
    async def get_room_members(self, room_db_id: int) -> List[Dict]:
        """获取房间所有成员"""
        result = await self.db.execute(
            select(RoomMembership, User)
            .join(User, RoomMembership.user_id == User.id)
            .where(RoomMembership.room_id == room_db_id)
        )
        
        members = []
        for membership, user in result.all():
            members.append({
                "user_id": user.user_id,
                "username": user.username,
                "display_name": user.display_name,
                "role": membership.role,
                "color": membership.color,
                "is_online": membership.is_online,
                "joined_at": membership.joined_at.isoformat(),
                "last_active_at": membership.last_active_at.isoformat(),
            })
        
        return members
    
    async def update_member_status(
        self,
        room_db_id: int,
        user_db_id: int,
        is_online: bool = None,
        current_chapter: str = None,
        cursor_position: int = None,
    ) -> bool:
        """更新成员状态"""
        membership = await self.get_membership(room_db_id, user_db_id)
        if not membership:
            return False
        
        if is_online is not None:
            membership.is_online = is_online
        if current_chapter is not None:
            membership.current_chapter = current_chapter
        if cursor_position is not None:
            membership.cursor_position = cursor_position
        
        membership.last_active_at = datetime.now()
        await self.db.commit()
        return True
    
    async def remove_member(self, room_db_id: int, user_db_id: int) -> bool:
        """移除成员"""
        membership = await self.get_membership(room_db_id, user_db_id)
        if not membership:
            return False
        
        await self.db.delete(membership)
        await self.db.commit()
        return True
    
    # ==================== 编辑历史 ====================
    
    async def record_edit(
        self,
        room_db_id: int,
        user_db_id: int,
        action: str,
        chapter_id: str = None,
        content_before: str = None,
        content_after: str = None,
        metadata: dict = None,
    ) -> EditHistory:
        """
        记录编辑历史
        
        Args:
            room_db_id: 房间数据库ID
            user_db_id: 用户数据库ID
            action: 操作类型
            chapter_id: 章节ID
            content_before: 修改前内容
            content_after: 修改后内容
            metadata: 额外元数据
        
        Returns:
            编辑历史记录
        """
        history = EditHistory(
            room_id=room_db_id,
            user_id=user_db_id,
            action=action,
            chapter_id=chapter_id,
            content_before=content_before,
            content_after=content_after,
            metadata=metadata or {},
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        
        return history
    
    async def get_room_edit_history(
        self,
        room_db_id: int,
        limit: int = 50,
    ) -> List[Dict]:
        """获取房间编辑历史"""
        result = await self.db.execute(
            select(EditHistory, User)
            .outerjoin(User, EditHistory.user_id == User.id)
            .where(EditHistory.room_id == room_db_id)
            .order_by(EditHistory.created_at.desc())
            .limit(limit)
        )
        
        histories = []
        for history, user in result.all():
            histories.append({
                "id": history.id,
                "action": history.action,
                "chapter_id": history.chapter_id,
                "user": {
                    "user_id": user.user_id if user else None,
                    "username": user.username if user else "未知用户",
                } if user else None,
                "created_at": history.created_at.isoformat(),
            })
        
        return histories
    
    # ==================== 锁定记录 ====================
    
    async def record_lock(
        self,
        room_db_id: int,
        user_db_id: int,
        chapter_id: str,
        expires_at: datetime,
    ) -> ChapterLockRecord:
        """记录章节锁定"""
        # 先释放该用户在该房间的其他锁
        await self.db.execute(
            update(ChapterLockRecord)
            .where(ChapterLockRecord.room_id == room_db_id)
            .where(ChapterLockRecord.user_id == user_db_id)
            .where(ChapterLockRecord.is_active == True)
            .values(is_active=False, released_at=datetime.now())
        )
        
        record = ChapterLockRecord(
            room_id=room_db_id,
            user_id=user_db_id,
            chapter_id=chapter_id,
            expires_at=expires_at,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        
        return record
    
    async def release_lock_record(
        self,
        room_db_id: int,
        user_db_id: int,
        chapter_id: str,
    ) -> bool:
        """释放锁定记录"""
        result = await self.db.execute(
            update(ChapterLockRecord)
            .where(ChapterLockRecord.room_id == room_db_id)
            .where(ChapterLockRecord.user_id == user_db_id)
            .where(ChapterLockRecord.chapter_id == chapter_id)
            .where(ChapterLockRecord.is_active == True)
            .values(is_active=False, released_at=datetime.now())
        )
        await self.db.commit()
        return result.rowcount > 0


def db_room_to_room(db_room: CollaborationRoom) -> Room:
    """将数据库房间对象转换为Room对象"""
    return Room(
        room_id=db_room.room_id,
        room_name=db_room.room_name,
        document_title=db_room.document_title,
        mode=CollaborationMode(db_room.mode),
        content=db_room.content,
        content_json=db_room.content_json,
        chapters=db_room.chapters or [],
        members={},  # 成员需要单独加载
        owner_id=str(db_room.owner_id) if db_room.owner_id else "",
        created_at=db_room.created_at,
        updated_at=db_room.updated_at,
        max_members=db_room.max_members,
    )

