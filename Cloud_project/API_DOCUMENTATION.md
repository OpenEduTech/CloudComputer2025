# API文档

## 概述

本文档描述了智能学习闭环系统的API接口，包括前端组件、后端服务、数据库访问等。

## 基础信息

### 基础URL

- **开发环境**: `http://localhost:8501`
- **生产环境**: `https://your-domain.com`

### 认证方式

当前版本使用会话认证，无需额外的认证头。

### 响应格式

所有API返回JSON格式：

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2026-01-18T10:00:00Z"
}
```

## 前端组件API

### 1. 仪表盘组件

#### 获取学习统计

**端点**: `GET /api/dashboard/stats`

**描述**: 获取用户学习统计数据

**请求参数**:
```json
{
  "user_id": "string",
  "time_range": "week|month|year"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_exams": 10,
    "total_questions": 100,
    "average_score": 85.5,
    "mistake_count": 15,
    "study_time": 1200
  }
}
```

#### 获取学习进度

**端点**: `GET /api/dashboard/progress`

**描述**: 获取用户学习进度

**请求参数**:
```json
{
  "user_id": "string"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "completed_lessons": 5,
    "total_lessons": 20,
    "progress_percentage": 25,
    "next_lesson": {
      "id": 6,
      "title": "第六课：高级应用",
      "difficulty": "medium"
    }
  }
}
```

### 2. 考试组件

#### 生成试卷

**端点**: `POST /api/exam/generate`

**描述**: 生成新的试卷

**请求参数**:
```json
{
  "user_id": "string",
  "difficulty": "easy|medium|hard",
  "question_count": 10,
  "topics": ["topic1", "topic2"]
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "exam_id": "exam_123",
    "questions": [
      {
        "id": 1,
        "type": "choice",
        "question": "问题内容",
        "options": ["A", "B", "C", "D"],
        "difficulty": "easy",
        "points": 10
      }
    ],
    "duration": 3600
  }
}
```

#### 提交答案

**端点**: `POST /api/exam/submit`

**描述**: 提交考试答案

**请求参数**:
```json
{
  "exam_id": "string",
  "user_id": "string",
  "answers": {
    "1": "A",
    "2": "B"
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "score": 85,
    "max_score": 100,
    "percentage": 85,
    "passed": true,
    "results": [
      {
        "question_id": 1,
        "user_answer": "A",
        "correct_answer": "A",
        "score": 10,
        "feedback": "回答正确"
      }
    ]
  }
}
```

#### 保存草稿

**端点**: `POST /api/exam/save_draft`

**描述**: 保存考试答案草稿

**请求参数**:
```json
{
  "exam_id": "string",
  "user_id": "string",
  "answers": {
    "1": "A",
    "2": "B"
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "草稿保存成功"
}
```

### 3. 错题本组件

#### 获取错题列表

**端点**: `GET /api/mistakes/list`

**描述**: 获取用户错题列表

**请求参数**:
```json
{
  "user_id": "string",
  "page": 1,
  "page_size": 20,
  "difficulty": "easy|medium|hard|all"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total": 15,
    "page": 1,
    "page_size": 20,
    "mistakes": [
      {
        "id": 1,
        "question": "问题内容",
        "user_answer": "A",
        "correct_answer": "B",
        "difficulty": "medium",
        "created_at": "2026-01-18T10:00:00Z"
      }
    ]
  }
}
```

#### 添加错题

**端点**: `POST /api/mistakes/add`

**描述**: 添加错题到错题本

**请求参数**:
```json
{
  "user_id": "string",
  "question": {
    "id": 1,
    "question": "问题内容",
    "user_answer": "A",
    "correct_answer": "B",
    "difficulty": "medium"
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "错题添加成功"
}
```

#### 删除错题

**端点**: `DELETE /api/mistakes/delete`

**描述**: 从错题本删除错题

**请求参数**:
```json
{
  "user_id": "string",
  "mistake_id": 1
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "错题删除成功"
}
```

### 4. 资料上传组件

#### 上传文件

**端点**: `POST /api/upload/file`

**描述**: 上传学习资料

**请求参数**:
```json
{
  "user_id": "string",
  "file": "binary",
  "file_type": "pdf|audio|video|image",
  "title": "文件标题",
  "description": "文件描述"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "file_id": "file_123",
    "file_url": "/uploads/file_123.pdf",
    "file_size": 1024000,
    "upload_time": "2026-01-18T10:00:00Z"
  }
}
```

#### 获取文件列表

**端点**: `GET /api/upload/files`

**描述**: 获取用户上传的文件列表

**请求参数**:
```json
{
  "user_id": "string",
  "page": 1,
  "page_size": 20
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total": 10,
    "files": [
      {
        "id": "file_123",
        "title": "学习资料1",
        "file_type": "pdf",
        "file_size": 1024000,
        "upload_time": "2026-01-18T10:00:00Z"
      }
    ]
  }
}
```

## 后端服务API

### 1. 数据库服务

#### 连接数据库

**类**: `DBManager`

**方法**: `__init__()`

**描述**: 初始化数据库连接

**示例**:
```python
from backend.database_service import DBManager

