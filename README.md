## 跨学科知识图谱智能体

backend目录包含后端代码，python+fastapi搭建  
frontend目录包含前端代码，基于Vue3+Vit+ECharts技术栈搭建  

### docker部署
需保证8000，80，27017端口空闲  
在`docker-compose.yml`同级目录下运行下面的命令
```bash
docker-compose up -d --build
```
访问80端口即可

### 快速体验
访问`http://124.71.187.190:8001/`（不保证一定能访问，服务器可能出问题）