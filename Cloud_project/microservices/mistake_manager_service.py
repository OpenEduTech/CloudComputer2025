from flask import Flask, request, jsonify
from backend.database_service import DBManager
from backend.rag_service import RAGService
from backend.agents.base_agent import BaseAgent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
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
        success = db.add_mistake(question, user_answer, result, user_id=user_id)
        
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
        
        agent = BaseAgent(temperature=0.3)
        suggestions = []
        for point in weak_points:
            keyword = point.get('keyword', '')
            difficulty = point.get('difficulty', '')
            error_times = point.get('error_times', 0)
            importance = point.get('importance', 1.0)
            last_error_time = point.get('last_error_time', '')
            
            relevant_content = rag.retrieve_relevant_content(
                keyword, k=3
            )
            
            if agent.llm is None:
                suggestion_text = f"[开发模式] 建议重点复习与“{keyword}”相关的内容，回顾课堂笔记和教材，并针对相同类型的题目多做练习。"
            else:
                prompt = ChatPromptTemplate.from_template("""
                你是一名学习辅导老师，需要根据学生在某个知识点上的错题情况生成个性化复习建议。

                [考点信息]
                - 知识点: {keyword}
                - 难度: {difficulty}
                - 错误次数: {error_times}
                - 考点重要性权重: {importance}
                - 最近错误时间: {last_error_time}

                [相关资料内容]
                {relevant_content}

                请给出一段针对该学生的复习建议，要求:
                1. 指出该知识点目前的薄弱点或常见错误原因
                2. 推荐应重点重温的资料位置或章节（如果无法确定章节，可描述为“教材中关于该概念的部分”）
                3. 建议具体的练习方式或复习策略
                4. 控制在80字以内，使用自然的中文表述。

                直接输出建议内容，不要添加序号或其它说明。
                """)
                chain = prompt | agent.llm | StrOutputParser()
                try:
                    suggestion_text = chain.invoke({
                        "keyword": keyword,
                        "difficulty": difficulty,
                        "error_times": error_times,
                        "importance": importance,
                        "last_error_time": str(last_error_time),
                        "relevant_content": relevant_content[:800] if isinstance(relevant_content, str) else str(relevant_content),
                    }).strip()
                except Exception as e:
                    print(f"生成复习建议失败: {e}")
                    suggestion_text = f"建议重温与“{keyword}”相关的课程内容，并结合错题解析再次练习。"
            
            suggestion = {
                'weak_point': point,
                'relevant_content': relevant_content,
                'suggestion': suggestion_text,
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
