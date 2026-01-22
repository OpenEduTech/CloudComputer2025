import React, { memo } from 'react';
import { Card, Typography, Space, Tag } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import type { Question } from '../types/quiz';
import type { GradingResult } from '../types/result';

const { Text, Paragraph } = Typography;

interface ResultCardProps {
  question: Question;
  questionNumber: number;
  userAnswer: string;
  result: GradingResult;
}

/**
 * ResultCard component - Memoized for performance optimization
 * Only re-renders when props actually change
 */
const ResultCard: React.FC<ResultCardProps> = memo(({
  question,
  questionNumber,
  userAnswer,
  result,
}) => {
  // Determine card styling based on correctness
  const cardStyle = {
    marginBottom: 16,
    borderColor: result.is_correct ? '#52c41a' : '#ff4d4f',
    borderWidth: 2,
  };

  return (
    <Card
      style={cardStyle}
      title={
        <Space>
          <Text strong>题目 {questionNumber}</Text>
          {result.is_correct ? (
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
          ) : (
            <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
          )}
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Question Text */}
        <div>
          <Text strong style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>题目:</Text>
          <Paragraph style={{ marginTop: 8, fontSize: 'clamp(14px, 2vw, 16px)' }}>
            {question.content}
          </Paragraph>
        </div>

        {/* User's Answer */}
        <div>
          <Text strong style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>您的答案:</Text>
          <Paragraph style={{ marginTop: 8, fontSize: 'clamp(14px, 2vw, 16px)' }}>
            {question.type === 'short_answer' ? (
              <img
                src={userAnswer}
                alt="用户答案"
                style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 4 }}
              />
            ) : (
              <Text>{userAnswer}</Text>
            )}
          </Paragraph>
        </div>

        {/* Correct Answer (for incorrect responses) */}
        {!result.is_correct && question.correct_answer && (
          <div>
            <Text strong style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>正确答案:</Text>
            <Paragraph style={{ marginTop: 8, color: '#52c41a', fontSize: 'clamp(14px, 2vw, 16px)' }}>
              {question.correct_answer}
            </Paragraph>
          </div>
        )}

        {/* Error Type Badge (for incorrect answers) */}
        {!result.is_correct && result.error_type && (
          <div>
            <Tag color="red" style={{ fontSize: 'clamp(12px, 2vw, 14px)', padding: '6px 12px', minHeight: '32px' }}>
              错误类型: {result.error_type}
            </Tag>
          </div>
        )}

        {/* Detailed Explanation */}
        <Card
          size="small"
          style={{
            backgroundColor: result.is_correct ? '#f6ffed' : '#fff2f0',
            borderColor: result.is_correct ? '#b7eb8f' : '#ffccc7',
          }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text strong style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>反馈:</Text>
            <Paragraph style={{ marginBottom: 0, fontSize: 'clamp(14px, 2vw, 16px)' }}>
              {result.feedback}
            </Paragraph>

            {/* Detailed Analysis */}
            {result.analysis && (
              <>
                <Text strong style={{ marginTop: 12, display: 'block', fontSize: 'clamp(14px, 2vw, 16px)' }}>
                  详细分析:
                </Text>
                <Paragraph style={{ marginBottom: 0, fontSize: 'clamp(14px, 2vw, 16px)' }}>
                  {result.analysis}
                </Paragraph>
              </>
            )}
          </Space>
        </Card>
      </Space>
    </Card>
  );
});

ResultCard.displayName = 'ResultCard';

export default ResultCard;
