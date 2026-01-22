# 部署指南

## 1. 快速开始

### 1.1 前置要求

- **Docker**: 20.10 或更高版本
- **Docker Compose**: 2.0 或更高版本
- **OpenAI API Key**: 用于 LLM 调用
- **系统要求**:
  - CPU: 2 核或以上
  - 内存: 4GB 或以上
  - 磁盘: 10GB 可用空间

### 1.2 一键部署

```bash
# 1. 克隆仓库
git clone <repository-url>
cd knowledge-graph-agent

# 2. 配置环境变量
cp env.example .env
# 编辑 .env 文件，填入你的 OPENAI_API_KEY

# 3. 启动所有服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 访问应用
# 前端: http://localhost:3000
# API文档: http://localhost:8000/docs
# Neo4j浏览器: http://localhost:7474
```

### 1.3 验证部署

```bash
# 检查所有容器状态
docker-compose ps

# 应该看到4个容器都在运行：
# - kg-backend
# - kg-frontend
# - kg-neo4j
# - kg-redis

# 健康检查
curl http://localhost:8000/health
```

## 2. 环境配置

### 2.1 环境变量说明

创建 `.env` 文件（基于 `env.example`）：

```bash
# OpenAI API配置
OPENAI_API_KEY=sk-xxx                    # 必填：你的OpenAI API密钥
OPENAI_API_BASE=https://api.openai.com/v1  # 可选：API基础URL
OPENAI_MODEL=gpt-4                       # 可选：使用的模型

# Neo4j配置
NEO4J_URI=bolt://neo4j:7687              # Neo4j连接URI
NEO4J_USER=neo4j                         # Neo4j用户名
NEO4J_PASSWORD=password123               # Neo4j密码（建议修改）

# Redis配置
REDIS_HOST=redis                         # Redis主机
REDIS_PORT=6379                          # Redis端口

# 应用配置
LOG_LEVEL=INFO                           # 日志级别
CACHE_TTL=3600                           # 缓存过期时间（秒）
MAX_CONCEPTS_PER_DOMAIN=5                # 每个学科最多概念数
```

### 2.2 使用其他 LLM 提供商

#### 使用 Azure OpenAI

```bash
OPENAI_API_KEY=your-azure-key
OPENAI_API_BASE=https://your-resource.openai.azure.com/
OPENAI_MODEL=gpt-4
```

#### 使用本地模型（如 Ollama）

```bash
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_MODEL=llama2
```

## 3. Docker Compose 部署

### 3.1 服务说明

```yaml
services:
  backend: # FastAPI后端服务
  frontend: # React前端服务
  neo4j: # Neo4j图数据库
  redis: # Redis缓存
```

### 3.2 端口映射

| 服务       | 容器端口 | 主机端口 | 说明         |
| ---------- | -------- | -------- | ------------ |
| Frontend   | 80       | 3000     | Web 界面     |
| Backend    | 8000     | 8000     | API 服务     |
| Neo4j HTTP | 7474     | 7474     | Neo4j 浏览器 |
| Neo4j Bolt | 7687     | 7687     | Neo4j 连接   |
| Redis      | 6379     | 6379     | Redis 服务   |

### 3.3 数据持久化

系统使用 Docker 卷持久化数据：

```yaml
volumes:
  neo4j-data: # Neo4j数据
  neo4j-logs: # Neo4j日志
  redis-data: # Redis数据
```

查看卷：

```bash
docker volume ls | grep kg
```

备份数据：

```bash
# 备份Neo4j
docker-compose exec neo4j neo4j-admin dump --to=/backups/neo4j-backup.dump

# 备份Redis
docker-compose exec redis redis-cli SAVE
```

### 3.4 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f [service_name]

# 进入容器
docker-compose exec backend bash
docker-compose exec neo4j bash

# 重新构建镜像
docker-compose build --no-cache

# 清理所有数据（危险操作！）
docker-compose down -v
```

## 4. Kubernetes 部署

### 4.1 前置要求

- Kubernetes 集群（1.20+）
- kubectl 已配置
- 持久化存储（PV/PVC）

### 4.2 部署步骤

```bash
# 1. 创建命名空间
kubectl create namespace knowledge-graph

# 2. 创建Secret（存储敏感信息）
kubectl create secret generic kg-secrets \
  --from-literal=openai-api-key=sk-xxx \
  --from-literal=neo4j-password=password123 \
  -n knowledge-graph

# 3. 应用配置
kubectl apply -f k8s/ -n knowledge-graph

# 4. 查看部署状态
kubectl get pods -n knowledge-graph
kubectl get svc -n knowledge-graph

