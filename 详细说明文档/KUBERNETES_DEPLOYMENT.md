# Kubernetes 部署指南

## 概述

本指南详细说明了如何使用 Kubernetes 部署智能学习助手系统的微服务架构。

## 架构说明

### 微服务组件

系统包含以下微服务：

1. **出题服务 (quiz-generator-service)** - 负责生成试卷和题目
2. **判卷服务 (quiz-grader-service)** - 负责评分和批改
3. **错题管理服务 (mistake-manager-service)** - 负责错题管理和复习建议
4. **API网关 (api-gateway)** - 负责流量分发和负载均衡

### 依赖服务

- **MongoDB副本集** - 数据持久化
- **Redis集群** - 缓存和会话管理

## 前置要求

### 必需软件

- Kubernetes 1.20+
- kubectl 1.20+
- Docker 20.10+
- Helm 3.0+ (可选)

### 资源要求

- CPU: 至少 4 核
- 内存: 至少 8GB
- 磁盘: 至少 50GB

## 部署步骤

### 1. 准备工作

#### 1.1 克隆仓库

```bash
git clone <repository-url>
cd Cloud_project
```

#### 1.2 配置密钥

编辑 `k8s/secrets.yaml`，将 `<base64-encoded-api-key>` 替换为实际的 API 密钥：

```bash
echo -n "your-openai-api-key" | base64
```

#### 1.2.1 创建命名空间

```bash
kubectl apply -f k8s/microservices-namespace.yaml
```

### 2. 部署配置

#### 2.1 部署 ConfigMap 和 Secret

```bash
kubectl apply -f k8s/configmaps.yaml
kubectl apply -f k8s/secrets.yaml
```

#### 2.2 部署微服务

```bash
kubectl apply -f k8s/quiz-generator-deployment.yaml
kubectl apply -f k8s/quiz-grader-deployment.yaml
kubectl apply -f k8s/mistake-manager-deployment.yaml
kubectl apply -f k8s/api-gateway-deployment.yaml
```

#### 2.3 验证部署

```bash
kubectl get pods -n learning-agent
kubectl get services -n learning-agent
```

### 3. 部署依赖服务

#### 3.1 部署 MongoDB

```bash
kubectl apply -f k8s/mongodb-statefulset.yaml
```

#### 3.2 部署 Redis

```bash
kubectl apply -f k8s/redis-statefulset.yaml
```

### 4. 访问应用

#### 4.1 获取 API 网关地址

```bash
kubectl get svc api-gateway -n learning-agent
```

#### 4.2 访问应用

如果使用 LoadBalancer 类型服务：

```bash
EXTERNAL_IP=$(kubectl get svc api-gateway -n learning-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "应用地址: http://$EXTERNAL_IP"
```

如果使用 NodePort 类型服务：

```bash
NODE_PORT=$(kubectl get svc api-gateway -n learning-agent -o jsonpath='{.spec.ports[0].nodePort}')
echo "应用地址: http://<node-ip>:$NODE_PORT"
```

## 管理操作

### 扩展服务

#### 手动扩展

```bash
kubectl scale deployment quiz-generator-service --replicas=5 -n learning-agent
```

#### 自动扩缩容

HPA 已配置，会根据 CPU 和内存使用率自动扩展：

```bash
kubectl get hpa -n learning-agent
```

### 查看日志

```bash
kubectl logs -f deployment/quiz-generator-service -n learning-agent
```

### 进入容器

```bash
kubectl exec -it deployment/quiz-generator-service -n learning-agent -- /bin/bash
```

### 更新服务

```bash
kubectl set image deployment/quiz-generator-service quiz-generator=learning-agent:quiz-generator:v2 -n learning-agent
```

### 回滚服务

```bash
kubectl rollout undo deployment/quiz-generator-service -n learning-agent
```

## 监控和告警

### Prometheus 集成

部署 Prometheus 监控：

```bash
kubectl apply -f k8s/monitoring/
```

访问 Grafana：

```bash
kubectl port-forward svc/grafana 3000:3000 -n learning-agent
```

### 查看指标

```bash
kubectl top pods -n learning-agent
kubectl top nodes
```

## 故障排除

### Pod 无法启动

```bash
kubectl describe pod <pod-name> -n learning-agent
kubectl logs <pod-name> -n learning-agent
```

### 服务无法访问

```bash
kubectl get endpoints -n learning-agent
kubectl describe svc <service-name> -n learning-agent
```

### 资源不足

```bash
kubectl describe nodes
kubectl get resourcequota -n learning-agent
```

## 性能优化

### 资源限制

根据实际负载调整资源限制：

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### HPA 配置

调整自动扩缩容参数：

```yaml
minReplicas: 2
maxReplicas: 10
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 安全加固

### 网络策略

启用网络策略限制服务间通信：

```bash
kubectl apply -f k8s/network-policies.yaml
```

### RBAC 配置

配置基于角色的访问控制：

```bash
kubectl apply -f k8s/rbac/
```

### Pod 安全策略

启用 Pod 安全策略：

```bash
kubectl apply -f k8s/pod-security-policies.yaml
```

## 备份和恢复

### MongoDB 备份

```bash
kubectl exec -it mongo1-0 -n learning-agent -- mongodump --archive=/data/backup/mongo-backup.gz
kubectl cp mongo1-0:/data/backup/mongo-backup.gz ./mongo-backup.gz -n learning-agent
```

### MongoDB 恢复

```bash
kubectl cp ./mongo-backup.gz mongo1-0:/data/backup/mongo-backup.gz -n learning-agent
kubectl exec -it mongo1-0 -n learning-agent -- mongorestore --archive=/data/backup/mongo-backup.gz
```

## 卸载

```bash
kubectl delete -f k8s/
kubectl delete namespace learning-agent
```

## 附录

### 端口映射

| 服务 | 端口 | 协议 |
|------|------|------|
| API 网关 | 80 | HTTP |
| 出题服务 | 8001 | HTTP |
| 判卷服务 | 8002 | HTTP |
| 错题管理服务 | 8003 | HTTP |
| MongoDB | 27017 | TCP |
| Redis | 6379 | TCP |

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| OPENAI_API_KEY | OpenAI API 密钥 | - |
| OPENAI_API_BASE | OpenAI API 地址 | https://open.bigmodel.cn/api/paas/v4 |
| MONGO_URI | MongoDB 连接字符串 | - |
| REDIS_CLUSTER_NODES | Redis 集群节点 | - |
| REDIS_PASSWORD | Redis 密码 | - |
| LOG_LEVEL | 日志级别 | INFO |

### 常用命令

```bash
# 查看所有 Pod
kubectl get pods -n learning-agent

# 查看所有服务
kubectl get svc -n learning-agent

# 查看部署状态
kubectl get deployments -n learning-agent

# 查看事件
kubectl get events -n learning-agent

# 查看资源使用
kubectl top pods -n learning-agent
```

## 支持

如有问题，请提交 Issue 或联系维护团队。