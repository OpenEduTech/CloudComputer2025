# 后端服务启动指南

## 服务架构

本项目包含两个后端服务：

1. **Agent Service** (端口 8001) - 智能体服务，负责生成知识图谱
2. **Backend API** (端口 8080) - 后端API服务，对外提供接口

## 启动顺序

### 1. 启动 Agent Service
```bash
# 在 agent-service 目录下
cd agent-service
python main.py  # 或根据实际启动命令
```

### 2. 启动 Backend API
```bash
# 在 backend 目录下
cd backend
python main.py  # 或根据实际启动命令
```

### 3. 启动前端
```bash
# 在项目根目录
npm run dev
```

## API 接口

### Backend API (http://localhost:8080)

- `POST /api/v1/graph/build` - 生成知识图谱
- `GET /api/v1/graph/{normalized_concept}` - 获取缓存结果
- `GET /api/v1/graph/health` - 健康检查

### Agent Service (http://localhost:8001)

- `POST /agent/v1/build` - 生成GraphJSON
- `GET /agent/v1/health` - 健康检查

## 数据格式

返回的数据符合 `schema/graph.schema.json` 规范，包含：
- `meta`: 元信息（概念、学科域、统计等）
- `nodes`: 节点数组（概念、学科信息等）
- `edges`: 边数组（概念间的关系）

## 故障排除

1. **连接失败**: 确保两个后端服务都已启动
2. **超时错误**: 检查 Agent Service 是否正常响应
3. **数据错误**: 验证返回数据是否符合 schema

## 开发模式

如果后端服务不可用，前端会自动使用模拟数据作为后备方案。