# 5. 访问应用
kubectl port-forward svc/frontend 3000:80 -n knowledge-graph
```

### 4.3 K8S 配置文件

#### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: knowledge-graph-backend:latest
          ports:
            - containerPort: 8000
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: kg-secrets
                  key: openai-api-key
            - name: NEO4J_URI
              value: "bolt://neo4j:7687"
            - name: REDIS_HOST
              value: "redis"
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: knowledge-graph-frontend:latest
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: neo4j
spec:
  serviceName: neo4j
  replicas: 1
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
        - name: neo4j
          image: neo4j:5.15-community
          ports:
            - containerPort: 7474
            - containerPort: 7687
          env:
            - name: NEO4J_AUTH
              valueFrom:
                secretKeyRef:
                  name: kg-secrets
                  key: neo4j-password
          volumeMounts:
            - name: neo4j-data
              mountPath: /data
  volumeClaimTemplates:
    - metadata:
        name: neo4j-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "200m"
```

#### service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 80
  type: LoadBalancer
---
apiVersion: v1
kind: Service
metadata:
  name: neo4j
spec:
  selector:
    app: neo4j
  ports:
    - name: http
      port: 7474
      targetPort: 7474
    - name: bolt
      port: 7687
      targetPort: 7687
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
  type: ClusterIP
```

### 4.4 水平扩展

```bash
# 扩展后端服务
kubectl scale deployment backend --replicas=5 -n knowledge-graph

# 自动扩展（HPA）
kubectl autoscale deployment backend \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n knowledge-graph
```

## 5. 本地开发部署

### 5.1 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export OPENAI_API_KEY=sk-xxx
export NEO4J_URI=bolt://localhost:7687
export REDIS_HOST=localhost

# 启动开发服务器
uvicorn api.main:app --reload --port 8000
```

### 5.2 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

### 5.3 数据库服务

```bash
# 只启动数据库服务
docker-compose up -d neo4j redis
```

## 6. 生产环境部署

### 6.1 安全加固

1. **修改默认密码**

```bash
# Neo4j密码
NEO4J_PASSWORD=strong-password-here
```

2. **启用 HTTPS**

```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    # ...
}
```

3. **API 限流**

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

4. **环境隔离**

```bash
# 使用不同的环境文件
docker-compose --env-file .env.prod up -d
```

### 6.2 性能优化

1. **增加副本数**

```yaml
services:
  backend:
    deploy:
      replicas: 3
```

2. **配置资源限制**

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
```

3. **使用生产级数据库**

- Neo4j Enterprise 版
- Redis Cluster

### 6.3 监控与日志

1. **集成 Prometheus**

```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

2. **日志聚合**

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

3. **健康检查**

```bash
# 定期检查服务健康
curl http://localhost:8000/health
```

## 7. 故障排查

### 7.1 常见问题

#### 问题 1: 容器启动失败

```bash
# 查看日志
docker-compose logs backend

# 常见原因：
# - 端口被占用
# - 环境变量未设置
# - 依赖服务未就绪
```

#### 问题 2: Neo4j 连接失败

```bash
# 检查Neo4j状态
docker-compose exec neo4j cypher-shell -u neo4j -p password123

# 等待Neo4j完全启动（约30秒）
docker-compose logs neo4j | grep "Started"
```

#### 问题 3: LLM 调用失败

```bash
# 检查API Key
echo $OPENAI_API_KEY

# 测试API连接
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### 问题 4: 前端无法访问后端

```bash
# 检查网络连接
docker network inspect knowledge-graph-agent_kg-network

# 检查后端健康
curl http://localhost:8000/health
```

### 7.2 调试技巧

```bash
# 进入容器调试
docker-compose exec backend bash

# 查看实时日志
docker-compose logs -f --tail=100 backend

# 重启单个服务
docker-compose restart backend

# 查看资源使用
docker stats
```

## 8. 备份与恢复

### 8.1 数据备份

```bash
# 创建备份目录
mkdir -p backups

# 备份Neo4j
docker-compose exec neo4j neo4j-admin dump \
  --database=neo4j \
  --to=/backups/neo4j-$(date +%Y%m%d).dump

# 备份Redis
docker-compose exec redis redis-cli BGSAVE
docker cp kg-redis:/data/dump.rdb backups/redis-$(date +%Y%m%d).rdb
```

### 8.2 数据恢复

```bash
# 恢复Neo4j
docker-compose exec neo4j neo4j-admin load \
  --from=/backups/neo4j-20240119.dump \
  --database=neo4j \
  --force

# 恢复Redis
docker cp backups/redis-20240119.rdb kg-redis:/data/dump.rdb
docker-compose restart redis
```

## 9. 升级指南

### 9.1 滚动升级

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker-compose build

# 3. 滚动更新
docker-compose up -d --no-deps --build backend
docker-compose up -d --no-deps --build frontend

# 4. 验证
curl http://localhost:8000/health
```

### 9.2 数据迁移

```bash
# 1. 备份当前数据
./scripts/backup.sh

# 2. 停止服务
docker-compose down

# 3. 升级
git pull && docker-compose build

# 4. 启动新版本
docker-compose up -d

# 5. 验证
./scripts/verify.sh
```

## 10. 卸载

```bash
# 停止并删除容器
docker-compose down

# 删除数据卷（危险！）
docker-compose down -v

# 删除镜像
docker rmi knowledge-graph-agent_backend
docker rmi knowledge-graph-agent_frontend

# 删除网络
docker network rm knowledge-graph-agent_kg-network




