# InterKnow_Graph_Agent
云计算大作业都在这里


docker build -t interknow_graph_agent .

docker run -p 8000:8000 interknow_graph_agent

http://127.0.0.1:8000/graph.html

docker container prune

docker rm -f $(docker ps -aq)


## 1. 项目概览
InterKnow Graph Agent——跨学科知识图谱智能体。

核心目标：输入任意“核心概念”，生成跨学科节点与关系，并在 Web 前端以可交互图谱展示，同时提供聊天与统计面板。

运行形态为FastAPI 后端 + 火山方舟 LLM + TinyDB 本地缓存 + ECharts 前端，支持 Docker 一键启动。

## 2. 架构设计
主要组件

  - 后端：FastAPI 服务 [main.py](main.py)、API 路由 [backend/routing/router.py](backend/routing/router.py)，业务逻辑集中在 [backend/models](backend/models)。
  
  - 智能体与工具链：LLM 图谱生成 [backend/models/llm_graph_builder.py](backend/models/llm_graph_builder.py)，聊天接口 [backend/models/chat.py](backend/models/chat.py)，Prompt 及校验工具位于 [backend/models/lib](backend/models/lib)。
  
  - 前端：页面模板 [frontend/templates/graph.html](frontend/templates/graph.html) 等，交互脚本 [frontend/static/js/app.js](frontend/static/js/app.js)，ECharts 库 [frontend/static/js_lib/echarts.min.js](frontend/static/js_lib/echarts.min.js)。
  
  - 数据与演示：示例图 [frontend/static/json/sample_data.json](frontend/static/json/sample_data.json)，根目录同步副本 [sample_data.json](sample_data.json)。
  
  - 测试与运维：健康检查脚本 [test/healthcheck.py](test/healthcheck.py)，图谱导出脚本 [test/dump_graph.py](test/dump_graph.py)。


数据流（/api/graph）
  1) 前端提交概念到 FastAPI；
  2) 布隆过滤器命中则直接从 TinyDB 复用；
  3) 未命中时调用火山方舟模型生成图；
  4) 经过 JSON 解析、内容校验、再生成/修复；
  5) 将 nodes/links 下发前端渲染并累积 token 计数。
- 部署拓扑：容器内运行 uvicorn，监听 8000 端口，静态文件与模板由 FastAPI 内建服务，外部仅需暴露 8000（或经网关/K8S Ingress 代理）。

## 3. 云原生与工程实践
容器化：提供 Dockerfile，可在干净环境 `docker build -t interknow_graph_agent .` 后 `docker run -p 8000:8000 interknow_graph_agent` 启动。

弹性与缓存：布隆过滤器 + TinyDB 复用热点概念；前端离线模式自动回退本地样例，避免后端不可用导致空白页。

观测与健壮性：LLM 调用计入 tokens/counts（/api/counts_and_tokens），校验层裁剪孤立节点、限制关系长度，减少幻觉和断链；健康检查脚本方便接入 CI。

## 4. 模块说明
- 后端入口与路由：
  - [main.py](main.py) 启动 uvicorn，并模拟其他用户更新计数，演示并发访问场景。
  - [backend/routing/router.py](backend/routing/router.py) 提供 /api/graph、/api/chat、/api/counts_and_tokens 以及页面路由。
- 智能体核心：
  - [backend/models/llm_graph_builder.py](backend/models/llm_graph_builder.py) 调用 Ark 模型生成图，包含强约束校验、再生成逻辑、节点/关系补全与缩放。
  - [backend/models/chat.py](backend/models/chat.py) 将最近 8 轮对话压缩为提示，调用同一 Ark 模型返回回复与 token 用量。
  - 辅助库 [backend/models/lib](backend/models/lib) 负责 Prompt 拼装、JSON 解析、质量检查（学科覆盖、关系合理性）和节点裁剪。
- 前端：
  - 模板 [frontend/templates/graph.html](frontend/templates/graph.html) 等负责页面布局。
  - 脚本 [frontend/static/js/app.js](frontend/static/js/app.js) 处理查询、文件导入导出、ECharts 渲染、离线样例回退与信息面板；其余 JS 管理计数展示、查找页等。
  - 样式 [frontend/static/css](frontend/static/css) 控制导航、时钟与主题风格。
- 数据与测试：TinyDB 数据文件 [db.json](db.json) 在运行时生成；测试脚本位于 [test](test)。

