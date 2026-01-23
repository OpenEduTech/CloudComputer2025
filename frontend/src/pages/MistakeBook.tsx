import React, { useEffect, useState } from 'react';
import {
  Typography,
  Card,
  Space,
  Alert,
  Empty,
  Collapse,
  Tag,
  Statistic,
  Row,
  Col,
  Divider,
  Button,
  message as antMessage,
} from 'antd';
import {
  BookOutlined,
  TrophyOutlined,
  BulbOutlined,
  WarningOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { getMistakeAnalysis, refreshMistakeAnalysis } from '../api/analysis';
import { MistakeBookSkeleton } from '../components/SkeletonLoader';
import type { MistakeAnalysis } from '../types/analysis';
import ResultCard from '../components/ResultCard';

const { Title, Paragraph, Text } = Typography;

/**
 * Mistake Book page
 * Displays user's incorrect answers with analysis and recommendations
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
 */
export const MistakeBook: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mistakeData, setMistakeData] = useState<MistakeAnalysis | null>(null);

  useEffect(() => {
    fetchMistakeAnalysis();
  }, []);

  const fetchMistakeAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getMistakeAnalysis();
      setMistakeData(data);
    } catch (err: any) {
      // Display user-friendly error message (already processed by API client interceptor)
      setError(err.message || '加载错题分析失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    try {
      antMessage.loading({ content: '正在刷新分析...', key: 'refresh', duration: 0 });
      const data = await refreshMistakeAnalysis();
      setMistakeData(data);
      antMessage.success({ content: '分析已刷新！', key: 'refresh' });
    } catch (err: any) {
      antMessage.error({ content: err.message || '刷新失败', key: 'refresh' });
    }
  };

  // Loading state with skeleton
  if (loading) {
    return <MistakeBookSkeleton />;
  }

  // Error state
  if (error) {
    return (
      <Alert
        message="加载错题失败"
        description={error}
        type="error"
        showIcon
        style={{ margin: '20px 0' }}
      />
    );
  }

  // Empty state - no mistakes (Requirements: 7.5)
  if (
    !mistakeData ||
    !mistakeData.recent_mistakes ||
    !mistakeData.weak_points ||
    (mistakeData.recent_mistakes.length === 0 &&
      mistakeData.weak_points.length === 0)
  ) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" size="large">
              <TrophyOutlined style={{ fontSize: 64, color: '#52c41a' }} />
              <Title level={3}>太棒了！</Title>
              <Paragraph style={{ fontSize: 16, color: '#666' }}>
                您还没有错题。继续保持！
              </Paragraph>
              <Paragraph style={{ fontSize: 14, color: '#999' }}>
                完成一些测验后，您可以在这里查看进度和需要改进的地方
              </Paragraph>
            </Space>
          }
        />
      </div>
    );
  }

  // Sort mistakes by recency (most recent first) - Requirements: 7.6
  // Backend returns mistakes already sorted by recency, so we use them as-is
  const sortedMistakes = mistakeData.recent_mistakes || [];

  // Group mistakes by error type - Requirements: 7.3
  const mistakesByErrorType = sortedMistakes.reduce((acc, mistake) => {
    const errorType = mistake.result.error_type || 'Other';
    if (!acc[errorType]) {
      acc[errorType] = [];
    }
    acc[errorType].push(mistake);
    return acc;
  }, {} as Record<string, typeof sortedMistakes>);

  // Group mistakes by knowledge point - Requirements: 7.3
  const mistakesByKnowledgePoint = sortedMistakes.reduce((acc, mistake) => {
    const knowledgePoint = mistake.question.knowledge_point || 'General';
    if (!acc[knowledgePoint]) {
      acc[knowledgePoint] = [];
    }
    acc[knowledgePoint].push(mistake);
    return acc;
  }, {} as Record<string, typeof sortedMistakes>);

  return (
    <div style={{ padding: '12px' }} className="fade-in">
      {/* Page Header */}
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2} style={{ fontSize: 'clamp(20px, 5vw, 30px)' }}>
              <BookOutlined /> 错题本
            </Title>
            <Paragraph style={{ fontSize: 'clamp(14px, 2vw, 16px)', color: '#666' }}>
              回顾您的错题并从中学习，提高您的理解能力
            </Paragraph>
          </div>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={handleRefresh}
            style={{ marginTop: 8 }}
          >
            刷新分析
          </Button>
        </div>

        {/* Weak Points Summary - Requirements: 7.1, 7.2 */}
        {mistakeData.weak_points && mistakeData.weak_points.length > 0 && (
          <Card
            title={
              <Space>
                <WarningOutlined style={{ color: '#ff4d4f' }} />
                <Text strong>薄弱知识点总结</Text>
              </Space>
            }
            style={{ backgroundColor: '#fff7e6', borderColor: '#ffa940' }}
          >
            <Row gutter={[16, 16]}>
              {mistakeData.weak_points.map((weakPoint, index) => (
                <Col xs={24} sm={12} md={8} key={index}>
                  <Card size="small" style={{ height: '100%' }}>
                    <Statistic
                      title={weakPoint.knowledge_point}
                      value={weakPoint.error_count}
                      suffix="个错误"
                      valueStyle={{ color: '#ff4d4f' }}
                    />
                    <Space wrap style={{ marginTop: 12 }}>
                      {weakPoint.error_types.map((errorType, idx) => (
                        <Tag color="red" key={idx}>
                          {errorType}
                        </Tag>
                      ))}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        )}

        {/* Personalized Recommendations - Requirements: 7.2, 7.4 */}
        {mistakeData.recommendations && mistakeData.recommendations.length > 0 && (
          <Card
            title={
              <Space>
                <BulbOutlined style={{ color: '#1890ff' }} />
                <Text strong>个性化建议</Text>
              </Space>
            }
            style={{ backgroundColor: '#e6f7ff', borderColor: '#91d5ff' }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {mistakeData.recommendations.map((recommendation, index) => (
                <Paragraph key={index} style={{ marginBottom: 8, fontSize: 'clamp(14px, 2vw, 16px)' }}>
                  <Text strong>{index + 1}.</Text> {recommendation}
                </Paragraph>
              ))}
            </Space>
          </Card>
        )}

        <Divider />

        {/* Mistakes Grouped by Error Type - Requirements: 7.3, 7.4 */}
        <div>
          <Title level={3} style={{ fontSize: 'clamp(18px, 4vw, 24px)' }}>
            按错误类型分类
          </Title>
          <Collapse 
            defaultActiveKey={[Object.keys(mistakesByErrorType)[0]]}
            items={Object.entries(mistakesByErrorType).map(([errorType, mistakes]) => ({
              key: errorType,
              label: (
                <Space>
                  <Tag color="red">{errorType}</Tag>
                  <Text>{mistakes.length} 个错误</Text>
                </Space>
              ),
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {mistakes.map((mistake, index) => (
                    <ResultCard
                      key={`${errorType}-${index}`}
                      question={mistake.question}
                      questionNumber={index + 1}
                      userAnswer={mistake.user_answer}
                      result={mistake.result}
                    />
                  ))}
                </Space>
              )
            }))}
          />
        </div>

        <Divider />

        {/* Mistakes Grouped by Knowledge Point - Requirements: 7.3, 7.4 */}
        <div>
          <Title level={3} style={{ fontSize: 'clamp(18px, 4vw, 24px)' }}>
            按知识点分类
          </Title>
          <Collapse
            items={Object.entries(mistakesByKnowledgePoint).map(
              ([knowledgePoint, mistakes]) => ({
                key: knowledgePoint,
                label: (
                  <Space>
                    <Tag color="blue">{knowledgePoint}</Tag>
                    <Text>{mistakes.length} 个错误</Text>
                  </Space>
                ),
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {mistakes.map((mistake, index) => (
                      <ResultCard
                        key={`${knowledgePoint}-${index}`}
                        question={mistake.question}
                        questionNumber={index + 1}
                        userAnswer={mistake.user_answer}
                        result={mistake.result}
                      />
                    ))}
                  </Space>
                )
              })
            )}
          />
        </div>
      </Space>
    </div>
  );
};
