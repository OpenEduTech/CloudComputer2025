import os
import sys

# 设置简单的环境变量用于测试
os.environ['CHECK_LLM_HEALTH'] = 'true'

try:
    # 尝试导入核心模块
    sys.path.append(os.getcwd())
    from backend.models.llm_graph_builder import build_knowledge_graph
    
    print("LLM Module Health Check")
    
    # 测试1：简单概念测试（不实际调用 API，只是导入测试）
    print("Core module import successful")
    
    # 测试2：检查环境变量
    api_key = os.getenv("VOLC_ARK_API_KEY", "")
    model_id = os.getenv("VOLC_ARK_MODEL", "")
    
    if not api_key or api_key == "1f0dfbb6-494f-4378-9662-37d0d563891a":
        print("API Key is using default or empty - production should set VOLC_ARK_API_KEY")
    else:
        print(f"API Key configured (length: {len(api_key)})")
    
    if model_id:
        print(f"Model ID: {model_id}")
    
    # 测试3：简单结构测试
    test_mode = os.getenv("HEALTHCHECK_TEST_MODE", "full")
    
    if test_mode == "full":
        # 完整测试（会调用 API）
        print("Running full health check (will call LLM API)...")
        result = build_knowledge_graph("熵")
        
        if result.get("error"):
            print(f"Health check failed: {result['error']}")
            sys.exit(1)
        
        nodes_count = len(result.get("nodes", []))
        links_count = len(result.get("links", []))
        
        print(f"Graph generated: {nodes_count} nodes, {links_count} links")
        
        if "warnings" in result:
            print(f"Warnings: {result['warnings']}")
        
    else:
        # 轻量测试（只检查模块功能）
        print("Light health check passed (no API call)")
    
    print("Health Check PASSED")
    sys.exit(0)
    
except ImportError as e:
    print(f"Import error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"Health check failed: {str(e)}")
    sys.exit(1)