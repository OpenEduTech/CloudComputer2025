# 使用官方 Python 3.10 镜像（稳定且兼容性好）
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（python-pptx 需要 libxml2/libxslt）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libxml2-dev \
        libxslt1-dev \
        && rm -rf /var/lib/apt/lists/*

# 复制依赖清单
COPY requirements.txt .

# 安装 Python 依赖（使用国内镜像加速可选，此处用官方源保证通用性）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建输出目录（避免容器内写入失败）
RUN mkdir -p output

# 暴露端口（FastAPI 默认 8000）
EXPOSE 8000

# 启动命令：运行 FastAPI 服务
# 注意：API Key 通过 -e ZHIPU_API_KEY=... 传入
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]