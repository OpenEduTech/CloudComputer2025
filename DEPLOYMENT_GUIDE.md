# 智能学习助手系统 - 完整部署指南

## 目录

1. [系统概述](#系统概述)
2. [环境要求](#环境要求)
3. [快速开始](#快速开始)
4. [详细部署步骤](#详细部署步骤)
5. [配置说明](#配置说明)
6. [性能调优](#性能调优)
7. [监控和告警](#监控和告警)
8. [故障排除](#故障排除)
9. [安全加固](#安全加固)
10. [备份和恢复](#备份和恢复)

---

## 系统概述

### 架构组件

智能学习助手系统采用微服务架构，包含以下核心组件：

#### 应用层
- **出题服务 (quiz-generator)**: 负责生成试卷和题目
- **判卷服务 (quiz-grader)**: 负责评分和批改
- **错题管理服务 (mistake-manager)**: 负责错题管理和复习建议
- **API网关 (api-gateway)**: 负责流量分发和负载均衡

#### 数据层
- **MongoDB副本集**: 主从复制，提供高可用性
- **Redis集群**: 3主3从，提供缓存和会话管理

#### 监控层
- **Prometheus**: 指标采集和存储
- **Grafana**: 可视化监控面板
- **Alertmanager**: 告警管理和通知

#### 日志层
- **Elasticsearch**: 日志存储和搜索
- **Logstash**: 日志收集和处理
- **Kibana**: 日志可视化

---

## 环境要求

### 硬件要求

#### 最小配置（开发/测试环境）
- CPU: 4 核
- 内存: 8 GB
- 磁盘: 50 GB SSD

#### 推荐配置（生产环境）
- CPU: 8 核
- 内存: 16 GB
- 磁盘: 100 GB SSD

#### 高可用配置（大规模生产环境）
- CPU: 16 核
- 内存: 32 GB
- 磁盘: 200 GB SSD

### 软件要求

#### 必需软件
- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+, RHEL 8+)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.8+

#### 可选软件（Kubernetes部署）
- **Kubernetes**: 1.20+
- **kubectl**: 1.20+
- **Helm**: 3.0+

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd Cloud_project
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

### 3. 启动服务

```bash
# 启动核心服务
docker-compose up -d

# 启动监控服务
cd monitoring
docker-compose up -d

# 启动日志服务
cd ../logging
docker-compose up -d
```

### 4. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 访问应用
# 主应用: http://localhost:8501
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

---

## 详细部署步骤

### 阶段1: 准备工作

#### 1.1 系统初始化

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装必要工具
sudo apt install -y curl wget git vim net-tools

# 配置系统参数
sudo sysctl -w vm.max_map_count=262144
sudo sysctl -w fs.file-max=65536
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
echo "fs.file-max=65536" | sudo tee -a /etc/sysctl.conf
```

#### 1.2 安装Docker

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker-compose --version
```

#### 1.3 配置Docker用户

```bash
# 将当前用户添加到docker组
sudo usermod -aG docker $USER

# 重新登录或运行
newgrp docker
```

### 阶段2: 部署核心服务

#### 2.1 配置环境变量

```bash
# 创建环境变量文件
cat > .env << EOF
# OpenAI API配置
OPENAI_API_KEY=your-api-key-here
OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4

# MongoDB配置
MONGO_INITDB_ROOT_USERNAME=root
MONGO_INITDB_ROOT_PASSWORD=example
MONGO_REPLICA_SET_NAME=rs0

# Redis配置
REDIS_PASSWORD=redis_password

# 应用配置
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE=100MB
EOF
```

#### 2.2 创建数据目录

```bash
# 创建数据持久化目录
mkdir -p data/mongo{1,2,3}/{db,configdb}
mkdir -p data/redis{1,2,3,4,5,6}
mkdir -p logs/mongo{1,2,3}
mkdir -p logs/redis{1,2,3,4,5,6}
mkdir -p temp

# 设置权限
chmod -R 755 data logs temp
```

#### 2.3 启动MongoDB副本集

```bash
# 启动MongoDB容器
docker-compose up -d mongo1 mongo2 mongo3

# 等待MongoDB启动
sleep 30

# 初始化副本集
docker exec mongo1 mongosh --eval "
rs.initiate({
  _id: 'rs0',
  members: [
    { _id: 0, host: 'mongo1:27017' },
    { _id: 1, host: 'mongo2:27017' },
    { _id: 2, host: 'mongo3:27017' }
  ]
})
"

# 验证副本集状态
docker exec mongo1 mongosh --eval "rs.status()"
```

#### 2.4 启动Redis集群

```bash
# 启动Redis容器
docker-compose up -d redis1 redis2 redis3 redis4 redis5 redis6

# 等待Redis启动
sleep 20

# 初始化Redis集群
docker exec redis1 redis-cli -a redis_password --cluster create \
  redis1:6379 redis2:6379 redis3:6379 redis4:6379 redis5:6379 redis6:6379 \
  --cluster-replicas 1 --cluster-yes

# 验证集群状态
docker exec redis1 redis-cli -a redis_password cluster nodes
```

#### 2.5 启动应用服务

```bash
# 构建应用镜像
docker-compose build

# 启动应用
docker-compose up -d app

# 查看日志
docker-compose logs -f app
```

### 阶段3: 部署监控服务

#### 3.1 启动Prometheus

```bash
cd monitoring

# 启动监控服务
docker-compose up -d

# 验证Prometheus
curl http://localhost:9090/-/healthy
```

#### 3.2 配置Grafana

```bash
# 访问Grafana
# http://localhost:3000
# 默认用户名: admin
# 默认密码: admin

# 添加Prometheus数据源
# 1. 登录Grafana
# 2. 进入 Configuration > Data Sources
# 3. 添加Prometheus
# 4. URL: http://prometheus:9090
# 5. 保存并测试
```

#### 3.3 导入仪表板

```bash
# 导入预配置的仪表板
# 1. 进入 Dashboards > Import
# 2. 上传 dashboard.json 文件
# 3. 选择Prometheus数据源
# 4. 导入
```

### 阶段4: 部署日志服务

#### 4.1 启动ELK Stack

```bash
cd ../logging

# 启动日志服务
docker-compose up -d

# 等待服务启动
sleep 60

# 验证Elasticsearch
curl http://localhost:9200/_cluster/health

# 验证Kibana
curl http://localhost:5601/api/status
```

#### 4.2 配置日志收集

```bash
# 访问Kibana
# http://localhost:5601

# 创建索引模式
# 1. 进入 Management > Stack Management > Index Patterns
# 2. 创建索引模式: learning-agent-*
# 3. 选择时间字段: @timestamp
# 4. 保存
```

---

## 配置说明

### MongoDB配置

#### 连接字符串

```yaml
# 开发环境
mongodb://root:example@localhost:27017/study_agent_db

# 生产环境（副本集）
mongodb://root:example@mongo1:27017,mongo2:27017,mongo3:27017/study_agent_db?replicaSet=rs0&authSource=admin

# 生产环境（带读写分离）
mongodb://root:example@mongo1:27017,mongo2:27017,mongo3:27017/study_agent_db?replicaSet=rs0&authSource=admin&readPreference=secondaryPreferred
```

#### 性能优化

```yaml
# MongoDB配置优化
storage:
  wiredTiger:
    engineConfig:
      cacheSizeGB: 2
      journalCompressor: snappy
    collectionConfig:
      blockCompressor: snappy
    indexConfig:
      prefixCompression: true

operationProfiling:
  mode: slowOp
  slowOpThresholdMs: 100

security:
  authorization: enabled
```

### Redis配置

#### 连接配置

```yaml
# 单节点
redis://:password@localhost:6379/0

# 集群模式
redis://:password@redis1:6379,redis2:6379,redis3:6379/0
```

#### 性能优化

```yaml
# Redis配置优化
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

### 应用配置

#### 环境变量

```bash
# API配置
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4
OPENAI_EMBEDDING_MODEL=embedding-2

# 数据库配置
MONGO_URI=mongodb://root:example@mongo1:27017,mongo2:27017,mongo3:27017/study_agent_db?replicaSet=rs0&authSource=admin
REDIS_CLUSTER_NODES=redis1:6379,redis2:6379,redis3:6379,redis4:6379,redis5:6379,redis6:6379
REDIS_PASSWORD=redis_password

# 应用配置
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE=100MB
ENABLE_CORS=true
CORS_ORIGINS=*

# 性能配置
WORKER_PROCESSES=4
MAX_REQUESTS=1000
REQUEST_TIMEOUT=300
```

---

## 性能调优

### 数据库优化

#### MongoDB索引优化

```javascript
// 创建复合索引
db.exam_records.createIndex({ user_id: 1, create_time: -1 })
db.error_questions.createIndex({ user_id: 1, error_times: -1 })
db.error_questions.createIndex({ keyword: 1, difficulty: 1 })

// 查看索引使用情况
db.exam_records.getIndexes()
db.error_questions.getIndexes()

// 分析查询性能
db.exam_records.find({ user_id: "user123" }).explain("executionStats")
```

#### Redis缓存优化

```bash
# 设置缓存过期时间
redis-cli -a redis_password SETEX "user:user123:exam:456" 3600 "exam_data"

# 批量操作减少网络开销
redis-cli -a redis_password MGET key1 key2 key3

# 使用Pipeline减少RTT
redis-cli -a redis_password --pipe <<EOF
SET key1 value1
SET key2 value2
SET key3 value3
EOF
```

### 应用优化

#### 连接池配置

```python
# MongoDB连接池
from pymongo import MongoClient

client = MongoClient(
    MONGO_URI,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=30000,
    connectTimeoutMS=5000,
    socketTimeoutMS=30000,
    serverSelectionTimeoutMS=5000
)

# Redis连接池
from redis.cluster import RedisCluster

redis_client = RedisCluster(
    startup_nodes=redis_nodes,
    password=REDIS_PASSWORD,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    max_connections_per_node=10
)
```

#### 异步处理

```python
# 使用异步处理提高并发
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def async_grade_submissions(submissions):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as executor:
        tasks = [
            loop.run_in_executor(executor, grade_submission, sub)
            for sub in submissions
        ]
        results = await asyncio.gather(*tasks)
    return results
```

### 系统优化

#### 内核参数调优

```bash
# 编辑 /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# 应用配置
sudo sysctl -p
```

#### Docker资源限制

```yaml
# docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

---

## 监控和告警

### 关键指标

#### 应用指标
- **请求速率**: http_requests_total
- **响应时间**: http_request_duration_seconds
- **错误率**: http_requests_total{status=~"5.."}
- **并发连接**: http_active_connections

#### 数据库指标
- **MongoDB**: 
  - 连接数: mongodb_connections
  - 操作延迟: mongodb_op_latency
  - 内存使用: mongodb_memory_usage
  
- **Redis**:
  - 命中率: cache_hit_rate
  - 内存使用: redis_memory_usage
  - 连接数: redis_connections

#### 系统指标
- **CPU使用率**: cpu_usage_percent
- **内存使用率**: memory_usage_percent
- **磁盘使用率**: disk_usage_percent
- **网络流量**: network_traffic

### 告警规则

#### Critical告警
- 服务不可用
- 错误率 > 10%
- 数据库连接失败
- 磁盘空间 < 15%

#### Warning告警
- 响应时间 > 1s
- CPU使用率 > 80%
- 内存使用率 > 85%
- 缓存命中率 < 50%

### 监控面板

访问Grafana查看预配置的监控面板：
- 系统概览
- 应用性能
- 数据库性能
- 错误分析

---

## 故障排除

### 常见问题

#### 1. 服务无法启动

```bash
# 查看容器日志
docker-compose logs app

# 检查容器状态
docker-compose ps

# 检查端口占用
netstat -tulpn | grep 8501

# 重启服务
docker-compose restart app
```

#### 2. MongoDB连接失败

```bash
# 检查MongoDB状态
docker exec mongo1 mongosh --eval "rs.status()"

# 检查连接
docker exec app ping mongo1

# 重启MongoDB
docker-compose restart mongo1 mongo2 mongo3
```

#### 3. Redis连接失败

```bash
# 检查Redis状态
docker exec redis1 redis-cli -a redis_password cluster nodes

# 检查连接
docker exec app ping redis1

# 重启Redis
docker-compose restart redis1 redis2 redis3 redis4 redis5 redis6
```

#### 4. API密钥错误

```bash
# 检查环境变量
docker-compose exec app env | grep OPENAI

# 更新API密钥
# 编辑 .env 文件
OPENAI_API_KEY=new-api-key

# 重启应用
docker-compose restart app
```

### 日志分析

```bash
# 查看应用日志
docker-compose logs -f app

# 查看MongoDB日志
docker-compose logs -f mongo1

# 查看Redis日志
docker-compose logs -f redis1

# 查看系统日志
journalctl -u docker -f
```

---

## 安全加固

### 1. 网络安全

```yaml
# 配置防火墙
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 限制Docker网络访问
# 编辑 /etc/docker/daemon.json
{
  "iptables": false,
  "userland-proxy": false
}
```

### 2. 数据加密

```bash
# 启用MongoDB加密
# 编辑MongoDB配置
security:
  encryptionKeyFile: /etc/mongodb/keyfile
  enableEncryption: true

# 启用Redis TLS
# 编辑Redis配置
tls-port 6379
port 0
tls-cert-file /etc/redis/redis.crt
tls-key-file /etc/redis/redis.key
```

### 3. 访问控制

```yaml
# 配置RBAC
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: learning-agent
  name: app-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
```

---

## 备份和恢复

### MongoDB备份

```bash
# 创建备份
docker exec mongo1 mongodump --archive=/data/backup/mongo-backup.gz --gzip

# 复制备份文件
docker cp mongo1:/data/backup/mongo-backup.gz ./mongo-backup.gz

# 恢复备份
docker cp ./mongo-backup.gz mongo1:/data/backup/mongo-backup.gz
docker exec mongo1 mongorestore --archive=/data/backup/mongo-backup.gz --gzip
```

### Redis备份

```bash
# 创建RDB备份
docker exec redis1 redis-cli -a redis_password BGSAVE

# 复制备份文件
docker cp redis1:/data/dump.rdb ./redis-backup.rdb

# 恢复备份
docker cp ./redis-backup.rdb redis1:/data/dump.rdb
docker restart redis1
```

### 自动化备份

```bash
# 创建备份脚本
cat > /opt/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups

# MongoDB备份
docker exec mongo1 mongodump --archive=$BACKUP_DIR/mongo_$DATE.gz --gzip

# Redis备份
docker exec redis1 redis-cli -a redis_password BGSAVE
docker cp redis1:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "mongo_*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "redis_*.rdb" -mtime +7 -delete
EOF

chmod +x /opt/backup.sh

# 添加到crontab
0 2 * * * /opt/backup.sh
```

---

## 附录

### 端口映射

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| 应用 | 8501 | HTTP | Streamlit应用 |
| API网关 | 8080 | HTTP | API网关 |
| 出题服务 | 8001 | HTTP | 出题API |
| 判卷服务 | 8002 | HTTP | 判卷API |
| 错题管理服务 | 8003 | HTTP | 错题管理API |
| MongoDB | 27017-27019 | TCP | MongoDB副本集 |
| Redis | 6379-6384 | TCP | Redis集群 |
| Prometheus | 9090 | HTTP | 监控指标 |
| Grafana | 3000 | HTTP | 监控面板 |
| Alertmanager | 9093 | HTTP | 告警管理 |
| Elasticsearch | 9200 | HTTP | 日志存储 |
| Kibana | 5601 | HTTP | 日志面板 |

### 常用命令

```bash
# Docker命令
docker-compose up -d              # 启动服务
docker-compose down                # 停止服务
docker-compose logs -f app         # 查看日志
docker-compose ps                  # 查看状态
docker-compose restart app         # 重启服务

# 数据库命令
docker exec mongo1 mongosh         # 连接MongoDB
docker exec redis1 redis-cli       # 连接Redis

# 监控命令
docker-compose -f monitoring/docker-compose.yml logs -f prometheus
docker-compose -f logging/docker-compose.yml logs -f elasticsearch
```

---

## 联系支持

如有问题，请：
1. 查看故障排除章节
2. 检查系统日志
3. 提交Issue
4. 联系技术支持团队

---

**文档版本**: v1.0  
**最后更新**: 2026-01-18  
**维护者**: 智能学习助手开发团队