# 1. 使用官方 Python 3.13 基础镜像
FROM python:3.13-slim-bookworm

# 2. 环境变量设置
ENV WORKDIR=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PATH="/app/.venv/bin:$PATH"

WORKDIR $WORKDIR

# 3. 换源并安装系统依赖
# 将 debian.sources 替换为阿里云镜像
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. 安装 uv (使用国内 pip 镜像)
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ uv

# 5. 复制依赖定义文件 
COPY pyproject.toml ./
# COPY uv.lock* ./

# 6. 安装依赖使用阿里云镜像
RUN uv sync --no-install-project --no-dev

# 7. 复制源代码
COPY . .

# 8. 暴露端口与启动
EXPOSE 8000
CMD ["uvicorn", "central_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]