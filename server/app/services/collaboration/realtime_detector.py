"""
PatPat-Inconsistency-Hunter 实时冲突检测服务
在协作编辑过程中实时检测文档冲突
"""

import asyncio
import uuid
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

from ...utils.logger import logger
from ...utils.db_session import async_session_maker
from ..document_processor import DocumentProcessor
from ..fact_extractor import FactExtractor
from ..conflict_detector import ConflictDetector
from ..llm_client import get_llm_client
from .room_manager import Room, CollaborationMode, get_room_manager
from .websocket_manager import get_ws_manager, MessageType, WebSocketMessage


class FactSummary(BaseModel):
    """事实摘要"""
    fact_id: str
    content: str
    fact_type: str
    location: str
    source_text: Optional[str] = None
    is_image_source: bool = False  # 是否来自图片


class ConflictSummary(BaseModel):
    """冲突摘要"""
    conflict_id: str
    fact_a_content: str
    fact_a_location: str
    fact_b_content: str
    fact_b_location: str
    conflict_type: str
    severity: float
    description: str
    suggestion: Optional[str] = None
    fact_a: Optional[FactSummary] = None
    fact_b: Optional[FactSummary] = None
    is_image_conflict: bool = False  # 是否涉及图片冲突


class DetectionResult(BaseModel):
    """检测结果"""
    room_id: str
    task_id: Optional[str] = None  # 任务编号
    detected_at: datetime = Field(default_factory=datetime.now)
    total_facts: int = 0
    total_conflicts: int = 0
    conflicts: List[ConflictSummary] = Field(default_factory=list)
    facts: List[FactSummary] = Field(default_factory=list)
    detection_time: float = 0.0


