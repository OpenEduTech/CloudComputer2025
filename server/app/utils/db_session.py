"""
PatPat-Inconsistency-Hunter 数据库会话管理
提供异步数据库会话的依赖注入
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from ..config import settings
from ..utils.logger import logger


# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
)

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖注入函数
    
    用于FastAPI的Depends
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库
    
    创建所有表
    """
    from ..models.database import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("数据库表初始化完成")


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
    logger.info("数据库连接已关闭")

