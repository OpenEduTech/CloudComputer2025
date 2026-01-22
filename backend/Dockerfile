# 多阶段构建 - 基础镜像
FROM python:3.11-slim AS base

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# 说明：构建时若访问 deb.debian.org 出现 502，可切换到国内镜像源。
RUN set -eux; \
        if [ -f /etc/apt/sources.list ]; then \
            sed -i \
                -e 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' \
                -e 's|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
                /etc/apt/sources.list; \
        fi; \
        if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
            sed -i \
                -e 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' \
                -e 's|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
                /etc/apt/sources.list.d/debian.sources; \
        fi; \
        apt-get -o Acquire::Retries=3 update; \
        apt-get install -y --no-install-recommends \
            build-essential \
            curl \
            tesseract-ocr \
            tesseract-ocr-chi-sim; \
        rm -rf /var/lib/apt/lists/*

# 生产阶段
FROM base AS production

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/uploads /app/data/chroma /app/logs

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
