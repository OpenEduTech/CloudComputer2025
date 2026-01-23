"""
PatPat-Inconsistency-Hunter 协作API路由
定义协作功能相关的所有API端点
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, Depends, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.collaboration.room_manager import (
    RoomManager, Room, RoomMember, CollaborationMode, get_room_manager
)
from ..services.collaboration.chapter_lock import (
    ChapterLockService, ChapterLock, get_chapter_lock_service
)
from ..services.collaboration.websocket_manager import (
    WebSocketManager, get_ws_manager, MessageType
)
from ..services.collaboration.realtime_detector import (
    RealtimeConflictDetector, get_realtime_detector
)
from ..services.collaboration.room_persistence import RoomPersistenceService
from ..services.document_editor import get_document_editor
from ..models.database import User
from ..utils.logger import logger
from ..utils.db_session import get_db_session, async_session_maker
from .auth_routes import get_current_user


async def persist_room_to_db(room: Room, owner_db_id: int = None):
    """辅助函数：将房间持久化到数据库"""
    try:
        async with async_session_maker() as db:
            persistence = RoomPersistenceService(db)
            await persistence.save_room(room, owner_db_id)
    except Exception as e:
        # 如果是唯一性约束冲突，尝试更新已有记录
        if "UniqueViolation" in str(e) or "unique constraint" in str(e).lower():
            logger.warning(f"房间持久化唯一性冲突，尝试更新: {e}")
            try:
                async with async_session_maker() as db:
                    from sqlalchemy import select, update
                    from ..models.database import CollaborationRoom
                    
                    # 通过 room_id 查找并更新
                    result = await db.execute(
                        select(CollaborationRoom).where(CollaborationRoom.room_id == room.room_id)
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        existing.content = room.content
                        existing.chapters = room.chapters
                        existing.room_name = room.room_name
                        existing.document_title = room.document_title
                        await db.commit()
                        logger.info(f"更新已存在的房间记录: {room.room_id}")
            except Exception as update_error:
                logger.error(f"更新房间失败: {update_error}")
        else:
            logger.error(f"持久化房间失败: {e}")


PERSIST_DEBOUNCE_SECONDS = 3.0
_room_persist_tasks: Dict[str, asyncio.Task] = {}


async def schedule_room_persist(room_id: str):
    """防抖持久化房间，避免频繁落盘"""
    existing = _room_persist_tasks.get(room_id)
    if existing:
        existing.cancel()

    async def _persist():
        try:
            await asyncio.sleep(PERSIST_DEBOUNCE_SECONDS)
            room_manager = get_room_manager()
            room = await room_manager.get_room(room_id)
            if room:
                await persist_room_to_db(room)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"防抖持久化房间失败: {e}")
        finally:
            _room_persist_tasks.pop(room_id, None)

    _room_persist_tasks[room_id] = asyncio.create_task(_persist())


async def persist_membership_to_db(room_db_id: int, user_db_id: int, role: str = "editor", color: str = "#6366f1"):
    """辅助函数：保存成员关系到数据库"""
    try:
        async with async_session_maker() as db:
            persistence = RoomPersistenceService(db)
            await persistence.add_member(room_db_id, user_db_id, role, color)
    except Exception as e:
        logger.error(f"持久化成员关系失败: {e}")


async def persist_edit_history(room_id: str, user_id: str, action: str, chapter_id: str = None, 
                                content_before: str = None, content_after: str = None):
    """辅助函数：记录编辑历史到数据库"""
    try:
        async with async_session_maker() as db:
            from sqlalchemy import select
            from ..models.database import CollaborationRoom, User as DBUser
            
            # 获取房间数据库ID
            result = await db.execute(
                select(CollaborationRoom).where(CollaborationRoom.room_id == room_id)
            )
            db_room = result.scalar_one_or_none()
            if not db_room:
                return
            
            # 获取用户数据库ID（如果是登录用户）
            user_db_id = None
            if user_id and not user_id.startswith("guest_"):
                result = await db.execute(
                    select(DBUser).where(DBUser.user_id == user_id)
                )
                db_user = result.scalar_one_or_none()
                if db_user:
                    user_db_id = db_user.id
            
            persistence = RoomPersistenceService(db)
            await persistence.record_edit(
                room_db_id=db_room.id,
                user_db_id=user_db_id,
                action=action,
                chapter_id=chapter_id,
                content_before=content_before,
                content_after=content_after,
            )
    except Exception as e:
        logger.error(f"记录编辑历史失败: {e}")


def _get_chapter_by_id(room: Room, chapter_id: str) -> Optional[dict]:
    return next((chapter for chapter in room.chapters if chapter.get("id") == chapter_id), None)


def _can_user_edit_chapter(room: Room, chapter_id: str, user_id: str) -> bool:
    if room.owner_id == user_id:
        return True
    chapter = _get_chapter_by_id(room, chapter_id)
    if not chapter:
        return False
    assigned_to = chapter.get("assigned_to")
    return assigned_to == user_id


async def persist_lock_record(room_id: str, user_id: str, chapter_id: str, expires_at):
    """辅助函数：记录章节锁定到数据库"""
    try:
        async with async_session_maker() as db:
            from sqlalchemy import select
            from ..models.database import CollaborationRoom, User as DBUser
            
            # 获取房间数据库ID
            result = await db.execute(
                select(CollaborationRoom).where(CollaborationRoom.room_id == room_id)
            )
            db_room = result.scalar_one_or_none()
            if not db_room:
                return
            
            # 获取用户数据库ID
            user_db_id = None
            if user_id and not user_id.startswith("guest_"):
                result = await db.execute(
                    select(DBUser).where(DBUser.user_id == user_id)
                )
                db_user = result.scalar_one_or_none()
                if db_user:
                    user_db_id = db_user.id
            
            if user_db_id:
                persistence = RoomPersistenceService(db)
                await persistence.record_lock(
                    room_db_id=db_room.id,
                    user_db_id=user_db_id,
                    chapter_id=chapter_id,
                    expires_at=expires_at,
                )
    except Exception as e:
        logger.error(f"记录锁定历史失败: {e}")


async def persist_lock_release(room_id: str, user_id: str, chapter_id: str):
    """辅助函数：记录锁释放到数据库"""
    try:
        async with async_session_maker() as db:
            from sqlalchemy import select
            from ..models.database import CollaborationRoom, User as DBUser
            
            # 获取房间数据库ID
            result = await db.execute(
                select(CollaborationRoom).where(CollaborationRoom.room_id == room_id)
            )
            db_room = result.scalar_one_or_none()
            if not db_room:
                return
            
            # 获取用户数据库ID
            user_db_id = None
            if user_id and not user_id.startswith("guest_"):
                result = await db.execute(
                    select(DBUser).where(DBUser.user_id == user_id)
                )
                db_user = result.scalar_one_or_none()
                if db_user:
                    user_db_id = db_user.id
            
            if user_db_id:
                persistence = RoomPersistenceService(db)
                await persistence.release_lock_record(
                    room_db_id=db_room.id,
                    user_db_id=user_db_id,
                    chapter_id=chapter_id,
                )
    except Exception as e:
        logger.error(f"记录锁释放失败: {e}")


router = APIRouter(prefix="/collaboration", tags=["协作"])


# ==================== 请求/响应模型 ====================

class CreateRoomRequest(BaseModel):
    """创建房间请求"""
    room_name: str = Field(..., description="房间名称", min_length=1, max_length=100)
    mode: CollaborationMode = Field(..., description="协作模式")
    document_title: str = Field(default="未命名文档", description="文档标题")
    initial_content: str = Field(default="", description="初始内容")
    owner_name: str = Field(..., description="房主名称")
    invite_code: Optional[str] = Field(default=None, description="邀请码（4-8位，不填则自动生成）")
    description: str = Field(default="", description="房间描述")
    document_id: Optional[int] = Field(default=None, description="选择已有文档的ID")


class JoinRoomRequest(BaseModel):
    """加入房间请求"""
    username: str = Field(..., description="用户名", min_length=1, max_length=50)
    invite_code: Optional[str] = Field(default=None, description="邀请码")


class UpdateContentRequest(BaseModel):
    """更新内容请求"""
    content: str = Field(..., description="新内容")
    user_id: str = Field(..., description="用户ID")
    content_json: Optional[dict] = Field(default=None, description="富文本内容JSON")


class TriggerDetectionRequest(BaseModel):
    """触发检测请求（可选内容，不落库）"""
    content: Optional[str] = Field(None, description="用于检测的文档内容")


class UpdateChapterRequest(BaseModel):
    """更新章节请求"""
    chapter_id: str = Field(..., description="章节ID")
    content: str = Field(..., description="新内容")
    user_id: str = Field(..., description="用户ID")


class AcquireLockRequest(BaseModel):
    """获取锁请求"""
    chapter_id: str = Field(..., description="章节ID")
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    duration: int = Field(default=300, description="锁定时长（秒）", ge=60, le=1800)


class ReleaseLockRequest(BaseModel):
    """释放锁请求"""
    chapter_id: str = Field(..., description="章节ID")
    user_id: str = Field(..., description="用户ID")


class RoomResponse(BaseModel):
    """房间响应"""
    room_id: str
    room_name: str
    document_title: str
    mode: str
    content: str
    content_json: Optional[dict] = None
    chapters: List[dict]
    members: dict
    owner_id: str
    created_at: str
    updated_at: str
    max_members: int
    online_count: int
    invite_code: Optional[str] = None
    description: str = ""
    has_invite_code: bool = False
    is_detecting: bool = False
    last_detection_time: Optional[str] = None


class DetectionStatusResponse(BaseModel):
    """检测状态响应"""
    is_detecting: bool
    room_is_detecting: bool
    lock: Optional[dict] = None
    last_detection_time: Optional[str] = None


class LockResponse(BaseModel):
    """锁响应"""
    chapter_id: str
    user_id: str
    username: str
    locked_at: str
    expires_at: str


# ==================== API 端点 ====================

@router.post("/rooms", response_model=RoomResponse)
async def create_room(
    request: CreateRoomRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    创建协作房间
    
    创建一个新的协作房间，支持两种模式：
    - realtime: 多人实时协同编辑
    - chapter_lock: 分章节锁定编辑
    
    支持设置邀请码，他人加入需要验证
    """
    import random
    import string
    from sqlalchemy import select
    from ..models.database import Document as DBDocument
    
    room_manager = get_room_manager()
    
    # 使用登录用户的ID，否则生成临时ID
    if current_user:
        owner_id = current_user.user_id
        owner_name = current_user.display_name or current_user.username
        owner_db_id = current_user.id
        owner_avatar_url = current_user.avatar_url
    else:
        owner_id = f"guest_{uuid.uuid4().hex[:12]}"
        owner_name = request.owner_name
        owner_db_id = None
        owner_avatar_url = None
    
    # 生成或验证邀请码
    invite_code = request.invite_code
    if invite_code:
        # 验证邀请码长度
        if len(invite_code) < 4 or len(invite_code) > 8:
            raise HTTPException(status_code=400, detail="邀请码长度必须为4-8位")
        
        # 检查邀请码是否已存在
        try:
            from ..models.database import CollaborationRoom
            async with async_session_maker() as db:
                existing = await db.execute(
                    select(CollaborationRoom).where(
                        CollaborationRoom.invite_code == invite_code,
                        CollaborationRoom.is_active == True
                    )
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="该邀请码已被使用，请更换其他邀请码")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"检查邀请码时出错: {e}")
    else:
        # 自动生成6位唯一邀请码
        for _ in range(10):  # 最多尝试10次
            invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            try:
                from ..models.database import CollaborationRoom
                async with async_session_maker() as db:
                    existing = await db.execute(
                        select(CollaborationRoom).where(
                            CollaborationRoom.invite_code == invite_code,
                            CollaborationRoom.is_active == True
                        )
                    )
                    if not existing.scalar_one_or_none():
                        break
            except Exception:
                break
    
    # 获取初始内容（可能从已有文档）
    initial_content = request.initial_content
    document_title = request.document_title
    
    if request.document_id and current_user:
        # 从用户已有文档获取内容
        try:
            async with async_session_maker() as db:
                from sqlalchemy import func
                result = await db.execute(
                    select(DBDocument).where(
                        DBDocument.id == request.document_id,
                        func.jsonb_extract_path_text(DBDocument.doc_metadata, 'user_id') == current_user.user_id
                    )
                )
                doc = result.scalar_one_or_none()
                if doc:
                    initial_content = doc.content or ""
                    document_title = doc.title or document_title
                    # 如果文档有富文本内容，也可以传递
                    logger.info(f"从文档导入内容: document_id={request.document_id}, title={document_title}, content_length={len(initial_content)}")
                else:
                    logger.warning(f"文档不存在或无权访问: document_id={request.document_id}")
        except Exception as e:
            logger.error(f"获取已有文档失败: {e}")
            import traceback
            traceback.print_exc()
    
    room = await room_manager.create_room(
        room_name=request.room_name,
        owner_id=owner_id,
        owner_name=owner_name,
        mode=request.mode,
        document_title=document_title,
        initial_content=initial_content,
        owner_avatar_url=owner_avatar_url,
    )
    
    # 设置房间额外属性
    room.invite_code = invite_code
    room.description = request.description
    await room_manager._save_room(room)
    
    # 持久化到数据库（包含邀请码）
    await persist_room_to_db(room, owner_db_id)
    
    ws_manager = get_ws_manager()
    online_count = ws_manager.connection_manager.get_room_user_count(room.room_id)
    
    return RoomResponse(
        room_id=room.room_id,
        room_name=room.room_name,
        document_title=room.document_title,
        mode=room.mode.value,
        content=room.content,
        content_json=getattr(room, "content_json", None),
        chapters=room.chapters,
        members={uid: m.model_dump() for uid, m in room.members.items()},
        owner_id=room.owner_id,
        created_at=room.created_at.isoformat(),
        updated_at=room.updated_at.isoformat(),
        max_members=room.max_members,
        online_count=online_count,
        invite_code=invite_code,
        description=room.description if hasattr(room, 'description') else "",
        has_invite_code=True,
        is_detecting=room.is_detecting,
        last_detection_time=room.last_detection_time.isoformat() if room.last_detection_time else None,
    )


