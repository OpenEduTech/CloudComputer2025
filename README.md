## 快速开始

### 环境要求

- Docker 20.0+ 和 Docker Compose 2.0+
- 大模型API Key（OpenAI或其他兼容服务）

### 部署步骤

1. **克隆项目**

```bash
git clone <your-repo-url>
cd knowledge-graph-agent
```

2. **配置环境变量**

创建 `.env` 文件，配置API密钥：

```bash
MAAS_API_KEY=your_api_key
MAAS_API_ENDPOINT=https://dashscope.aliyuncs.com/compatible-mode/v1
MAAS_MODEL_NAME=qwen-turbo
REDIS_HOST=redis
REDIS_PORT=6379
```

3. **启动服务**

```bash
docker-compose up -d
```

4. **访问系统**

打开浏览器访问 `http://localhost:8080`

### 本地开发

如果想在本地开发调试：

```bash
# 安装Python依赖
pip install -r requirements.txt

# 启动Redis（如果还没启动）
docker run -d -p 6379:6379 redis:alpine

# 启动后端（在项目根目录）
python -m backend.app

# 前端可以用简单的HTTP服务器（Python 3）
cd frontend
python -m http.server 8080
```
