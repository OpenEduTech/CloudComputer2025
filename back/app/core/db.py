from neo4j import GraphDatabase
import redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Neo4j驱动
neo4j_driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
)

# Redis客户端
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True  # 自动解码为字符串
)

def test_neo4j_connection():
    """测试Neo4j连接"""
    try:
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1 AS one")
            return result.single()["one"] == 1
    except Exception as e:
        logger.error(f"Neo4j连接失败: {e}")
        return False

def test_redis_connection():
    """测试Redis连接"""
    try:
        return redis_client.ping()
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
        return False

# 初始化时测试连接
if test_neo4j_connection():
    logger.info("✅ Neo4j连接成功")
else:
    logger.warning("⚠️ Neo4j连接失败，请检查配置")

if test_redis_connection():
    logger.info("✅ Redis连接成功")
else:
    logger.warning("⚠️ Redis连接失败，请检查配置")