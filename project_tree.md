```
Cloud_project_v7
├─ .env
├─ .streamlit
│  └─ config.toml
├─ app.py
├─ backend
│  ├─ agents
│  │  ├─ base_agent.py
│  │  ├─ quiz_generator.py
│  │  └─ quiz_grader.py
│  ├─ config.py
│  ├─ dashboard_service.py
│  ├─ database_service.py
│  ├─ ingestion_service.py
│  └─ rag_service.py
├─ debug_ocr.py
├─ docker-compose.yml
├─ Dockerfile
├─ frontend
│  ├─ auth_view.py
│  ├─ dashboard_view.py
│  ├─ exam_view.py
│  ├─ sidebar.py
│  └─ style.css
├─ init-mongo.js
├─ input
│  ├─ mmexport1768842375092.mp3
│  ├─ 当代数据管理系统实验课总结（考试携带）v1.0.pdf
│  ├─ 环境配置—QEMU+xv6.pdf
│  └─ 第一单元.pdf
├─ k8s
│  ├─ api-gateway-deployment.yaml
│  ├─ app-deployment.yaml
│  ├─ configmaps.yaml
│  ├─ microservices-namespace.yaml
│  ├─ mistake-manager-deployment.yaml
│  ├─ mongodb-replica.yaml
│  ├─ namespace.yaml
│  ├─ quiz-generator-deployment.yaml
│  ├─ quiz-grader-deployment.yaml
│  ├─ redis-cluster.yaml
│  └─ secrets.yaml
├─ logging
│  ├─ docker-compose.yml
│  ├─ filebeat
│  │  └─ filebeat.yml
│  ├─ kibana
│  │  └─ kibana.yml
│  ├─ logstash
│  │  ├─ config
│  │  │  └─ logstash.yml
│  │  └─ pipeline
│  │     └─ logstash.conf
│  └─ README.md
├─ microservices
│  ├─ .env
│  ├─ docker-compose.yml
│  ├─ mistake_manager_service.py
│  ├─ nginx
│  │  └─ nginx.conf
│  ├─ quiz_generator_service.py
│  └─ quiz_grader_service.py
├─ monitoring
│  ├─ alertmanager
│  │  └─ alertmanager.yml
│  ├─ alerts
│  │  └─ learning-agent-alerts.yml
│  ├─ docker-compose.yml
│  ├─ grafana
│  │  └─ provisioning
│  │     ├─ dashboards
│  │     │  └─ learning_agent_dashboard.json
│  │     └─ datasources
│  │        └─ prometheus.yml
│  ├─ prometheus
│  │  └─ prometheus.yml
│  ├─ prometheus.yml
│  └─ README.md
├─ project_tree.md
├─ README.md
├─ requirements.txt
├─ static
└─ 说明文档（README）
   ├─ API_DOCUMENTATION.md
   ├─ ARCHITECTURE.md
   ├─ DEPLOYMENT_GUIDE.md
   ├─ KUBERNETES_DEPLOYMENT.md
   ├─ README.md
   └─ TESTING_GUIDE.md

```