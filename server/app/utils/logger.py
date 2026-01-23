"""
PatPat-Inconsistency-Hunter 日志模块
提供统一的日志记录功能
"""

import sys
import os
from loguru import logger as _logger

from ..config import settings


def setup_logging():
    """配置日志系统"""
    # 移除默认处理器
    _logger.remove()
    
    # 控制台输出
    _logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )
    
    # 文件输出
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    _logger.add(
        settings.LOG_FILE,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
    )
    
    return _logger


# 导出logger实例
logger = _logger


# 初始化日志
setup_logging()

