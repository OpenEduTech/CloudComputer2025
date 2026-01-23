#!/bin/bash

# 跨学科知识图谱开发环境启动脚本

echo "🚀 启动跨学科知识图谱开发环境..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

# 检查环境变量文件
if [ ! -f "dev.env" ]; then
    echo "⚠️  未找到 dev.env 文件，正在从模板创建..."
    cp dev.env.example dev.env 2>/dev/null || echo "请手动创建 dev.env 文件"
fi

# 构建并启动所有服务
echo "📦 构建并启动服务..."
docker-compose up --build -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."

# 检查前端
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ 前端服务: http://localhost:3000"
else
    echo "❌ 前端服务未启动"
fi

# 检查后端API
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ 后端API: http://localhost:8080 (文档: http://localhost:8080/docs)"
else
    echo "❌ 后端API未启动"
fi

# 检查Agent服务
if curl -f http://localhost:8001/healthz > /dev/null 2>&1; then
    echo "✅ Agent服务: http://localhost:8001"
else
    echo "❌ Agent服务未启动"
fi

# 检查Neo4j
if curl -f http://localhost:7474 > /dev/null 2>&1; then
    echo "✅ Neo4j浏览器: http://localhost:7474 (用户名: neo4j, 密码: password123)"
else
    echo "❌ Neo4j未启动"
fi

# 检查Redis
if docker exec knowledge-graph-redis redis-cli ping | grep -q PONG; then
    echo "✅ Redis缓存服务运行正常"
else
    echo "❌ Redis未启动"
fi

echo ""
echo "🎉 开发环境启动完成！"
echo ""
echo "📖 服务地址:"
echo "   前端应用: http://localhost:3000"
echo "   后端API:  http://localhost:8080/docs"
echo "   Agent服务: http://localhost:8001"
echo "   Neo4j:     http://localhost:7474"
echo ""
echo "🛠️  管理命令:"
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
