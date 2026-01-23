#!/bin/bash

# 跨学科知识图谱智能体 - 启动脚本

set -e

echo "=========================================="
echo "  跨学科知识图谱智能体 - 启动脚本"
echo "=========================================="
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未安装Docker"
    echo "请访问 https://docs.docker.com/get-docker/ 安装Docker"
    exit 1
fi

# 检查Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: 未安装Docker Compose"
    echo "请访问 https://docs.docker.com/compose/install/ 安装Docker Compose"
    exit 1
fi

echo "✅ Docker 和 Docker Compose 已安装"
echo ""

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，从模板创建..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "✅ 已创建 .env 文件"
        echo ""
        echo "⚠️  请编辑 .env 文件，填入你的 OPENAI_API_KEY"
        echo "   然后重新运行此脚本"
        exit 0
    else
        echo "❌ 错误: 未找到 env.example 文件"
        exit 1
    fi
fi

# 检查API Key
if grep -q "your-openai-api-key-here" .env; then
    echo "⚠️  警告: 请在 .env 文件中设置你的 OPENAI_API_KEY"
    echo "   当前使用的是示例值，无法正常工作"
    read -p "是否继续？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo "✅ 环境配置检查完成"
echo ""

# 停止旧容器
echo "🔄 停止旧容器..."
docker-compose down 2>/dev/null || true
echo ""

# 拉取镜像
echo "📦 拉取基础镜像..."
docker-compose pull neo4j redis
echo ""

# 构建镜像
echo "🔨 构建应用镜像..."
docker-compose build
echo ""

# 启动服务
echo "🚀 启动所有服务..."
docker-compose up -d
echo ""

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker-compose ps
echo ""

# 等待后端健康检查
echo "⏳ 等待后端服务就绪..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 后端服务已就绪"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done
echo ""

if [ $attempt -eq $max_attempts ]; then
    echo "⚠️  警告: 后端服务启动超时，请检查日志"
    echo "   运行: docker-compose logs backend"
else
    echo ""
    echo "=========================================="
    echo "  🎉 启动成功！"
    echo "=========================================="
    echo ""
    echo "📱 访问地址:"
    echo "   前端界面:    http://localhost:3000"
    echo "   API文档:     http://localhost:8000/docs"
    echo "   Neo4j浏览器: http://localhost:7474"
    echo ""
    echo "📝 常用命令:"
    echo "   查看日志:    docker-compose logs -f"
    echo "   停止服务:    docker-compose down"
    echo "   重启服务:    docker-compose restart"
    echo ""
    echo "💡 提示: 首次生成图谱可能需要30-60秒"
    echo "=========================================="
fi

