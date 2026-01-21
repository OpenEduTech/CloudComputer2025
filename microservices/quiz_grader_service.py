from flask import Flask, request, jsonify
from backend.database_service import DBManager
from backend.rag_service import RAGService
from backend.agents.quiz_grader import QuizGrader
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'quiz_grader'}), 200

@app.route('/api/grade-submission', methods=['POST'])
def grade_submission():
    try:
        data = request.json
        question_type = data.get('question_type', 'choice')
        question = data.get('question', '')
        correct_answer = data.get('correct_answer', '')
        user_answer = data.get('user_answer', '')
        context = data.get('context', '')
        
        rag = RAGService()
        grader = QuizGrader()
        
        relevant_content = rag.retrieve_relevant_content(question, top_k=3)
        result = grader.grade_submission(
            question_type, question, correct_answer, user_answer, relevant_content
        )
        
        return jsonify({
            'success': True,
            'data': result,
            'message': '评分成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '评分失败'
        }), 500

@app.route('/api/batch-grade', methods=['POST'])
def batch_grade():
    try:
        data = request.json
        submissions = data.get('submissions', [])
        
        rag = RAGService()
        grader = QuizGrader()
        
        results = []
        for submission in submissions:
            relevant_content = rag.retrieve_relevant_content(
                submission.get('question', ''), top_k=3
            )
            result = grader.grade_submission(
                submission.get('question_type', 'choice'),
                submission.get('question', ''),
                submission.get('correct_answer', ''),
                submission.get('user_answer', ''),
                relevant_content
            )
            results.append(result)
        
        return jsonify({
            'success': True,
            'data': results,
            'message': '批量评分成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '批量评分失败'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8002))
    app.run(host='0.0.0.0', port=port, debug=False)