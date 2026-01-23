#!/bin/bash

# 部署脚本示例
# 用于 CI/CD 自动部署

set -e

echo "🚀 开始部署知识图谱应用..."

# 配置变量
APP_DIR="/app/knowledge-graph-agent"
DOCKER_COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="/backup/kg-$(date +%Y%m%d-%H%M%S)"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 函数：打印信息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 未安装，请先安装"
        exit 1
    fi
}

# 检查必要的命令
log_info "检查依赖..."
check_command docker
check_command docker-compose

# 进入应用目录
cd $APP_DIR || {
    log_error "应用目录不存在: $APP_DIR"
    exit 1
}

# 备份当前数据
log_info "备份数据..."
mkdir -p $BACKUP_DIR
docker-compose exec -T neo4j neo4j-admin dump --to=/tmp/neo4j-backup.dump || log_warn "Neo4j 备份失败"
docker cp kg-neo4j:/tmp/neo4j-backup.dump $BACKUP_DIR/ || log_warn "复制备份文件失败"

# 拉取最新代码（如果使用 git）
if [ -d ".git" ]; then
    log_info "拉取最新代码..."
    git pull origin main
fi

# 拉取最新镜像
log_info "拉取最新 Docker 镜像..."
docker-compose pull

# 停止旧容器
log_info "停止旧容器..."
docker-compose down

# 启动新容器
log_info "启动新容器..."
docker-compose up -d

# 等待服务启动
log_info "等待服务启动..."
sleep 10

# 健康检查
log_info "执行健康检查..."
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$BACKEND_HEALTH" == "200" ]; then
    log_info "后端服务健康 ✓"
else
    log_error "后端服务不健康 (HTTP $BACKEND_HEALTH)"
    exit 1
fi

FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ "$FRONTEND_HEALTH" == "200" ]; then
    log_info "前端服务健康 ✓"
else
    log_error "前端服务不健康 (HTTP $FRONTEND_HEALTH)"
    exit 1
fi

# 清理旧镜像
log_info "清理旧镜像..."
docker image prune -f

# 显示运行状态
log_info "当前运行状态:"
docker-compose ps

log_info "✅ 部署完成！"
log_info "前端地址: http://localhost:3000"
log_info "后端 API: http://localhost:8000"
log_info "Neo4j 浏览器: http://localhost:7474"
log_info "备份位置: $BACKUP_DIR"

