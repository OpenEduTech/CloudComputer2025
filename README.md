# CloudComputer2025 课程仓库说明

本分支用于提交云计算课程期末大作业，包含各组项目与统一说明。

## 快速链接
- 项目入口目录：`group-029/`
- 环境配置指南：`group-029/docs/ENVIRONMENT.markdown`
- 技术文档：`group-029/docs/TECH_DOC.markdown`
- 演示视频：`group-029/docs/视频演示.mp4`

## 仓库结构概览
```
.
├── .github/
│   └── workflows/...
├── group-029/
│   ├── app/
│   ├── docs/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
└── README.md
```

## group-029 子目录说明

### 核心目录
- `app/`：后端与前端静态页面
  - `app/main.py`：API 入口与路由
  - `app/models.py`：数据模型
  - `app/services/`：出题/判卷/检索/错题本/对话等核心服务
  - `app/core/`：配置读取与全局设置
  - `app/static/`：前端页面（主页与错题本）
- `docs/`：文档与演示材料
  - `docs/ENVIRONMENT.markdown`：环境配置指南
  - `docs/TECH_DOC.markdown`：技术文档
  - `docs/视频演示.mp4`：演示录屏

### 工程文件
- `Dockerfile`：API 镜像构建
- `docker-compose.yml`：API + Redis 编排
- `requirements.txt`：Python 依赖
- `.env.example`：环境变量模板
- `.gitignore`：Git 忽略配置

## 推荐阅读
- 运行与配置：`group-029/docs/ENVIRONMENT.markdown`
- 项目说明与测试流程：`group-029/README.md`
