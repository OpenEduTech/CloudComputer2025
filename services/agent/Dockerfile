FROM python:3.10-slim

WORKDIR /app

# 复制项目
COPY . /app

# 安装依赖（如果你有 requirements.txt 就用它）
# 优先建议你维护 requirements.txt
RUN pip install --no-cache-dir -U pip \
 && if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

EXPOSE 8000

CMD ["uvicorn", "services.agent.app:app", "--host", "0.0.0.0", "--port", "8000"]
