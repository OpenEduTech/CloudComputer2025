# PPT 内容扩展智能体

## 一、项目简介

本项目面向考前复习场景：针对只有 PPT 标题、缺乏背景与细节的课件，构建一个可以自动扩展知识点的智能体系统。
用户上传 PPT 后，系统会解析 PPT 的层级结构，并基于向量检索与大模型，对每一页内容生成更完整的讲解、推导与延伸阅读建议。

## 二、核心功能

- 解析 PPT 文档的层级结构（目录、主标题、子标题、正文、图片说明等）
- 针对每个页面 / 知识点，自动调用 LLM 补充原理说明、公式推导或代码示例
- 通过向量检索 + 外部权威资源（ Arxiv 等），提供多维延伸阅读
- 以 Web 界面形式对外提供服务

## 三、技术选型概览

详见 `技术文档.md` 或下表（节选）：

- 后端框架：FastAPI
- LLM：DeepSeek 云 API（可按需替换为其他云端模型）
- 向量库：Chroma
- 文档解析：python-pptx
- 外部知识源： Arxiv
- 部署方式：Docker + docker-compose
- 协作与 CI：GitHub + GitHub Actions

## 四、系统架构（概览）

整体架构如下：

- 前端 / 客户端：负责文件上传与扩展内容展示
- 后端 API（FastAPI）：
  - 文档解析模块（PPT Parser）
  - Embedding Service + Chroma 向量库
  - LLM Agent（封装 DeepSeek LLM 调用）
  - External Knowledge Tool（访问 Arxiv）

数据流向简要说明：

1. 用户上传 PPT 或提供链接；
2. 后端解析 PPT，提取每页目录、标题等结构化信息；
3. 对各页面 / 切片生成向量，写入 Chroma 向量库；
4. 用户选择页面或发起“扩展讲解”请求时，后端基于向量检索召回相关内容；
5. LLM Agent 结合检索结果与外部知识源，生成扩展讲解并返回前端展示。

## 五、环境配置指南
### 环境要求
1. 操作系统：Windows 10/11，macOS 10.15+，或 Ubuntu 18.04+

2. Python版本：Python 3.11（推荐）

3. 内存：至少 8GB RAM

4. 磁盘空间：至少 2GB 可用空间

### 克隆仓库
```bash
# 进入你希望存放代码的目录
cd ~/projects

# 执行克隆命令
git clone -b 020 --single-branch https://github.com/OpenEduTech/CloudComputer2025.git

# 克隆完成后会自动创建 CloudComputer2025 目录
cd CloudComputer2025
```

### 嵌入模型说明

- 向量检索使用 Chroma 默认的 ONNX 嵌入模型 `onnx_mini_lm_l6_v2`。
- 首次在本机或容器中运行检索相关接口时，Chroma 会自动从网络下载该模型并缓存到用户目录（本项目的 Docker 配置中缓存路径挂载为 `/root/.cache` 的 `chroma_cache` 卷）。
- 下载大小大约为80MB，通常只在第一次运行时发生；后续再次启动容器或应用会直接复用本地缓存，无需重新下载。
- 因此，运行本项目时需要保证首次启动时能够访问外网以完成模型下载；下载完成后，即使离线也可以继续使用已有的向量库与嵌入模型缓存。

### 本地运行

```bash
# 首先创建虚拟环境
conda create -n ai_ppt python=3.11
conda activate ai_ppt

# 配置api密钥（这里是临时设置，确保密钥安全）
$env:SILICONFLOW_API_KEY="你的key"
$env:SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
$env:DEEPSEEK_MODEL="deepseek-ai/DeepSeek-V3.2-Exp"

# 下载依赖
pip install -r requirements.txt


# 稳定运行
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000

```

### Docker 运行
请确保本地已安装 `Docker` 和 `Docker Compose`

```bash
# 同样创建虚拟环境
conda create -n ai_ppt python=3.11
conda activate ai_ppt

# 配置api密钥（这里是临时设置，确保密钥安全）
$env:SILICONFLOW_API_KEY="你的key"
$env:SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
$env:DEEPSEEK_MODEL="deepseek-ai/DeepSeek-V3.2-Exp"

# 构建容器
docker compose up -d --build
```

### 打开网页

1. 打开导航页：
http://localhost:8000/ui/index.html

2. 测试健康检查(看到结果为{"status":"ok"}即可)：
http://localhost:8000/health