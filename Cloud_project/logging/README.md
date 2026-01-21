# 日志管理系统文档

## 概述

本项目使用 ELK Stack (Elasticsearch + Logstash + Kibana) + Filebeat 构建完整的日志管理系统，实现日志的集中收集、存储、分析和可视化。

## 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                   应用容器                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │   App    │  │ MongoDB  │  │  Redis   │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │             │             │                     │
│       └─────────────┴─────────────┘                     │
│                     │                                   │
│                     ▼                                   │
└─────────────────────┼───────────────────────────────────┘
                      │
                      │ Docker日志
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   Filebeat                             │
│  收集Docker容器日志并发送到Logstash                      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ Beats协议
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   Logstash                             │
│  过滤、解析和转换日志数据                               │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ HTTP协议
                      ▼
┌─────────────────────────────────────────────────────────┐
│                Elasticsearch                           │
│  存储和索引日志数据                                    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ HTTP协议
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    Kibana                               │
│  日志可视化和分析界面                                   │
└─────────────────────────────────────────────────────────┘
```

## 快速启动

### 1. 启动日志服务

```bash
cd logging
docker-compose up -d
```

### 2. 访问日志界面

- **Kibana**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200
- **Logstash**: http://localhost:9600

### 3. 配置Kibana索引模式

1. 打开 Kibana (http://localhost:5601)
2. 进入 "Management" > "Stack Management" > "Index Patterns"
3. 创建索引模式: `learning-agent-logs-*`
4. 选择时间字段: `@timestamp`

## 配置说明

### Filebeat 配置

Filebeat 负责收集 Docker 容器的日志：

```yaml
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  processors:
  - add_docker_metadata:
      host: "unix:///var/run/docker.sock"
```

**主要功能**:
- 自动收集所有容器日志
- 添加 Docker 元数据（容器名称、镜像、标签等）
- 发送到 Logstash

### Logstash 配置

Logstash 负责过滤和转换日志数据：

```conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [container][name] {
    mutate {
      add_field => { "service_name" => "%{[container][name]}" }
    }
  }

  if [message] =~ /ERROR/ {
    mutate {
      add_tag => ["error"]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "learning-agent-logs-%{+YYYY.MM.dd}"
  }
}
```

**主要功能**:
- 接收 Filebeat 发送的日志
- 添加服务名称字段
- 根据日志级别添加标签（error、warning、info）
- 按日期创建索引

### Elasticsearch 配置

Elasticsearch 负责存储和索引日志数据：

```yaml
environment:
  - discovery.type=single-node
  - ES_JAVA_OPTS=-Xms512m -Xmx512m
  - xpack.security.enabled=false
```

**主要配置**:
- 单节点模式
- 内存限制 512MB
- 禁用安全认证（开发环境）

### Kibana 配置

Kibana 提供日志可视化界面：

```yaml
environment:
  - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
  - SERVER_NAME=kibana
```

**主要功能**:
- 连接到 Elasticsearch
- 提供日志搜索和可视化
- 创建仪表盘和报表

## 日志查询示例

### Kibana 查询语法

1. **查询所有错误日志**:
   ```
   tags: "error"
   ```

2. **查询特定服务的日志**:
   ```
   service_name: "learning_agent_app"
   ```

3. **查询时间范围内的日志**:
   ```
   @timestamp: [now-1h TO now]
   ```

4. **组合查询**:
   ```
   service_name: "learning_agent_app" AND tags: "error"
   ```

### Elasticsearch API 查询

```bash
# 查询所有日志
curl -X GET "localhost:9200/learning-agent-logs-*/_search?pretty"

# 查询错误日志
curl -X GET "localhost:9200/learning-agent-logs-*/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "query": {
    "term": {
      "tags": "error"
    }
  }
}'

