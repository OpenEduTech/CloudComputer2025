#!/bin/bash

# 跨学科知识图谱系统 - 快速启动脚本

echo "========================================"
echo "跨学科知识图谱系统 - Docker快速部署"
echo "========================================"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker未安装"
    echo "请先安装Docker: https://www.docker.com/get-started"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose未安装"
    echo "请先安装Docker Compose"
    exit 1
fi

echo "✅ Docker环境检查通过"
echo ""

# 检查.env文件
if [ ! -f .env ]; then
    echo "⚠️  未找到.env文件，正在创建..."
    cp .env.example .env
    echo "📝 请编辑.env文件，填入你的OPENROUTER_API_KEY"
    echo "   文件位置: $(pwd)/.env"
    read -p "按回车键继续..." 
fi

echo "🚀 开始构建并启动服务..."
echo ""

# 构建并启动
docker-compose up --build -d

# 检查启动状态
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 服务启动成功！"
    echo ""
    echo "📍 访问地址："
    echo "   - 前端界面: http://localhost:3000"
    echo "   - 后端API: http://localhost:8000/docs"
    echo "   - Neo4j浏览器: http://localhost:7474 (neo4j/conceptgraph123)"
    echo ""
    echo "📊 查看日志: docker-compose logs -f"
    echo "🛑 停止服务: docker-compose down"
    echo ""
else
    echo ""
    echo "❌ 服务启动失败，请查看错误信息"
    exit 1
fi