db = DBManager()
```

#### 保存考试记录

**方法**: `save_exam_record(exam, answers, score, results)`

**描述**: 保存考试记录到数据库

**参数**:
- `exam`: 试卷对象
- `answers`: 用户答案字典
- `score`: 总分
- `results`: 评分结果列表

**返回值**: `bool`

**示例**:
```python
success = db.save_exam_record(exam, answers, score, results)
```

#### 获取考试记录

**方法**: `get_exam_records(user_id, limit=10)`

**描述**: 获取用户的考试记录

**参数**:
- `user_id`: 用户ID
- `limit`: 返回记录数量限制

**返回值**: `List[Dict]`

**示例**:
```python
records = db.get_exam_records(user_id, limit=10)
```

#### 添加错题

**方法**: `add_mistake(question, user_answer, result)`

**描述**: 添加错题到错题本

**参数**:
- `question`: 问题对象
- `user_answer`: 用户答案
- `result`: 评分结果

**返回值**: `bool`

**示例**:
```python
success = db.add_mistake(question, user_answer, result)
```

#### 获取错题列表

**方法**: `get_mistakes(user_id, difficulty=None)`

**描述**: 获取用户的错题列表

**参数**:
- `user_id`: 用户ID
- `difficulty`: 难度过滤（可选）

**返回值**: `List[Dict]`

**示例**:
```python
mistakes = db.get_mistakes(user_id, difficulty="medium")
```

### 2. RAG服务

#### 初始化RAG服务

**类**: `RAGService`

**方法**: `__init__()`

**描述**: 初始化RAG服务

**示例**:
```python
from backend.rag_service import RAGService

rag = RAGService()
```

#### 检索相关内容

**方法**: `retrieve_relevant_content(query, top_k=5)`

**描述**: 根据查询检索相关内容

**参数**:
- `query`: 查询文本
- `top_k`: 返回结果数量

**返回值**: `List[str]`

**示例**:
```python
content = rag.retrieve_relevant_content("核心考点", top_k=5)
```

#### 添加文档

**方法**: `add_document(text, metadata=None)`

**描述**: 添加文档到知识库

**参数**:
- `text`: 文档文本
- `metadata`: 文档元数据（可选）

**返回值**: `str` (文档ID)

**示例**:
```python
doc_id = rag.add_document("文档内容", {"title": "文档标题"})
```

### 3. 智能体服务

#### 试卷生成器

**类**: `QuizGenerator`

**方法**: `generate_comprehensive_exam(context)`

**描述**: 生成综合试卷

**参数**:
- `context`: 上下文内容

**返回值**: `List[Dict]`

**示例**:
```python
from backend.agents.quiz_generator import QuizGenerator

generator = QuizGenerator()
exam = generator.generate_comprehensive_exam(context)
```

#### 试卷评分器

**类**: `QuizGrader`

**方法**: `grade_submission(question_type, question, correct_answer, user_answer, context)`

**描述**: 评分用户提交的答案

**参数**:
- `question_type`: 题目类型
- `question`: 问题内容
- `correct_answer`: 正确答案
- `user_answer`: 用户答案
- `context`: 上下文内容

**返回值**: `Dict`

**示例**:
```python
from backend.agents.quiz_grader import QuizGrader

grader = QuizGrader()
result = grader.grade_submission(
    "choice",
    "问题内容",
    "A",
    "B",
    context
)
```

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  },
  "timestamp": "2026-01-18T10:00:00Z"
}
```

### 常见错误码

| 错误码 | 描述 | HTTP状态码 |
|--------|------|-----------|
| `INVALID_REQUEST` | 请求参数无效 | 400 |
| `UNAUTHORIZED` | 未授权 | 401 |
| `FORBIDDEN` | 禁止访问 | 403 |
| `NOT_FOUND` | 资源不存在 | 404 |
| `INTERNAL_ERROR` | 内部服务器错误 | 500 |
| `DATABASE_ERROR` | 数据库错误 | 500 |
| `AI_SERVICE_ERROR` | AI服务错误 | 500 |
| `FILE_UPLOAD_ERROR` | 文件上传错误 | 400 |
| `VALIDATION_ERROR` | 数据验证错误 | 400 |

### 错误处理示例

```python
try:
    result = db.save_exam_record(exam, answers, score, results)
except DatabaseError as e:
    return {
        "success": False,
        "error": {
            "code": "DATABASE_ERROR",
            "message": str(e)
        }
    }
```

## 速率限制

### 默认限制

- **每分钟请求数**: 100
- **每小时请求数**: 1000
- **每天请求数**: 10000

### 速率限制响应

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "请求过于频繁，请稍后再试",
    "retry_after": 60
  }
}
```

## 版本控制

### API版本

当前版本: `v1.0.0`

### 版本策略

- 主版本号: 重大变更
- 次版本号: 功能新增
- 修订版本号: Bug修复

## 更新日志

### v1.0.0 (2026-01-18)

- 初始版本发布
- 实现基础API接口
- 实现前端组件API
- 实现后端服务API
- 实现错误处理机制
- 实现速率限制

## 相关文档

- [架构文档](ARCHITECTURE.md)
- [部署文档](README.md)
- [故障排除指南](TROUBLESHOOTING.md)
- [前端组件文档](frontend/README.md)