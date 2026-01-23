# 基础镜像：Python 3.9 + 系统依赖（ffmpeg/redis）
FROM python:3.9-slim

# ========== 核心修复：先设置工作目录 ==========
WORKDIR /app

# 安装系统依赖（ffmpeg必需，否则Whisper无法识别音频）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ========== 现在COPY能找到文件了 ==========
# 复制依赖文件（先复制requirements.txt，利用Docker缓存）
COPY requirements.txt .

# 安装Python依赖（指定国内源加速）
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# 复制项目所有代码到容器
COPY . .

# 创建.env文件的模板（也可以挂载外部.env）
RUN echo "# Qwen API配置" > .env && \
    echo "QWEN_API_KEY=your_qwen_api_key_here" >> .env && \
    echo "# Redis配置（docker-compose里的容器名是redis）" >> .env && \
    echo "REDIS_HOST=redis" >> .env && \
    echo "REDIS_PORT=6379" >> .env && \
    echo "REDIS_DB=0" >> .env

# 启动命令（默认运行main.py）
CMD ["python", "main.py"]