# 本地开发与配置完整流程（开发人员版）

> 适用于 Windows / macOS / Linux 本地开发环境。

## 1. 前置软件与依赖

### 必需
- Git
- Node.js 18+
- Python 3.11+
- Docker & Docker Compose

### 可选（启用OCR时必需）
- Tesseract OCR
  - Windows: 安装 Tesseract 并记录安装路径
  - macOS: `brew install tesseract`
  - Linux: `apt-get install tesseract-ocr`

## 2. 克隆项目并进入目录

```bash
git clone <repository-url>
cd ppt-learning-assistant
```

## 3. 环境变量配置

复制模板并填写：

```bash
cp .env.example .env
```

重点配置项：
- `DEEPSEEK_API_KEY`（必填）
- `DEEPSEEK_API_BASE`（建议保持 https://api.deepseek.com）
- `DEEPSEEK_MODEL`（可选 deepseek-chat / deepseek-reasoner）
- `OCR_ENABLED`（如需OCR置为 true）
- `TESSERACT_CMD`（Windows下指定 tesseract.exe 路径）
- 外部检索API Key（可选）

## 4. 后端本地运行（非Docker）

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# 启动FastAPI
uvicorn app.main:app --reload --port 8000
```

验证：
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 5. 前端本地运行（非Docker）

```bash
cd frontend
npm install
npm run dev
```

访问：
- 前端: http://localhost:8080

## 6. Docker 一键启动（推荐）

```bash
docker-compose up -d
```

访问：
- 前端: http://localhost:8080
- 后端: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 7. 常见问题排查

### 7.1 DeepSeek 认证失败
- 检查 `.env` 中 `DEEPSEEK_API_KEY`
- 确认网络可访问 `https://api.deepseek.com`

### 7.2 OCR 无效
- Windows: 设置 `TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe`
- 确保 `OCR_ENABLED=true`

### 7.3 外部搜索无结果
- 多数API是可选的，未配置Key可能无法返回
- Bing/Google CSE 需配置对应 Key 与 Engine ID

## 8. 推荐开发流程

1) 上传PPT并解析，确认结构化输出正常
2) 检查向量检索是否能定位知识点
3) 使用“外部搜索”页面验证多维检索
4) 生成题目（启用严格上下文），确保不脱离PPT
5) 提交答案，观察判卷增强信息与错因分类
6) 在错题本生成小灶纠偏

## 9. 目录说明

- frontend/: 前端 Vue 应用
- backend/: FastAPI 后端
- docs/: 文档
- docker-compose.yml: 容器编排
