import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(autouse=True)
def setup_test_env():
    """设置测试环境变量"""
    # 设置测试用的环境变量
    import os
    os.environ['OPENAI_API_KEY'] = 'test-key'
    os.environ['MILVUS_HOST'] = 'localhost'
    os.environ['REDIS_HOST'] = 'localhost'
    os.environ['POSTGRES_HOST'] = 'localhost'
    yield