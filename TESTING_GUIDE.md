# 修改后功能测试指南

## 概述

本文档详细说明如何测试智能学习助手系统的所有改进功能，包括微服务架构、Kubernetes部署、监控告警、CI/CD和性能测试。

---

## 测试前准备

### 1. 启动Docker

#### Windows
1. 打开Docker Desktop
2. 等待Docker完全启动（状态栏显示"Docker Desktop is running"）
3. 验证Docker运行状态：
   ```bash
   docker ps
   ```

#### Linux
```bash
sudo systemctl start docker
sudo systemctl enable docker
docker ps
```

### 2. 检查环境变量

确保 `.env` 文件包含必要的配置：

```bash
OPENAI_API_KEY=your-api-key-here
OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4
MONGO_INITDB_ROOT_USERNAME=root
MONGO_INITDB_ROOT_PASSWORD=example
MONGO_REPLICA_SET_NAME=rs0
REDIS_PASSWORD=redis_password
LOG_LEVEL=INFO
```

### 3. 安装测试依赖

```bash
pip install requests locust pytest pytest-cov
```

---

## 测试1: 微服务架构测试

### 1.1 启动微服务

```bash
cd d:\dasansang3\yunjisuan\Cloud_project\microservices
docker-compose up -d
```

### 1.2 验证服务状态

```bash
# 查看所有容器状态
docker-compose ps

# 查看服务日志
docker-compose logs -f
```

预期输出：
```
NAME                              STATUS              PORTS
learning_agent_api_gateway          Up (healthy)         0.0.0.0:8080->80/tcp
learning_agent_quiz_generator       Up (healthy)         0.0.0.0:8001->8001/tcp
learning_agent_quiz_grader         Up (healthy)         0.0.0.0:8002->8002/tcp
learning_agent_mistake_manager     Up (healthy)         0.0.0.0:8003->8003/tcp
```

### 1.3 运行自动化测试

#### Windows
```bash
cd d:\dasansang3\yunjisuan\Cloud_project
run_tests.bat
```

#### Linux/Mac
```bash
cd d:\dasansang3\yunjisuan\Cloud_project
python test_microservices.py
```

### 1.4 手动测试API端点

#### 测试API网关
```bash
# 健康检查
curl http://localhost:8080/health

# 测试路由
curl http://localhost:8080/api/generate-exam
```

#### 测试出题服务
```bash
# 生成试卷
curl -X POST http://localhost:8001/api/generate-exam \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "context": "云计算基础概念",
    "difficulty": "easy",
    "question_count": 5,
    "question_types": ["choice"]
  }'
```

#### 测试判卷服务
```bash
# 评分
curl -X POST http://localhost:8002/api/grade-submission \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "question_type": "choice",
    "question": "什么是云计算？",
    "correct_answer": "A",
    "user_answer": "A",
    "context": "云计算基础"
  }'
```

#### 测试错题管理服务
```bash
# 获取错题列表
curl "http://localhost:8003/api/mistakes?user_id=test_user_001&page=1&page_size=10"
```

---

## 测试2: 监控和告警测试

### 2.1 启动监控服务

```bash
cd d:\dasansang3\yunjisuan\Cloud_project\monitoring
docker-compose up -d
```

### 2.2 验证监控服务

```bash
# 查看监控服务状态
docker-compose ps
```

预期输出：
```
NAME                              STATUS              PORTS
learning_agent_prometheus          Up                  0.0.0.0:9090->9090/tcp
learning_agent_grafana            Up                  0.0.0.0:3000->3000/tcp
learning_agent_node_exporter       Up                  0.0.0.0:9100->9100/tcp
learning_agent_alertmanager       Up                  0.0.0.0:9093->9093/tcp
```

### 2.3 访问监控面板

#### Prometheus
- URL: http://localhost:9090
- 功能: 查询和可视化指标
- 测试: 在查询框输入 `up` 并执行

#### Grafana
- URL: http://localhost:3000
- 用户名: admin
- 密码: admin
- 功能: 监控仪表板
- 测试: 导入预配置的仪表板

#### Alertmanager
- URL: http://localhost:9093
- 功能: 查看和管理告警
- 测试: 查看告警列表

