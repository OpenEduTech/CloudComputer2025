# SmartLecPPTKiller 提交版 API 文档

2026-01

---

## 1. 基础信息

### 1.1 服务地址

- 后端容器内部监听：`http://localhost:8000`
- 使用 `docker-compose.yml` 启动时，宿主机映射为：`http://localhost:8002`（`8002:8000`）

### 1.2 OpenAPI 文档

- Swagger UI：`GET /docs`
- ReDoc：`GET /redoc`

### 1.3 通用约定

- API 前缀：`/api`
- 认证：当前实现未包含鉴权（无 JWT/Session）。
- 数据格式：
  - 上传接口使用 `multipart/form-data`
  - 其余大部分接口使用 `application/json` 或 query 参数
- 用户隔离：多数与“历史/错题”相关接口均支持 query/body 的 `user_id`，默认值为 `default`。

---

## 2. 健康检查与根路由

### 2.1 健康检查

- `GET /health`

响应示例：
```json
{
  "status": "healthy",
  "app_name": "PPT学习助手",
  "version": "1.0.0"
}
```

### 2.2 根路由

- `GET /`

响应示例：
```json
{
  "message": "欢迎使用PPT学习助手API",
  "docs": "/docs",
  "health": "/health"
}
```

---

## 3. PPT 管理（/api/ppt）

### 3.1 上传 PPT/PDF

- `POST /api/ppt/upload`

请求：
- Content-Type：`multipart/form-data`
- 表单字段：
  - `file`：文件（必填）
- Query 参数：
  - `user_id`：用户标识（可选，默认 `default`）

响应模型：`PPTUploadResponse`

响应字段：
- `file_id`：服务端生成的 UUID
- `filename`：原始文件名
- `file_size`：字节数
- `upload_time`：时间戳
- `message`：提示信息

### 3.2 解析文件

- `GET /api/ppt/parse/{file_id}`

Path 参数：
- `file_id`：上传时返回的文件 ID

Query 参数：
- `user_id`：用户标识（可选，默认 `default`），用于记录解析历史

响应模型：`PPTParseResponse`

响应字段（核心）：
- `file_id`
- `total_slides`
- `slides[]`：`PPTSlide` 列表，字段包含：
  - `slide_number`
  - `title` / `subtitle`
  - `content[]`：聚合文本与图片描述
  - `body[]`：正文层级内容
  - `images[]`：图片占位 ID
  - `image_descriptions[]`：图片描述（可能来自 OCR 文本的语义概括）
  - `ocr_texts[]`：OCR 提取文本（如启用 OCR）
  - `notes`：备注
- `metadata`：解析元数据（动态字典），当前实现中可能包含：
  - `core_properties`（PPT 文档属性）
  - `outline[]`（结构化目录，便于前端展示）
  - `outline_summary[]`（目录概括，若启用）
  - `indexed/indexing`（索引状态标记）
  - `llm_validation`（目录概括校验报告，若启用）

说明：
- 解析后会提交“向量索引”后台任务（FastAPI BackgroundTasks），用于后续语义检索/出题的上下文定位。
- 同时会将解析历史写入 Redis 列表 `history:ppt:{user_id}`。

### 3.3 获取解析历史

- `GET /api/ppt/history`

Query 参数：
- `limit`：返回条数（默认 20）
- `user_id`：用户标识（默认 `default`）

响应：
```json
{
  "success": true,
  "items": [
    {
      "file_id": "...",
      "filename": "...",
      "total_slides": 10,
      "outline": [],
      "parsed_at": "2026-01-19T...",
      "user_id": "default"
    }
  ]
}
```

### 3.4 删除文件

- `DELETE /api/ppt/{file_id}`

响应模型：`StandardResponse`

---

## 4. 知识扩充（/api/knowledge）

### 4.1 扩充知识点（RAG：先检索再扩写）

- `POST /api/knowledge/expand`

请求模型：`KnowledgeExpansionRequest`

请求字段：
- `file_id`：文件 ID（必填）
- `slide_number`：页码（可选；当前接口会使用向量检索作为主要上下文来源）
- `query`：知识点（必填）
- `max_length`：最大字数（默认 500）
- `include_external`：是否检索外部资源（默认 true）
- `user_id`：用户标识（默认 `default`，用于记录历史）

响应模型：`KnowledgeExpansion`

响应字段：
- `query`
- `expansion`
- `formulas[]`
- `code_examples[]`
- `external_resources[]`：`ExternalResource` 列表
- `related_topics[]`
- `llm_validation`：校验报告（可选）

说明：
- 服务会先在 ChromaDB 中对 `query` 做相似检索（`top_k=3`）作为上下文，再调用 LLM 生成结构化结果。
- 扩充历史会写入 Redis 列表 `history:knowledge:{user_id}`（保存 expansion 的前 300 字摘要）。

### 4.2 语义搜索 PPT 内容

- `POST /api/knowledge/search`

Query 参数：
- `file_id`：文件 ID（必填）
- `query`：查询文本（必填）
- `top_k`：返回数量（默认 5）

响应：
```json
{
  "success": true,
  "query": "...",
  "results": [
    {
      "content": "...",
      "metadata": {},
      "relevance": 0.73
    }
  ]
}
```

### 4.3 外部权威资源检索

