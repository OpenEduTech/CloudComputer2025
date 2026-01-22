import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging
from app.core.config import settings  # ✅ 新增：导入配置以获取USE_MOCK设置

logger = logging.getLogger(__name__)

class TaskService:
    """任务服务"""
    
    def __init__(self):
        self.task_prefix = "task:"
        
        # ✅ 核心修改：根据配置决定存储后端
        if settings.USE_MOCK:
            logger.info("✅ TaskService 使用内存Mock模式")
            self._mock_storage = {}  # 用字典模拟Redis存储
            self._storage_type = "mock"
        else:
            # 仅在非Mock模式下导入redis_client，避免连接错误
            from app.core.db import redis_client
            self.redis_client = redis_client
            self._storage_type = "redis"
            logger.info("✅ TaskService 使用Redis存储")
    
    def create_task(self, concept: str) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "concept": concept,
            "status": "pending",
            "progress": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            if self._storage_type == "mock":
                # Mock模式：存储到内存字典
                self._mock_storage[task_id] = task_data
                logger.info(f"✅ Mock任务创建成功: {task_id} - {concept}")
            else:
                # Redis模式：原有逻辑
                self.redis_client.setex(
                    f"{self.task_prefix}{task_id}",
                    3600,  # 1小时过期
                    json.dumps(task_data)
                )
                logger.info(f"✅ Redis任务创建成功: {task_id} - {concept}")
            return task_id
        except Exception as e:
            logger.error(f"❌ 任务创建失败: {e}")
            return ""
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新任务状态"""
        try:
            if self._storage_type == "mock":
                # Mock模式：更新内存字典
                if task_id in self._mock_storage:
                    self._mock_storage[task_id].update(updates)
                    self._mock_storage[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                    logger.info(f"✅ Mock任务更新: {task_id} -> {updates.get('status', 'unknown')}")
                    return True
                logger.warning(f"⚠️ Mock任务不存在: {task_id}")
                return False
            else:
                # Redis模式：原有逻辑
                task_key = f"{self.task_prefix}{task_id}"
                task_data_json = self.redis_client.get(task_key)
                
                if not task_data_json:
                    logger.warning(f"⚠️ Redis任务不存在: {task_id}")
                    return False
                
                task_data = json.loads(task_data_json)
                task_data.update(updates)
                task_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                
                # 更新Redis
                self.redis_client.setex(
                    task_key,
                    3600,  # 续期
                    json.dumps(task_data)
                )
                
                logger.info(f"✅ Redis任务更新: {task_id} -> {updates.get('status', 'unknown')}")
                return True
                
        except Exception as e:
            logger.error(f"❌ 任务更新失败: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        try:
            if self._storage_type == "mock":
                # Mock模式：从内存字典获取
                return self._mock_storage.get(task_id)
            else:
                # Redis模式：原有逻辑
                task_key = f"{self.task_prefix}{task_id}"
                task_data_json = self.redis_client.get(task_key)
                
                if task_data_json:
                    return json.loads(task_data_json)
                return None
        except Exception as e:
            logger.error(f"❌ 获取任务失败: {e}")
            return None

task_service = TaskService()