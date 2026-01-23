"""
PatPat-Inconsistency-Hunter WebSocket管理器
处理实时通信和消息广播
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, Callable
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ...utils.logger import logger
from .room_manager import RoomMember


class MessageType(str, Enum):
    """消息类型"""
    # 连接相关
    JOIN = "join"
    LEAVE = "leave"
    USER_LIST = "user_list"
    
    # 编辑相关
    CONTENT_UPDATE = "content_update"
    DRAFT_UPDATE = "draft_update"
    CURSOR_UPDATE = "cursor_update"
    SELECTION_UPDATE = "selection_update"
    
    # 章节锁定相关
    LOCK_ACQUIRE = "lock_acquire"
    LOCK_RELEASE = "lock_release"
    LOCK_STATUS = "lock_status"
    CHAPTER_UPDATE = "chapter_update"
    
    # 冲突检测相关
    CONFLICT_DETECTED = "conflict_detected"
    DETECTION_START = "detection_start"
    DETECTION_COMPLETE = "detection_complete"
    DETECTION_CANCEL = "detection_cancel"
    
    # 系统消息
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: MessageType
    room_id: str
    user_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ConnectionInfo(BaseModel):
    """连接信息"""
    websocket: Any  # WebSocket对象
    user_id: str
    username: str
    avatar_url: Optional[str] = None
    room_id: str
    connected_at: datetime = Field(default_factory=datetime.now)
    last_ping: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True


class ConnectionManager:
    """
    WebSocket连接管理器
    
    管理所有WebSocket连接，处理消息路由和广播
    """
    
    def __init__(self):
        # room_id -> user_id -> ConnectionInfo
        self._connections: Dict[str, Dict[str, ConnectionInfo]] = {}
        # 消息处理器
        self._handlers: Dict[MessageType, List[Callable]] = {}
        # 心跳任务
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def connect(
        self,
        websocket: WebSocket,
        room_id: str,
        user_id: str,
        username: str,
        avatar_url: Optional[str] = None,
    ) -> bool:
        """
        建立WebSocket连接
        
        Args:
            websocket: WebSocket对象
            room_id: 房间ID
            user_id: 用户ID
            username: 用户名
        
        Returns:
            是否成功连接
        """
        try:
            await websocket.accept()
            
            # 初始化房间连接池
            if room_id not in self._connections:
                self._connections[room_id] = {}
            
            # 如果用户已有连接，关闭旧连接
            if user_id in self._connections[room_id]:
                old_conn = self._connections[room_id][user_id]
                try:
                    await old_conn.websocket.close()
                except Exception:
                    pass
            
            # 保存新连接
            conn_info = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                username=username,
                avatar_url=avatar_url,
                room_id=room_id,
            )
            self._connections[room_id][user_id] = conn_info
            
            logger.info(f"WebSocket连接建立: room={room_id}, user={username}")
            
            # 广播用户加入消息
            await self.broadcast_to_room(
                room_id,
                WebSocketMessage(
                    type=MessageType.JOIN,
                    room_id=room_id,
                    user_id=user_id,
                    data={
                        "username": username,
                        "user_id": user_id,
                        "avatar_url": avatar_url,
                    }
                ),
                exclude_user=user_id,
            )
            
            # 发送当前用户列表
            await self.send_user_list(room_id, user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return False
    
    async def disconnect(self, room_id: str, user_id: str):
        """
        断开WebSocket连接
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
        """
        if room_id in self._connections and user_id in self._connections[room_id]:
            conn_info = self._connections[room_id][user_id]
            username = conn_info.username
            
            del self._connections[room_id][user_id]
            
            # 如果房间为空，清理
            if not self._connections[room_id]:
                del self._connections[room_id]
            
            logger.info(f"WebSocket连接断开: room={room_id}, user={username}")
            
            # 广播用户离开消息
            await self.broadcast_to_room(
                room_id,
                WebSocketMessage(
                    type=MessageType.LEAVE,
                    room_id=room_id,
                    user_id=user_id,
                    data={
                        "username": username,
                        "user_id": user_id,
                    }
                ),
            )

    async def disconnect_user(self, room_id: str, user_id: str):
        """
        强制断开用户的WebSocket连接（用于踢人）
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
        """
        if room_id in self._connections and user_id in self._connections[room_id]:
            conn_info = self._connections[room_id][user_id]
            try:
                # 尝试关闭WebSocket连接
                await conn_info.websocket.close(code=1000, reason="You have been removed from the room")
            except Exception as e:
                logger.warning(f"关闭WebSocket连接失败: {e}")
            
            # 调用普通断开逻辑
            await self.disconnect(room_id, user_id)
    
    async def send_personal(
        self,
        room_id: str,
        user_id: str,
        message: Any,  # 支持 WebSocketMessage 或 dict
    ):
        """
        发送个人消息
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            message: 消息对象（WebSocketMessage 或 dict）
        """
        if room_id in self._connections and user_id in self._connections[room_id]:
            conn_info = self._connections[room_id][user_id]
            try:
                # 支持 Pydantic 模型和普通字典
                if hasattr(message, 'model_dump'):
                    message_json = message.model_dump(mode='json')
                else:
                    message_json = message
                await conn_info.websocket.send_json(message_json)
            except Exception as e:
                logger.error(f"发送个人消息失败: {e}")
                await self.disconnect(room_id, user_id)
    
    async def broadcast_to_room(
        self,
        room_id: str,
        message: Any,  # 支持 WebSocketMessage 或 dict
        exclude_user: Optional[str] = None,
    ):
        """
        向房间广播消息
        
        Args:
            room_id: 房间ID
            message: 消息对象（WebSocketMessage 或 dict）
            exclude_user: 排除的用户ID
        """
        if room_id not in self._connections:
            return
        
        disconnected = []
        # 支持 Pydantic 模型和普通字典
        if hasattr(message, 'model_dump'):
            message_json = message.model_dump(mode='json')
        else:
            message_json = message
        
        for user_id, conn_info in self._connections[room_id].items():
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                await conn_info.websocket.send_json(message_json)
            except Exception as e:
                logger.error(f"广播消息失败: user={user_id}, error={e}")
                disconnected.append(user_id)
        
        # 清理断开的连接
        for user_id in disconnected:
            await self.disconnect(room_id, user_id)
    
    async def send_user_list(self, room_id: str, to_user_id: str):
        """
        发送用户列表
        
        Args:
            room_id: 房间ID
            to_user_id: 目标用户ID
        """
        if room_id not in self._connections:
            return
        
        users = []
        for user_id, conn_info in self._connections[room_id].items():
            users.append({
                "user_id": user_id,
                "username": conn_info.username,
                "avatar_url": conn_info.avatar_url,
                "connected_at": conn_info.connected_at.isoformat(),
            })
        
        await self.send_personal(
            room_id,
            to_user_id,
            WebSocketMessage(
                type=MessageType.USER_LIST,
                room_id=room_id,
                data={"users": users}
            )
        )
    
    async def broadcast_user_list(self, room_id: str, members: Dict[str, RoomMember]):
        """
        向房间所有在线成员广播最新成员列表
        """
        if room_id not in self._connections:
            return
        
        users = []
        for user_id, member in members.items():
            users.append({
                "user_id": user_id,
                "username": getattr(member, "username", ""),
                "avatar_url": getattr(member, "avatar_url", None),
            })
        
        broadcast_message = WebSocketMessage(
            type=MessageType.USER_LIST,
            room_id=room_id,
            data={"users": users},
        )
        
        await self.broadcast_to_room(room_id, broadcast_message)
    
    async def broadcast_content_update(
        self,
        room_id: str,
        user_id: str,
        content: str,
        version: int = 0,
        content_json: Optional[Dict[str, Any]] = None,
    ):
        """
        广播内容更新
        
        Args:
            room_id: 房间ID
            user_id: 操作用户ID
            content: 新内容
            version: 版本号
        """
        await self.broadcast_to_room(
            room_id,
            WebSocketMessage(
                type=MessageType.CONTENT_UPDATE,
                room_id=room_id,
                user_id=user_id,
                data={
                    "content": content,
                    "version": version,
                    "content_json": content_json,
                }
            ),
            exclude_user=user_id,
        )

    async def broadcast_draft_update(
        self,
        room_id: str,
        user_id: str,
        content: str,
        content_json: Optional[Dict[str, Any]] = None,
    ):
        """
        广播临时内容更新（不落库）
        """
        await self.broadcast_to_room(
            room_id,
            WebSocketMessage(
                type=MessageType.DRAFT_UPDATE,
                room_id=room_id,
                user_id=user_id,
                data={
                    "content": content,
                    "content_json": content_json,
                }
            ),
            exclude_user=user_id,
        )
    
    async def broadcast_cursor_update(
        self,
        room_id: str,
        user_id: str,
        username: str,
        color: str,
        avatar_url: Optional[str],
        position: int,
        selection_start: Optional[int] = None,
        selection_end: Optional[int] = None,
        mouse_x: Optional[float] = None,
        mouse_y: Optional[float] = None,
    ):
        """
        广播光标更新
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            username: 用户名
            color: 用户颜色
            position: 光标位置
            selection_start: 选区起始
            selection_end: 选区结束
        """
        await self.broadcast_to_room(
            room_id,
            WebSocketMessage(
                type=MessageType.CURSOR_UPDATE,
                room_id=room_id,
                user_id=user_id,
                data={
                    "username": username,
                    "color": color,
                    "avatar_url": avatar_url,
                    "position": position,
                    "selection_start": selection_start,
                    "selection_end": selection_end,
                    "mouse_x": mouse_x,
                    "mouse_y": mouse_y,
                }
            ),
            exclude_user=user_id,
        )
    
    async def broadcast_lock_status(
        self,
        room_id: str,
        locks: List[Dict],
    ):
        """
        广播锁状态
        
        Args:
            room_id: 房间ID
            locks: 锁列表
        """
        await self.broadcast_to_room(
            room_id,
            WebSocketMessage(
                type=MessageType.LOCK_STATUS,
                room_id=room_id,
                data={"locks": locks}
            )
        )
    
    async def broadcast_conflict_detected(
        self,
        room_id: str,
        conflicts: List[Dict],
    ):
        """
        广播检测到的冲突
        
        Args:
            room_id: 房间ID
            conflicts: 冲突列表
        """
        await self.broadcast_to_room(
            room_id,
            WebSocketMessage(
                type=MessageType.CONFLICT_DETECTED,
                room_id=room_id,
                data={"conflicts": conflicts}
            )
        )
    
    def get_room_user_count(self, room_id: str) -> int:
        """获取房间用户数"""
        if room_id not in self._connections:
            return 0
        return len(self._connections[room_id])
    
    def get_room_users(self, room_id: str) -> List[Dict]:
        """获取房间用户列表"""
        if room_id not in self._connections:
            return []
        
        return [
            {
                "user_id": user_id,
                "username": conn.username,
            }
            for user_id, conn in self._connections[room_id].items()
        ]
    
    def is_user_online(self, room_id: str, user_id: str) -> bool:
        """
        检查用户是否在线（有活跃的WebSocket连接）
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
        
        Returns:
            用户是否在线
        """
        if room_id not in self._connections:
            return False
        return user_id in self._connections[room_id]
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """注册消息处理器"""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
    
    async def handle_message(
        self,
        room_id: str,
        user_id: str,
        message: Dict,
    ):
        """
        处理收到的消息
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            message: 消息字典
        """
        try:
            msg_type = MessageType(message.get("type"))
            
            # 处理心跳
            if msg_type == MessageType.PING:
                await self.send_personal(
                    room_id,
                    user_id,
                    WebSocketMessage(
                        type=MessageType.PONG,
                        room_id=room_id,
                    )
                )
                # 更新最后活跃时间
                if room_id in self._connections and user_id in self._connections[room_id]:
                    self._connections[room_id][user_id].last_ping = datetime.now()
                return
            
            # 调用注册的处理器
            if msg_type in self._handlers:
                for handler in self._handlers[msg_type]:
                    await handler(room_id, user_id, message.get("data", {}))
                    
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            await self.send_personal(
                room_id,
                user_id,
                WebSocketMessage(
                    type=MessageType.ERROR,
                    room_id=room_id,
                    data={"error": str(e)}
                )
            )


class WebSocketManager:
    """
    WebSocket管理器（高级封装）
    
    整合连接管理、消息路由和业务逻辑
    """
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
    
    async def handle_websocket(
        self,
        websocket: WebSocket,
        room_id: str,
        user_id: str,
        username: str,
        avatar_url: Optional[str] = None,
    ):
        """
        处理WebSocket连接的完整生命周期
        
        Args:
            websocket: WebSocket对象
            room_id: 房间ID
            user_id: 用户ID
            username: 用户名
        """
        connected = await self.connection_manager.connect(
            websocket, room_id, user_id, username, avatar_url
        )
        
        if not connected:
            return
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_json()
                await self.connection_manager.handle_message(room_id, user_id, data)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket客户端断开连接: room={room_id}, user={user_id}")
        except Exception as e:
            logger.error(f"WebSocket错误: {e}")
        finally:
            await self.connection_manager.disconnect(room_id, user_id)


# 全局WebSocket管理器实例
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """获取WebSocket管理器单例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager

