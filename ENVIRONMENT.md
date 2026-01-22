# 环境变量配置

## 开发环境

创建 `dev.env` 文件并配置以下变量：

```bash
# Frontend Configuration
REACT_APP_API_URL=http://localhost:8080
REACT_APP_AGENT_SERVICE_URL=http://localhost:8001
NODE_ENV=development
VITE_APP_TITLE=跨学科知识图谱

# Backend Configuration
USE_MOCK=False

# Agent Service Configuration
AGENT_SERVICE_URL=http://agent-service:8001
AGENT_TIMEOUT=30
AGENT_MAX_NODES=30
AGENT_MAX_EDGES=50
AGENT_MIN_CONFIDENCE=0.55

# Database Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# LLM Configuration (for agent service)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
LLM_TIMEOUT=300
LLM_MAX_RETRIES=3
```

## 生产环境

创建 `.env.production` 文件：

```bash
# API URLs
REACT_APP_API_URL=https://your-backend-domain.com
REACT_APP_AGENT_SERVICE_URL=https://your-agent-service-domain.com

# Production settings
NODE_ENV=production

# Google Gemini API Key
GOOGLE_API_KEY=your_production_api_key_here

# Other configuration
VITE_APP_TITLE=跨学科知识图谱
```

## Docker 环境变量

在 `docker-compose.yml` 中设置：

```yaml
environment:
  - REACT_APP_API_URL=http://backend:8080
  - REACT_APP_AGENT_SERVICE_URL=http://agent-service:8001
  - GOOGLE_API_KEY=${GOOGLE_API_KEY}
```

## 安全注意事项

- 永远不要将 `.env` 文件提交到版本控制系统
- 在生产环境中使用密钥管理服务
- API 密钥应该通过环境变量传递，而不是硬编码在代码中
