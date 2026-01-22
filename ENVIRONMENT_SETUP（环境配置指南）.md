# 环境配置指南

## 目录
1. [系统要求](#系统要求)
2. [前置依赖安装](#前置依赖安装)
3. [环境变量配置](#环境变量配置)
4. [数据库配置](#数据库配置)
5. [服务端口说明](#服务端口说明)
6. [开发环境配置](#开发环境配置)
7. [生产环境配置](#生产环境配置)
8. [常见问题](#常见问题)

---

## 系统要求

### 硬件要求
- CPU: 2核心或以上
- 内存: 4GB RAM（推荐8GB）
- 磁盘: 至少10GB可用空间

### 操作系统
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 20.04+, CentOS 8+)

### 软件版本
| 软件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Node.js | 16.x | 18.x |
| Python | 3.9 | 3.11 |
| Docker | 20.10 | 24.x |
| Docker Compose | 2.0 | 2.20+ |

---

## 前置依赖安装

### Windows环境

#### 1. 安装Node.js
```powershell
# 下载Node.js安装包
# 访问: https://nodejs.org/
# 下载LTS版本 (推荐18.x)

# 验证安装
node --version
npm --version
```

#### 2. 安装Python
```powershell
# 下载Python安装包
# 访问: https://www.python.org/downloads/
# 下载Python 3.11

# 验证安装
python --version
pip --version
```

#### 3. 安装Docker Desktop
```powershell
# 下载Docker Desktop
# 访问: https://www.docker.com/products/docker-desktop/

# 启动Docker Desktop
# 等待服务完全启动

# 验证安装
docker --version
docker-compose --version
```

### macOS环境

#### 1. 使用Homebrew安装依赖
```bash
# 安装Homebrew (如未安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装Node.js
brew install node@18

# 安装Python
brew install python@3.11

# 安装Docker Desktop
brew install --cask docker
```

### Linux环境 (Ubuntu)

#### 1. 安装Node.js
```bash
# 添加NodeSource仓库
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# 安装Node.js
sudo apt-get install -y nodejs

# 验证安装
node --version
npm --version
```

#### 2. 安装Python
```bash
# 安装Python 3.11
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# 验证安装
python3.11 --version
pip3 --version
```

#### 3. 安装Docker
```bash
# 卸载旧版本
sudo apt-get remove docker docker-engine docker.io containerd runc

# 安装依赖
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加Docker官方GPG密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 设置仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到docker组
sudo usermod -aG docker $USER

# 验证安装
docker --version
docker compose version
```

---

## 环境变量配置

### 1. 创建.env文件

在项目根目录创建`.env`文件（从模板复制）：

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/macOS
cp .env.example .env
```

### 2. 配置API密钥

编辑`.env`文件，填入以下必需配置：

```env
# === 必需配置 ===

# OpenRouter API配置 (LLM服务)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# OpenAI API配置 (Embedding服务)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# === 可选配置 ===

# 后端服务配置
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0

# 前端服务配置
FRONTEND_PORT=3000

# Neo4j数据库配置（本地开发）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Neo4j数据库配置（Docker环境）
# NEO4J_URI=bolt://neo4j:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=conceptgraph123

# Redis配置（本地开发）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Redis配置（Docker环境）
# REDIS_HOST=redis
# REDIS_PORT=6379
# REDIS_PASSWORD=conceptgraph123

# 日志级别
LOG_LEVEL=INFO
```

### 3. 获取API密钥

#### OpenRouter API密钥
1. 访问 https://openrouter.ai/
2. 注册/登录账号
3. 进入 Settings -> API Keys
4. 创建新的API密钥
5. 复制密钥到`.env`文件的`OPENROUTER_API_KEY`

#### OpenAI API密钥
1. 访问 https://platform.openai.com/
2. 注册/登录账号
3. 进入 API Keys
4. 创建新的API密钥
5. 复制密钥到`.env`文件的`OPENAI_API_KEY`

---

## 数据库配置

### Neo4j配置

#### 本地开发环境

1. **下载安装Neo4j Desktop**
   - 访问: https://neo4j.com/download/
   - 下载Neo4j Desktop
   - 安装并启动

2. **创建数据库**
   ```
   - 打开Neo4j Desktop
   - 点击 "New" -> "Create Project"
   - 点击 "Add" -> "Local DBMS"
   - 名称: ConceptGraph
   - 密码: password
   - 版本: 5.15.0
   - 点击 "Create"
   ```

3. **启动数据库**
   ```
   - 选择刚创建的数据库
   - 点击 "Start"
   - 等待启动完成
   ```

4. **验证连接**
   - 打开浏览器访问: http://localhost:7474
   - 用户名: neo4j
   - 密码: password

#### Docker环境

Docker环境下Neo4j会自动配置，无需手动操作。

配置文件位于 `docker-compose.yml`:
```yaml
neo4j:
  image: neo4j:5.15.0
  environment:
    - NEO4J_AUTH=neo4j/conceptgraph123
  ports:
    - "7474:7474"
    - "7687:7687"
```

### Redis配置

#### 本地开发环境

**Windows:**
```powershell
# 下载Redis for Windows
# 访问: https://github.com/microsoftarchive/redis/releases
# 下载Redis-x64-x.x.xxx.msi

# 安装后启动服务
# 服务会自动在后台运行
```

**macOS:**
```bash
# 使用Homebrew安装
brew install redis

# 启动Redis服务
brew services start redis

# 验证
redis-cli ping
# 应返回: PONG
```

**Linux:**
```bash
# 安装Redis
sudo apt-get update
sudo apt-get install -y redis-server

# 启动服务
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 验证
redis-cli ping
# 应返回: PONG
```

#### Docker环境

Docker环境下Redis会自动配置。

---

## 服务端口说明

| 服务 | 默认端口 | 用途 | 访问地址 |
|------|---------|------|---------|
| Frontend | 3000 | React前端应用 | http://localhost:3000 |
| Backend | 8000 | FastAPI后端API | http://localhost:8000 |
| Backend Docs | 8000 | API文档 | http://localhost:8000/docs |
| Neo4j Browser | 7474 | Neo4j Web界面 | http://localhost:7474 |
| Neo4j Bolt | 7687 | Neo4j数据库连接 | bolt://localhost:7687 |
| Redis | 6379 | Redis缓存服务 | localhost:6379 |

**端口冲突解决:**

如果端口被占用，修改`.env`文件中的端口配置，或修改`docker-compose.yml`中的端口映射。

---

## 开发环境配置

### 前端开发环境

1. **进入前端目录**
```bash
cd frontend
```

2. **安装依赖**
```bash
npm install
```

3. **启动开发服务器**
```bash
npm start
```

4. **访问应用**
- 打开浏览器访问: http://localhost:3000
- 支持热重载，修改代码自动刷新

### 后端开发环境

1. **进入后端目录**
```bash
cd backend
```

2. **创建虚拟环境（推荐）**

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **启动后端服务**
```bash
# 开发模式（支持热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 或使用启动脚本
python start_backend.py
```

5. **验证服务**
- 访问API文档: http://localhost:8000/docs
- 测试健康检查: http://localhost:8000/health

### 数据库准备

确保Neo4j和Redis服务已启动：

**检查Neo4j:**
```bash
# 访问浏览器
http://localhost:7474

# 或使用cypher-shell
cypher-shell -u neo4j -p password
```

**检查Redis:**
```bash
redis-cli ping
# 应返回: PONG
```

---

## 生产环境配置

### Docker部署（推荐）

#### 1. 准备环境

确保已安装Docker和Docker Compose:
```bash
docker --version
docker-compose --version
```

#### 2. 配置环境变量

编辑`.env`文件，设置生产环境配置：
```env
# 使用Docker内部服务名
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=conceptgraph123

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=conceptgraph123
```

#### 3. 启动服务

**Windows PowerShell:**
```powershell
.\start.ps1
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

**或手动启动:**
```bash
docker-compose -p conceptgraph up -d --build
```

#### 4. 验证部署

```bash
# 查看容器状态
docker-compose -p conceptgraph ps

# 查看日志
docker-compose -p conceptgraph logs -f

# 访问服务
# Frontend: http://localhost:3000
# Backend: http://localhost:8000/docs
# Neo4j: http://localhost:7474
```

#### 5. 停止服务

```bash
docker-compose -p conceptgraph down
```

#### 6. 数据持久化

Docker环境下数据会保存在以下Volume中：
- `conceptgraph_neo4j_data` - Neo4j数据库数据
- `conceptgraph_redis_data` - Redis缓存数据
- `conceptgraph_neo4j_logs` - Neo4j日志
- `conceptgraph_neo4j_import` - Neo4j导入文件
- `conceptgraph_neo4j_plugins` - Neo4j插件

查看Volume:
```bash
docker volume ls | grep conceptgraph
```

备份数据:
```bash
# 备份Neo4j数据
docker run --rm \
  -v conceptgraph_neo4j_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/neo4j_backup.tar.gz /data
```

---

## 常见问题

### 1. Docker相关

#### Q: Docker命令执行缓慢或卡住
**A:** 
- 重启Docker Desktop
- 检查Docker设置中的资源分配（内存、CPU）
- 清理Docker缓存: `docker system prune -a`

#### Q: 端口被占用
**A:**
```bash
# Windows查看端口占用
netstat -ano | findstr :3000

# Linux/macOS查看端口占用
lsof -i :3000

# 修改docker-compose.yml中的端口映射
ports:
  - "3001:3000"  # 使用3001代替3000
```

#### Q: 容器无法启动
**A:**
```bash
# 查看详细日志
docker-compose -p conceptgraph logs <service-name>

# 检查容器状态
docker-compose -p conceptgraph ps

# 重新构建
docker-compose -p conceptgraph up -d --build --force-recreate
```

### 2. 数据库相关

#### Q: Neo4j无法连接
**A:**
- 检查Neo4j服务是否启动
- 验证端口7687是否可访问
- 检查用户名密码是否正确
- 查看Neo4j日志: `docker-compose -p conceptgraph logs neo4j`

#### Q: Redis连接失败
**A:**
- 检查Redis服务是否运行: `redis-cli ping`
- 验证端口6379是否开放
- 检查防火墙设置
- 查看Redis日志: `docker-compose -p conceptgraph logs redis`

### 3. API相关

#### Q: LLM调用失败
**A:**
- 检查`.env`中的API密钥是否正确
- 验证网络连接
- 检查API配额是否用尽
- 查看后端日志获取详细错误信息

#### Q: Wikipedia/Arxiv API超时
**A:**
- 检查网络连接
- 增加超时时间（代码中timeout参数）
- 使用代理服务器（如需要）

### 4. 前端相关

#### Q: npm install失败
**A:**
```bash
# 清理缓存
npm cache clean --force

# 删除node_modules和package-lock.json
rm -rf node_modules package-lock.json

# 重新安装
npm install --legacy-peer-deps
```

#### Q: 页面无法加载
**A:**
- 检查后端服务是否正常运行
- 验证API地址配置是否正确
- 查看浏览器Console错误信息
- 检查CORS配置

### 5. Python环境

#### Q: pip安装依赖失败
**A:**
```bash
# 升级pip
python -m pip install --upgrade pip

# 使用清华镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 单独安装问题包
pip install <package-name> --no-cache-dir
```

#### Q: 虚拟环境激活失败（Windows）
**A:**
```powershell
# 修改PowerShell执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 重新激活
.\venv\Scripts\Activate.ps1
```

---

## 技术支持

如遇到其他问题：

1. 查看项目文档:
   - [README.md](README.md) - 项目概述

2. 检查日志:
   ```bash
   # Docker日志
   docker-compose -p conceptgraph logs -f
   
   # 单个服务日志
   docker-compose -p conceptgraph logs -f backend
   ```

3. 提交Issue到GitHub仓库

4. 联系开发团队