@router.get("/rooms", response_model=List[dict])
async def list_rooms(limit: int = Query(default=20, ge=1, le=100)):
    """
    列出所有协作房间
    """
    room_manager = get_room_manager()
    ws_manager = get_ws_manager()
    
    rooms = await room_manager.list_rooms(limit=limit)
    
    result = []
    for room in rooms:
        online_count = ws_manager.connection_manager.get_room_user_count(room.room_id)
        has_invite_code = bool(getattr(room, 'invite_code', None))
        result.append({
            "room_id": room.room_id,
            "room_name": room.room_name,
            "document_title": room.document_title,
            "mode": room.mode.value,
            "member_count": len(room.members),
            "online_count": online_count,
            "created_at": room.created_at.isoformat(),
            "has_invite_code": has_invite_code,
            "description": getattr(room, 'description', ''),
        })
    
    return result


@router.get("/user/documents", response_model=List[dict])
async def get_user_documents(
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的所有文档列表
    
    用于创建房间时选择已有文档
    """
    if not current_user:
        return []
    
    try:
        from sqlalchemy import select, func
        from ..models.database import Document as DBDocument
        
        async with async_session_maker() as db:
            result = await db.execute(
                select(DBDocument)
                .where(func.jsonb_extract_path_text(DBDocument.doc_metadata, 'user_id') == current_user.user_id)
                .order_by(DBDocument.created_at.desc())
                .limit(50)
            )
            documents = result.scalars().all()
            
            return [
                {
                    "id": doc.id,
                    "task_id": doc.task_id,
                    "title": doc.title or "未命名文档",
                    "content_length": doc.content_length,
                    "total_facts": doc.total_facts,
                    "total_conflicts": doc.total_conflicts,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "status": doc.status,
                }
                for doc in documents
            ]
    except Exception as e:
        logger.error(f"获取用户文档列表失败: {e}")
        import traceback
        traceback.print_exc()
        return []


@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str):
    """
    获取房间详情
    """
    room_manager = get_room_manager()
    room = await room_manager.get_room(room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    ws_manager = get_ws_manager()
    online_count = ws_manager.connection_manager.get_room_user_count(room_id)
    
    # 获取邀请码相关信息
    invite_code = getattr(room, 'invite_code', None)
    has_invite_code = bool(invite_code)
    description = getattr(room, 'description', '')
    
    return RoomResponse(
        room_id=room.room_id,
        room_name=room.room_name,
        document_title=room.document_title,
        mode=room.mode.value,
        content=room.content,
        content_json=getattr(room, "content_json", None),
        chapters=room.chapters,
        members={uid: m.model_dump() for uid, m in room.members.items()},
        owner_id=room.owner_id,
        created_at=room.created_at.isoformat(),
        updated_at=room.updated_at.isoformat(),
        max_members=room.max_members,
        online_count=online_count,
        invite_code=invite_code,
        description=description,
        has_invite_code=has_invite_code,
        is_detecting=room.is_detecting,
        last_detection_time=room.last_detection_time.isoformat() if room.last_detection_time else None,
    )


@router.post("/rooms/{room_id}/join")
async def join_room(
    room_id: str, 
    request: JoinRoomRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    加入协作房间
    
    如果房间设置了邀请码，需要提供正确的邀请码才能加入
    """
    room_manager = get_room_manager()
    
    # 先获取房间检查邀请码
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 验证邀请码（如果房间设置了邀请码）
    room_invite_code = getattr(room, 'invite_code', None)
    if room_invite_code:
        # 房间设置了邀请码，需要验证
        if not request.invite_code:
            raise HTTPException(status_code=403, detail="该房间需要邀请码才能加入")
        if request.invite_code.upper() != room_invite_code.upper():
            raise HTTPException(status_code=403, detail="邀请码不正确")
    
    # 使用登录用户的ID，否则生成临时ID
    if current_user:
        user_id = current_user.user_id
        username = current_user.display_name or current_user.username
        avatar_url = current_user.avatar_url
    else:
        user_id = f"guest_{uuid.uuid4().hex[:12]}"
        username = request.username
        avatar_url = None
    
    # 检查用户是否已经在房间中
    if user_id in room.members:
        # 用户已在房间中，更新在线状态并返回成功
        room.members[user_id].is_online = True
        await room_manager._save_room(room)
        return {
            "user_id": user_id,
            "room_id": room_id,
            "message": "已重新连接到房间",
            "already_member": True,
        }
    
    room = await room_manager.join_room(
        room_id=room_id,
        user_id=user_id,
        username=username,
        avatar_url=avatar_url,
    )
    
    if not room:
        raise HTTPException(status_code=400, detail="无法加入房间（房间已满）")
    
    # 持久化成员关系到数据库
    if current_user:
        try:
            async with async_session_maker() as db:
                from sqlalchemy import select
                from ..models.database import CollaborationRoom
                persistence = RoomPersistenceService(db)
                # 获取房间数据库ID
                result = await db.execute(
                    select(CollaborationRoom).where(CollaborationRoom.room_id == room_id)
                )
                db_room = result.scalar_one_or_none()
                if db_room:
                    member = room.members.get(user_id)
                    color = member.color if member else "#6366f1"
                    await persistence.add_member(db_room.id, current_user.id, "editor", color)
        except Exception as e:
            logger.error(f"持久化成员关系失败: {e}")
    
    return {
        "user_id": user_id,
        "room_id": room_id,
        "message": "成功加入房间",
        "already_member": False,
    }


@router.post("/rooms/{room_id}/leave")
async def leave_room(room_id: str, user_id: str):
    """
    离开协作房间
    """
    room_manager = get_room_manager()
    lock_service = get_chapter_lock_service()
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 离开前先持久化房间内容
    room = await room_manager.get_room(room_id)
    if room:
        await persist_room_to_db(room)
    
    # 释放用户的所有锁
    await lock_service.release_user_locks(room_id, user_id)
    
    success = await room_manager.leave_room(room_id, user_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="离开房间失败")
    
    return {"message": "已离开房间"}


@router.put("/rooms/{room_id}/content")
async def update_room_content(room_id: str, request: UpdateContentRequest):
    """
    更新房间文档内容
    """
    room_manager = get_room_manager()
    
    success, new_version = await room_manager.update_content(
        room_id=room_id,
        content=request.content,
        user_id=request.user_id,
        content_json=request.content_json,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="更新内容失败")
    
    # 持久化到数据库
    room = await room_manager.get_room(room_id)
    if room:
        await persist_room_to_db(room)
    
    # 广播内容更新
    ws_manager = get_ws_manager()
    await ws_manager.connection_manager.broadcast_content_update(
        room_id=room_id,
        user_id=request.user_id,
        content=request.content,
        content_json=request.content_json,
    )
    
    return {"message": "内容已更新"}


@router.put("/rooms/{room_id}/chapters/{chapter_id}")
async def update_chapter_content(
    room_id: str,
    chapter_id: str,
    request: UpdateChapterRequest,
):
    """
    更新章节内容（分章节模式）
    """
    room_manager = get_room_manager()
    lock_service = get_chapter_lock_service()
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    if room.mode == CollaborationMode.CHAPTER_LOCK and not _can_user_edit_chapter(room, chapter_id, request.user_id):
        raise HTTPException(status_code=403, detail="您没有该章节的编辑权限")
    
    # 检查锁
    can_edit = await lock_service.can_edit_chapter(room_id, chapter_id, request.user_id)
    if not can_edit:
        raise HTTPException(status_code=403, detail="该章节已被其他人锁定")
    
    success = await room_manager.update_chapter_content(
        room_id=room_id,
        chapter_id=chapter_id,
        content=request.content,
        user_id=request.user_id,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="更新章节失败")
    
    # 防抖持久化与记录历史（不自动检测）
    room = await room_manager.get_room(room_id)
    if room:
        # 记录编辑历史
        await persist_edit_history(
            room_id=room_id,
            user_id=request.user_id,
            action="update",
            chapter_id=chapter_id,
            content_after=request.content,
        )

        await schedule_room_persist(room_id)

        ws_manager = get_ws_manager()
        await ws_manager.connection_manager.broadcast_to_room(
            room_id,
            {
                "type": "chapters_updated",
                "data": {
                    "chapters": room.chapters,
                },
            },
            exclude_user=request.user_id,
        )
    
    return {"message": "章节已更新"}


# ==================== 章节锁定 API ====================

@router.post("/rooms/{room_id}/locks", response_model=LockResponse)
async def acquire_chapter_lock(room_id: str, request: AcquireLockRequest):
    """
    获取章节锁
    """
    room_manager = get_room_manager()
    lock_service = get_chapter_lock_service()
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    if room.mode == CollaborationMode.CHAPTER_LOCK and not _can_user_edit_chapter(room, request.chapter_id, request.user_id):
        raise HTTPException(status_code=403, detail="您没有该章节的编辑权限")
    
    lock = await lock_service.acquire_lock(
        room_id=room_id,
        chapter_id=request.chapter_id,
        user_id=request.user_id,
        username=request.username,
        duration=request.duration,
    )
    
    if not lock:
        raise HTTPException(status_code=409, detail="无法获取锁（章节已被锁定）")
    
    # 持久化锁定记录
    await persist_lock_record(room_id, request.user_id, request.chapter_id, lock.expires_at)
    
    # 广播锁状态
    ws_manager = get_ws_manager()
    locks = await lock_service.get_room_locks(room_id)
    await ws_manager.connection_manager.broadcast_lock_status(
        room_id,
        [{"chapter_id": l.chapter_id, "user_id": l.user_id, "username": l.username} for l in locks]
    )
    
    return LockResponse(
        chapter_id=lock.chapter_id,
        user_id=lock.user_id,
        username=lock.username,
        locked_at=lock.locked_at.isoformat(),
        expires_at=lock.expires_at.isoformat(),
    )


@router.delete("/rooms/{room_id}/locks/{chapter_id}")
async def release_chapter_lock(room_id: str, chapter_id: str, user_id: str):
    """
    释放章节锁
    """
    lock_service = get_chapter_lock_service()
    
    success = await lock_service.release_lock(room_id, chapter_id, user_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="释放锁失败")
    
    # 持久化锁释放记录
    await persist_lock_release(room_id, user_id, chapter_id)
    
    # 广播锁状态
    ws_manager = get_ws_manager()
    locks = await lock_service.get_room_locks(room_id)
    await ws_manager.connection_manager.broadcast_lock_status(
        room_id,
        [{"chapter_id": l.chapter_id, "user_id": l.user_id, "username": l.username} for l in locks]
    )
    
    return {"message": "锁已释放"}


@router.get("/rooms/{room_id}/locks", response_model=List[LockResponse])
async def get_room_locks(room_id: str):
    """
    获取房间内所有锁
    """
    lock_service = get_chapter_lock_service()
    locks = await lock_service.get_room_locks(room_id)
    
    return [
        LockResponse(
            chapter_id=lock.chapter_id,
            user_id=lock.user_id,
            username=lock.username,
            locked_at=lock.locked_at.isoformat(),
            expires_at=lock.expires_at.isoformat(),
        )
        for lock in locks
    ]


# ==================== 房主权限管理 API ====================

class UpdateRoomSettingsRequest(BaseModel):
    """更新房间设置请求"""
    room_name: Optional[str] = None
    document_title: Optional[str] = None
    max_members: Optional[int] = None


class AssignChapterRequest(BaseModel):
    """分配章节请求"""
    chapter_id: str = Field(..., description="章节ID")
    user_id: str = Field(..., description="目标用户ID")
    force: bool = Field(default=False, description="是否强制分配（解除原有锁定）")


class UnassignChapterRequest(BaseModel):
    """取消章节分配请求"""
    chapter_id: str = Field(..., description="章节ID")
    user_id: Optional[str] = Field(default=None, description="目标用户ID")


class AddChapterRequest(BaseModel):
    """添加章节请求"""
    title: str = Field(..., description="章节标题")
    content: str = Field(default="", description="章节内容")
    position: Optional[int] = Field(None, description="插入位置（从0开始）")


@router.put("/rooms/{room_id}/settings")
async def update_room_settings(
    room_id: str,
    request: UpdateRoomSettingsRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    更新房间设置（仅房主）
    """
    room_manager = get_room_manager()
    room = await room_manager.get_room(room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查权限
    user_id = current_user.user_id if current_user else None
    if room.owner_id != user_id:
        raise HTTPException(status_code=403, detail="只有房主可以修改房间设置")
    
    # 更新设置
    if request.room_name is not None:
        room.room_name = request.room_name
    if request.document_title is not None:
        room.document_title = request.document_title
    if request.max_members is not None:
        if request.max_members < len(room.members):
            raise HTTPException(status_code=400, detail="最大成员数不能小于当前成员数")
        room.max_members = request.max_members
    
    room.updated_at = datetime.now()
    await room_manager._save_room(room)
    
    return {"message": "设置已更新"}


@router.post("/rooms/{room_id}/assign-chapter")
async def assign_chapter(
    room_id: str,
    request: AssignChapterRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    为用户分配章节编辑权限（仅房主，仅限chapter_lock模式）
    """
    room_manager = get_room_manager()
    lock_service = get_chapter_lock_service()
    ws_manager = get_ws_manager()
    
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查模式
    if room.mode != CollaborationMode.CHAPTER_LOCK:
        raise HTTPException(status_code=400, detail="只有分章节锁定模式支持章节分配")
    
    # 检查权限
    requester_id = current_user.user_id if current_user else None
    if room.owner_id != requester_id:
        raise HTTPException(status_code=403, detail="只有房主可以分配章节")
    
    # 检查目标用户是否在房间中
    if request.user_id not in room.members:
        raise HTTPException(status_code=400, detail="目标用户不在房间中")
    
    # 检查章节是否存在
    chapter = _get_chapter_by_id(room, request.chapter_id)
    if not chapter:
        raise HTTPException(status_code=400, detail="章节不存在")
    
    lock_released = False
    # 如果章节已被锁定且force=True，则先释放
    if request.force:
        current_lock = await lock_service.get_chapter_lock(room_id, request.chapter_id)
        if current_lock and current_lock.user_id != request.user_id:
            await lock_service.release_lock(room_id, request.chapter_id, current_lock.user_id)
            lock_released = True
    
    # 获取用户名
    target_member = room.members.get(request.user_id)
    username = target_member.username if target_member else "Unknown"
    
    chapter["assigned_to"] = request.user_id
    chapter["assigned_to_name"] = username
    room.updated_at = datetime.now()
    await room_manager._save_room(room)
    
    if lock_released:
        locks = await lock_service.get_room_locks(room_id)
        await ws_manager.connection_manager.broadcast_lock_status(
            room_id,
            [{"chapter_id": l.chapter_id, "user_id": l.user_id, "username": l.username} for l in locks]
        )
    
    # 获取章节名称
    chapter_title = next((c.get("title", "未命名章节") for c in room.chapters if c.get("id") == request.chapter_id), "未命名章节")
    
    # 发送权限变更通知给被分配的用户
    await ws_manager.connection_manager.send_personal(
        room_id,
        request.user_id,
        {
            "type": "permission_changed",
            "data": {
                "message": f"房主已将章节 \"{chapter_title}\" 分配给您",
                "chapter_id": request.chapter_id,
                "chapter_title": chapter_title,
                "action": "assigned",
            }
        }
    )
    
    # 广播权限变更给所有用户（用于同步显示）
    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "chapter_assignment_changed",
            "data": {
                "chapter_id": request.chapter_id,
                "chapter_title": chapter_title,
                "assigned_to": request.user_id,
                "assigned_to_name": username,
                "action": "assigned",
            }
        }
    )

    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "chapters_updated",
            "data": {
                "chapters": room.chapters,
            },
        },
    )
    
    return {
        "message": f"已将章节 {request.chapter_id} 分配给用户",
        "chapter_id": request.chapter_id,
        "user_id": request.user_id,
    }


