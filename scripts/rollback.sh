#!/bin/bash

# 回滚脚本
# 用于快速回滚到上一个版本

set -e

APP_DIR="/app/knowledge-graph-agent"
BACKUP_DIR="/backup"

echo "🔄 开始回滚..."

# 进入应用目录
cd $APP_DIR

# 列出可用的备份
echo "可用的备份:"
ls -lt $BACKUP_DIR | head -10

# 提示用户选择备份
read -p "请输入要恢复的备份目录名（或按 Enter 使用最新备份）: " BACKUP_NAME

if [ -z "$BACKUP_NAME" ]; then
    # 使用最新备份
    BACKUP_NAME=$(ls -t $BACKUP_DIR | head -1)
fi

RESTORE_PATH="$BACKUP_DIR/$BACKUP_NAME"

if [ ! -d "$RESTORE_PATH" ]; then
    echo "❌ 备份不存在: $RESTORE_PATH"
    exit 1
fi

echo "📦 使用备份: $RESTORE_PATH"

# 停止服务
echo "停止服务..."
docker-compose down

# 恢复 Neo4j 数据
if [ -f "$RESTORE_PATH/neo4j-backup.dump" ]; then
    echo "恢复 Neo4j 数据..."
    docker-compose up -d neo4j
    sleep 10
    docker cp $RESTORE_PATH/neo4j-backup.dump kg-neo4j:/tmp/
    docker-compose exec -T neo4j neo4j-admin load --from=/tmp/neo4j-backup.dump --force
fi

# 启动所有服务
echo "启动服务..."
docker-compose up -d

echo "✅ 回滚完成！"