## 5. 智能体策略与 Prompt 工程
- Prompt 生成与模型调用：
  - 使用 `build_prompt()` 生成首轮提示，限制节点/边规模，要求跨学科覆盖。
  - 若校验失败，`stronger_prompt_for_regen()` 触发第二轮生成以提高质量；必要时使用 `force_json_repair_prompt()` 修复 JSON。
- 质量控制：
  - 阈值设置：最小学科数、最小有效边数、关系长度范围、跨学科边比例、通用关系占比上限等，防止幻觉和过度概括。
  - `content_check()` 过滤无效或过长关系，`prune_isolated_nodes()` 移除孤立节点，`compute_node_values_scaled()` 放大节点权重以优化力导布局。
- 缓存与降级：
  - 布隆过滤器避免重复 LLM 调用；TinyDB 持久化热点概念；前端离线模式使用本地样例。
- 输出增强：为空 description 自动补文案；将 token 用量回传用于计费/监控。


## 6. 部署与运行
- 配置：在 [config.py](config.py) 填入有效的 `BASE_URL`、`API_KEY`、`MODEL_ID`（建议改为读取环境变量并避免提交密钥）。
- 本地运行：先安装依赖再启动，默认监听 8000。

  - Windows（PowerShell/CMD）
    ```powershell
    cd "C:\Users\13903\Desktop\云计算系统\大作业\版本4\InterKnow_Graph_Agent-main"
    python -m pip install -r requirements.txt
    python -u .\main.py
    ```

  - Git Bash（POSIX 路径）
    ```bash
    cd "/c/Users/13903/Desktop/云计算系统/大作业/版本4/InterKnow_Graph_Agent-main"
    python -m pip install -r requirements.txt
    python -u main.py
    ```
  - 核对 `python` 与 `pip` 一致：
    ```bash
    python -c "import sys; print(sys.executable)"
    python -m pip --version
    ```
- 容器运行：`docker build -t interknow_graph_agent .`，`docker run -p 8000:8000 interknow_graph_agent`，访问 `http://127.0.0.1:8000/graph.html`。


## 7. 路由速览
- 页面：
  - `/index.html` 首页
  - `/graph.html` 图谱可视化
  - `/find.html` 知识查询
- API：
  - `POST /api/graph` 生成概念图谱
  - `POST /api/chat` 聊天与用量返回
  - `POST /api/counts_and_tokens` 累计调用与 tokens
- 资源下载：
  - `GET /download/source` 打包并下载 `frontend/static/downloads` 目录为 `downloads.zip`（下载完成后服务端自动清理临时 zip；若目录不存在返回 404）。

前端样式与资源均通过 `/frontend/static/...` 挂载，模板中引用样式请使用 `frontend/static/css/navigater.css`。

## 8. 演示与测试


## 8. 演示与测试
演示见演示视频，包含架构讲解（数据流、云原生组件、Agent 工具链），示例查询和离线回退过程。

测试：
  - 运行 [test/healthcheck.py](test/healthcheck.py) 验证 LLM 与 API 可用性。
  - 运行 [test/dump_graph.py](test/dump_graph.py) 生成示例图谱，检查 JSON 结构。
  
通过 /api/counts_and_tokens 展示累计 tokens 与调用次数，可在前端计数面板显示。

## 9. 常见问题（Windows）
- `pip install -r requirements.txt` 报路径错误：请使用引号包裹完整路径或在项目目录下执行相对路径安装。
  - PowerShell/CMD：
    ```powershell
    python -m pip install -r "C:\Users\13903\Desktop\云计算系统\大作业\版本4\InterKnow_Graph_Agent-main\requirements.txt"
    ```
  - Git Bash：
    ```bash
    python -m pip install -r "/c/Users/13903/Desktop/云计算系统/大作业/版本4/InterKnow_Graph_Agent-main/requirements.txt"
    ```

- 指定版本不兼容（Python 3.9）：个别依赖在 3.10+ 才提供固定版本（如 `click==8.3.1`、`dnspython==2.8.0`）。
  - 方案 A（推荐）：使用 Python 3.10+。
  - 方案 B：保持 3.9 时，将这两项放宽到兼容版本，例如 `click==8.1.8`、`dnspython==2.7.0` 后再安装。

- 运行报 `ModuleNotFoundError: No module named 'tinydb'`：依赖未安装成功，请先完成安装再运行。