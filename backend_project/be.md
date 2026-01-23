# AI 刷题助手 - 后端 API 接口文档

[cite_start]本项目基于 **FastAPI** 框架开发，集成了 **OpenAI GPT-3.5** 进行题目生成与智能判卷，并使用 **Redis** 进行错题持久化存储 [cite: 2]。

---

## 1. 基础信息
* [cite_start]**API 根路径**: `http://localhost:8000` [cite: 2]
* [cite_start]**容器化支持**: 服务通过 Docker 部署，后端映射端口为 `8000` [cite: 2, 3]。
* **数据格式**: 除文件上传接口外，所有请求和响应均使用 `application/json`。

---

## 2. 核心 API 接口说明

### 2.1 健康检查
* **URL**: `/`
* **方法**: `GET`
* **说明**: 用于确认后端服务和 Redis 是否正常运行。

### 2.2 文件上传与文本解析
* **URL**: `/api/upload_file`
* **方法**: `POST`
* **数据类型**: `multipart/form-data`
* **参数**: `file` (支持 `.pdf`, `.txt`, `.md`)
* **功能**: 
    * [cite_start]针对 PDF 使用 `PyMuPDF` 进行解析 [cite: 1]。
    * [cite_start]针对 TXT/MD 文件支持 UTF-8 和 GBK 编码兼容 [cite: 1]。
* **响应**: 返回解析后的纯文本字符串。

### 2.3 题目生成 (单题)
* **URL**: `/api/generate_one`
* **方法**: `POST`
* **请求体**:
    ```json
    {
      "text": "用于出题的参考文本",
      "type": "mcq" // 或 "short"
    }
    ```
* **功能**: 
    * [cite_start]`mcq`: 生成含四个选项的单选题 [cite: 1]。
    * [cite_start]`short`: 生成需要关键词匹配的简答题 [cite: 1]。
* [cite_start]**逻辑**: 后端会自动截取文本前 1500 字以适配 Token 限制，并强制 AI 输出标准 JSON 格式 [cite: 1]。

### 2.4 简答题智能判卷
* **URL**: `/api/grade_short`
* **方法**: `POST`
* **请求体**:
    ```json
    {
      "question_data": { "question": "...", "reference_answer": "..." },
      "user_answer": "用户回答的内容"
    }
    ```
* [cite_start]**功能**: AI 根据标准答案给用户打分 (0-100) 并给出评语 [cite: 1]。
* **自动错题本**: 如果评分 **低于 60 分**，该题会自动存入 Redis 错题库。

### 2.5 选择题错题保存与纠偏
* **URL**: `/api/save_mistake`
* **方法**: `POST`
* [cite_start]**功能**: 当用户选错时，AI 会针对“正确答案”和“用户错选”进行个性化分析（50字以内），并存入 Redis [cite: 1]。

### 2.6 错题本管理
* **获取所有错题**: `GET /api/mistakes`
* **清空错题本**: `POST /api/clear_mistakes`

---

## 3. 数据结构定义 (Model)

### 题目对象 (Question Object)
| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `type` | string | `mcq` (选择) 或 `short` (简答) |
| `question` | string | 题干内容 |
| `options` | array | [cite_start]仅选择题有效，包含 A-D 四个选项 [cite: 1] |
| `reference_answer` | string | 正确答案文本 |
| `analysis` | string | 题目解析 |

---

## 4. 异常处理机制
* [cite_start]**JSON 解析保护**: 如果 AI 返回格式不标准，后端具备“暴力提取”逻辑，尝试定位 `{}` 边界 [cite: 1]。
* [cite_start]**服务兜底**: 若 AI 接口调用失败，接口会返回预设的“重试”提示对象，防止前端逻辑崩溃 [cite: 1]。