@router.post("/rooms/{room_id}/unassign-chapter")
async def unassign_chapter(
    room_id: str,
    request: UnassignChapterRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    取消章节分配（仅房主，仅限chapter_lock模式）
    """
    room_manager = get_room_manager()
    lock_service = get_chapter_lock_service()
    ws_manager = get_ws_manager()

    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")

    if room.mode != CollaborationMode.CHAPTER_LOCK:
        raise HTTPException(status_code=400, detail="只有分章节锁定模式支持取消分配")

    requester_id = current_user.user_id if current_user else None
    if room.owner_id != requester_id:
        raise HTTPException(status_code=403, detail="只有房主可以取消分配")

    chapter = _get_chapter_by_id(room, request.chapter_id)
    if not chapter:
        raise HTTPException(status_code=400, detail="章节不存在")

    assigned_to = chapter.get("assigned_to")
    assigned_to_name = chapter.get("assigned_to_name")
    if not assigned_to:
        raise HTTPException(status_code=400, detail="章节尚未分配")
    if request.user_id and assigned_to != request.user_id:
        raise HTTPException(status_code=400, detail="章节未分配给该用户")

    chapter.pop("assigned_to", None)
    chapter.pop("assigned_to_name", None)
    room.updated_at = datetime.now()
    await room_manager._save_room(room)

    current_lock = await lock_service.get_chapter_lock(room_id, request.chapter_id)
    if current_lock:
        await lock_service.release_lock(room_id, request.chapter_id, current_lock.user_id)
        locks = await lock_service.get_room_locks(room_id)
        await ws_manager.connection_manager.broadcast_lock_status(
            room_id,
            [{"chapter_id": l.chapter_id, "user_id": l.user_id, "username": l.username} for l in locks]
        )

    chapter_title = next((c.get("title", "未命名章节") for c in room.chapters if c.get("id") == request.chapter_id), "未命名章节")

    if assigned_to:
        await ws_manager.connection_manager.send_personal(
            room_id,
            assigned_to,
            {
                "type": "permission_changed",
                "data": {
                    "message": f"房主已取消您对章节 \"{chapter_title}\" 的编辑权限",
                    "chapter_id": request.chapter_id,
                    "chapter_title": chapter_title,
                    "action": "unassigned",
                }
            }
        )

    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "chapter_assignment_changed",
            "data": {
                "chapter_id": request.chapter_id,
                "chapter_title": chapter_title,
                "assigned_to": None,
                "assigned_to_name": None,
                "action": "unassigned",
            }
        }
    )

    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "chapters_updated",
            "data": {
                "chapters": room.chapters,
            },
        },
    )

    return {
        "message": f"已取消章节 {request.chapter_id} 的分配",
        "chapter_id": request.chapter_id,
        "user_id": assigned_to,
        "username": assigned_to_name,
    }


@router.post("/rooms/{room_id}/chapters")
async def add_chapter(
    room_id: str,
    request: AddChapterRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    添加新章节（仅房主，仅限chapter_lock模式）
    """
    room_manager = get_room_manager()
    room = await room_manager.get_room(room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查模式
    if room.mode != CollaborationMode.CHAPTER_LOCK:
        raise HTTPException(status_code=400, detail="只有分章节锁定模式支持添加章节")
    
    # 检查权限
    requester_id = current_user.user_id if current_user else None
    if room.owner_id != requester_id:
        raise HTTPException(status_code=403, detail="只有房主可以添加章节")
    
    # 创建新章节
    chapter_id = f"chapter_{len(room.chapters) + 1}_{uuid.uuid4().hex[:6]}"
    new_chapter = {
        "id": chapter_id,
        "title": request.title,
        "content": request.content,
        "start_line": 0,
        "end_line": 0,
    }
    
    # 插入章节
    if request.position is not None and 0 <= request.position <= len(room.chapters):
        room.chapters.insert(request.position, new_chapter)
    else:
        room.chapters.append(new_chapter)
    
    # 重建内容
    room.content = room_manager._build_content_from_chapters(room.chapters)
    room.updated_at = datetime.now()
    await room_manager._save_room(room)
    
    # 广播章节更新
    ws_manager = get_ws_manager()
    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "chapters_updated",
            "data": {
                "chapters": room.chapters,
            },
        },
    )
    
    return {
        "message": "章节已添加",
        "chapter": new_chapter,
    }