# 查询特定服务的日志
curl -X GET "localhost:9200/learning-agent-logs-*/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "query": {
    "term": {
      "service_name": "learning_agent_app"
    }
  }
}'
```

## 日志分析

### 1. 创建仪表盘

在 Kibana 中创建自定义仪表盘：

1. 进入 "Visualize Library"
2. 创建可视化图表：
   - 错误日志趋势图
   - 服务日志分布
   - 响应时间分布
   - 请求量统计

### 2. 设置告警

在 Kibana 中设置告警规则：

1. 进入 "Alerting and Rules"
2. 创建告警规则：
   - 错误日志数量超过阈值
   - 特定服务日志停止更新
   - 响应时间异常

### 3. 日志导出

```bash
# 导出日志到文件
curl -X GET "localhost:9200/learning-agent-logs-*/_search?pretty&size=10000" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match_all": {}
  }
}' > logs.json
```

## 性能优化

### 1. Elasticsearch 优化

```yaml
# 增加内存分配
- ES_JAVA_OPTS=-Xms1g -Xmx1g

# 配置索引生命周期管理
PUT _ilm/policy/logs_policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "30d"
          }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

### 2. Logstash 优化

```conf
# 增加管道工作线程数量
pipeline.workers: 4
pipeline.batch.size: 125
pipeline.batch.delay: 50
```

### 3. Filebeat 优化

```yaml
# 调整日志收集频率
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  scan_frequency: 10s
  harvester_buffer_size: 16384
```

## 故障排除

### Elasticsearch 无法启动

```bash
# 检查内存是否足够
docker stats learning_agent_elasticsearch

# 查看日志
docker logs learning_agent_elasticsearch

# 检查数据目录权限
ls -la /var/lib/docker/volumes/logging_elasticsearch_data/_data
```

### Kibana 无法连接 Elasticsearch

1. 检查 Elasticsearch 是否正常运行
2. 检查网络连接
3. 检查配置文件中的 Elasticsearch 地址

### 日志未显示在 Kibana

1. 检查 Filebeat 是否正常运行
2. 检查 Logstash 是否接收日志
3. 检查 Elasticsearch 索引是否创建
4. 检查 Kibana 索引模式配置

### 日志收集延迟

```bash
# 检查 Filebeat 性能
docker stats learning_agent_filebeat

# 检查 Logstash 性能
docker stats learning_agent_logstash

# 检查 Elasticsearch 性能
curl -X GET "localhost:9200/_cat/indices?v"
```

## 安全配置

### 启用 Elasticsearch 安全

```yaml
environment:
  - xpack.security.enabled=true
  - ELASTIC_PASSWORD=your_secure_password
```

### 启用 Kibana 安全

```yaml
environment:
  - ELASTICSEARCH_USERNAME=kibana_system
  - ELASTICSEARCH_PASSWORD=your_secure_password
```

## 监控和告警

### Elasticsearch 监控

```bash
# 查看集群健康状态
curl -X GET "localhost:9200/_cluster/health?pretty"

# 查看节点统计信息
curl -X GET "localhost:9200/_nodes/stats?pretty"

# 查看索引统计信息
curl -X GET "localhost:9200/_cat/indices?v"
```

### Logstash 监控

```bash
# 查看 Logstash 统计信息
curl -X GET "localhost:9600/_node/stats?pretty"
```

### Filebeat 监控

```bash
# 查看 Filebeat 统计信息
curl -X GET "localhost:5066/stats?pretty"
```

## 最佳实践

1. **定期清理旧日志**: 配置索引生命周期管理，自动删除旧日志
2. **设置合理的告警阈值**: 避免告警疲劳
3. **优化日志格式**: 使用结构化日志格式（JSON）
4. **监控日志系统性能**: 定期检查 Elasticsearch、Logstash、Filebeat 的性能
5. **备份重要日志**: 定期备份 Elasticsearch 数据
6. **限制日志保留时间**: 根据需求设置合理的日志保留时间
7. **使用日志级别**: 合理使用不同日志级别（DEBUG、INFO、WARNING、ERROR）

## 相关文档

- [Elasticsearch 官方文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Logstash 官方文档](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Kibana 官方文档](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Filebeat 官方文档](https://www.elastic.co/guide/en/beats/filebeat/current/index.html)
- [项目主 README](../README.md)
- [监控文档](../monitoring/README.md)