class RealtimeConflictDetector:
    """
    实时冲突检测器
    
    在协作编辑过程中监控文档变化，自动检测冲突
    """
    
    # 检测配置
    DEBOUNCE_SECONDS = 5       # 防抖时间（用户停止编辑后多久触发检测）
    MIN_INTERVAL_SECONDS = 30  # 最小检测间隔
    MAX_CONTENT_LENGTH = 50000 # 最大检测内容长度
    
    def __init__(self):
        self._pending_detections: Dict[str, asyncio.Task] = {}
        self._last_detection_time: Dict[str, datetime] = {}
        self._detection_results: Dict[str, DetectionResult] = {}
        self._detection_locks: Dict[str, asyncio.Lock] = {}  # 检测锁
        self._is_detecting: Dict[str, bool] = {}  # 检测状态标记
        self._cancel_requests: Set[str] = set()  # 取消检测标记
        self._running_detections: Dict[str, asyncio.Task] = {}  # 正在执行的检测任务
        
        # 处理器
        self._document_processor = DocumentProcessor()
        self._fact_extractor: Optional[FactExtractor] = None
        self._conflict_detector: Optional[ConflictDetector] = None

    def _get_detection_lock(self, room_id: str) -> asyncio.Lock:
        """获取房间的检测锁"""
        if room_id not in self._detection_locks:
            self._detection_locks[room_id] = asyncio.Lock()
        return self._detection_locks[room_id]

    def is_detecting(self, room_id: str) -> bool:
        """检查房间是否正在检测"""
        return self._is_detecting.get(room_id, False)

    def _is_cancelled(self, room_id: str) -> bool:
        """检查是否请求取消检测"""
        return room_id in self._cancel_requests

    async def request_cancel(self, room_id: str):
        """请求取消检测"""
        self._cancel_requests.add(room_id)
        await self.cancel_pending_detection(room_id)
        running_task = self._running_detections.get(room_id)
        if running_task and not running_task.done():
            running_task.cancel()
    
    def _get_fact_extractor(self) -> FactExtractor:
        """获取事实提取器"""
        if self._fact_extractor is None:
            self._fact_extractor = FactExtractor(
                llm_client=get_llm_client(),
                max_concurrency=3,
            )
        return self._fact_extractor
    
    def _get_conflict_detector(self) -> ConflictDetector:
        """获取冲突检测器"""
        if self._conflict_detector is None:
            self._conflict_detector = ConflictDetector(
                llm_client=get_llm_client(),
                max_concurrency=3,
            )
        return self._conflict_detector
    
    async def _enhance_content_with_images(self, content: str, room_id: str) -> str:
        """
        用视觉模型提取的图片描述增强文档内容
        
        Args:
            content: 原始文档内容
            room_id: 房间ID（用于查找图片）
            
        Returns:
            增强后的内容
        """
        # 查找图片占位符 [IMAGE:image_id:alt_text]
        image_pattern = r'\[IMAGE:([^\]:]+)(?::([^\]]+))?\]'
        matches = list(re.finditer(image_pattern, content))
        
        if not matches:
            return content
        
        logger.info(f"发现 {len(matches)} 个图片占位符，开始提取描述")
        
        # 尝试使用视觉服务
        try:
            from ..vision_service import get_vision_service
            vision_service = get_vision_service()
        except ImportError:
            logger.warning("视觉服务不可用，跳过图片处理")
            return content
        
        # 收集需要处理的图片
        images_to_process = []
        for match in matches:
            image_id = match.group(1)
            alt_text = match.group(2) or "图片"
            
            # 先从数据库查找已有的描述
            existing_desc = await self._get_image_description_from_db(image_id, room_id)
            if existing_desc:
                images_to_process.append({
                    "image_id": image_id,
                    "alt_text": alt_text,
                    "description": existing_desc,
                    "match": match,
                    "from_cache": True,
                })
            else:
                # 需要调用视觉模型
                image_path = self._get_image_path(image_id, room_id)
                images_to_process.append({
                    "image_id": image_id,
                    "alt_text": alt_text,
                    "image_path": image_path,
                    "match": match,
                    "from_cache": False,
                })
        
        # 批量处理未缓存的图片
        uncached_images = [img for img in images_to_process if not img.get("from_cache")]
        if uncached_images:
            try:
                descriptions = await vision_service.batch_extract_descriptions([{
                    "image_id": img["image_id"],
                    "image_path": img["image_path"],
                    "context": img["alt_text"],
                } for img in uncached_images])
                
                # 更新描述并保存到数据库
                desc_map = {d["image_id"]: d["description"] for d in descriptions}
                for img in uncached_images:
                    desc = desc_map.get(img["image_id"], f"[图片: {img['alt_text']}]")
                    img["description"] = desc
                    # 保存到数据库
                    await self._save_image_description_to_db(
                        img["image_id"], desc, room_id
                    )
            except Exception as e:
                logger.warning(f"视觉模型处理失败: {e}")
                for img in uncached_images:
                    img["description"] = f"[图片: {img['alt_text']}]"
        
        # 替换内容中的图片占位符
        enhanced_content = content
        for img in reversed(images_to_process):  # 从后往前替换避免位置偏移
            match = img["match"]
            image_id = img["image_id"]
            alt_text = img["alt_text"]
            desc = img.get("description", f"[图片: {alt_text}]")
            
            # 保留 image_id 以便后续提取事实时能关联到具体图片
            replacement = f"\n[图片内容开始: {image_id}: {alt_text}]\n{desc}\n[图片内容结束]\n"
            enhanced_content = (
                enhanced_content[:match.start()] + 
                replacement + 
                enhanced_content[match.end():]
            )
        
        return enhanced_content
    
    def _get_image_path(self, image_id: str, room_id: str) -> str:
        """获取图片文件路径"""
        import os
        from pathlib import Path
        from datetime import datetime, timedelta
        from ..document_editor import UPLOAD_DIR
        
        # 使用配置的 UPLOAD_DIR
        uploads_dir = UPLOAD_DIR if UPLOAD_DIR else Path("uploads/images")
        uploads_dir = Path(uploads_dir) if not isinstance(uploads_dir, Path) else uploads_dir
        
        logger.debug(f"🔍 [realtime_detector] 获取图片路径: image_id={image_id}, UPLOAD_DIR={uploads_dir}")
        
        # 尝试日期格式的路径 (2026/01/18/img_xxx.png)
        if image_id.startswith("img_"):
            for days_ago in range(7):
                date = datetime.now() - timedelta(days=days_ago)
                date_path = date.strftime("%Y/%m/%d")
                for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
                    path = uploads_dir / date_path / f"{image_id}{ext}"
                    if path.exists():
                        logger.debug(f"✅ [realtime_detector] 找到图片: {path}")
                        return str(path.absolute())
        
        # 尝试其他可能的路径
        possible_paths = [
            uploads_dir / image_id,
            uploads_dir / f"{image_id}.png",
            uploads_dir / f"{image_id}.jpg",
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.debug(f"✅ [realtime_detector] 找到图片: {path}")
                return str(path.absolute())
        
        # 返回第一个可能的路径（即使不存在，用于后续处理）
        result = str(possible_paths[0].absolute()) if possible_paths else ""
        logger.debug(f"⚠️ [realtime_detector] 图片不存在，返回: {result}")
        return result
    
    async def _get_image_description_from_db(
        self, image_id: str, room_id: str
    ) -> Optional[str]:
        """从数据库获取已缓存的图片描述"""
        try:
            from ...models.database import DocumentImage
            from sqlalchemy import select
            
            async with async_session_maker() as db:
                result = await db.execute(
                    select(DocumentImage.description)
                    .where(DocumentImage.image_id == image_id)
                    .where(DocumentImage.description.isnot(None))
                )
                row = result.scalar_one_or_none()
                return row if row else None
        except Exception as e:
            logger.debug(f"获取图片描述缓存失败: {e}")
            return None
    
    async def _save_image_description_to_db(
        self, image_id: str, description: str, room_id: str
    ):
        """保存图片描述到数据库（PostgreSQL）"""
        try:
            from ...models.database import DocumentImage
            from sqlalchemy import select, update
            
            async with async_session_maker() as db:
                # 先查找是否存在该图片记录
                result = await db.execute(
                    select(DocumentImage).where(DocumentImage.image_id == image_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # 更新已有记录的描述
                    await db.execute(
                        update(DocumentImage)
                        .where(DocumentImage.image_id == image_id)
                        .values(
                            description=description,
                            description_extracted_at=datetime.now(),
                        )
                    )
                else:
                    # 创建新记录
                    new_image = DocumentImage(
                        image_id=image_id,
                        room_id=room_id,
                        file_name=f"{image_id}.png",
                        file_path=self._get_image_path(image_id, room_id),
                        file_url=f"/api/images/{image_id}",
                        file_size=0,
                        mime_type="image/png",
                        description=description,
                        description_extracted_at=datetime.now(),
                    )
                    db.add(new_image)
                
                await db.commit()
                logger.debug(f"图片描述已保存到PostgreSQL: {image_id}")
        except Exception as e:
            logger.error(f"保存图片描述到PostgreSQL失败: {e}")
    
    async def schedule_detection(self, room_id: str, content: str):
        """
        调度冲突检测（带防抖）
        
        Args:
            room_id: 房间ID
            content: 文档内容
        """
        # 取消之前的待执行检测
        if room_id in self._pending_detections:
            self._pending_detections[room_id].cancel()
        
        # 检查最小间隔
        last_time = self._last_detection_time.get(room_id)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < self.MIN_INTERVAL_SECONDS:
                wait_time = self.MIN_INTERVAL_SECONDS - elapsed + self.DEBOUNCE_SECONDS
            else:
                wait_time = self.DEBOUNCE_SECONDS
        else:
            wait_time = self.DEBOUNCE_SECONDS
        
        # 创建新的延迟检测任务
        async def delayed_detection():
            await asyncio.sleep(wait_time)
            await self.detect_conflicts(room_id, content)
        
        task = asyncio.create_task(delayed_detection())
        self._pending_detections[room_id] = task
    
    async def detect_conflicts(
        self,
        room_id: str,
        content: str,
        force: bool = False,
        owner_user_id: str = None,
        document_title: str = None,
    ) -> Optional[DetectionResult]:
        """
        执行冲突检测
        
        Args:
            room_id: 房间ID
            content: 文档内容
            force: 是否强制检测（忽略间隔限制）
            owner_user_id: 房主用户ID（用于关联到用户）
            document_title: 文档标题
        
        Returns:
            检测结果
        """
        # 检查是否已经在检测
        if self.is_detecting(room_id):
            logger.info(f"房间 {room_id} 正在检测中，跳过本次请求")
            return None
        
        # 检查最小间隔（非强制模式）
        if not force:
            last_time = self._last_detection_time.get(room_id)
            if last_time:
                elapsed = (datetime.now() - last_time).total_seconds()
                if elapsed < self.MIN_INTERVAL_SECONDS:
                    logger.debug(f"跳过检测，距离上次检测仅 {elapsed:.1f}秒")
                    return None
        
        # 检查内容长度
        if len(content) > self.MAX_CONTENT_LENGTH:
            logger.warning(f"内容过长 ({len(content)} 字符)，截断到 {self.MAX_CONTENT_LENGTH}")
            content = content[:self.MAX_CONTENT_LENGTH]
        
        if len(content) < 100:
            logger.debug("内容过短，跳过检测")
            return None
        
        # 获取检测锁
        lock = self._get_detection_lock(room_id)
        if lock.locked():
            logger.info(f"房间 {room_id} 检测锁已被占用")
            return None

        # 获取Redis检测锁
        task_id = f"collab_{room_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        from ..document_editor import get_document_editor
        editor = get_document_editor()
        lock_acquired = await editor.acquire_detection_lock("room", room_id, task_id)
        if not lock_acquired:
            logger.info(f"房间 {room_id} Redis检测锁已被占用")
            return None

        async with lock:
            current_task = asyncio.current_task()
            if current_task:
                self._running_detections[room_id] = current_task
            # 标记正在检测
            self._is_detecting[room_id] = True
            
            logger.info(f"开始实时冲突检测: room={room_id}")
            start_time = datetime.now()
            
            room_manager = get_room_manager()
            room = None

            try:
                # 更新房间状态
                room = await room_manager.get_room(room_id)
                if room:
                    room.is_detecting = True
                    await room_manager._save_room(room)

                # 通知开始检测
                ws_manager = get_ws_manager()
                await ws_manager.connection_manager.broadcast_to_room(
                    room_id,
                    WebSocketMessage(
                        type=MessageType.DETECTION_START,
                        room_id=room_id,
                        data={
                            "message": "正在检测文档冲突...",
                            "task_id": task_id,
                        }
                    )
                )

                if self._is_cancelled(room_id):
                    logger.info(f"房间 {room_id} 检测已被取消")
                    return None

                # 0. 处理图片内容（如果有）
                enhanced_content = await self._enhance_content_with_images(content, room_id)

                # 1. 处理文档，分块
                from ...models.schemas import DocumentInput
                doc_input = DocumentInput(content=enhanced_content)
                chunks, metadata = self._document_processor.process_document(doc_input)
                
                if not chunks:
                    self._is_detecting[room_id] = False
                    return None
                
                if self._is_cancelled(room_id):
                    logger.info(f"房间 {room_id} 检测已被取消")
                    return None

                # 2. 提取事实
                fact_extractor = self._get_fact_extractor()
                facts = await fact_extractor.extract_and_filter(chunks)
                
                if self._is_cancelled(room_id):
                    logger.info(f"房间 {room_id} 检测已被取消")
                    return None

                if len(facts) < 2:
                    logger.info("事实数量不足，无需检测冲突")
                    return DetectionResult(
                        room_id=room_id,
                        task_id=task_id,
                        total_facts=len(facts),
                        total_conflicts=0,
                        conflicts=[],
                        detection_time=(datetime.now() - start_time).total_seconds(),
                    )
            
                # 3. 检测冲突
                conflict_detector = self._get_conflict_detector()
                conflicts = await conflict_detector.detect_conflicts(facts)
                
                if self._is_cancelled(room_id):
                    logger.info(f"房间 {room_id} 检测已被取消")
                    return None
                
                # 4. 构建结果
                # 辅助函数：检查是否是图片来源的事实
                def is_image_fact(fact_type: str) -> bool:
                    return fact_type.startswith("image_") if fact_type else False
                
                # 构建事实摘要
                fact_summaries = []
                for fact in facts:
                    fact_type_str = fact.fact_type.value if hasattr(fact.fact_type, 'value') else str(fact.fact_type)
                    fact_summary = FactSummary(
                        fact_id=fact.fact_id,
                        content=fact.content,
                        fact_type=fact_type_str,
                        location=fact.location_description or "",
                        source_text=fact.source_text[:200] if fact.source_text else None,
                        is_image_source=is_image_fact(fact_type_str),
                    )
                    fact_summaries.append(fact_summary)
                
                # 构建冲突摘要
                conflict_summaries = []
                for conflict in conflicts:
                    fact_a_type = conflict.fact_a.fact_type.value if hasattr(conflict.fact_a.fact_type, 'value') else str(conflict.fact_a.fact_type)
                    fact_b_type = conflict.fact_b.fact_type.value if hasattr(conflict.fact_b.fact_type, 'value') else str(conflict.fact_b.fact_type)
                    is_image_a = is_image_fact(fact_a_type)
                    is_image_b = is_image_fact(fact_b_type)
                    
                    summary = ConflictSummary(
                        conflict_id=conflict.conflict_id,
                        fact_a_content=conflict.fact_a.content,
                        fact_a_location=conflict.fact_a.location_description,
                        fact_b_content=conflict.fact_b.content,
                        fact_b_location=conflict.fact_b.location_description,
                        conflict_type=conflict.conflict_type.value,
                        severity=conflict.severity,
                        description=conflict.description,
                        suggestion=conflict.suggestion,
                        is_image_conflict=is_image_a or is_image_b,
                        fact_a=FactSummary(
                            fact_id=conflict.fact_a.fact_id,
                            content=conflict.fact_a.content,
                            fact_type=fact_a_type,
                            location=conflict.fact_a.location_description or "",
                            source_text=conflict.fact_a.source_text[:200] if conflict.fact_a.source_text else None,
                            is_image_source=is_image_a,
                        ),
                        fact_b=FactSummary(
                            fact_id=conflict.fact_b.fact_id,
                            content=conflict.fact_b.content,
                            fact_type=fact_b_type,
                            location=conflict.fact_b.location_description or "",
                            source_text=conflict.fact_b.source_text[:200] if conflict.fact_b.source_text else None,
                            is_image_source=is_image_b,
                        ),
                    )
                    conflict_summaries.append(summary)
                
                detection_time = (datetime.now() - start_time).total_seconds()
                
                result = DetectionResult(
                    room_id=room_id,
                    task_id=task_id,
                    total_facts=len(facts),
                    total_conflicts=len(conflicts),
                    conflicts=conflict_summaries,
                    facts=fact_summaries,
                    detection_time=detection_time,
                )

                if self._is_cancelled(room_id):
                    logger.info(f"房间 {room_id} 检测已被取消")
                    return None
                
                # 保存检测结果到数据库
                await self._save_detection_to_db(
                    task_id=task_id,
                    room_id=room_id,
                    content=content,
                    title=document_title or room.document_title if room else "协作文档",
                    facts=facts,
                    conflicts=conflicts,
                    detection_time=detection_time,
                    owner_user_id=owner_user_id or (room.owner_id if room else None),
                    collaboration_mode=room.mode if room else None,
                )
                
                # 保存结果到内存缓存
                self._detection_results[room_id] = result
                self._last_detection_time[room_id] = datetime.now()
                
                # 更新房间状态
                if room:
                    room.is_detecting = False
                    room.last_detection_time = datetime.now()
                    await room_manager._save_room(room)

                if self._is_cancelled(room_id):
                    logger.info(f"房间 {room_id} 检测已被取消")
                    return None
                
                # 广播检测结果（chapter_lock 按用户分发）
                if room and room.mode == CollaborationMode.CHAPTER_LOCK:
                    await self._broadcast_chapter_lock_results(
                        room,
                        task_id,
                        conflict_summaries,
                        fact_summaries,
                        result.detection_time,
                    )
                else:
                    await ws_manager.connection_manager.broadcast_to_room(
                        room_id,
                        WebSocketMessage(
                            type=MessageType.DETECTION_COMPLETE,
                            room_id=room_id,
                            data={
                                "task_id": task_id,
                                "total_facts": result.total_facts,
                                "total_conflicts": result.total_conflicts,
                                "detection_time": result.detection_time,
                                "conflicts": [c.model_dump() for c in conflict_summaries],
                                "facts": [f.model_dump() for f in fact_summaries],
                            }
                        )
                    )

                    if conflict_summaries:
                        await ws_manager.connection_manager.broadcast_conflict_detected(
                            room_id,
                            [c.model_dump() for c in conflict_summaries],
                        )
                
                logger.info(
                    f"实时冲突检测完成: room={room_id}, "
                    f"facts={result.total_facts}, conflicts={result.total_conflicts}, "
                    f"time={detection_time:.2f}s"
                )
                
                return result

            except asyncio.CancelledError:
                logger.info(f"实时冲突检测被取消: room={room_id}")
                return None
            except Exception as e:
                logger.error(f"实时冲突检测失败: {e}")

                # 通知检测失败
                ws_manager = get_ws_manager()
                await ws_manager.connection_manager.broadcast_to_room(
                    room_id,
                    WebSocketMessage(
                        type=MessageType.ERROR,
                        room_id=room_id,
                        data={"error": f"冲突检测失败: {str(e)}"}
                    )
                )

                return None
            finally:
                # 清理检测状态
                was_cancelled = self._is_cancelled(room_id)
                if current_task and self._running_detections.get(room_id) is current_task:
                    del self._running_detections[room_id]
                self._is_detecting[room_id] = False
                if room:
                    room.is_detecting = False
                    await room_manager._save_room(room)
                await editor.release_detection_lock("room", room_id, task_id)
                if was_cancelled:
                    ws_manager = get_ws_manager()
                    await ws_manager.connection_manager.broadcast_to_room(
                        room_id,
                        WebSocketMessage(
                            type=MessageType.DETECTION_CANCEL,
                            room_id=room_id,
                            data={
                                "message": "检测已取消",
                                "task_id": task_id,
                            }
                        )
                    )
                self._cancel_requests.discard(room_id)

    async def _broadcast_chapter_lock_results(
        self,
        room: Room,
        task_id: str,
        conflicts: List[ConflictSummary],
        facts: List[FactSummary],
        detection_time: float,
    ) -> None:
        ws_manager = get_ws_manager()

        chapter_contents = {
            chapter.get("id"): (chapter.get("content") or "").lower()
            for chapter in room.chapters
        }
        chapter_user_map = {
            chapter.get("id"): chapter.get("assigned_to")
            for chapter in room.chapters
            if chapter.get("assigned_to")
        }
        user_chapters: Dict[str, Set[str]] = {}
        for chapter_id, user_id in chapter_user_map.items():
            user_chapters.setdefault(user_id, set()).add(chapter_id)

        def find_related_chapters(texts: List[Optional[str]]) -> Set[str]:
            related: Set[str] = set()
            for text in texts:
                if not text:
                    continue
                normalized = " ".join(text.lower().split()).strip()
                if not normalized:
                    continue
                snippet = normalized[:100]
                for chapter_id, chapter_content in chapter_contents.items():
                    if snippet and snippet in chapter_content:
                        related.add(chapter_id)
            return related

        user_conflicts: Dict[str, List[dict]] = {user_id: [] for user_id in room.members.keys()}
        for conflict in conflicts:
            related_chapters = find_related_chapters([
                conflict.fact_a_content,
                conflict.fact_b_content,
                conflict.fact_a.source_text if conflict.fact_a else None,
                conflict.fact_b.source_text if conflict.fact_b else None,
            ])
            if not related_chapters:
                continue
            conflict_dict = conflict.model_dump()
            for user_id, chapters in user_chapters.items():
                if related_chapters.intersection(chapters):
                    user_conflicts.setdefault(user_id, []).append(conflict_dict)

        user_facts: Dict[str, List[dict]] = {user_id: [] for user_id in room.members.keys()}
        for fact in facts:
            related_chapters = find_related_chapters([
                fact.content,
                fact.source_text,
            ])
            if not related_chapters:
                continue
            fact_dict = fact.model_dump()
            for user_id, chapters in user_chapters.items():
                if related_chapters.intersection(chapters):
                    user_facts.setdefault(user_id, []).append(fact_dict)

        for user_id in room.members.keys():
            if user_id == room.owner_id:
                await ws_manager.connection_manager.send_personal(
                    room.room_id,
                    user_id,
                    {
                        "type": MessageType.DETECTION_COMPLETE,
                        "room_id": room.room_id,
                        "data": {
                            "task_id": task_id,
                            "total_facts": len(facts),
                            "total_conflicts": len(conflicts),
                            "detection_time": detection_time,
                            "conflicts": [c.model_dump() for c in conflicts],
                            "facts": [f.model_dump() for f in facts],
                            "is_owner_view": True,
                        },
                    },
                )
                continue

            filtered_conflicts = user_conflicts.get(user_id, [])
            filtered_facts = user_facts.get(user_id, [])
            await ws_manager.connection_manager.send_personal(
                room.room_id,
                user_id,
                {
                    "type": MessageType.DETECTION_COMPLETE,
                    "room_id": room.room_id,
                    "data": {
                        "task_id": task_id,
                        "total_facts": len(filtered_facts),
                        "total_conflicts": len(filtered_conflicts),
                        "detection_time": detection_time,
                        "conflicts": filtered_conflicts,
                        "facts": filtered_facts,
                        "filtered_for_user": True,
                    },
                },
            )
    
    async def _save_detection_to_db(
        self,
        task_id: str,
        room_id: str,
        content: str,
        title: str,
        facts: list,
        conflicts: list,
        detection_time: float,
        owner_user_id: str = None,
        collaboration_mode: Optional[CollaborationMode] = None,
    ):
        """
        保存检测结果到数据库
        
        Args:
            task_id: 任务ID
            room_id: 房间ID  
            content: 文档内容
            title: 文档标题
            facts: 事实列表
            conflicts: 冲突列表
            detection_time: 检测耗时
            owner_user_id: 房主用户ID
        """
        try:
            from ...models.database import Document, FactRecord, ConflictRecord, AnalysisHistory, User
            from sqlalchemy import select
            
            async with async_session_maker() as db:
                # 获取用户数据库ID
                user_db_id = None
                if owner_user_id:
                    user_result = await db.execute(
                        select(User).where(User.user_id == owner_user_id)
                    )
                    user = user_result.scalar_one_or_none()
                    if user:
                        user_db_id = user.id
                
                def build_collaboration_title(raw_title: str) -> str:
                    base_title = (raw_title or "协作文档").strip()
                    base_title = re.sub(r"^\s*(\[[^\]]+\]\s*)+", "", base_title).strip()
                    label = "[协作][分章节]" if collaboration_mode == CollaborationMode.CHAPTER_LOCK else "[协作]"
                    return f"{label} {base_title}".strip() if base_title else label

                # 创建文档记录
                content_hash = hashlib.md5(content.encode()).hexdigest()
                doc = Document(
                    task_id=task_id,
                    title=build_collaboration_title(title),
                    content=content,
                    content_length=len(content),
                    content_hash=content_hash,
                    status="completed",
                    progress=100.0,
                    total_facts=len(facts),
                    total_conflicts=len(conflicts),
                    analysis_time=detection_time,
                    completed_at=datetime.now(),
                    doc_metadata={
                        "room_id": room_id,
                        "user_id": owner_user_id,
                        "source": "collaboration",
                        "user_db_id": user_db_id,
                    }
                )
                db.add(doc)
                await db.flush()  # 获取 doc.id
                
                # 保存事实记录
                for fact in facts:
                    # 获取 source_position 元组 (start, end)
                    source_start = 0
                    source_end = 0
                    if hasattr(fact, 'source_position') and fact.source_position:
                        source_start = fact.source_position[0] if len(fact.source_position) > 0 else 0
                        source_end = fact.source_position[1] if len(fact.source_position) > 1 else 0
                    
                    # 获取 chunk_id (可能叫 source_chunk_id)
                    chunk_id = ""
                    if hasattr(fact, 'source_chunk_id'):
                        chunk_id = fact.source_chunk_id or ""
                    elif hasattr(fact, 'chunk_id'):
                        chunk_id = fact.chunk_id or ""
                    
                    # 检查是否来自图片
                    fact_type_str = fact.fact_type.value if hasattr(fact.fact_type, 'value') else str(fact.fact_type)
                    is_image_source = fact_type_str.startswith('image_') if fact_type_str else False
                    
                    fact_record = FactRecord(
                        fact_id=fact.fact_id,
                        document_id=doc.id,
                        content=fact.content,
                        fact_type=fact_type_str,
                        confidence=fact.confidence,
                        source_text=fact.source_text or "",
                        source_start=source_start,
                        source_end=source_end,
                        chapter=getattr(fact, 'chapter', None),
                        section=getattr(fact, 'section', None),
                        chunk_id=chunk_id,
                        is_image_source=is_image_source,
                        image_id=getattr(fact, 'image_source_id', None),
                        image_description=getattr(fact, 'image_description', None),
                    )
                    db.add(fact_record)
                
                # 保存冲突记录
                for conflict in conflicts:
                    # 检查是否涉及图片冲突
                    fact_a_type = conflict.fact_a.fact_type.value if hasattr(conflict.fact_a.fact_type, 'value') else str(conflict.fact_a.fact_type)
                    fact_b_type = conflict.fact_b.fact_type.value if hasattr(conflict.fact_b.fact_type, 'value') else str(conflict.fact_b.fact_type)
                    is_image_conflict = (
                        (fact_a_type and fact_a_type.startswith('image_')) or 
                        (fact_b_type and fact_b_type.startswith('image_'))
                    )
                    
                    conflict_record = ConflictRecord(
                        conflict_id=conflict.conflict_id,
                        document_id=doc.id,
                        fact_a_id=conflict.fact_a.fact_id,
                        fact_b_id=conflict.fact_b.fact_id,
                        conflict_type=conflict.conflict_type.value if hasattr(conflict.conflict_type, 'value') else str(conflict.conflict_type),
                        severity=conflict.severity,
                        description=conflict.description,
                        suggestion=conflict.suggestion,
                        is_image_conflict=is_image_conflict,
                    )
                    db.add(conflict_record)
                
                # 创建分析历史记录
                history = AnalysisHistory(
                    task_id=task_id,
                    step_name="collaboration_detection",
                    step_status="completed",
                    step_detail=f"协作房间 {room_id} 冲突检测完成: {len(facts)}个事实, {len(conflicts)}个冲突",
                    output_data={
                        "room_id": room_id,
                        "total_facts": len(facts),
                        "total_conflicts": len(conflicts),
                        "analysis_time": detection_time,
                        "document_length": len(content),
                        "user_id": owner_user_id,
                    },
                    duration=detection_time,
                )
                db.add(history)
                
                await db.commit()
                logger.info(f"协作检测结果已保存到数据库: task_id={task_id}, room_id={room_id}")
                
        except Exception as e:
            logger.error(f"保存协作检测结果到数据库失败: {e}")
    
    async def get_last_result(self, room_id: str) -> Optional[DetectionResult]:
        """获取上次检测结果"""
        # 先从内存缓存获取
        result = self._detection_results.get(room_id)
        if result:
            return result
        
        # 从数据库获取最新检测结果
        try:
            from ...models.database import Document, FactRecord, ConflictRecord
            from sqlalchemy import select, desc
            
            async with async_session_maker() as db:
                # 查找该房间最新的检测记录
                doc_result = await db.execute(
                    select(Document)
                    .where(Document.task_id.like(f"collab_{room_id}_%"))
                    .order_by(desc(Document.created_at))
                    .limit(1)
                )
                doc = doc_result.scalar_one_or_none()
                
                if not doc:
                    return None
                
                # 获取事实
                facts_result = await db.execute(
                    select(FactRecord).where(FactRecord.document_id == doc.id)
                )
                facts = facts_result.scalars().all()
                
                # 获取冲突
                conflicts_result = await db.execute(
                    select(ConflictRecord).where(ConflictRecord.document_id == doc.id)
                )
                conflicts = conflicts_result.scalars().all()
                
                # 辅助函数：检查是否是图片来源
                def is_image_fact(fact_type: str) -> bool:
                    return fact_type.startswith("image_") if fact_type else False
                
                # 构建结果
                fact_summaries = [
                    FactSummary(
                        fact_id=f.fact_id,
                        content=f.content,
                        fact_type=f.fact_type,
                        location=f.chapter or "",
                        source_text=f.source_text[:200] if f.source_text else None,
                        is_image_source=is_image_fact(f.fact_type),
                    )
                    for f in facts
                ]
                
                conflict_summaries = []
                # 构建冲突摘要需要关联事实
                facts_dict = {f.fact_id: f for f in facts}
                for c in conflicts:
                    fact_a = facts_dict.get(c.fact_a_id)
                    fact_b = facts_dict.get(c.fact_b_id)
                    
                    is_image_a = is_image_fact(fact_a.fact_type) if fact_a else False
                    is_image_b = is_image_fact(fact_b.fact_type) if fact_b else False
                    
                    conflict_summaries.append(ConflictSummary(
                        conflict_id=c.conflict_id,
                        fact_a_content=fact_a.content if fact_a else "",
                        fact_a_location=fact_a.chapter or "" if fact_a else "",
                        fact_b_content=fact_b.content if fact_b else "",
                        fact_b_location=fact_b.chapter or "" if fact_b else "",
                        conflict_type=c.conflict_type,
                        severity=c.severity,
                        description=c.description,
                        suggestion=c.suggestion,
                        is_image_conflict=is_image_a or is_image_b,
                        fact_a=FactSummary(
                            fact_id=fact_a.fact_id,
                            content=fact_a.content,
                            fact_type=fact_a.fact_type,
                            location=fact_a.chapter or "",
                            source_text=fact_a.source_text[:200] if fact_a and fact_a.source_text else None,
                            is_image_source=is_image_a,
                        ) if fact_a else None,
                        fact_b=FactSummary(
                            fact_id=fact_b.fact_id,
                            content=fact_b.content,
                            fact_type=fact_b.fact_type,
                            location=fact_b.chapter or "",
                            source_text=fact_b.source_text[:200] if fact_b and fact_b.source_text else None,
                            is_image_source=is_image_b,
                        ) if fact_b else None,
                    ))
                
                result = DetectionResult(
                    room_id=room_id,
                    task_id=doc.task_id,
                    total_facts=len(facts),
                    total_conflicts=len(conflicts),
                    conflicts=conflict_summaries,
                    facts=fact_summaries,
                    detection_time=doc.analysis_time,
                )
                
                # 缓存到内存
                self._detection_results[room_id] = result
                
                return result
                
        except Exception as e:
            logger.error(f"从数据库获取检测结果失败: {e}")
            return None
    
    async def cancel_pending_detection(self, room_id: str):
        """取消待执行的检测"""
        if room_id in self._pending_detections:
            self._pending_detections[room_id].cancel()
            del self._pending_detections[room_id]
    
    def clear_room_data(self, room_id: str):
        """清理房间数据"""
        if room_id in self._pending_detections:
            self._pending_detections[room_id].cancel()
            del self._pending_detections[room_id]
        
        if room_id in self._last_detection_time:
            del self._last_detection_time[room_id]
        
        if room_id in self._detection_results:
            del self._detection_results[room_id]


# 全局实时冲突检测器实例
_realtime_detector: Optional[RealtimeConflictDetector] = None


def get_realtime_detector() -> RealtimeConflictDetector:
    """获取实时冲突检测器单例"""
    global _realtime_detector
    if _realtime_detector is None:
        _realtime_detector = RealtimeConflictDetector()
    return _realtime_detector

