# FactGuardian Backend Dockerfile
# 使用 Python 3.10 精简版作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# 安装系统依赖（使用缓存，如果已安装过会跳过）
# - build-essential: 编译某些 Python 包可能需要（如某些需要编译的 C 扩展）
# - poppler-utils: PDF 处理库 pdfplumber 的依赖
# - libmagic1: 文件类型检测（python-magic 的依赖）
# - curl: 健康检查使用
# 使用 --mount=type=cache 加速 apt 缓存
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip 到最新版本（使用缓存）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

# 先复制依赖文件（利用 Docker 缓存层，提高构建效率）
COPY requirements.txt .

# 安装 Python 依赖（使用 pip 缓存，如果依赖未变化会跳过）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户（安全最佳实践）
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
# 检查 /health 端点，每30秒检查一次，超时10秒，启动后40秒开始检查，失败3次后标记为不健康
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令（使用 uvicorn）
# --reload 参数在 docker-compose.yml 中通过 command 覆盖，生产环境应移除
# 生产环境建议使用：CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]