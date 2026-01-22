"""
PatPat-Inconsistency-Hunter 协作服务模块
提供多人协同编辑和分章节锁定编辑功能
"""

from .room_manager import RoomManager, Room, RoomMember
from .chapter_lock import ChapterLockService, ChapterLock
from .realtime_detector import RealtimeConflictDetector
from .websocket_manager import WebSocketManager, ConnectionManager

__all__ = [
    "RoomManager",
    "Room",
    "RoomMember",
    "ChapterLockService",
    "ChapterLock",
    "RealtimeConflictDetector",
    "WebSocketManager",
    "ConnectionManager",
]

