分工说明：

- 柯宇：负责LLM Agent 设计 + 智能逻辑实现，PPT 内容理解 Agent，知识扩展 / RAG Agent，DeepSeek API 调用，向量化与检索逻辑，Prompt 设计与优化

  ```
  backend/
  ├── app/agents/
  │   ├── ppt_agent.py
  │   ├── expansion_agent.py
  │   ├── orchestrator.py
  ├── app/parsers/
  │   ├── ppt_parser.py
  │   ├── pdf_parser.py
  ├── app/models/
  ```

- 王可楠:负责系统架构设计 + 前后端工程实现，系统整体架构设计，FastAPI 后端工程，Vue3 前端工程，Docker 容器化与部署，前后端接口设计

  ```
  frontend/
  ├── src/
  │   ├── views/
  │   ├── components/
  │   ├── api/
  │   ├── stores/
  │   ├── router/
  
  backend/
  ├── app/api/
  ├── app/core/
  ├── Dockerfile
  
  docker/
  ├── docker-compose.yml
  ```

  

