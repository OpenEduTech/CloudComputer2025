# PPTAS 系统快速使用指南

## 简介

PPTAS （PPT Agent System）是一个 AI 驱动的PPT 内容扩展智能体，能够自动识别 PPT 的章节层级与核心论点，构建思维导图，实现多维权威资源延伸和智能笔记生成等多种功能。

项目聚焦学生考前复习与课后自学阶段的核心痛点，通过技术手段优化学习资源的适配性与可用性，解决了学生依托 PPT 课件学习复习时面临的三大困境：
- 第一，融合云原生架构与大模型智能体技术，改变静态 PPT 课件为针对性动态自学辅助系统；
- 第二，基于向量数据库语义检索与思维导图，辅助学生组合碎片化的PPT内容构建完整知识框架；
- 第三，通过多维资源扩展搜索，依托前沿技术和权威资源对学生的知识进行动态更新与扩展。
## 快速开始

### 1. 环境要求

- Python 3.9+
- Node.js 16.0+
- LibreOffice

### 2. 安装配置

#### 后端安装

```bash
cd backend
pip install -r requirements.txt
```

#### 前端安装

```bash
cd frontend
npm install
```

#### 配置 LLM

编辑 `backend/config.json`:

```json
{
  "llm": {
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  }
}
```
系统使用的 LLM 提供商

- OpenAI: `base_url: "https://api.openai.com/v1"`, `model: "gpt-4"`
- SiliconFlow: `base_url: "https://api.siliconflow.cn/v1"`, `model: "deepseek-ai/DeepSeek-V3.2-Exp"`

#### 启动后端

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 启动前端

```bash
cd frontend
npm run dev
```

访问地址: http://localhost:5173

#### 使用 Docker（推荐）

```bash
docker-compose up --build -d

```
```
# 启动容器
docker-compose up --build -d

# 访问应用
# 前端：http://localhost
# 后端 API：http://localhost:8000/docs

# 查看日志
docker-compose logs -f backend

# 停止容器
docker-compose down
```

## 基本使用

### 1. 上传文档

1. 打开前端界面
2. 点击上传区域
3. 选择 PPTX 或 PDF 文件

### 2. 全局分析（可选）

1. 点击"全局分析"按钮
2. 等待分析完成
3. 查看文档主题和知识点框架

### 3. 单页分析

1. 选择要分析的页面
2. 点击"使用 AI 深度分析此页面"
3. 实时查看分析进度
4. 查看分析结果

#### 分析结果说明

- **知识聚类**: 识别难以理解的概念
- **学习笔记**: 结构化的 Markdown 笔记
- **知识缺口**: 需要补充的知识点
- **补充说明**: 为缺口生成的详细说明
- **参考资料**: 从外部知识源检索的资料

### 4. 附加功能

1. 思维导图
2. 语义检索
3. 外部资源扩展
4. AI助教


## 详细内容

- 详细文档:  [USER_GUIDE_DETAILED.md](USER_GUIDE_DETAILED.md)
- 技术文档:  [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md)
- API 文档:  http://localhost:8000/docs
- DEMO视频：[DEMO](DEMO.mp4)


## 任务分工

贡献度均为33.3%，组内均分

#### 高嘉泽@AM-SuSh
- 前端设计与开发优化
- 页面预览交互实现
- 思维导图绘制与显示优化
- 语义检索与向量数据库
- 外部资源搜索

#### 郭一心@SSSSizn 
- LLM流水线架构设计与实现
- 单页分析与全局分析
- 数据库存储与缓存机制
- AI助教功能
- 技术文档编写与维护


#### 李晨语@Licy1228
- PPT内容解析
- 关键词提取与标题优化
- Docker容器化部署
- Bug修复与冲突解决

具体commits记录可查看：https://github.com/AM-SuSh/PPTAS/commits/main/

