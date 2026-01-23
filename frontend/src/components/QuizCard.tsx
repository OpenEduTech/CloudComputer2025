import React, { memo } from 'react';
import { Card, Radio, Upload, Badge, Typography, Space } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, UploadOutlined } from '@ant-design/icons';
import type { Question } from '../types/quiz';
import type { GradingResult } from '../types/result';
import type { UploadFile } from 'antd';

const { Text, Paragraph } = Typography;

interface QuizCardProps {
  question: Question;
  questionNumber: number;
  answer: string | null;
  onAnswerChange: (questionId: string, answer: string) => void;
  disabled?: boolean;
  showResult?: boolean;
  result?: GradingResult;
}

/**
 * QuizCard component - Memoized for performance optimization
 * Only re-renders when props actually change
 */
const QuizCard: React.FC<QuizCardProps> = memo(({
  question,
  questionNumber,
  answer,
  onAnswerChange,
  disabled = false,
  showResult = false,
  result,
}) => {
  const [fileList, setFileList] = React.useState<UploadFile[]>([]);

  // Determine card styling based on result
  const getCardStyle = () => {
    if (!showResult || !result) return {};
    return {
      borderColor: result.is_correct ? '#52c41a' : '#ff4d4f',
      borderWidth: 2,
    };
  };

  // Handle multiple choice answer change
  const handleRadioChange = (e: any) => {
    onAnswerChange(question.id, e.target.value);
  };

  // Handle image upload for short answer
  const handleUploadChange = (info: any) => {
    let newFileList = [...info.fileList];
    // Limit to 1 file
    newFileList = newFileList.slice(-1);
    setFileList(newFileList);

    // When upload is done, update answer with the base64 data
    if (info.file.status === 'done' && info.file.response?.base64) {
      onAnswerChange(question.id, info.file.response.base64);
    }
  };

  // Convert image to base64
  const customRequest = (options: any) => {
    const { onSuccess, onError, file } = options;
    
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      onSuccess({ base64 });
    };
    reader.onerror = (error) => {
      onError(error);
    };
    reader.readAsDataURL(file);
  };

  return (
    <Card
      style={{ marginBottom: 16, ...getCardStyle() }}
      title={
        <Space>
          <Text strong>题目 {questionNumber}</Text>
          {showResult && result && (
            result.is_correct ? (
              <Badge
                count={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                style={{ backgroundColor: '#f6ffed' }}
              />
            ) : (
              <Badge
                count={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                style={{ backgroundColor: '#fff2f0' }}
              />
            )
          )}
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Question Text */}
        <Paragraph style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>
          {question.content}
        </Paragraph>

        {/* Answer Input */}
        {question.type === 'multiple_choice' && question.options ? (
          <Radio.Group
            onChange={handleRadioChange}
            value={answer}
            disabled={disabled}
            style={{ width: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {question.options.map((option, index) => (
                <Radio
                  key={index}
                  value={option}
                  style={{
                    display: 'block',
                    padding: '12px 0',
                    minHeight: '44px',
                    alignItems: 'center',
                  }}
                >
                  <span style={{ fontSize: 'clamp(14px, 2vw, 16px)' }}>{option}</span>
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        ) : (
          <Upload
            customRequest={customRequest}
            fileList={fileList}
            onChange={handleUploadChange}
            disabled={disabled}
            accept="image/*"
            maxCount={1}
          >
            <button
              type="button"
              style={{
                padding: '12px 16px',
                minHeight: '44px',
                minWidth: '160px',
                border: '1px solid #d9d9d9',
                borderRadius: '6px',
                background: disabled ? '#f5f5f5' : '#fff',
                cursor: disabled ? 'not-allowed' : 'pointer',
                fontSize: 'clamp(14px, 2vw, 16px)',
              }}
              disabled={disabled}
            >
              <UploadOutlined /> 上传答案图片
            </button>
          </Upload>
        )}

        {/* Result Display */}
        {showResult && result && (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {/* Error Type Badge */}
            {!result.is_correct && result.error_type && (
              <Badge
                color={result.is_correct ? 'green' : 'red'}
                text={
                  <Text type={result.is_correct ? 'success' : 'danger'}>
                    错误类型: {result.error_type}
                  </Text>
                }
              />
            )}

            {/* Explanation */}
            <Card
              size="small"
              style={{
                backgroundColor: result.is_correct ? '#f6ffed' : '#fff2f0',
                borderColor: result.is_correct ? '#b7eb8f' : '#ffccc7',
              }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>解析:</Text>
                <Paragraph style={{ marginBottom: 0 }}>
                  {result.explanation || result.analysis || result.feedback}
                </Paragraph>

                {/* Personalized Feedback */}
                {result.personalized_feedback && (
                  <>
                    <Text strong>个性化反馈:</Text>
                    <Paragraph style={{ marginBottom: 0 }}>
                      {result.personalized_feedback}
                    </Paragraph>
                  </>
                )}
              </Space>
            </Card>
          </Space>
        )}
      </Space>
    </Card>
  );
});

QuizCard.displayName = 'QuizCard';

export default QuizCard;
