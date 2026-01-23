# 第一阶段：构建阶段
FROM python:3.10-slim AS builder

# 设置工作目录
WORKDIR /app

# 使用阿里云镜像源加速系统依赖下载
# ✅ 新代码：修复了源替换失败的问题
RUN \
    # 处理新版 Debian 的源文件 (debian.sources)
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    # 处理旧版 Debian 的源文件 (sources.list)
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
    fi && \
    # 开始安装依赖
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt文件
COPY requirements.txt .

# 使用阿里云镜像源安装Python依赖到临时目录
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    --prefix=/install \
    -r requirements.txt

# 第二阶段：运行阶段
FROM python:3.10-slim AS streamlit-app

# 设置工作目录
WORKDIR /app

# ✅ 合并后的依赖安装命令：同时包含 poppler-utils 和 ffmpeg
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; \
    then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    poppler-utils \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制安装的依赖
COPY --from=builder /install /usr/local

# 确保 plotly 已安装（备用安装）
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ plotly

# 复制应用代码（只复制必要的文件，排除不必要的文件）
COPY . .

# 创建数据和临时目录
RUN mkdir -p /app/data/mongo /app/data/redis /app/temp

# 暴露端口
EXPOSE 8501 8001 8002 8003

# 健康检查（使用更简单的健康检查方式）
HEALTHCHECK CMD python3 -c "import socket; sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); result = sock.connect_ex(('localhost', 8501)); exit(0 if result == 0 else 1)"

# 设置环境变量
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
# 优化Streamlit启动性能的环境变量
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
ENV STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 运行应用
CMD ["streamlit", "run", "app.py"]

# 第三阶段：出题服务
FROM python:3.10-slim AS quiz-generator

WORKDIR /app

RUN if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ flask

COPY . .
RUN mkdir -p /app/data/mongo /app/data/redis /app/temp

EXPOSE 8001

ENV PYTHONPATH=/app
ENV SERVICE_TYPE=quiz_generator

CMD ["python", "microservices/quiz_generator_service.py"]

# 第四阶段：判卷服务
FROM python:3.10-slim AS quiz-grader

WORKDIR /app

RUN if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ flask

COPY . .
RUN mkdir -p /app/data/mongo /app/data/redis /app/temp

EXPOSE 8002

ENV PYTHONPATH=/app
ENV SERVICE_TYPE=quiz_grader

CMD ["python", "microservices/quiz_grader_service.py"]

# 第五阶段：错题管理服务
FROM python:3.10-slim AS mistake-manager

WORKDIR /app

RUN if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ flask

COPY . .
RUN mkdir -p /app/data/mongo /app/data/redis /app/temp

EXPOSE 8003

ENV PYTHONPATH=/app
ENV SERVICE_TYPE=mistake_manager

CMD ["python", "microservices/mistake_manager_service.py"]