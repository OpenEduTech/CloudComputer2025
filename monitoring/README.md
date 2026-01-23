# 监控体系文档

## 概述

本项目使用 Prometheus + Grafana 构建完整的监控体系，实时监控系统性能、资源使用情况和应用健康状态。

## 架构说明

```
┌─────────────────┐
│   Grafana     │  (可视化面板)
│   :3000       │
└──────┬─────────┘
       │
       │ 查询指标
       ▼
┌─────────────────┐
│  Prometheus   │  (指标采集和存储)
│   :9090       │
└──────┬─────────┘
       │
       │ 采集指标
       ├──────────────┬──────────────┬──────────────┐
       │              │              │              │
       ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ MongoDB  │  │  Redis   │  │   App    │  │  Node    │
│  Exporter│  │  Exporter│  │  Metrics │  │ Exporter │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

## 快速启动

### 1. 启动监控服务

```bash
cd monitoring
docker-compose up -d
```

### 2. 访问监控界面

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - 用户名: `admin`
  - 密码: `admin`

### 3. 查看预配置的仪表盘

Grafana 已预配置了 "Learning Agent System Dashboard"，包含以下面板：

1. **System CPU Usage** - 系统CPU使用率
2. **System Memory Usage** - 系统内存使用率
3. **Redis Memory Usage** - Redis内存使用情况
4. **MongoDB Connections** - MongoDB连接数
5. **Application Response Time** - 应用响应时间
6. **Request Rate** - 请求速率

## 配置说明

### Prometheus 配置 (prometheus.yml)

```yaml
global:
  scrape_interval: 15s  # 采集间隔
  evaluation_interval: 15s  # 评估间隔

scrape_configs:
  - job_name: 'mongodb'
    static_configs:
      - targets: ['mongo1:27017', 'mongo2:27018', 'mongo3:27019']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis1:6379', 'redis2:6380', 'redis3:6381', 'redis4:6382', 'redis5:6383', 'redis6:6384']

  - job_name: 'learning_agent_app'
    static_configs:
      - targets: ['app:8501']
    metrics_path: '/metrics'
```

### Grafana 数据源配置

Grafana 已自动配置 Prometheus 数据源，无需手动配置。

## 监控指标说明

### 系统级指标

| 指标名称 | 说明 | 告警阈值 |
|----------|------|----------|
| `node_cpu_seconds_total` | CPU使用时间 | > 80% |
| `node_memory_MemAvailable_bytes` | 可用内存 | < 20% |
| `node_filesystem_avail_bytes` | 磁盘可用空间 | < 10% |

### 应用级指标

| 指标名称 | 说明 | 告警阈值 |
|----------|------|----------|
| `redis_memory_used_bytes` | Redis内存使用 | > 80% |
| `mongodb_connections` | MongoDB连接数 | > 100 |
| `http_request_duration_seconds` | HTTP请求耗时 | > 1s |
| `http_requests_total` | HTTP请求总数 | - |

## 告警配置

### 添加告警规则

创建 `alerting.yml` 文件：

```yaml
groups:
  - name: learning_agent_alerts
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode!='idle'}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"

      - alert: HighMemoryUsage
        expr: 100 * (1 - ((node_memory_MemAvailable_bytes) / (node_memory_MemTotal_bytes))) > 80
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"

      - alert: RedisDown
        expr: up{job='redis'} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis instance is down"

      - alert: MongoDBDown
        expr: up{job='mongodb'} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "MongoDB instance is down"
```

### 配置告警通知

在 `prometheus.yml` 中添加告警配置：

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

## 性能分析

### 1. 查看系统资源使用

在 Grafana 仪表盘中查看 CPU、内存、磁盘使用情况，识别资源瓶颈。

### 2. 分析应用性能

查看应用响应时间和请求速率，识别性能问题。

### 3. 数据库性能分析

查看 MongoDB 和 Redis 的连接数和内存使用情况，优化数据库配置。

## 故障排除

### Prometheus 无法启动

```bash
# 检查配置文件语法
docker exec learning_agent_prometheus promtool check config /etc/prometheus/prometheus.yml

# 查看日志
docker logs learning_agent_prometheus
```

### Grafana 无法连接 Prometheus

1. 检查 Prometheus 是否正常运行
2. 检查数据源配置是否正确
3. 检查网络连接

### 指标采集失败

```bash
# 检查目标服务是否可达
curl http://localhost:9090/api/v1/targets

# 检查服务是否暴露指标端点
curl http://app:8501/metrics
```

## 扩展监控

### 添加自定义指标

在应用代码中添加 Prometheus 客户端：

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

# 记录指标
request_count.labels(method='GET', status=200).inc()
request_duration.observe(0.5)
```

### 添加新的监控目标

在 `prometheus.yml` 中添加新的 scrape_config：

```yaml
scrape_configs:
  - job_name: 'new_service'
    static_configs:
      - targets: ['new_service:8080']
```

## 最佳实践

1. **定期检查监控数据**：每天查看仪表盘，及时发现异常
2. **设置合理的告警阈值**：避免告警疲劳
3. **优化告警通知**：使用邮件、短信等多种通知方式
4. **定期备份监控数据**：避免数据丢失
5. **持续优化监控配置**：根据实际需求调整采集间隔和存储策略

## 相关文档

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [项目主 README](../README.md)