# 后端服务集成完成 ✅

## 已集成服务

### 1. 后端API服务 (端口8080)
- **框架**: FastAPI
- **功能**: 提供图谱和任务管理API
- **数据库**: Neo4j (图数据库) + Redis (缓存)
- **文档**: http://localhost:8080/docs

### 2. Agent服务 (端口8001)
- **框架**: FastAPI
- **功能**: 基于LLM的智能图谱生成
- **模型**: DeepSeek (可配置)
- **健康检查**: http://localhost:8001/healthz

### 3. 数据库服务
- **Neo4j**: 图数据库 (http://localhost:7474)
  - 用户名: neo4j
  - 密码: password123
- **Redis**: 缓存服务 (端口6379)

## 服务架构

```
前端 (React) ───> 后端API ───> Agent服务 ───> LLM
                      │
                      ├──> Neo4j (存储图谱)
                      └──> Redis (缓存)
```

## 快速启动

1. **配置环境变量**:
   ```bash
   # 复制并编辑环境变量
   cp dev.env.example dev.env
   # 编辑 dev.env，设置 DEEPSEEK_API_KEY
   ```

2. **启动服务**:
   ```bash
   # 使用启动脚本
   ./start-dev.sh

   # 或使用Makefile
   make up-dev
   ```

3. **测试集成**:
   ```bash
   # 运行集成测试
   ./test-integration.sh
   ```

## 环境变量配置

关键配置项：

- `USE_MOCK`: 是否使用模拟数据 (False = 使用真实Agent服务)
- `DEEPSEEK_API_KEY`: LLM API密钥
- `AGENT_SERVICE_URL`: Agent服务地址
- `NEO4J_URI`: Neo4j连接地址
- `REDIS_HOST`: Redis主机地址

## API端点

### 后端API
- `GET /health`: 健康检查
- `POST /api/graph/build`: 生成图谱
- `GET /docs`: API文档

### Agent服务
- `GET /healthz`: 健康检查
- `POST /graph/build`: 生成图谱

## 开发注意事项

1. **API密钥**: 需要设置 `DEEPSEEK_API_KEY` 才能使用Agent服务
2. **网络**: 服务间通过Docker网络通信
3. **数据持久化**: Neo4j和Redis数据会持久化到Docker volumes
4. **热重载**: 前端支持热重载，后端需要重启容器

## 故障排除

- **Agent服务调用失败**: 检查 `DEEPSEEK_API_KEY` 配置
- **数据库连接失败**: 等待服务完全启动 (15-30秒)
- **端口冲突**: 检查3000, 8000, 8001, 8080端口是否被占用

## 下一步

1. 配置LLM API密钥开始测试Agent服务
2. 根据需要调整Agent服务的配置参数
3. 完善前端与后端API的集成
4. 准备生产环境的配置
