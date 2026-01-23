# 后端 Dockerfile
FROM python:3.9-slim

WORKDIR /app/backend

# 使用阿里巴巴 Debian 镜像源加速
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装系统依赖（带重试机制）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 清华源加速
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动后端服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
