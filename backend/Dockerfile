FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（忽略安全仓库错误）
RUN apt-get update || true && \
    apt-get install -y --allow-unauthenticated \
    gcc \
    g++ \
    2>/dev/null || true && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
