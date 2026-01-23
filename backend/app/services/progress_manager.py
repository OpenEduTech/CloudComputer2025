"""
进度管理服务
用于追踪和推送实时进度到前端
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ProgressStage(Enum):
    """进度阶段"""
    UPLOAD = "upload"
    EXTRACT_FACTS = "extract_facts"
    DETECT_CONFLICTS = "detect_conflicts"
    VERIFY_FACTS = "verify_facts"
    COMPLETE = "complete"


@dataclass
class ProgressState:
    """进度状态"""
    stage: ProgressStage = ProgressStage.UPLOAD
    stage_label: str = "上传文档"
    current: int = 0
    total: int = 0
    message: str = ""
    sub_message: str = ""
    started_at: float = field(default_factory=time.time)
    completed_stages: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        elapsed = time.time() - self.started_at
        return {
            "stage": self.stage.value,
            "stage_label": self.stage_label,
            "current": self.current,
            "total": self.total,
            "progress": round(self.current / self.total * 100, 1) if self.total > 0 else 0,
            "message": self.message,
            "sub_message": self.sub_message,
            "elapsed_seconds": round(elapsed, 1),
            "completed_stages": self.completed_stages
        }


class ProgressManager:
    """进度管理器 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._progress: Dict[str, ProgressState] = {}
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        logger.info("ProgressManager 初始化完成")
    
    def create_session(self, document_id: str) -> ProgressState:
        """创建新的进度会话"""
        self._progress[document_id] = ProgressState()
        self._listeners[document_id] = []
        logger.info(f"创建进度会话: {document_id}")
        return self._progress[document_id]
    
    def get_progress(self, document_id: str) -> Optional[ProgressState]:
        """获取进度状态"""
        return self._progress.get(document_id)
    
    async def update_progress(
        self,
        document_id: str,
        stage: Optional[ProgressStage] = None,
        stage_label: Optional[str] = None,
        current: Optional[int] = None,
        total: Optional[int] = None,
        message: Optional[str] = None,
        sub_message: Optional[str] = None,
        mark_stage_complete: bool = False
    ):
        """更新进度并通知所有监听者"""
        progress = self._progress.get(document_id)
        if not progress:
            progress = self.create_session(document_id)
        
        # 标记上一阶段完成
        if mark_stage_complete and progress.stage.value not in progress.completed_stages:
            progress.completed_stages.append(progress.stage.value)
        
        # 更新字段
        if stage is not None:
            progress.stage = stage
        if stage_label is not None:
            progress.stage_label = stage_label
        if current is not None:
            progress.current = current
        if total is not None:
            progress.total = total
        if message is not None:
            progress.message = message
        if sub_message is not None:
            progress.sub_message = sub_message
        
        # 通知所有监听者
        await self._notify_listeners(document_id, progress)
    
    async def _notify_listeners(self, document_id: str, progress: ProgressState):
        """通知所有监听该文档的客户端"""
        listeners = self._listeners.get(document_id, [])
        data = progress.to_dict()
        
        for queue in listeners:
            try:
                await queue.put(data)
            except Exception as e:
                logger.error(f"通知监听者失败: {e}")
    
    def subscribe(self, document_id: str) -> asyncio.Queue:
        """订阅进度更新"""
        if document_id not in self._listeners:
            self._listeners[document_id] = []
        
        queue = asyncio.Queue()
        self._listeners[document_id].append(queue)
        logger.info(f"新订阅者加入: {document_id}, 当前订阅数: {len(self._listeners[document_id])}")
        return queue
    
    def unsubscribe(self, document_id: str, queue: asyncio.Queue):
        """取消订阅"""
        if document_id in self._listeners:
            try:
                self._listeners[document_id].remove(queue)
                logger.info(f"订阅者离开: {document_id}, 剩余订阅数: {len(self._listeners[document_id])}")
            except ValueError:
                pass
    
    def cleanup(self, document_id: str):
        """清理会话"""
        if document_id in self._progress:
            del self._progress[document_id]
        if document_id in self._listeners:
            del self._listeners[document_id]
        logger.info(f"清理进度会话: {document_id}")


# 全局实例
progress_manager = ProgressManager()

