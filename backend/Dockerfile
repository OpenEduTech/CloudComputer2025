# 基础镜像（Python 3.10 兼容大多数库）
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

RUN echo "" > /etc/apt/sources.list && \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "Acquire::Check-Valid-Until \"false\";" > /etc/apt/apt.conf.d/99no-check-valid-until && \
    apt-get clean

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc --fix-missing && \
    rm -rf /var/lib/apt/lists/*

# 升级pip + 配置国内PyPI源（加速Python依赖安装）
RUN pip install --upgrade pip && \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有代码到容器
COPY . .

# 启动命令（运行FastAPI）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]