# 使用官方 Python 轻量镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 1. 安装系统依赖 (如果需要编译某些库)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 2. 拷贝依赖文件并安装
# 注意：路径是相对于项目根目录的
COPY services/agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 拷贝核心代码和数据资产
# 必须拷贝 data 和 docs，因为 PDF 提到后端需要挂载 /assets 和 /doc_assets
COPY services/ /app/services/
COPY data/ /app/data/
COPY docs/ /app/docs/
COPY index/ /app/index/
COPY scripts/ /app/scripts/

# 4. 设置环境变量
ENV PYTHONPATH=/app

# 5. 暴露端口 (对应 PDF 中的 8088)
EXPOSE 8088

# 6. 启动命令
# --host 0.0.0.0 允许外部访问
# --port 8088 匹配项目配置
CMD ["uvicorn", "services.agent.rag_demo:app", "--host", "0.0.0.0", "--port", "8088"]