### 2.4 测试告警规则

```bash
# 查看Prometheus告警规则
curl http://localhost:9090/api/v1/rules

# 查看当前告警
curl http://localhost:9090/api/v1/alerts
```

---

## 测试3: 日志系统测试

### 3.1 启动日志服务

```bash
cd d:\dasansang3\yunjisuan\Cloud_project\logging
docker-compose up -d
```

### 3.2 验证日志服务

```bash
# 查看日志服务状态
docker-compose ps
```

预期输出：
```
NAME                              STATUS              PORTS
elasticsearch                      Up                  0.0.0.0:9200->9200/tcp
logstash                          Up                  0.0.0.0:5044->5044/tcp
kibana                            Up                  0.0.0.0:5601->5601/tcp
```

### 3.3 访问Kibana

- URL: http://localhost:5601
- 功能: 日志搜索和分析
- 测试步骤:
  1. 创建索引模式: `learning-agent-*`
  2. 选择时间字段: `@timestamp`
  3. 查看日志

---

## 测试4: 性能测试

### 4.1 正常负载测试

```bash
cd d:\dasansang3\yunjisuan\Cloud_project

# 使用Python脚本
python performance_test_comprehensive.py \
  --env development \
  --test-type normal \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --host http://localhost:8080
```

### 4.2 压力测试

```bash
python performance_test_comprehensive.py \
  --env development \
  --test-type stress \
  --users 200 \
  --spawn-rate 20 \
  --run-time 3m \
  --host http://localhost:8080
```

### 4.3 尖峰测试

```bash
python performance_test_comprehensive.py \
  --env development \
  --test-type spike \
  --users 500 \
  --spawn-rate 50 \
  --run-time 2m \
  --host http://localhost:8080
```

### 4.4 耐久测试

```bash
python performance_test_comprehensive.py \
  --env development \
  --test-type endurance \
  --users 30 \
  --spawn-rate 3 \
  --run-time 30m \
  --host http://localhost:8080
```

### 4.5 使用Locust Web界面

```bash
locust -f performance_test_enhanced.py --host http://localhost:8080
```

然后在浏览器中打开: http://localhost:8089

---

## 测试5: Kubernetes部署测试

### 5.1 准备Kubernetes环境

```bash
# 检查kubectl是否安装
kubectl version --client

# 检查集群连接
kubectl cluster-info
```

### 5.2 创建命名空间

```bash
kubectl apply -f k8s/microservices-namespace.yaml
```

### 5.3 部署配置和密钥

```bash
# 部署ConfigMap
kubectl apply -f k8s/configmaps.yaml

# 部署Secret（需要先编辑secrets.yaml）
kubectl apply -f k8s/secrets.yaml
```

### 5.4 部署微服务

```bash
# 部署出题服务
kubectl apply -f k8s/quiz-generator-deployment.yaml

# 部署判卷服务
kubectl apply -f k8s/quiz-grader-deployment.yaml

# 部署错题管理服务
kubectl apply -f k8s/mistake-manager-deployment.yaml

# 部署API网关
kubectl apply -f k8s/api-gateway-deployment.yaml
```

### 5.5 验证部署

```bash
# 查看Pod状态
kubectl get pods -n learning-agent

# 查看Service状态
kubectl get services -n learning-agent

# 查看Deployment状态
kubectl get deployments -n learning-agent

# 查看HPA状态
kubectl get hpa -n learning-agent
```

### 5.6 测试服务

```bash
# 获取API网关地址
kubectl get svc api-gateway -n learning-agent

# 测试服务
kubectl port-forward svc/api-gateway 8080:80 -n learning-agent
```

然后在浏览器中访问: http://localhost:8080

---

## 测试6: CI/CD测试

### 6.1 配置GitHub Secrets

在GitHub仓库中配置以下Secrets：
- `STAGING_KUBE_CONFIG`: 测试环境kubeconfig
- `PRODUCTION_KUBE_CONFIG`: 生产环境kubeconfig
- `SLACK_WEBHOOK`: Slack通知webhook

### 6.2 触发CI/CD

```bash
# 推送代码到develop分支
git checkout develop
git add .
git commit -m "Test CI/CD pipeline"
git push origin develop
```

