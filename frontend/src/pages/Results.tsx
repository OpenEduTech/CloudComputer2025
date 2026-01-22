import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, Typography, message, Statistic, Row, Col, Alert } from 'antd';
import { HomeOutlined, BookOutlined } from '@ant-design/icons';
import ResultCard from '../components/ResultCard';
import { ResultsSkeleton } from '../components/SkeletonLoader';
import { getQuizResult } from '../api/quiz';
import { getQuiz } from '../api/quiz';
import type { QuizResult } from '../types/result';
import type { Quiz } from '../types/quiz';

const { Title, Paragraph } = Typography;

export const Results: React.FC = () => {
  const { resultId } = useParams<{ resultId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [quiz, setQuiz] = useState<Quiz | null>(null);

  useEffect(() => {
    const fetchResultData = async () => {
      if (!resultId) {
        message.error('结果ID缺失');
        navigate('/');
        return;
      }

      try {
        setLoading(true);
        
        // Fetch the quiz result
        const resultData = await getQuizResult(resultId);
        setResult(resultData);

        // Fetch the quiz to get question details
        const quizData = await getQuiz(resultData.quiz_id);
        setQuiz(quizData);
      } catch (error: any) {
        // Display user-friendly error message (already processed by API client interceptor)
        message.error(error.message || '加载结果失败');
        console.error('Error fetching result:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchResultData();
  }, [resultId, navigate]);

  const handleBackToHome = () => {
    navigate('/');
  };

  const handleViewMistakes = () => {
    navigate('/mistakes');
  };

  if (loading) {
    return <ResultsSkeleton />;
  }

  if (!result || !quiz) {
    return (
      <Alert
        message="未找到结果"
        description="无法加载测验结果，请重试"
        type="error"
        showIcon
      />
    );
  }

  // Calculate score
  const correctCount = result.results.filter((r) => r.is_correct).length;
  const totalCount = result.results.length;
  const scorePercentage = totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '12px' }} className="fade-in">
      {/* Overall Score and Analysis */}
      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Title level={2} style={{ marginBottom: 0, fontSize: 'clamp(20px, 5vw, 30px)' }}>
            测验结果
          </Title>

          {/* Score Statistics */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Statistic
                title="得分"
                value={scorePercentage}
                suffix="%"
                valueStyle={{ color: scorePercentage >= 60 ? '#3f8600' : '#cf1322' }}
              />
            </Col>
            <Col xs={24} sm={8}>
              <Statistic
                title="正确答案"
                value={correctCount}
                suffix={`/ ${totalCount}`}
                valueStyle={{ color: '#3f8600' }}
              />
            </Col>
            <Col xs={24} sm={8}>
              <Statistic
                title="错误答案"
                value={totalCount - correctCount}
                suffix={`/ ${totalCount}`}
                valueStyle={{ color: '#cf1322' }}
              />
            </Col>
          </Row>

          {/* Overall Analysis */}
          {result.overall_analysis && (
            <div>
              <Title level={4} style={{ fontSize: 'clamp(16px, 3vw, 20px)' }}>
                总体分析
              </Title>
              <Paragraph style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>
                {result.overall_analysis}
              </Paragraph>
            </div>
          )}

          {/* Action Buttons */}
          <Space wrap>
            <Button
              type="primary"
              icon={<HomeOutlined />}
              onClick={handleBackToHome}
              size="large"
              style={{ minHeight: '44px', minWidth: '120px' }}
            >
              返回首页
            </Button>
            <Button
              icon={<BookOutlined />}
              onClick={handleViewMistakes}
              size="large"
              style={{ minHeight: '44px', minWidth: '120px' }}
            >
              查看错题
            </Button>
          </Space>
        </Space>
      </Card>

      {/* Individual Question Results */}
      <Title level={3} style={{ marginBottom: 16, fontSize: 'clamp(18px, 4vw, 24px)' }}>
        题目详情
      </Title>
      {quiz.questions.map((question, index) => {
        const questionResult = result.results.find((r) => r.question_id === question.id);
        const userAnswer = result.submission.answers.find((a) => a.question_id === question.id);

        if (!questionResult || !userAnswer) {
          return null;
        }

        return (
          <ResultCard
            key={question.id}
            question={question}
            questionNumber={index + 1}
            userAnswer={userAnswer.user_answer}
            result={questionResult}
          />
        );
      })}
    </div>
  );
};
