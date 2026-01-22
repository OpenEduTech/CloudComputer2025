#!/bin/bash

# API测试脚本

echo "=========================================="
echo "  API功能测试"
echo "=========================================="
echo ""

API_BASE="http://localhost:8000"

# 测试1: 健康检查
echo "测试 1: 健康检查"
echo "----------------------------------------"
response=$(curl -s ${API_BASE}/health)
echo $response | python -m json.tool
echo ""

# 测试2: 生成知识图谱
echo "测试 2: 生成知识图谱（概念：熵）"
echo "----------------------------------------"
echo "正在生成图谱，请稍候（30-60秒）..."
response=$(curl -s -X POST ${API_BASE}/api/graph/generate \
  -H "Content-Type: application/json" \
  -d '{"concept": "熵", "enable_validation": true}')

echo $response | python -m json.tool > /tmp/graph_result.json
echo "✅ 图谱生成完成"
echo ""

# 提取graph_id
graph_id=$(echo $response | python -c "import sys, json; print(json.load(sys.stdin)['data']['graph_id'])" 2>/dev/null)

if [ ! -z "$graph_id" ]; then
    echo "Graph ID: $graph_id"
    echo ""
    
    # 测试3: 查询图谱
    echo "测试 3: 查询已生成的图谱"
    echo "----------------------------------------"
    response=$(curl -s ${API_BASE}/api/graph/${graph_id})
    echo $response | python -m json.tool | head -30
    echo "..."
    echo ""
    
    # 测试4: 列出所有图谱
    echo "测试 4: 列出所有图谱"
    echo "----------------------------------------"
    response=$(curl -s ${API_BASE}/api/graphs)
    echo $response | python -m json.tool
    echo ""
else
    echo "⚠️  未能获取graph_id，跳过后续测试"
fi

echo "=========================================="
echo "  测试完成"
echo "=========================================="
echo ""
echo "详细结果已保存到: /tmp/graph_result.json"
echo "可以使用以下命令查看:"
echo "  cat /tmp/graph_result.json | python -m json.tool"

