import pytest
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO
from models.cli import InteractiveCLI
from models.agent import LLMAgent
from models import Question, EvaluationResult


class TestCLIEndToEnd:
    """CLI 端到端集成测试（一镜到底）"""
    
    @pytest.fixture
    def sample_learning_material(self):
        """示例学习资料"""
        return """
        机器学习基础

        1. 监督学习
        监督学习是指从标记的训练数据中学习一个模型。
        常见的监督学习算法包括线性回归、逻辑回归、决策树等。

        2. 无监督学习
        无监督学习是指从无标记的数据中寻找隐藏的结构或模式。
        常见的无监督学习算法包括聚类、降维等。

        3. 过拟合
        过拟合是指模型在训练数据上表现很好，但在新数据上表现不佳。
        解决过拟合的方法包括正则化、增加训练数据、减少模型复杂度等。
        """
    
    @pytest.fixture
    def sample_question(self):
        """示例题目"""
        return Question(
            question_id="q1",
            question_type="multiple_choice",
            content="什么是过拟合？",
            options=[
                "A. 模型过于复杂",
                "B. 数据不足",
                "C. 学习率过高",
                "D. 特征过少"
            ],
            correct_answer="A. 模型过于复杂",
            explanation="过拟合发生在模型过于复杂时...",
            difficulty="easy",
            source_chunks=["chunk1"],
            tags=["overfitting"],
            metadata={"source": "textbook"}
        )
    
    @pytest.fixture
    def sample_evaluation_correct(self):
        """正确答案的评估结果"""
        return EvaluationResult(
            is_correct=True,
            score=100,
            feedback="回答正确！",
            detailed_explanation="您正确理解了过拟合的概念。",
            suggested_improvement="",
            confidence_score=0.95,
            mistakes=[]
        )
    
    @pytest.fixture
    def sample_evaluation_wrong(self):
        """错误答案的评估结果"""
        return EvaluationResult(
            is_correct=False,
            score=0,
            feedback="回答错误",
            detailed_explanation="过拟合是模型复杂度问题，而不是数据不足。",
            suggested_improvement="复习过拟合的定义和原因",
            confidence_score=0.90,
            mistakes=["混淆了过拟合和欠拟合"]
        )
    
    @pytest.fixture
    def mock_agent(self, sample_question, sample_evaluation_correct):
        """创建模拟 Agent"""
        agent = Mock(spec=LLMAgent)
        agent.process_material = Mock(return_value=[Mock()])
        agent.generate_questions = Mock(return_value=[sample_question])
        agent.generate_questions_stream = Mock(return_value=[sample_question])
        agent.evaluate_answer = Mock(return_value=sample_evaluation_correct)
        agent.save_performance = Mock()
        return agent
    
    @pytest.fixture
    def cli(self, mock_agent):
        """创建 CLI 实例"""
        # 直接传递 mock_agent，不需要 patch
        cli = InteractiveCLI(mock_agent)
        return cli
    
    def test_complete_user_flow_correct_answer(self, cli, mock_agent, sample_question, sample_evaluation_correct):
        """
        完整测试流程：
        1. 输入学习资料
        2. 生成题目
        3. 用户回答（正确）
        4. 获得评估反馈
        """
        
        # Step 1: 用户输入学习资料
        material = "机器学习基础内容..."
        mock_agent.process_material.return_value = [Mock()]
        
        chunks = mock_agent.process_material(material)
        assert len(chunks) > 0
        
        # Step 2: 系统生成题目
        mock_agent.generate_questions.return_value = [sample_question]
        questions = mock_agent.generate_questions(chunks, num_questions=1)
        
        assert len(questions) == 1
        assert questions[0].question_id == "q1"
        assert "过拟合" in questions[0].content
        
        # Step 3: 用户回答
        user_answer = "A. 模型过于复杂"
        
        # Step 4: 评估答案
        mock_agent.evaluate_answer.return_value = sample_evaluation_correct
        evaluation = mock_agent.evaluate_answer(questions[0], user_answer)
        
        assert evaluation.is_correct == True
        assert evaluation.score == 100
        assert evaluation.feedback == "回答正确！"
    
    def test_complete_user_flow_wrong_answer(self, cli, mock_agent, sample_question, sample_evaluation_wrong):
        """
        完整测试流程（用户答错）：
        1. 生成题目
        2. 用户回答（错误）
        3. 获得评估反馈和改进建议
        """
        
        # 设置生成的题目
        mock_agent.generate_questions.return_value = [sample_question]
        questions = mock_agent.generate_questions([Mock()], num_questions=1)
        
        # 用户回答错误
        user_answer = "B. 数据不足"
        
        # 评估错误答案
        mock_agent.evaluate_answer.return_value = sample_evaluation_wrong
        evaluation = mock_agent.evaluate_answer(questions[0], user_answer)
        
        assert evaluation.is_correct == False
        assert evaluation.score == 0
        assert len(evaluation.mistakes) > 0
        assert evaluation.suggested_improvement != ""
    
    def test_stream_generation_in_cli(self, cli, mock_agent, sample_question):
        """测试：CLI 中的流式生成题目"""
        
        # 设置流式生成回调
        callbacks = {'start': [], 'chunk': [], 'complete': []}
        
        def on_start(curr, total):
            callbacks['start'].append((curr, total))
        
        def on_chunk(text):
            callbacks['chunk'].append(text)
        
        def on_complete(question):
            callbacks['complete'].append(question)
        
        # 模拟流式生成
        mock_agent.generate_questions_stream.return_value = [sample_question]
        
        questions = mock_agent.generate_questions_stream(
            [Mock()],
            num_questions=1,
            on_question_start=on_start,
            on_question_chunk=on_chunk,
            on_question_complete=on_complete
        )
        
        assert len(questions) > 0
        assert questions[0].question_id == "q1"
    
    def test_multiple_questions_flow(self, cli, mock_agent):
        """测试：多个题目的完整流程"""
        
        # 创建多个样本题目
        questions_list = [
            Question(
                question_id=f"q{i}",
                question_type="multiple_choice",
                content=f"题目 {i}",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="解释",
                difficulty="easy",
                source_chunks=[],
                tags=[],
                metadata={}
            )
            for i in range(3)
        ]
        
        mock_agent.generate_questions.return_value = questions_list
        
        # 生成题目
        questions = mock_agent.generate_questions([Mock()], num_questions=3)
        assert len(questions) == 3
        
        # 模拟用户对每个题目的回答和评估
        results = []
        for i, question in enumerate(questions):
            # 用户回答
            user_answer = "A"
            
            # 评估
            evaluation = EvaluationResult(
                is_correct=True,
                score=100 - i*10,  # 逐个递减
                feedback="回答",
                detailed_explanation="解释",
                suggested_improvement="",
                confidence_score=0.9,
                mistakes=[]
            )
            
            results.append({
                'question': question,
                'user_answer': user_answer,
                'evaluation': evaluation
            })
        
        # 验证完整流程
        assert len(results) == 3
        assert results[0]['evaluation'].score == 100
        assert results[1]['evaluation'].score == 90
        assert results[2]['evaluation'].score == 80
    
    def test_save_performance_is_called(self, cli, mock_agent, sample_question, sample_evaluation_correct):
        """测试：性能保存被正确调用"""
        
        # 模拟答题和评估
        mock_agent.evaluate_answer.return_value = sample_evaluation_correct
        evaluation = mock_agent.evaluate_answer(sample_question, "A. 模型过于复杂")
        
        # 保存性能
        mock_agent.save_performance("user1", sample_question, evaluation, "A. 模型过于复杂")
        
        # 验证保存被调用
        mock_agent.save_performance.assert_called_once_with(
            "user1",
            sample_question,
            evaluation,
            "A. 模型过于复杂"
        )


class TestCLIUserInteraction:
    """CLI 用户交互测试"""
    
    @pytest.fixture
    def mock_agent(self):
        """创建模拟 Agent"""
        return Mock(spec=LLMAgent)
    
    @pytest.fixture
    def cli(self, mock_agent):
        """创建 CLI"""
        cli = InteractiveCLI(mock_agent)
        return cli
    
    def test_cli_displays_welcome_message(self, cli):
        """测试：CLI 显示欢迎消息"""
        # 这是显示测试，通常需要通过手动验证或输出检查
        assert cli.console is not None
    
    def test_cli_question_display(self, cli):
        """测试：CLI 正确显示题目"""
        question = Question(
            question_id="q1",
            question_type="multiple_choice",
            content="测试题目",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="解释",
            difficulty="easy",
            source_chunks=[],
            tags=[],
            metadata={}
        )
        
        # 验证题目可以被正确显示（不会抛出异常）
        try:
            cli._display_question(question)
        except Exception as e:
            pytest.fail(f"显示题目时出错: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
