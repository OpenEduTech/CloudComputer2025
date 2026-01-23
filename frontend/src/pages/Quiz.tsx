import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Button, Progress, Space, message } from 'antd';
import QuizCard from '../components/QuizCard';
import { QuizSkeleton } from '../components/SkeletonLoader';
import * as quizApi from '../api/quiz';
import type { Quiz as QuizType, Answer } from '../types/quiz';

const { Title, Text } = Typography;

/**
 * Quiz page
 * Displays quiz questions and handles answer submission
 * 
 * Features:
 * - Fetches quiz data using quizId from route params
 * - Displays all questions using QuizCard components
 * - Manages answer state (map of questionId to answer)
 * - Shows progress indicator (X of Y answered)
 * - Enables submit button only when all questions are answered
 * - Submits answers and navigates to results page
 * 
 * Requirements: 5.1, 5.4, 5.5, 5.6, 5.7, 6.1, 6.2
 */
export const Quiz: React.FC = () => {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();

  // State management
  const [quiz, setQuiz] = useState<QuizType | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Fetch quiz data on mount
  useEffect(() => {
    const fetchQuiz = async () => {
      if (!quizId) {
        message.error('测验ID缺失');
        navigate('/');
        return;
      }

      try {
        setLoading(true);
        const data = await quizApi.getQuiz(quizId);
        setQuiz(data);
      } catch (error: any) {
        // Display user-friendly error message (already processed by API client interceptor)
        message.error(error.message || '加载测验失败');
        navigate('/');
      } finally {
        setLoading(false);
      }
    };

    fetchQuiz();
  }, [quizId, navigate]);

  // Handle answer change - memoized to prevent unnecessary re-renders
  const handleAnswerChange = useCallback((questionId: string, answer: string) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: answer,
    }));
  }, []);

  // Calculate progress
  const getProgress = () => {
    if (!quiz) return { answered: 0, total: 0, percentage: 0 };
    
    const total = quiz.questions.length;
    const answered = Object.keys(answers).filter(qId => 
      quiz.questions.some(q => q.id === qId) && answers[qId]
    ).length;
    const percentage = total > 0 ? Math.round((answered / total) * 100) : 0;

    return { answered, total, percentage };
  };

  // Check if all questions are answered
  const isAllAnswered = () => {
    if (!quiz) return false;
    return quiz.questions.every(q => answers[q.id] && answers[q.id].trim() !== '');
  };

  // Handle quiz submission
  const handleSubmit = async () => {
    if (!quiz || !quizId) return;

    try {
      setSubmitting(true);

      // Convert answers object to Answer array
      const answerArray: Answer[] = quiz.questions.map(q => ({
        question_id: q.id,
        user_answer: answers[q.id] || '',
      }));

      // Submit quiz
      const result = await quizApi.submitQuiz(quizId, answerArray);

      console.log('✅ 测验提交成功，返回结果:', result);
      console.log('📊 result.id:', result.id);

      // Show success message
      message.success('测验提交成功！');

      // Navigate to results page
      if (result.id) {
        console.log('🚀 跳转到结果页面，resultId:', result.id);
        navigate(`/results/${result.id}`);
      } else {
        console.error('❌ 无法获取结果ID:', result);
        message.error('提交成功，但无法跳转到结果页面');
      }
    } catch (error: any) {
      // Display user-friendly error message (already processed by API client interceptor)
      message.error(error.message || '提交测验失败');
    } finally {
      setSubmitting(false);
    }
  };

  // Loading state with skeleton
  if (loading) {
    return <QuizSkeleton />;
  }

  // No quiz found
  if (!quiz) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Text>未找到测验</Text>
      </div>
    );
  }

  const progress = getProgress();

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '12px' }} className="fade-in">
      {/* Quiz Header */}
      <Space direction="vertical" size="large" style={{ width: '100%', marginBottom: 24 }}>
        <Title level={2} style={{ fontSize: 'clamp(20px, 5vw, 30px)' }}>
          {quiz.title}
        </Title>

        {/* Progress Indicator */}
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>
            进度: {progress.answered} / {progress.total} 已回答
          </Text>
          <Progress 
            percent={progress.percentage} 
            status={progress.percentage === 100 ? 'success' : 'active'}
          />
        </Space>
      </Space>

      {/* Questions */}
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {quiz.questions.map((question, index) => (
          <QuizCard
            key={question.id}
            question={question}
            questionNumber={index + 1}
            answer={answers[question.id] || null}
            onAnswerChange={handleAnswerChange}
            disabled={submitting}
          />
        ))}
      </Space>

      {/* Submit Button */}
      <div style={{ marginTop: 32, textAlign: 'center' }}>
        <Button
          type="primary"
          size="large"
          onClick={handleSubmit}
          disabled={!isAllAnswered()}
          loading={submitting}
          style={{ minHeight: '44px', minWidth: '120px' }}
        >
          提交测验
        </Button>
        {!isAllAnswered() && (
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 'clamp(12px, 2vw, 14px)' }}>
              请回答所有问题后再提交
            </Text>
          </div>
        )}
      </div>
    </div>
  );
};
