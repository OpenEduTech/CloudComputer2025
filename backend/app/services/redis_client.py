"""
Redis 客户端服务
用于存储和检索事实数据
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import redis

logger = logging.getLogger(__name__)

# 模块级全局变量：共享内存后备存储（确保所有 RedisClient 实例使用同一个字典）
_SHARED_MEM_FACTS = {}
_SHARED_MEM_DOCS = {}
_SHARED_MEM_CONFLICTS = {}


class RedisClient:
    """Redis 客户端封装（单例模式）"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式：确保全局只有一个 RedisClient 实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # 只初始化一次
        if self._initialized:
            return
        
        self.host = os.getenv("REDIS_HOST", "redis")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self._client: Optional[redis.Redis] = None
        # 内存后备存储引用全局共享变量
        self._mem_facts = _SHARED_MEM_FACTS
        self._mem_docs = _SHARED_MEM_DOCS
        self._mem_conflicts = _SHARED_MEM_CONFLICTS
        self._initialized = True
        logger.info("RedisClient 单例初始化完成")
        
        # 立即检查连接状态，提前预警环境问题
        try:
            # Create a temporary client for check
            check_client = redis.Redis(host=self.host, port=self.port, db=self.db, socket_timeout=1)
            check_client.ping()
            logger.info(f"Redis 连接检查通过: {self.host}:{self.port}")
            check_client.close()
        except Exception as e:
            logger.warning(f"Redis 连接初始化检查失败: {e}")
            if self.host == "redis" and "getaddrinfo failed" in str(e):
                logger.critical("""
╔════════════════════════════════════════════════════════════════╗
║          【云原生部署要求警告】                                    ║
╠════════════════════════════════════════════════════════════════╣
║  检测到 Redis 服务不可用 (主机名 'redis' 无法解析)                  ║
║                                                                  ║
║  ⚠️  当前环境不符合项目的云原生架构要求                            ║
║  系统将降级使用进程内存，但这会导致：                               ║
║    • 无法实现'统一事实黑板'（多实例数据不同步）                      ║
║    • 数据重启后丢失（不持久化）                                     ║
║    • 并发一致性无法保证                                            ║
║                                                                  ║
║  ✅ 正确启动方式:                                                 ║
║     docker-compose up --build                                   ║
║                                                                  ║
╚════════════════════════════════════════════════════════════════╝
""")

    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端（延迟连接）"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
        return self._client
    
    def is_connected(self) -> bool:
        """检查 Redis 是否连接"""
        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 连接失败: {str(e)}")
            return False
    
    def save_facts(self, document_id: str, facts: List[Dict[str, Any]]) -> bool:
        """
        保存文档的事实列表
        
        Args:
            document_id: 文档ID
            facts: 事实列表
        
        Returns:
            是否保存成功
        """
        try:
            key = f"facts:{document_id}"
            value = json.dumps(facts, ensure_ascii=False)
            self.client.set(key, value)
            
            # 设置过期时间（24小时）
            self.client.expire(key, 86400)
            
            logger.info(f"保存事实成功: {document_id}, 共 {len(facts)} 条")
            return True
        except Exception as e:
            logger.error(f"保存事实失败: {str(e)}，改用内存后备存储")
            logger.info(f"[DEBUG] 保存到内存: document_id={document_id}, facts count={len(facts)}")
            logger.info(f"[DEBUG] 内存字典 ID: {id(self._mem_facts)}, 内容: {list(self._mem_facts.keys())}")
            self._mem_facts[document_id] = facts
            logger.info(f"[DEBUG] 保存后内存字典内容: {list(self._mem_facts.keys())}")
            return True
    
    def get_facts(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取文档的事实列表
        
        Args:
            document_id: 文档ID
        
        Returns:
            事实列表，不存在返回 None
        """
        try:
            key = f"facts:{document_id}"
            value = self.client.get(key)
            
            if value is None:
                # 尝试内存后备
                logger.info(f"[DEBUG] Redis 返回 None，检查内存。document_id={document_id}")
                logger.info(f"[DEBUG] 内存字典 ID: {id(self._mem_facts)}, 内容: {list(self._mem_facts.keys())}")
                result = self._mem_facts.get(document_id)
                logger.info(f"[DEBUG] 内存查询结果: {result is not None}")
                return result
            
            return json.loads(value)
        except Exception as e:
            logger.error(f"获取事实失败: {str(e)}，尝试内存后备")
            logger.info(f"[DEBUG] 异常时检查内存。document_id={document_id}")
            logger.info(f"[DEBUG] 内存字典 ID: {id(self._mem_facts)}, 内容: {list(self._mem_facts.keys())}")
            result = self._mem_facts.get(document_id)
            logger.info(f"[DEBUG] 异常时内存查询结果: {result is not None}")
            return result
    
    def delete_facts(self, document_id: str) -> bool:
        """删除文档的事实"""
        try:
            key = f"facts:{document_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除事实失败: {str(e)}")
            return False
    
    def save_document_metadata(self, document_id: str, metadata: Dict[str, Any]) -> bool:
        """保存文档元数据"""
        try:
            key = f"doc:{document_id}"
            value = json.dumps(metadata, ensure_ascii=False)
            self.client.set(key, value)
            self.client.expire(key, 86400)
            return True
        except Exception as e:
            logger.error(f"保存文档元数据失败: {str(e)}，改用内存后备存储")
            self._mem_docs[document_id] = metadata
            return True
    
    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档元数据"""
        try:
            key = f"doc:{document_id}"
            value = self.client.get(key)
            
            if value is None:
                # 尝试内存后备
                return self._mem_docs.get(document_id)
            
            return json.loads(value)
        except Exception as e:
            logger.error(f"获取文档元数据失败: {str(e)}，尝试内存后备")
            return self._mem_docs.get(document_id)
    
    def list_documents(self) -> List[str]:
        """列出所有文档ID"""
        try:
            keys = self.client.keys("doc:*")
            return [key.replace("doc:", "") for key in keys]
        except Exception as e:
            logger.error(f"列出文档失败: {str(e)}")
            return []
    
    def save_conflicts(self, document_id: str, conflicts: List[Dict[str, Any]]) -> bool:
        """
        保存文档的冲突列表
        
        Args:
            document_id: 文档ID
            conflicts: 冲突列表
        
        Returns:
            是否保存成功
        """
        try:
            key = f"conflicts:{document_id}"
            value = json.dumps(conflicts, ensure_ascii=False)
            self.client.set(key, value)
            
            # 设置过期时间（24小时）
            self.client.expire(key, 86400)
            
            logger.info(f"保存冲突成功: {document_id}, 共 {len(conflicts)} 条")
            return True
        except Exception as e:
            logger.error(f"保存冲突失败: {str(e)}，改用内存后备存储")
            self._mem_conflicts[document_id] = conflicts
            return True
    
    def get_conflicts(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取文档的冲突列表
        
        Args:
            document_id: 文档ID
        
        Returns:
            冲突列表，不存在返回 None
        """
        try:
            key = f"conflicts:{document_id}"
            value = self.client.get(key)
            
            if value is None:
                # 尝试内存后备
                return self._mem_conflicts.get(document_id)
            
            return json.loads(value)
        except Exception as e:
            logger.error(f"获取冲突失败: {str(e)}，尝试内存后备")
            return self._mem_conflicts.get(document_id)
    
    def delete_conflicts(self, document_id: str) -> bool:
        """删除文档的冲突"""
        try:
            key = f"conflicts:{document_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除冲突失败: {str(e)}")
            return False


# 全局 Redis 客户端实例
redis_client = RedisClient()

