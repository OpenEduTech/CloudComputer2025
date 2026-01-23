"""
Flask后端主应用
提供RESTful API接口
"""

import os
import json
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import redis

try:
    from .agent import KnowledgeGraphAgent
    from .validator import KnowledgeValidator
    from .graph_builder import GraphBuilder
except ImportError:
    from agent import KnowledgeGraphAgent
    from validator import KnowledgeValidator
    from graph_builder import GraphBuilder

# 加载环境变量
load_dotenv()

app = Flask(__name__)
# 配置CORS允许所有来源（包括file://协议）
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# 初始化组件
agent = KnowledgeGraphAgent()
validator = KnowledgeValidator(agent)
graph_builder = GraphBuilder()

# 初始化Redis缓存
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True
    )
    redis_client.ping()
    print("[OK] Redis connected successfully")
except Exception as e:
    try:
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[FAIL] Redis connection failed: {error_msg}")
    except:
        print("[FAIL] Redis connection failed")
    print("Note: Redis is optional. App will run without cache.")
    redis_client = None

def get_cache_key(concept):
    """生成缓存键"""
    return f"kg:{hashlib.md5(concept.encode()).hexdigest()}"

@app.route('/', methods=['GET'])
def index():
    """根路径 - API信息"""
    return jsonify({
        'message': 'Knowledge Graph Agent API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'generate': '/api/generate',
            'expand': '/api/expand',
            'clear_cache': '/api/cache/clear'
        },
        'redis': redis_client is not None and redis_client.ping() if redis_client else False
    })

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    redis_status = False
    if redis_client:
        try:
            redis_status = redis_client.ping()
        except:
            redis_status = False
    
    return jsonify({
        'status': 'healthy',
        'redis': redis_status
    })

@app.route('/api/generate', methods=['POST'])
def generate_graph():
    """生成知识图谱"""
    try:
        data = request.get_json()
        concept = data.get('concept', '').strip()
        
        if not concept:
            return jsonify({'error': '请输入概念'}), 400
        
        # 检查缓存
        cache_key = get_cache_key(concept)
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    print(f"[OK] 从缓存获取: {concept}")
                    return jsonify(json.loads(cached))
            except Exception as e:
                print(f"缓存读取失败: {str(e)}")
        
        # Step 1: 使用Agent挖掘关联
        print(f"开始挖掘概念: {concept}")
        raw_data = agent.mine_relations(concept)
        
        # Step 2: 验证关联的准确性
        print("验证关联准确性...")
        validated_data = validator.validate_graph(raw_data)
        
        # Step 3: 检查完整性
        is_complete, message = validator.check_completeness(validated_data)
        if not is_complete:
            return jsonify({'error': f'图谱生成失败: {message}'}), 400
        
        # Step 4: 构建图数据结构
        print("构建知识图谱...")
        graph_data = graph_builder.build_graph(validated_data)
        
        # Step 5: 转换为前端格式
        result = {
            'success': True,
            'data': graph_builder.to_echarts_format(graph_data),
            'metadata': graph_data['metadata'],
            'validation_summary': {
                'total_relations': validated_data['total_relations'],
                'validated_relations': validated_data['validated_relations']
            }
        }
        
        # 缓存结果（24小时）
        if redis_client:
            try:
                redis_client.setex(cache_key, 86400, json.dumps(result))
                print(f"[OK] 结果已缓存")
            except Exception as e:
                print(f"缓存写入失败: {str(e)}")
        
        return jsonify(result)
    
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/expand', methods=['POST'])
def expand_concept():
    """扩展概念详情"""
    try:
        data = request.get_json()
        concept = data.get('concept', '').strip()
        discipline = data.get('discipline', '').strip()
        
        if not concept or not discipline:
            return jsonify({'error': '参数不完整'}), 400
        
        # 这里可以调用Agent的扩展功能
        # 简化实现，返回基本信息
        result = {
            'success': True,
            'concept': concept,
            'discipline': discipline,
            'details': f'{concept}在{discipline}领域的详细信息'
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """清除缓存"""
    if not redis_client:
        return jsonify({'error': 'Redis未连接'}), 500
    
    try:
        # 清除所有kg:*的键
        keys = redis_client.keys('kg:*')
        if keys:
            redis_client.delete(*keys)
        return jsonify({'success': True, 'cleared': len(keys)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('BACKEND_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"启动Flask服务器: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