@router.delete("/rooms/{room_id}/chapters/{chapter_id}")
async def delete_chapter(
    room_id: str,
    chapter_id: str,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    删除章节（仅房主，仅限chapter_lock模式）
    """
    room_manager = get_room_manager()
    lock_service = get_chapter_lock_service()
    
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查模式
    if room.mode != CollaborationMode.CHAPTER_LOCK:
        raise HTTPException(status_code=400, detail="只有分章节锁定模式支持删除章节")
    
    # 检查权限
    requester_id = current_user.user_id if current_user else None
    if room.owner_id != requester_id:
        raise HTTPException(status_code=403, detail="只有房主可以删除章节")
    
    # 检查章节是否被锁定
    lock = await lock_service.get_chapter_lock(room_id, chapter_id)
    if lock:
        raise HTTPException(status_code=400, detail="章节正在被编辑，无法删除")
    
    # 删除章节
    room.chapters = [c for c in room.chapters if c.get("id") != chapter_id]
    
    # 重建内容
    room.content = room_manager._build_content_from_chapters(room.chapters)
    room.updated_at = datetime.now()
    await room_manager._save_room(room)
    
    # 广播章节更新
    ws_manager = get_ws_manager()
    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "chapters_updated",
            "data": {
                "chapters": room.chapters,
            },
        },
    )
    
    return {"message": "章节已删除"}


@router.get("/rooms/{room_id}/members")
async def get_room_members(room_id: str):
    """
    获取房间成员列表
    """
    room_manager = get_room_manager()
    ws_manager = get_ws_manager()
    
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    members = []
    for user_id, member in room.members.items():
        is_online = ws_manager.connection_manager.is_user_online(room_id, user_id)
        members.append({
            "user_id": user_id,
            "username": member.username,
            "color": member.color,
            "avatar_url": member.avatar_url,
            "is_owner": user_id == room.owner_id,
            "is_online": is_online,
            "joined_at": member.joined_at.isoformat(),
        })
    
    return {
        "room_id": room_id,
        "owner_id": room.owner_id,
        "members": members,
    }


# ==================== 房间管理 API ====================

class EndRoomRequest(BaseModel):
    """结束房间请求"""
    run_detection: bool = Field(default=False, description="是否在结束前进行冲突检测")


@router.post("/rooms/{room_id}/end")
async def end_room(
    room_id: str,
    request: EndRoomRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    结束房间（仅房主）
    - 可选择是否在结束前进行冲突检测
    - 生成文档下载链接
    - 通知所有成员
    - 关闭房间
    """
    room_manager = get_room_manager()
    ws_manager = get_ws_manager()
    
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查权限
    requester_id = current_user.user_id if current_user else None
    if room.owner_id != requester_id:
        raise HTTPException(status_code=403, detail="只有房主可以结束房间")
    
    detection_result = None
    
    # 如果需要进行检测
    if request.run_detection and room.content:
        detector = get_realtime_detector()
        detection_result = await detector.detect_conflicts(room_id, room.content, force=True)
    
    # 持久化房间内容到数据库
    await persist_room_to_db(room)
    
    # 生成文档内容用于下载
    document_content = room.content
    document_title = room.document_title or "协作文档"
    
    # 通知所有成员房间已结束
    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "room_ended",
            "data": {
                "message": "房间已被房主结束",
                "document_title": document_title,
                "document_content": document_content,
                "detection_result": {
                    "total_facts": detection_result.total_facts if detection_result else 0,
                    "total_conflicts": detection_result.total_conflicts if detection_result else 0,
                    "conflicts": [c.model_dump() for c in detection_result.conflicts] if detection_result else [],
                } if detection_result else None,
            }
        }
    )
    
    # 标记房间为已结束
    room.status = "ended"
    await room_manager._save_room(room)
    
    return {
        "message": "房间已结束",
        "document_title": document_title,
        "document_content": document_content,
        "detection_result": {
            "total_facts": detection_result.total_facts,
            "total_conflicts": detection_result.total_conflicts,
        } if detection_result else None,
    }


