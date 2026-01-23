"""
服务包装模块 
"""

import os
import sys

# 确保可以导入 services
services_path = os.path.join(os.path.dirname(__file__), 'services')
if services_path not in sys.path:
    sys.path.insert(0, services_path)

# 直接导入
try:
    from page_analysis_service import PageDeepAnalysisService, DeepAnalysisResult
    __all__ = ['PageDeepAnalysisService', 'DeepAnalysisResult']
except ImportError as e:
    print(f"导入 PageDeepAnalysisService 失败: {e}")
    PageDeepAnalysisService = None
    DeepAnalysisResult = None

try:
    from ai_tutor_service import AITutorService, ChatMessage
    __all__ = __all__ + ['AITutorService', 'ChatMessage'] if '__all__' in locals() else ['AITutorService', 'ChatMessage']
except ImportError as e:
    print(f"导入 AITutorService 失败: {e}")
    AITutorService = None
    ChatMessage = None

try:
    from reference_search_service import ReferenceSearchService, ReferenceItem, ReferenceSearchResult
    __all__ = __all__ + ['ReferenceSearchService', 'ReferenceItem', 'ReferenceSearchResult'] if '__all__' in locals() else ['ReferenceSearchService', 'ReferenceItem', 'ReferenceSearchResult']
except ImportError as e:
    print(f"导入 ReferenceSearchService 失败: {e}")
    ReferenceSearchService = None
    ReferenceItem = None
    ReferenceSearchResult = None

print("✅ 服务包装模块加载完成")
