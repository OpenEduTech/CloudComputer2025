# config.py
import os

# 从环境变量中读取智谱AI的API Key
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

# 使用的模型名称
MODEL_NAME = "glm-4-flash"

# 其他可选配置（可根据需要扩展）
DEFAULT_MAX_TOKENS = 1024
TEMPERATURE = 0.3  # 降低随机性，提高事实一致性（适合扩展任务）

# 校验关键配置是否缺失
if not ZHIPU_API_KEY:
    raise EnvironmentError(
        "未设置环境变量 ZHIPU_API_KEY。请通过以下方式之一提供：\n"
        "- 本地运行: export ZHIPU_API_KEY='your_key' (Linux/macOS) 或 set ZHIPU_API_KEY=... (Windows)\n"
        "- Docker运行: -e ZHIPU_API_KEY=your_key\n"
        "- 或使用 .env 文件（配合 python-dotenv）"
    )