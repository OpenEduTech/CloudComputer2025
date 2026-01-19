FROM python:3.9-slim

WORKDIR /app

# 安装构建依赖 (如果需要编译某些库)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Worker 不需要暴露端口，它主动连接 Redis
CMD ["python", "-u", "worker_main.py"]
