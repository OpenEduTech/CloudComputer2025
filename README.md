# PPT 内容扩展智能体（命题一）

本项目实现了一个 **PPT 内容扩展智能体**，能够自动解析 PowerPoint（`.pptx`）文件，理解幻灯片结构，并基于 **智谱 AI 的 glm-4-flash 模型** 为每一页生成教学级扩展说明内容。

系统引入 **独立事实校验层（Check Layer）**，用于降低大模型幻觉风险，并支持 **本地运行、Web API 服务以及 Docker 容器化部署**，符合云原生应用设计理念。

---

## 一、功能说明

* 📑 **语义解析**：解析 `.pptx` 文件，提取每页文本并保持层级结构
* 🧠 **知识扩展**：调用 glm-4-flash 自动补充背景知识、原理解释、案例说明
* ✅ **事实校验**：扩展内容需通过独立校验层，未通过会给出原因
* 📦 **结构化输出**：生成 Markdown 报告 + JSON 结构化数据
* 🌐 **服务化部署**：提供 FastAPI Web 接口，支持 Docker 运行

---

## 二、本地运行

### 1️⃣ Python 与环境准备

* Python 版本要求：**3.8 ~ 3.12**
* 推荐使用 **项目内虚拟环境（`.venv`）**，避免与 Conda `(base)` 冲突

#### 创建虚拟环境（只需一次）

```bash
python -m venv .venv
```

#### 激活虚拟环境（⚠️ 根据终端类型选择）

**Windows（CMD / VS Code 默认终端）**

```bat
.venv\Scripts\activate
```

**Windows（PowerShell）**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

> 成功后，终端前缀应出现：
> `(.venv)`
> 如果看到 `(base) (.venv)`，说明你是在 Conda 基础环境之上又激活了 venv，这是**允许的，不影响运行**。

---

### 2️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

> 若出现 `ModuleNotFoundError: sniffio`，可手动执行：

```bash
pip install sniffio
```

---

### 3️⃣ 设置 API Key（⚠️ 不要写进代码）

通过环境变量注入智谱 AI API Key。

**Windows PowerShell**

```powershell
$env:ZHIPU_API_KEY="YOUR_API_KEY"
```

**Windows CMD**

```bat
set ZHIPU_API_KEY=YOUR_API_KEY
```

**Linux / macOS**

```bash
export ZHIPU_API_KEY="YOUR_API_KEY"
```

---

### 4️⃣ 运行本地演示

```bash
python demo.py sample.pptx
```

指定输出目录（可选）：

```bash
python demo.py sample.pptx --output output
```

输出结果包括：

* `output/report.md`：人类可读的扩展报告
* `output/result.json`：结构化 JSON 结果（含校验状态）

---

## 三、启动 Web 服务（FastAPI）

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

浏览器访问：

```
http://localhost:8000/docs
```

可查看并测试交互式 API 文档。

---

## 四、Docker 容器化部署

### 1️⃣ 构建镜像

```bash
docker build -t ppt-expander .
```

### 2️⃣ 运行容器

```bash
docker run -d \
  --name ppt-agent \
  -p 8000:8000 \
  -e ZHIPU_API_KEY="YOUR_API_KEY" \
  ppt-expander
```

### 3️⃣ 验证服务

```bash
curl http://localhost:8000/
```

应返回 JSON 欢迎信息。

---

## 五、API 接口说明

### POST `/expand`

上传 `.pptx` 文件，返回扩展结果。

**请求示例：**

```bash
curl -X POST http://localhost:8000/expand \
  -F "file=@presentation.pptx" \
  -o output.json
```

**响应字段：**

* `original`：原始幻灯片文本
* `expanded`：扩展生成内容
* `is_verified`：是否通过事实校验
* `verification_reason`：未通过时的原因说明

---

## 六、项目结构

```
.
├── config.py               # 配置管理（从环境变量读取 API Key）
├── zhipu_client.py         # 智谱 AI API 封装
├── input_handler.py        # PPT 解析模块
├── agent_core.py           # 智能体核心：扩展 + 校验
├── output_formatter.py     # 输出格式化（JSON / Markdown）
├── app.py                  # FastAPI Web 服务
├── demo.py                 # 本地命令行演示脚本
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 构建文件
├── output/                 # 输出结果目录
└── README.md               # 项目说明
```

---

## 七、设计说明（给老师看的重点）

* 系统采用 **云原生、无状态设计**
* 核心推理通过 **云端 LLM API（glm-4-flash）**
* 本地服务仅负责：

  * 文档解析
  * 请求编排
  * 校验控制
  * 结果格式化
* 支持水平扩展，适合部署在云环境中

---

## 八、注意事项

1. 仅支持 `.pptx` 文件，不支持旧版 `.ppt`
2. API Key **必须通过环境变量传入**
3. 所有生成内容均经过校验层处理
4. Docker 镜像内已包含完整运行环境

---