# 架构设计文档

## 1. 系统概述

跨学科知识图谱智能体是一个基于云原生架构的智能系统，能够自动挖掘不同学科间的概念关联，并构建可视化的知识图谱。系统采用微服务架构，充分体现云原生特征。

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                 │
│                   Web浏览器 (React)                           │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────────┐
│                    前端服务 (Nginx)                           │
│              - 静态资源服务                                    │
│              - API代理                                        │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                  API Gateway (FastAPI)                       │
│              - 请求路由                                        │
│              - 参数验证                                        │
│              - 统一错误处理                                    │
│              - 健康检查                                        │
└─────┬──────────────────────────────┬────────────────────────┘
      │                              │
      │                              │
┌─────▼──────────────┐      ┌───────▼─────────────────────────┐
│  Agent Service     │      │  Knowledge Graph Service        │
│  智能体服务         │      │  图谱服务                        │
│                    │      │                                 │
│  - Prompt工程      │      │  - 实体关系提取                  │
│  - LLM调用管理     │◄─────┤  - 图谱构建                      │
│  - 多轮对话        │      │  - Neo4j操作                     │
│  - 校验层          │      │  - 图谱查询                      │
└─────┬──────────────┘      └───────┬─────────────────────────┘
      │                              │
      │                              │
┌─────▼──────────────┐      ┌───────▼─────────────────────────┐
│  LLM API           │      │  Neo4j 图数据库                  │
│  (OpenAI/本地)     │      │  - 节点存储                      │
│                    │      │  - 关系存储                      │
│  - GPT-4           │      │  - Cypher查询                    │
│  - 流式响应        │      │  - 图算法                        │
└────────────────────┘      └─────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Redis 缓存层                              │
│              - 图谱结果缓存                                    │
│              - 减少重复LLM调用                                 │
│              - TTL过期管理                                    │
└─────────────────────────────────────────────────────────────┘
```

## 3. 云原生组件

### 3.1 容器化 (Docker)

所有服务均采用 Docker 容器化部署：

- **Backend 容器**: Python 3.11 + FastAPI
- **Frontend 容器**: Node.js 构建 + Nginx 服务
- **Neo4j 容器**: Neo4j 5.15 Community
- **Redis 容器**: Redis 7 Alpine

### 3.2 服务编排 (Docker Compose)

使用 Docker Compose 进行多容器编排：

```yaml
services:
  - backend: API服务
  - frontend: Web界面
  - neo4j: 图数据库
  - redis: 缓存服务
```

所有服务通过自定义网络`kg-network`互联，实现服务间通信。

### 3.3 微服务架构

系统采用微服务架构，各服务职责单一：

| 服务          | 职责                  | 技术栈             |
| ------------- | --------------------- | ------------------ |
| API Gateway   | 统一入口、路由、验证  | FastAPI            |
| Agent Service | LLM 调用、Prompt 工程 | Python + LangChain |
| Graph Service | 图谱构建、存储        | Python + Neo4j     |
| Frontend      | 用户界面、可视化      | React + ECharts    |
| Cache Layer   | 结果缓存              | Redis              |

### 3.4 服务解耦

- **通信方式**: REST API (HTTP/JSON)
- **配置管理**: 环境变量外部化
- **状态管理**: 无状态设计，可水平扩展
- **数据持久化**: 独立的数据卷

## 4. 核心模块设计

### 4.1 Agent Service (智能体服务)

**职责**：

- 管理与 LLM 的交互
- 实现多阶段 Prompt 策略
- 执行校验层逻辑

**核心组件**：

```
agent_service/
├── prompts.py          # Prompt模板库
├── llm_client.py       # LLM客户端封装
├── validator.py        # 校验层实现
└── agent.py            # 主逻辑协调
```

**工作流程**：

```
输入概念
    ↓
[阶段1] 概念识别 (Prompt 1)
    ↓
[阶段2] 跨学科挖掘 (Prompt 2)
    ↓
[阶段3] 关系验证 (校验层)
    ↓
[阶段4] 图谱构建
    ↓
输出结构化数据
```

### 4.2 校验层 (Check Layer)

为防止 LLM 幻觉，实现三重校验机制：

**1. 直接验证**

- 使用专门的验证 Prompt
- 评估关系的合理性
- 输出置信度分数

**2. 反向验证**

- 从目标概念反向验证关系
- 确保双向一致性

**3. 一致性检查**

- 多次采样（n=3）
- 比较结果一致性
- 计算一致性分数

**验证流程**：

```python
def validate_relation(relation):
    # 直接验证
    direct_result = direct_validation(relation)

    # 反向验证
    reverse_result = reverse_validation(relation)

    # 综合判断
    is_valid = (
        direct_result.valid and
        direct_result.confidence >= 0.6 and
        reverse_result.valid and
        reverse_result.confidence >= 0.6
    )

    return is_valid
