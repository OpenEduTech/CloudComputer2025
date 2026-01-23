"""
PatPat-Inconsistency-Hunter 服务层模块
包含核心业务逻辑的实现

优化版本特性：
- 视觉模型服务：使用 InternVL 处理图片内容
- LangGraph 引擎：更高效的 Agent 工作流
- 增强的冲突检测：支持图文冲突
"""

from .llm_client import DeepSeekClient
from .fact_extractor import FactExtractor
from .conflict_detector import ConflictDetector
from .fact_verifier import FactVerifier
from .document_processor import DocumentProcessor
from .analysis_engine import AnalysisEngine, get_analysis_engine, get_enhanced_analysis_engine

# 可选模块（需要额外依赖）
try:
    from .vision_service import VisionService, get_vision_service
except ImportError:
    VisionService = None
    get_vision_service = None

try:
    from .langgraph_engine import LangGraphAnalysisEngine, get_langgraph_engine
except ImportError:
    LangGraphAnalysisEngine = None
    get_langgraph_engine = None

__all__ = [
    "DeepSeekClient",
    "FactExtractor",
    "ConflictDetector",
    "FactVerifier",
    "DocumentProcessor",
    "AnalysisEngine",
    "get_analysis_engine",
    "get_enhanced_analysis_engine",
    # 可选模块
    "VisionService",
    "get_vision_service",
    "LangGraphAnalysisEngine",
    "get_langgraph_engine",
]

