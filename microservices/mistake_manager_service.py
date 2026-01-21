from flask import Flask, request, jsonify
from backend.database_service import DBManager
from backend.rag_service import RAGService
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'mistake_manager'}), 200

@app.route('/api/mistakes', methods=['GET'])
def get_mistakes():
    try:
        user_id = request.args.get('user_id', '')
        difficulty = request.args.get('difficulty', None)
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        db = DBManager()
        mistakes = db.get_mistakes(user_id, difficulty)
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_mistakes = mistakes[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'data': {
                'mistakes': paginated_mistakes,
                'total': len(mistakes),
                'page': page,
                'page_size': page_size,
                'total_pages': (len(mistakes) + page_size - 1) // page_size
            },
            'message': '获取错题成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取错题失败'
        }), 500

@app.route('/api/mistakes/<int:mistake_id>', methods=['GET'])
def get_mistake(mistake_id):
    try:
        db = DBManager()
        mistake = db.get_mistake_by_id(mistake_id)
        
        if mistake:
            return jsonify({
                'success': True,
                'data': mistake,
                'message': '获取错题详情成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Mistake not found',
                'message': '错题不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取错题详情失败'
        }), 500

@app.route('/api/mistakes', methods=['POST'])
def add_mistake():
    try:
        data = request.json
        user_id = data.get('user_id', '')
        question = data.get('question', {})
        user_answer = data.get('user_answer', '')
        result = data.get('result', {})
        
        db = DBManager()
        success = db.add_mistake(question, user_answer, result)
        
        if success:
            return jsonify({
                'success': True,
                'message': '添加错题成功'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add mistake',
                'message': '添加错题失败'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '添加错题失败'
        }), 500

@app.route('/api/mistakes/<int:mistake_id>', methods=['DELETE'])
def delete_mistake(mistake_id):
    try:
        user_id = request.args.get('user_id', '')
        
        db = DBManager()
        success = db.delete_mistake(mistake_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '删除错题成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Mistake not found',
                'message': '错题不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '删除错题失败'
        }), 500

@app.route('/api/mistakes/<int:mistake_id>/mastered', methods=['PUT'])
def mark_mastered(mistake_id):
    try:
        data = request.json
        user_id = data.get('user_id', '')
        
        db = DBManager()
        success = db.mark_mistake_mastered(mistake_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '标记已掌握成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Mistake not found',
                'message': '错题不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '标记已掌握失败'
        }), 500

@app.route('/api/weak-points', methods=['GET'])
def get_weak_points():
    try:
        user_id = request.args.get('user_id', '')
        limit = int(request.args.get('limit', 5))
        
        db = DBManager()
        weak_points = db.get_weak_points(user_id, limit)
        
        return jsonify({
            'success': True,
            'data': weak_points,
            'message': '获取薄弱点成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取薄弱点失败'
        }), 500

@app.route('/api/review-suggestions', methods=['GET'])
def get_review_suggestions():
    try:
        user_id = request.args.get('user_id', '')
        
        rag = RAGService()
        db = DBManager()
        weak_points = db.get_weak_points(user_id, limit=5)
        
        suggestions = []
        for point in weak_points:
            relevant_content = rag.retrieve_relevant_content(
                point.get('keyword', ''), top_k=3
            )
            suggestion = {
                'weak_point': point,
                'relevant_content': relevant_content,
                'suggestion': f"建议重温教材第{point.get('chapter', '')}章第{point.get('section', '')}节的{point.get('keyword', '')}相关内容"
            }
            suggestions.append(suggestion)
        
        return jsonify({
            'success': True,
            'data': suggestions,
            'message': '获取复习建议成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取复习建议失败'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8003))
    app.run(host='0.0.0.0', port=port, debug=False)