```

### 4.3 Knowledge Graph Service (图谱服务)

**职责**：

- 管理 Neo4j 连接
- 执行图谱 CRUD 操作
- 提供图查询接口

**数据模型**：

```cypher
# 节点
(:Concept {
    id: String,
    label: String,
    domain: String,
    type: String,  // "center" or "related"
    definition: String,
    keywords: [String]
})

# 关系
(:Concept)-[:RELATES_TO {
    relation_type: String,
    strength: Integer,  // 1-10
    explanation: String,
    confidence: Float   // 0-1
}]->(:Concept)
```

### 4.4 Frontend Service (前端服务)

**技术栈**：

- React 18: 组件化 UI
- ECharts: 图谱可视化
- Axios: HTTP 客户端
- Vite: 构建工具

**核心功能**：

- 概念输入界面
- 实时图谱渲染
- 节点交互扩展
- 响应式设计

## 5. 数据流

### 5.1 图谱生成流程

```
用户输入概念
    ↓
Frontend发送POST请求
    ↓
API Gateway接收并验证
    ↓
检查Redis缓存
    ├─ 命中 → 返回缓存结果
    └─ 未命中 ↓
Agent Service处理
    ├─ 概念识别
    ├─ 跨学科挖掘
    └─ 校验层验证
    ↓
Graph Service存储
    └─ 写入Neo4j
    ↓
缓存到Redis
    ↓
返回结果给Frontend
    ↓
ECharts渲染图谱
```

### 5.2 节点扩展流程

```
用户点击节点
    ↓
Frontend发送扩展请求
    ↓
API Gateway路由
    ↓
从Neo4j获取节点信息
    ↓
Agent Service扩展概念
    ├─ 生成新关系
    └─ 校验层验证
    ↓
Graph Service更新图谱
    ↓
清除相关缓存
    ↓
返回更新后的图谱
    ↓
Frontend重新渲染
```

## 6. 性能优化

### 6.1 缓存策略

- **Redis 缓存**: 缓存已生成的图谱（TTL: 1 小时）
- **缓存键**: `graph:{md5(concept)}`
- **缓存失效**: 图谱更新时主动清除

### 6.2 异步处理

- FastAPI 异步接口
- 并发 LLM 调用（校验层）
- 非阻塞 I/O 操作

### 6.3 连接池

- Neo4j 连接池管理
- Redis 连接复用
- HTTP 连接池

### 6.4 前端优化

- 图谱按需加载
- 组件懒加载
- 防抖节流

## 7. 可扩展性

### 7.1 水平扩展

- 无状态设计，支持多实例部署
- 通过负载均衡分发请求
- 数据库读写分离（可选）

### 7.2 Kubernetes 部署

提供 K8S 配置文件：

```
k8s/
├── deployment.yaml    # 部署配置
├── service.yaml       # 服务暴露
├── configmap.yaml     # 配置管理
└── ingress.yaml       # 入口配置
```

### 7.3 监控与日志

- 结构化日志输出
- 健康检查端点
- 性能指标收集（可扩展 Prometheus）

## 8. 安全性

### 8.1 API 安全

- 输入参数验证（Pydantic）
- 请求大小限制
- CORS 配置

### 8.2 数据安全

- 环境变量管理敏感信息
- Neo4j 认证
- Redis 密码保护（可选）

### 8.3 容器安全

- 最小化基础镜像
- 非 root 用户运行
- 定期更新依赖

## 9. 容错与恢复

### 9.1 重试机制

- LLM 调用失败自动重试（最多 3 次）
- 指数退避策略

### 9.2 健康检查

- 容器级健康检查
- 服务依赖检查
- 自动重启策略

### 9.3 错误处理

- 统一错误响应格式
- 详细错误日志
- 用户友好的错误提示

## 10. 技术选型理由

| 技术      | 选型理由                        |
| --------- | ------------------------------- |
| FastAPI   | 高性能、异步支持、自动 API 文档 |
| Neo4j     | 原生图数据库、强大的图查询能力  |
| Redis     | 高性能缓存、简单易用            |
| React     | 组件化、生态丰富                |
| ECharts   | 强大的图表库、支持力导向图      |
| Docker    | 标准化容器、易于部署            |
| LangChain | LLM 应用框架、丰富的工具链      |

## 11. 未来扩展方向

1. **多模型支持**: 支持更多 LLM 后端（Claude、本地模型等）
2. **知识库集成**: 接入外部知识库进行事实验证
3. **协作功能**: 多用户协作编辑图谱
4. **导出功能**: 支持导出为 PDF、PNG 等格式
5. **推荐系统**: 基于用户历史推荐相关概念
6. **API 限流**: 实现请求限流和配额管理
7. **分布式追踪**: 集成 Jaeger 进行链路追踪