### 6.3 查看CI/CD状态

在GitHub仓库中查看Actions标签页：
1. 查看工作流运行状态
2. 查看各个job的日志
3. 查看部署结果

---

## 测试结果验证

### 1. 自动化测试结果

运行 `test_microservices.py` 后，检查生成的JSON文件：

```bash
# 查看最新的测试结果
ls -lt test_results_*.json | head -1
```

预期结果：
- `total_tests`: >= 8
- `passed_tests`: >= 7
- `success_rate`: >= 85%

### 2. 性能测试结果

查看生成的性能报告：
- HTML报告: `performance_report_*.html`
- JSON结果: `performance_results_*.json`

关键指标：
- 平均响应时间 < 500ms
- P95响应时间 < 1000ms
- 错误率 < 1%

### 3. 监控指标

在Grafana中查看：
- 系统概览仪表板
- 应用性能仪表板
- 数据库性能仪表板

### 4. 日志分析

在Kibana中查看：
- 应用日志
- 错误日志
- 性能日志

---

## 故障排除

### 问题1: Docker服务未运行

**症状**: `docker ps` 命令失败

**解决方案**:
```bash
# Windows
# 打开Docker Desktop

# Linux
sudo systemctl start docker
```

### 问题2: 端口被占用

**症状**: `Error: bind: address already in use`

**解决方案**:
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8080
kill -9 <PID>
```

### 问题3: 服务启动失败

**症状**: 容器反复重启

**解决方案**:
```bash
# 查看容器日志
docker logs <container_name>

# 查看详细状态
docker inspect <container_name>

# 重启服务
docker-compose restart <service_name>
```

### 问题4: 数据库连接失败

**症状**: API返回数据库连接错误

**解决方案**:
```bash
# 检查MongoDB状态
docker exec mongo1 mongosh --eval "rs.status()"

# 检查Redis状态
docker exec redis1 redis-cli -a redis_password cluster nodes

# 重启数据库服务
docker-compose restart mongo1 mongo2 mongo3
docker-compose restart redis1 redis2 redis3 redis4 redis5 redis6
```

### 问题5: API返回404

**症状**: API端点返回404错误

**解决方案**:
```bash
# 检查API网关配置
cat nginx/nginx.conf

# 检查服务路由
docker-compose logs api_gateway

# 测试直接访问服务
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

---

## 测试检查清单

### 微服务架构
- [ ] 所有服务正常启动
- [ ] 健康检查通过
- [ ] API网关路由正常
- [ ] 各服务API端点可访问
- [ ] 服务间通信正常

### 监控告警
- [ ] Prometheus正常运行
- [ ] Grafana可访问
- [ ] Alertmanager正常运行
- [ ] 告警规则加载成功
- [ ] 指标采集正常

### 日志系统
- [ ] Elasticsearch正常运行
- [ ] Logstash正常运行
- [ ] Kibana可访问
- [ ] 日志收集正常
- [ ] 日志搜索正常

### 性能测试
- [ ] 正常负载测试通过
- [ ] 压力测试通过
- [ ] 尖峰测试通过
- [ ] 耐久测试通过
- [ ] 性能指标达标

### Kubernetes部署
- [ ] 命名空间创建成功
- [ ] ConfigMap部署成功
- [ ] Secret部署成功
- [ ] 所有Pod正常运行
- [ ] Service可访问
- [ ] HPA正常工作

### CI/CD
- [ ] 代码检查通过
- [ ] 单元测试通过
- [ ] 安全扫描通过
- [ ] 镜像构建成功
- [ ] 部署成功
- [ ] 通知发送成功

---

## 总结

完成以上所有测试后，你应该能够验证：

1. ✅ 微服务架构正常工作
2. ✅ 所有API端点可访问
3. ✅ 监控和告警系统正常
4. ✅ 日志系统正常收集
5. ✅ 性能指标达标
6. ✅ Kubernetes部署成功
7. ✅ CI/CD流水线正常

如果所有测试都通过，说明系统的改进功能都已正常工作！

---

**文档版本**: v1.0
**最后更新**: 2026-01-18
**维护者**: 智能学习助手开发团队