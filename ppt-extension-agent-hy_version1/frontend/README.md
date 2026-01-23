# PPT内容扩展智能体 - 前端项目

基于React + TypeScript + Tailwind CSS构建的PPT内容扩展智能体前端界面。

## 技术栈

- **React 18**: 用户界面框架
- **TypeScript**: 类型安全
- **Vite**: 快速构建工具
- **Tailwind CSS**: 样式框架
- **Axios**: HTTP客户端
- **Lucide React**: 图标库

## 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

前端将在 http://localhost:3000 启动。

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 项目结构

```
src/
├── components/
│   ├── UploadArea/          # 文件上传组件
│   ├── PPTViewer/          # PPT预览组件
│   ├── ExpansionPanel/      # 扩展内容面板
│   └── ProgressBar/        # 进度条组件
├── App.tsx                # 主应用组件
├── main.tsx               # 应用入口
└── index.css              # 全局样式
```

## 功能特性

### 1. 文件上传
- 支持拖拽上传PPT文件
- 支持通过URL上传PPT
- 支持.pptx和.ppt格式

### 2. PPT预览
- 可交互的PPT预览界面
- 支持翻页浏览
- 文本框选择功能（单选/多选/全选）

### 3. 内容扩展
- 单选扩展：扩展选中的文本框
- 批量扩展：扩展多个选中的文本框
- 整页扩展：扩展整页所有内容

### 4. 扩展内容展示
- 5个Tab展示不同维度的扩展内容：
  - 📖 背景说明
  - 🔬 原理阐述
  - 📐 公式推导
  - 💻 代码示例
  - ✓ 要点总结
- 延伸阅读链接

### 5. 实时进度反馈
- 进度条显示处理进度
- 状态提示信息

## API集成

前端通过以下API与后端通信：

- `POST /api/v1/upload` - 上传PPT文件
- `POST /api/v1/process-url` - 处理PPT URL
- `POST /api/v1/expand` - 扩展知识点
- `GET /api/v1/task/{task_id}` - 查询任务状态

所有API请求都会通过Vite代理转发到后端服务（http://localhost:8000）。

## 开发说明

### 添加新组件

1. 在`src/components/`下创建新组件目录
2. 创建组件文件（如`ComponentName.tsx`）
3. 在`App.tsx`中导入并使用组件

### 修改样式

- 使用Tailwind CSS类名
- 在`index.css`中添加全局样式
- 在`tailwind.config.js`中自定义主题

### 类型定义

所有类型定义都在组件文件中，使用TypeScript接口定义。

## 注意事项

- 确保后端服务已启动（http://localhost:8000）
- 前端默认运行在3000端口
- 如需修改端口，编辑`vite.config.ts`