- `GET /api/knowledge/external-search`

Query 参数：
- `query`：查询词（必填）

响应：
```json
{
  "success": true,
  "query": "...",
  "resources": [
    {
      "source": "Wikipedia",
      "title": "...",
      "url": "...",
      "summary": "..."
    }
  ]
}
```

### 4.4 获取知识扩充历史

- `GET /api/knowledge/history`

Query 参数：
- `limit`：返回条数（默认 20）
- `user_id`：用户标识（默认 `default`）

响应：
```json
{
  "success": true,
  "items": [
    {
      "file_id": "...",
      "query": "...",
      "expansion": "...",
      "created_at": "2026-01-19T...",
      "user_id": "default"
    }
  ]
}
```

---

## 5. 题目管理（/api/questions）

### 5.1 生成题目

- `POST /api/questions/generate`

请求模型：`GenerateQuestionsRequest`

请求字段：
- `file_id`（必填）
- `num_questions`：题目数量（默认 5，范围 1~20）
- `question_types[]`：题型列表（默认 `["choice"]`）
- `difficulty_levels[]`：难度列表（默认 `["medium"]`）
- `slide_numbers[]`：指定页码（可选；当检索无结果时用于回退筛页）
- `focus_query`：知识点定位查询（可选；会优先走向量检索定位上下文）
- `top_k`：向量检索数量（默认 3，范围 1~10）
- `strict_context`：是否严格基于上下文出题（默认 true）

响应模型：`GenerateQuestionsResponse`

响应字段：
- `file_id`
- `questions[]`：`Question` 列表（每题包含 `question_id/question_type/difficulty/content/options/correct_answer/explanation/tags` 等）
- `llm_validation`：题目生成校验报告（可选）

说明：
- 生成的题目会写入 Redis，键为 `question:{question_id}`，过期时间为 24 小时。

### 5.2 评估答案

- `POST /api/questions/evaluate`

请求模型：`SubmitAnswerRequest`

请求字段：
- `question_id`：题目 ID（必填；需存在于 Redis 且未过期）
- `user_answer`：用户答案（必填）
- `user_id`：用户标识（默认 `default`；用于错题本归属）

响应模型：`AnswerEvaluation`

响应字段（核心）：
- `question_id`
- `is_correct`
- `score`（0~100）
- `detailed_feedback`
- `improvement_suggestions[]`
- `semantic_similarity`（可选）
- `error_type`（可选）
- `alignment_score/alignment_summary`（可选）
- `llm_validation`（可选）

说明：
- 若判定为错误答案，会将错题记录写入 Redis（集合 `mistakes:{user_id}` + 详情 `mistake:{user_id}:{question_id}`，并兼容旧键 `mistake:{question_id}`）。

---

## 6. 错题本（/api/mistakes）

### 6.1 获取错题列表

- `GET /api/mistakes/list`

Query 参数：
- `limit`：返回条数（默认 20）
- `user_id`：用户标识（默认 `default`）

响应：
```json
{
  "success": true,
  "mistakes": [
    {
      "question_id": "...",
      "user_id": "default",
      "question": {},
      "evaluation": {},
      "timestamp": "2026-01-19T..."
    }
  ],
  "total": 1
}
```

说明：
- 若用户维度的错题集合为空，会回退读取兼容集合 `mistakes:all`。

### 6.2 获取错题统计

- `GET /api/mistakes/stats`

Query 参数：
- `user_id`：用户标识（默认 `default`）

响应模型：`MistakeStats`

说明：
- 当前实现中 `by_difficulty/by_type/improvement_rate` 为占位统计；`weak_topics` 主要由错误类型去重得到。

### 6.3 从错题本移除

- `DELETE /api/mistakes/{question_id}`

Query 参数：
- `user_id`：用户标识（默认 `default`）

响应：
```json
{ "success": true, "message": "已从错题本中移除" }
```

### 6.4 标记为已复习

- `POST /api/mistakes/{question_id}/review`

Query 参数：
- `user_id`：用户标识（默认 `default`）

响应：
```json
{
  "success": true,
  "message": "已标记为复习",
  "review_count": 1
}
```

### 6.5 生成小灶纠偏

- `POST /api/mistakes/remediate`

请求模型：`RemediationRequest`

请求字段：
- `question_id`（必填）
- `user_id`（默认 `default`）
- `user_profile`（可选；兼容旧字段，当前前端不再传）
- `focus_topic`（可选；兼容旧字段）

响应模型：`RemediationResponse`

响应字段：
- `explain`
- `contrast`
- `practice`（对象：包含 `question/answer/explanation`）
- `transfer`（对象：包含 `question/answer/explanation`）
- `tips[]`
- `markdown`（可选；后端会生成 Markdown 版本便于展示/下载）

---

## 7. 错误响应与状态码

### 7.1 FastAPI HTTPException

业务校验失败时，接口会抛出 `HTTPException(status_code=400/404/500, detail=...)`，客户端可直接读取 `detail`。

### 7.2 全局异常处理（500）

当出现未捕获异常时，后端会返回：
```json
{
  "success": false,
  "message": "服务器内部错误",
  "detail": "..."
}
```

注意：`detail` 字段仅在后端配置 `DEBUG=true` 时返回（见配置）。
