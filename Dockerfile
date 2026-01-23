# 使用 Python 3.12 官方镜像作为基础
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口（如果应用使用）
EXPOSE 8000

# 创建非 root 用户运行应用
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# 启动应用
CMD ["python", "main.py"]
