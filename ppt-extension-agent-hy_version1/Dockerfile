# PPT内容扩展智能体 - 云原生容器化部署
# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置维护者信息
LABEL maintainer="ppt-extension-agent@cloud-class"
LABEL description="PPT内容扩展智能体 - 基于云原生架构的学习助手系统"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100

# 配置 pip 使用国内镜像源（加速依赖安装）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 使用国内镜像源（清华源）并安装系统依赖（包含tesseract OCR）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    curl \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用Docker缓存层
COPY requirements.txt .

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制项目代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/uploads /app/output /app/logs

# 暴露服务端口（可根据实际需要修改）
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 设置容器启动命令
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
