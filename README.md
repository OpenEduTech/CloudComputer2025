# 智能学习效果评估系统

基于大模型智能体的学习评估与巩固系统，支持自动出题、智能判卷、错题分析和个性化学习建议。

## 🎯 核心功能

- **📄 PDF 解析**: 自动解析学习材料
- **📝 动态出题**: 根据材料生成选择题和简答题
- **🤖 智能判卷**: AI 评分并提供详细解析
- **📚 错题本**: 自动收集错题并生成学习建议
- **🎓 年级适配**: 根据用户年级调整题目难度
- **🖼️ 图片识别**: 支持手写答案识别

## 分工
童宇凡 负责整体架构设计，智能体设计，后端开发（45%）  
邓皓文 负责API设计，mongodb数据库设计（20%）  
陈鑫 负责前端设计（35%）  
评分方式：按任务量来

## 🏗️ 技术架构

### 前端
- React 18 + TypeScript
- Ant Design UI
- Vite 构建工具
- Axios HTTP 客户端

### 后端
- FastAPI (Python)
- LangChain (LLM 编排)
- Motor (异步 MongoDB 驱动)
- Pydantic (数据验证)

### 数据库
- MongoDB (主数据库)

### AI 服务
- DeepSeek API (题目生成、判题、建议)
- 智谱AI API (PDF 解析、图片识别)

### 云原生
- Docker 容器化
- Docker Compose 编排
- Nginx 反向代理

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ 可用内存

### 部署步骤

```bash
# 1. 克隆仓库
git clone <repository-url>

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Keys

# 3. 启动所有服务
docker-compose up -d

# 4. 访问应用
# 前端: http://localhost
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 停止服务

```bash
docker-compose down

# 删除数据卷（清空数据库）
docker-compose down -v
```


## 📖 使用指南

1. **注册账号**: 访问 http://localhost，填写用户名、邮箱、密码和年级
2. **上传材料**: 登录后上传 PDF 文件，系统自动解析内容
3. **生成测验**: 设置测验标题和题目数量，系统根据年级生成适合的题目
4. **答题**: 选择题直接选择选项，简答题可上传手写答案图片或输入文字
5. **查看结果**: 提交后查看评分和解析，系统会指出错误类型和改进建议
6. **错题本**: 查看所有错题、薄弱知识点统计和个性化学习建议

## 🛠️ 本地开发

### 后端开发

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python start.py
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

## 📁 项目结构

```
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   └── services/       # 业务逻辑
│   │       └── agents/     # 智能体实现
│   └── requirements.txt
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── api/           # API 调用
│   │   ├── components/    # React 组件
│   │   ├── pages/         # 页面组件
│   │   └── types/         # TypeScript 类型
│   └── package.json
├── docs/                   # 文档
└── docker-compose.yml      # Docker 编排
```

## 🎨 智能体设计

- **PDF 解析 Agent**: 智谱AI File Parser + PyPDF 降级方案
- **题目生成 Agent**: DeepSeek LLM + 年级适配 + Check Layer 验证
- **判题 Agent**: 智谱AI 图片识别 + DeepSeek 评分 + 自动重试
- **导师 Agent**: 错题分析 + 个性化建议 + 缓存机制

## 🐛 故障排查

```bash
# 查看日志
docker-compose logs backend

# 重启服务
docker-compose restart

# 检查 MongoDB 状态
docker-compose ps mongo
```


## 📝 API 文档

启动服务后访问 http://localhost:8000/docs

---

**注意**: 本项目需要 DeepSeek 和智谱AI 的 API Keys，请在 `.env` 文件中正确配置。

