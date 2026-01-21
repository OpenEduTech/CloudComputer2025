from flask import Flask, request, jsonify
from backend.database_service import DBManager
from backend.rag_service import RAGService
from backend.agents.quiz_generator import QuizGenerator
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'quiz_generator'}), 200

@app.route('/api/generate-exam', methods=['POST'])
def generate_exam():
    try:
        data = request.json
        context = data.get('context', '')
        difficulty = data.get('difficulty', 'mixed')
        question_count = data.get('question_count', 10)
        
        rag = RAGService()
        generator = QuizGenerator()
        
        relevant_content = rag.retrieve_relevant_content(context, top_k=5)
        exam = generator.generate_comprehensive_exam(relevant_content)
        
        return jsonify({
            'success': True,
            'data': exam,
            'message': '试卷生成成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '试卷生成失败'
        }), 500

@app.route('/api/generate-question', methods=['POST'])
def generate_question():
    try:
        data = request.json
        topic = data.get('topic', '')
        difficulty = data.get('difficulty', 'medium')
        question_type = data.get('question_type', 'choice')
        
        generator = QuizGenerator()
        question = generator.generate_single_question(topic, difficulty, question_type)
        
        return jsonify({
            'success': True,
            'data': question,
            'message': '题目生成成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '题目生成失败'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8001))
    app.run(host='0.0.0.0', port=port, debug=False)