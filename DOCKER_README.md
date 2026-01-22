# 容器化开发指南

## 当前状态

项目已经配置了完整的容器化环境，包括：
- **前端服务**：React + Vite 应用（端口3000）
- **后端API服务**：FastAPI 服务（端口8080）
- **Agent服务**：LLM智能图谱生成服务（端口8001）
- **Neo4j数据库**：图数据库（端口7474/7687）
- **Redis缓存**：缓存服务（端口6379）
- 多阶段 Dockerfile（开发/生产）
- Docker Compose 配置
- Nginx 配置用于生产部署
- Makefile 用于简化操作

## 快速开始

### 前提条件
- 安装 Docker Desktop
- 启动 Docker Desktop

### 开发环境启动

```bash
# 使用启动脚本（推荐）
./start-dev.sh

# 或者使用 Makefile
make up-dev

# 或者直接使用 docker-compose
docker-compose up --build
```

所有服务启动后，可以通过以下地址访问：

- **前端应用**: http://localhost:3000
- **后端API文档**: http://localhost:8080/docs
- **Agent服务**: http://localhost:8001
- **Neo4j浏览器**: http://localhost:7474 (用户名: neo4j, 密码: password123)

### 停止服务

```bash
# 使用 Makefile
make down

# 或者直接使用 docker-compose
docker-compose down
```

## 构建镜像

### 开发镜像
```bash
make build-dev
# 或
docker build --target development -t interdisciplinary-knowledge-graph:dev .
```

### 生产镜像
```bash
make build-prod
# 或
docker build --target production -t interdisciplinary-knowledge-graph:latest .
```

## 环境变量配置

参考 `ENVIRONMENT.md` 配置环境变量。

## 后端集成准备

当后端代码准备好时：

1. 在项目根目录创建 `backend/` 和 `agent-service/` 目录
2. 取消注释 `docker-compose.yml` 中的后端服务配置
3. 更新 `docker-compose.prod.yml` 中的镜像名称
4. 配置适当的环境变量

## 故障排除

### Docker Desktop 未运行
- 启动 Docker Desktop
- 等待 Docker 服务完全启动

### 端口冲突
- 检查 3000 端口是否被占用
- 修改 `docker-compose.yml` 中的端口映射

### 构建失败
- 检查网络连接
- 清理 Docker 缓存：`docker system prune`

## 开发工作流程

1. 代码修改后，热重载会自动生效
2. 需要添加新依赖时，重建镜像：`make up-dev`
3. 查看日志：`make logs`

## 生产部署

当代码完善后，使用生产配置：

```bash
make up-prod
```

这将在端口 80 启动 Nginx 服务前端应用。