@router.get("/rooms/{room_id}/export")
async def export_room_document(
    room_id: str,
    format: str = "md",
    include_analysis: bool = Query(False, description="是否包含冲突和事实分析结果"),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    导出房间文档
    
    支持格式:
    - txt: 纯文本
    - md: Markdown
    - html: HTML
    - docx: Word文档
    - pdf: PDF文档
    
    参数:
    - include_analysis: 是否包含冲突和事实分析结果
    """
    from fastapi.responses import Response
    import base64
    
    room_manager = get_room_manager()
    detector = get_realtime_detector()
    
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查用户是否是房间成员
    requester_id = current_user.user_id if current_user else None
    if requester_id and requester_id not in room.members:
        raise HTTPException(status_code=403, detail="您不是房间成员")
    
    content = room.content
    title = room.document_title or "协作文档"
    
    # 如果需要包含分析结果
    conflicts_section = ""
    facts_section = ""
    if include_analysis:
        last_result = await detector.get_last_result(room_id)
        if last_result and last_result.conflicts:
            conflicts_section = "\n\n---\n\n## 📋 冲突检测结果\n\n"
            conflicts_section += f"共检测到 **{len(last_result.conflicts)}** 个潜在冲突：\n\n"
            for i, conflict in enumerate(last_result.conflicts, 1):
                conflicts_section += f"### 冲突 {i}: {conflict.conflict_type}\n\n"
                conflicts_section += f"- **严重程度**: {conflict.severity * 100:.0f}%\n"
                conflicts_section += f"- **描述**: {conflict.description}\n"
                conflicts_section += f"- **事实A**: {conflict.fact_a_content}\n"
                conflicts_section += f"- **事实B**: {conflict.fact_b_content}\n"
                if conflict.suggestion:
                    conflicts_section += f"- **建议**: {conflict.suggestion}\n"
                conflicts_section += "\n"
        
        if last_result and last_result.facts:
            facts_section = "\n\n---\n\n## 📝 提取的原子事实\n\n"
            facts_section += f"共提取 **{len(last_result.facts)}** 个原子事实：\n\n"
            for i, fact in enumerate(last_result.facts, 1):
                facts_section += f"{i}. **[{fact.fact_type}]** {fact.content}\n"
    
    if format == "md":
        # Markdown 格式
        exported_content = f"# {title}\n\n{content}{conflicts_section}{facts_section}"
        content_type = "text/markdown"
        filename = f"{title}.md"
    elif format == "html":
        # HTML 格式 - 增强样式
        html_content = content.replace(chr(10), '<br>')
        
        # 转换冲突和事实为 HTML
        conflicts_html = ""
        facts_html = ""
        if include_analysis:
            last_result = await detector.get_last_result(room_id)
            if last_result and last_result.conflicts:
                conflicts_html = '<div class="analysis-section"><h2>📋 冲突检测结果</h2>'
                conflicts_html += f'<p>共检测到 <strong>{len(last_result.conflicts)}</strong> 个潜在冲突：</p>'
                for i, conflict in enumerate(last_result.conflicts, 1):
                    conflicts_html += f'''
                    <div class="conflict-item">
                        <h3>冲突 {i}: {conflict.conflict_type}</h3>
                        <ul>
                            <li><strong>严重程度:</strong> {conflict.severity * 100:.0f}%</li>
                            <li><strong>描述:</strong> {conflict.description}</li>
                            <li><strong>事实A:</strong> {conflict.fact_a_content}</li>
                            <li><strong>事实B:</strong> {conflict.fact_b_content}</li>
                            {f'<li><strong>建议:</strong> {conflict.suggestion}</li>' if conflict.suggestion else ''}
                        </ul>
                    </div>'''
                conflicts_html += '</div>'
            
            if last_result and last_result.facts:
                facts_html = '<div class="analysis-section"><h2>📝 提取的原子事实</h2>'
                facts_html += f'<p>共提取 <strong>{len(last_result.facts)}</strong> 个原子事实：</p><ol>'
                for fact in last_result.facts:
                    facts_html += f'<li><span class="fact-type">[{fact.fact_type}]</span> {fact.content}</li>'
                facts_html += '</ol></div>'
        
        exported_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            color: #1a202c;
        }}
        h1 {{ color: #1a365d; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }}
        h2 {{ color: #2d3748; margin-top: 2rem; }}
        h3 {{ color: #4a5568; }}
        p {{ margin: 1rem 0; }}
        .content {{ background: #f7fafc; padding: 1.5rem; border-radius: 8px; margin: 1rem 0; }}
        .analysis-section {{ margin-top: 2rem; padding: 1rem; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }}
        .conflict-item {{ background: #fff5f5; padding: 1rem; border-left: 4px solid #fc8181; margin: 1rem 0; border-radius: 4px; }}
        .fact-type {{ background: #ebf8ff; color: #3182ce; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }}
        ol {{ padding-left: 1.5rem; }}
        li {{ margin: 0.5rem 0; }}
        ul {{ list-style: none; padding-left: 0; }}
        ul li {{ margin: 0.3rem 0; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="content">{html_content}</div>
    {conflicts_html}
    {facts_html}
</body>
</html>"""
        content_type = "text/html"
        filename = f"{title}.html"
    elif format == "docx":
        # Word DOCX 格式 - 使用 document_editor 服务
        try:
            from ..services.document_editor import RichTextContent, get_document_editor
            
            editor = get_document_editor()
            
            # 构建富文本内容
            content_json = RichTextContent.from_plain_text(content)
            
            # 如果有分析结果，添加到内容中
            if include_analysis:
                last_result = await detector.get_last_result(room_id)
                if last_result:
                    analysis_text = ""
                    if last_result.conflicts:
                        analysis_text += f"\n\n冲突检测结果\n共检测到 {len(last_result.conflicts)} 个潜在冲突：\n\n"
                        for i, conflict in enumerate(last_result.conflicts, 1):
                            analysis_text += f"冲突 {i}: {conflict.conflict_type}\n"
                            analysis_text += f"  严重程度: {conflict.severity * 100:.0f}%\n"
                            analysis_text += f"  描述: {conflict.description}\n"
                            analysis_text += f"  事实A: {conflict.fact_a_content}\n"
                            analysis_text += f"  事实B: {conflict.fact_b_content}\n"
                            if conflict.suggestion:
                                analysis_text += f"  建议: {conflict.suggestion}\n"
                            analysis_text += "\n"
                    
                    if last_result.facts:
                        analysis_text += f"\n提取的原子事实\n共提取 {len(last_result.facts)} 个原子事实：\n\n"
                        for i, fact in enumerate(last_result.facts, 1):
                            analysis_text += f"{i}. [{fact.fact_type}] {fact.content}\n"
                    
                    # 合并分析结果到内容
                    content_json = RichTextContent.from_plain_text(content + analysis_text)
            
            docx_content = await editor.convert_to_docx(content_json, title)
            
            return {
                "content": base64.b64encode(docx_content).decode('utf-8'),
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "filename": f"{title}.docx",
                "title": title,
                "is_binary": True,
            }
        except ImportError as e:
            logger.error(f"DOCX导出依赖缺失: {e}")
            raise HTTPException(status_code=500, detail="服务器未安装python-docx库，无法导出DOCX格式")
        except Exception as e:
            logger.error(f"DOCX导出失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"DOCX导出失败: {str(e)}")
    elif format == "pdf":
        # PDF 格式 - 使用 document_editor 服务
        try:
            from ..services.document_editor import RichTextContent, get_document_editor
            
            editor = get_document_editor()
            
            # 构建富文本内容
            full_content = content
            
            # 如果有分析结果，添加到内容中
            if include_analysis:
                last_result = await detector.get_last_result(room_id)
                if last_result:
                    if last_result.conflicts:
                        full_content += f"\n\n冲突检测结果\n共检测到 {len(last_result.conflicts)} 个潜在冲突：\n\n"
                        for i, conflict in enumerate(last_result.conflicts, 1):
                            full_content += f"冲突 {i}: {conflict.conflict_type}\n"
                            full_content += f"  严重程度: {conflict.severity * 100:.0f}%\n"
                            full_content += f"  描述: {conflict.description}\n"
                            full_content += f"  事实A: {conflict.fact_a_content}\n"
                            full_content += f"  事实B: {conflict.fact_b_content}\n"
                            if conflict.suggestion:
                                full_content += f"  建议: {conflict.suggestion}\n"
                            full_content += "\n"
                    
                    if last_result.facts:
                        full_content += f"\n提取的原子事实\n共提取 {len(last_result.facts)} 个原子事实：\n\n"
                        for i, fact in enumerate(last_result.facts, 1):
                            full_content += f"{i}. [{fact.fact_type}] {fact.content}\n"
            
            content_json = RichTextContent.from_plain_text(full_content)
            pdf_content = await editor.convert_to_pdf(content_json, title)
            
            return {
                "content": base64.b64encode(pdf_content).decode('utf-8'),
                "content_type": "application/pdf",
                "filename": f"{title}.pdf",
                "title": title,
                "is_binary": True,
            }
        except ImportError as e:
            logger.error(f"PDF导出依赖缺失: {e}")
            raise HTTPException(status_code=500, detail="服务器未安装reportlab库，无法导出PDF格式")
        except Exception as e:
            logger.error(f"PDF导出失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"PDF导出失败: {str(e)}")
    else:
        # 纯文本格式（默认）
        exported_content = f"{title}\n{'='*len(title)}\n\n{content}{conflicts_section}{facts_section}"
        content_type = "text/plain"
        filename = f"{title}.txt"
    
    return {
        "content": exported_content,
        "content_type": content_type,
        "filename": filename,
        "title": title,
    }


class KickMemberRequest(BaseModel):
    """踢出成员请求"""
    user_id: str = Field(..., description="要踢出的用户ID")
    reason: Optional[str] = Field(None, description="踢出原因")


@router.post("/rooms/{room_id}/kick")
async def kick_member(
    room_id: str,
    request: KickMemberRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    踢出成员（仅房主）
    """
    room_manager = get_room_manager()
    ws_manager = get_ws_manager()
    lock_service = get_chapter_lock_service()
    
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    # 检查权限
    requester_id = current_user.user_id if current_user else None
    if room.owner_id != requester_id:
        raise HTTPException(status_code=403, detail="只有房主可以踢出成员")
    
    # 不能踢出自己
    if request.user_id == requester_id:
        raise HTTPException(status_code=400, detail="不能踢出自己")
    
    # 检查目标用户是否在房间中
    if request.user_id not in room.members:
        raise HTTPException(status_code=400, detail="目标用户不在房间中")
    
    # 释放该用户持有的所有锁
    await lock_service.release_user_locks(room_id, request.user_id)
    
    # 获取被踢用户信息
    kicked_member = room.members.get(request.user_id)
    kicked_username = kicked_member.username if kicked_member else "Unknown"
    
    # 先通知被踢用户
    await ws_manager.connection_manager.send_personal(
        room_id,
        request.user_id,
        {
            "type": "kicked",
            "data": {
                "message": f"您已被房主移出房间",
                "reason": request.reason,
            }
        }
    )
    
    # 从房间移除用户
    del room.members[request.user_id]
    room.updated_at = datetime.now()
    await room_manager._save_room(room)
    
    # 关闭该用户的WebSocket连接
    await ws_manager.connection_manager.disconnect_user(room_id, request.user_id)
    
    # 通知其他成员
    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "member_kicked",
            "data": {
                "user_id": request.user_id,
                "username": kicked_username,
                "reason": request.reason,
            }
        }
    )
    
    # 更新用户列表
    await ws_manager.connection_manager.broadcast_user_list(room_id, room.members)
    
    return {
        "message": f"已将 {kicked_username} 移出房间",
        "kicked_user_id": request.user_id,
    }


# ==================== 冲突检测 API ====================

@router.post("/rooms/{room_id}/detect")
async def trigger_conflict_detection(
    room_id: str, 
    force: bool = False,
    request: Optional[TriggerDetectionRequest] = Body(default=None),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    手动触发冲突检测
    
    对于 chapter_lock 模式：
    - 使用全局检测锁确保同一时间只能进行一次检测
    - 检测完成后，将冲突按章节分发给对应用户
    - 房主可以收到所有冲突和事实
    - 普通用户只能收到与自己章节相关的冲突和事实
    """
    room_manager = get_room_manager()
    ws_manager = get_ws_manager()
    lock_service = get_chapter_lock_service()
    
    room = await room_manager.get_room(room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    detector = get_realtime_detector()
    editor = get_document_editor()
    lock_info = await editor.check_detection_lock("room", room_id)
    if lock_info:
        raise HTTPException(status_code=409, detail="文档正在检测中，请稍后再试")
    
    # 检查是否正在检测
    if detector.is_detecting(room_id):
        raise HTTPException(status_code=409, detail="文档正在检测中，请稍后再试")
    
    content_for_detection = request.content if request and request.content is not None else room.content
    if room.mode == CollaborationMode.CHAPTER_LOCK:
        content_for_detection = room.content

    result = await detector.detect_conflicts(
        room_id=room_id, 
        content=content_for_detection, 
        force=force,
        owner_user_id=current_user.user_id if current_user else room.owner_id,
        document_title=room.document_title,
    )
    
    if result:
        # 判断请求用户是否是房主
        requester_id = current_user.user_id if current_user else None
        is_owner = requester_id == room.owner_id
        
        # 如果是章节锁定模式，按章节分发冲突
        if room.mode == CollaborationMode.CHAPTER_LOCK and (result.conflicts or result.facts):
            chapter_user_map = {
                chapter.get("id"): chapter.get("assigned_to")
                for chapter in room.chapters
                if chapter.get("assigned_to")
            }
            
            # 为每个冲突找到相关章节
            def get_related_chapters_for_content(content: str) -> set:
                related = set()
                if not content:
                    return related
                content_lower = content.lower()[:100]  # 取前100字符进行匹配
                for chapter in room.chapters:
                    chapter_content = chapter.get("content", "").lower()
                    if content_lower in chapter_content:
                        related.add(chapter.get("id"))
                return related
            
            # 按用户分组冲突
            user_conflicts = {}
            user_facts = {}
            
            for conflict in result.conflicts:
                conflict_dict = conflict.model_dump()
                
                # 查找冲突相关的章节
                related_chapters = set()
                related_chapters.update(get_related_chapters_for_content(conflict.fact_a_content))
                related_chapters.update(get_related_chapters_for_content(conflict.fact_b_content))
                
                # 分发给相关章节的负责用户
                for chapter_id in related_chapters:
                    if chapter_id in chapter_user_map:
                        user_id = chapter_user_map[chapter_id]
                        if user_id not in user_conflicts:
                            user_conflicts[user_id] = []
                        if conflict_dict not in user_conflicts[user_id]:
                            user_conflicts[user_id].append(conflict_dict)
            
            # 按用户分组事实
            for fact in result.facts:
                fact_dict = fact.model_dump()
                
                # 查找事实相关的章节
                related_chapters = get_related_chapters_for_content(fact.content)
                if not related_chapters and fact.source_text:
                    related_chapters = get_related_chapters_for_content(fact.source_text)
                
                # 分发给相关章节的负责用户
                for chapter_id in related_chapters:
                    if chapter_id in chapter_user_map:
                        user_id = chapter_user_map[chapter_id]
                        if user_id not in user_facts:
                            user_facts[user_id] = []
                        if fact_dict not in user_facts[user_id]:
                            user_facts[user_id].append(fact_dict)
            
            # 发送个性化通知给每个用户
            for user_id in set(list(user_conflicts.keys()) + list(user_facts.keys())):
                user_conflict_list = user_conflicts.get(user_id, [])
                user_fact_list = user_facts.get(user_id, [])
                
                # 跳过房主，房主会单独收到所有数据
                if user_id == room.owner_id:
                    continue
                
                await ws_manager.connection_manager.send_personal(
                    room_id,
                    user_id,
                    {
                        "type": "chapter_conflicts",
                        "data": {
                            "message": f"检测到 {len(user_conflict_list)} 个与您负责章节相关的冲突，{len(user_fact_list)} 个事实",
                            "conflicts": user_conflict_list,
                            "facts": user_fact_list,
                        }
                    }
                )
            
            # 房主收到所有冲突和事实
            await ws_manager.connection_manager.send_personal(
                room_id,
                room.owner_id,
                {
                    "type": "all_conflicts",
                    "data": {
                        "message": f"检测完成，共发现 {result.total_conflicts} 个冲突，{result.total_facts} 个事实",
                        "conflicts": [c.model_dump() for c in result.conflicts],
                        "facts": [f.model_dump() for f in result.facts] if result.facts else [],
                        "is_owner_view": True,
                    }
                }
            )
        
        # 返回结果
        # 如果是房主或实时协作模式，返回全部数据
        if is_owner or room.mode == CollaborationMode.REALTIME:
            return {
                "task_id": result.task_id,
                "total_facts": result.total_facts,
                "total_conflicts": result.total_conflicts,
                "conflicts": [c.model_dump() for c in result.conflicts],
                "facts": [f.model_dump() for f in result.facts] if hasattr(result, 'facts') and result.facts else [],
                "detection_time": result.detection_time,
            }
        else:
            # 非房主在章节锁定模式下，只返回自己章节相关的数据
            my_chapters = [
                chapter.get("id")
                for chapter in room.chapters
                if chapter.get("assigned_to") == requester_id
            ]
            
            # 过滤冲突
            my_conflicts = []
            for conflict in result.conflicts:
                for chapter in room.chapters:
                    if chapter.get("id") in my_chapters:
                        chapter_content = chapter.get("content", "").lower()
                        if (conflict.fact_a_content and conflict.fact_a_content.lower()[:50] in chapter_content) or \
                           (conflict.fact_b_content and conflict.fact_b_content.lower()[:50] in chapter_content):
                            my_conflicts.append(conflict.model_dump())
                            break
            
            # 过滤事实
            my_facts = []
            for fact in result.facts:
                for chapter in room.chapters:
                    if chapter.get("id") in my_chapters:
                        chapter_content = chapter.get("content", "").lower()
                        if fact.content.lower()[:50] in chapter_content:
                            my_facts.append(fact.model_dump())
                            break
            
            return {
                "task_id": result.task_id,
                "total_facts": len(my_facts),
                "total_conflicts": len(my_conflicts),
                "conflicts": my_conflicts,
                "facts": my_facts,
                "detection_time": result.detection_time,
                "filtered_for_user": True,
            }
    
    return {"message": "检测已跳过或正在进行中", "conflicts": [], "facts": []}


@router.get("/rooms/{room_id}/detection/status", response_model=DetectionStatusResponse)
async def get_detection_status(room_id: str):
    """获取房间检测状态"""
    room_manager = get_room_manager()
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")

    detector = get_realtime_detector()
    editor = get_document_editor()
    lock_info = await editor.check_detection_lock("room", room_id)
    is_detecting = detector.is_detecting(room_id) or bool(lock_info) or bool(room.is_detecting)

    return DetectionStatusResponse(
        is_detecting=is_detecting,
        room_is_detecting=room.is_detecting,
        lock=lock_info,
        last_detection_time=room.last_detection_time.isoformat() if room.last_detection_time else None,
    )


@router.post("/rooms/{room_id}/detection/cancel")
async def cancel_detection(room_id: str):
    """取消房间冲突检测"""
    room_manager = get_room_manager()
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")

    detector = get_realtime_detector()
    await detector.request_cancel(room_id)

    editor = get_document_editor()
    lock_info = await editor.check_detection_lock("room", room_id)
    if lock_info:
        await editor.release_detection_lock("room", room_id, lock_info.get("task_id"))

    room.is_detecting = False
    await room_manager._save_room(room)

    ws_manager = get_ws_manager()
    await ws_manager.connection_manager.broadcast_to_room(
        room_id,
        {
            "type": MessageType.DETECTION_CANCEL,
            "room_id": room_id,
            "data": {
                "message": "检测已取消",
                "task_id": lock_info.get("task_id") if lock_info else None,
            },
        }
    )

    return {
        "message": "检测已取消",
        "task_id": lock_info.get("task_id") if lock_info else None,
    }


@router.get("/rooms/{room_id}/conflicts")
async def get_room_conflicts(
    room_id: str,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    获取房间最近的冲突检测结果
    """
    room_manager = get_room_manager()
    detector = get_realtime_detector()
    room = await room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")

    result = await detector.get_last_result(room_id)

    if not result:
        return {"message": "暂无检测结果", "conflicts": [], "facts": []}

    requester_id = current_user.user_id if current_user else None
    is_owner = requester_id == room.owner_id

    if room.mode == CollaborationMode.CHAPTER_LOCK and not is_owner:
        my_chapters = [
            chapter.get("id")
            for chapter in room.chapters
            if chapter.get("assigned_to") == requester_id
        ]

        def is_related_to_my_chapter(text: str) -> bool:
            if not text:
                return False
            snippet = text.lower()[:50]
            for chapter in room.chapters:
                if chapter.get("id") in my_chapters:
                    chapter_content = (chapter.get("content") or "").lower()
                    if snippet and snippet in chapter_content:
                        return True
            return False

        filtered_conflicts = []
        for conflict in result.conflicts:
            if is_related_to_my_chapter(conflict.fact_a_content) or is_related_to_my_chapter(conflict.fact_b_content):
                filtered_conflicts.append(conflict.model_dump())

        filtered_facts = []
        for fact in result.facts:
            if is_related_to_my_chapter(fact.content) or is_related_to_my_chapter(fact.source_text or ""):
                filtered_facts.append(fact.model_dump())

        return {
            "task_id": result.task_id,
            "detected_at": result.detected_at.isoformat(),
            "total_facts": len(filtered_facts),
            "total_conflicts": len(filtered_conflicts),
            "conflicts": filtered_conflicts,
            "facts": filtered_facts,
            "detection_time": result.detection_time,
            "filtered_for_user": True,
        }

    return {
        "task_id": result.task_id,
        "detected_at": result.detected_at.isoformat(),
        "total_facts": result.total_facts,
        "total_conflicts": result.total_conflicts,
        "conflicts": [c.model_dump() for c in result.conflicts],
        "facts": [f.model_dump() for f in result.facts] if result.facts else [],
        "detection_time": result.detection_time,
    }


# ==================== WebSocket 端点 ====================

@router.websocket("/ws/{room_id}/{user_id}/{username}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
    username: str,
):
    """
    WebSocket连接端点
    
    用于实时协作通信
    """
    ws_manager = get_ws_manager()
    room_manager = get_room_manager()
    lock_service = get_chapter_lock_service()
    detector = get_realtime_detector()
    
    # 注册消息处理器
    async def handle_content_update(rid: str, uid: str, data: dict):
        """处理内容更新"""
        content = data.get("content", "")
        base_version = data.get("version")  # 可选的基础版本号
        content_json = data.get("content_json")
        success, new_version = await room_manager.update_content(
            rid,
            content,
            uid,
            base_version,
            content_json=content_json,
        )
        if success:
            # 广播内容更新，包含新版本号
            await ws_manager.connection_manager.broadcast_content_update(
                rid,
                uid,
                content,
                new_version,
                content_json=content_json,
            )
            await detector.schedule_detection(rid, content)

    async def handle_draft_update(rid: str, uid: str, data: dict):
        """处理临时内容更新（不落库）"""
        content = data.get("content", "")
        content_json = data.get("content_json")
        await ws_manager.connection_manager.broadcast_draft_update(rid, uid, content, content_json)
    
    async def handle_cursor_update(rid: str, uid: str, data: dict):
        """处理光标更新"""
        room = await room_manager.get_room(rid)
        if room and uid in room.members:
            member = room.members[uid]
            if data.get("position") is not None:
                member.cursor_position = data.get("position")
            if data.get("selection_start") is not None:
                member.selection_start = data.get("selection_start")
            if data.get("selection_end") is not None:
                member.selection_end = data.get("selection_end")
            if data.get("mouse_x") is not None:
                member.mouse_x = data.get("mouse_x")
            if data.get("mouse_y") is not None:
                member.mouse_y = data.get("mouse_y")
            await ws_manager.connection_manager.broadcast_cursor_update(
                rid,
                uid,
                member.username,
                member.color,
                member.avatar_url,
                member.cursor_position or data.get("position", 0),
                member.selection_start,
                member.selection_end,
                member.mouse_x,
                member.mouse_y,
            )
    
    async def handle_lock_acquire(rid: str, uid: str, data: dict):
        """处理锁获取"""
        chapter_id = data.get("chapter_id")
        username = data.get("username", "Unknown")
        if chapter_id:
            await lock_service.acquire_lock(rid, chapter_id, uid, username)
            locks = await lock_service.get_room_locks(rid)
            await ws_manager.connection_manager.broadcast_lock_status(
                rid,
                [{"chapter_id": l.chapter_id, "user_id": l.user_id, "username": l.username} for l in locks]
            )
    
    async def handle_lock_release(rid: str, uid: str, data: dict):
        """处理锁释放"""
        chapter_id = data.get("chapter_id")
        if chapter_id:
            await lock_service.release_lock(rid, chapter_id, uid)
            locks = await lock_service.get_room_locks(rid)
            await ws_manager.connection_manager.broadcast_lock_status(
                rid,
                [{"chapter_id": l.chapter_id, "user_id": l.user_id, "username": l.username} for l in locks]
            )
    
    # 注册处理器
    ws_manager.connection_manager.register_handler(MessageType.CONTENT_UPDATE, handle_content_update)
    ws_manager.connection_manager.register_handler(MessageType.DRAFT_UPDATE, handle_draft_update)
    ws_manager.connection_manager.register_handler(MessageType.CURSOR_UPDATE, handle_cursor_update)
    ws_manager.connection_manager.register_handler(MessageType.LOCK_ACQUIRE, handle_lock_acquire)
    ws_manager.connection_manager.register_handler(MessageType.LOCK_RELEASE, handle_lock_release)
    
    # 处理WebSocket连接
    room = await room_manager.get_room(room_id)
    avatar_url = None
    if room and user_id in room.members:
        avatar_url = room.members[user_id].avatar_url
    await ws_manager.handle_websocket(websocket, room_id, user_id, username, avatar_url)
    
    # 连接断开后释放用户的锁
    await lock_service.release_user_locks(room_id, user_id)
    
    # 连接断开后持久化房间内容
    room = await room_manager.get_room(room_id)
    if room:
        await persist_room_to_db(room)

