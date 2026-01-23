# 使用更稳定的 Python 版本
FROM python:3.11-slim-bullseye

WORKDIR /app

# 设置时区和语言
ENV TZ=Asia/Shanghai
ENV LANG=C.UTF-8
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 设置国内源（apt）
RUN echo "deb http://mirrors.aliyun.com/debian/ bullseye main non-free contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bullseye-security main non-free contrib" >> /etc/apt/sources.list

# 安装最小系统依赖（添加重试和超时）
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置 pip 国内源
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ENV PIP_TIMEOUT=100
ENV PIP_DEFAULT_TIMEOUT=100

# 升级 pip 并安装依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip config set global.timeout 100 && \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 先复制 requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建目录
RUN mkdir -p /app/uploads /app/data /app/logs

# 复制代码
COPY . .

# 设置权限
RUN chmod +x main.py

EXPOSE 8010 8501

# 使用 bash 启动，确保环境变量正确加载
CMD ["sh", "-c", "sleep 10 && python main.py --mode api"]