import React from 'react';
import { Steps, Card, Typography, theme } from 'antd';
import { 
  CloudUploadOutlined, 
  RobotOutlined, 
  ReadOutlined, 
  NodeIndexOutlined, 
  CheckCircleOutlined,
  LoadingOutlined 
} from '@ant-design/icons';
import { motion } from 'framer-motion';

const { Title, Text } = Typography;

const AgentStatus = ({ statusData }) => {
  const { token } = theme.useToken();
  
  // Default to initial state if no data provided
  const { step_index = 0, message = "Initializing..." } = statusData || {};

  const steps = [
    {
      title: '任务分发',
      description: '任务已发送至 Redis 队列...',
      icon: <CloudUploadOutlined />,
    },
    {
      title: 'Agent 接单',
      description: 'AI Worker (Agent) 已接单...',
      icon: <RobotOutlined />,
    },
    {
      title: '知识检索',
      description: '正在检索 ArXiv 和教科书...',
      icon: <ReadOutlined />,
    },
    {
      title: '信息抽取',
      description: '正在提取实体与关系...',
      icon: <NodeIndexOutlined />,
    },
    {
      title: '图谱构建',
      description: '图谱构建完成，正在渲染...',
      icon: <CheckCircleOutlined />,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10,
        pointerEvents: 'none', // Allow clicking through background if needed, but Card intercepts
      }}
    >
      <Card
        style={{
          width: '100%',
          maxWidth: 500,
          boxShadow: '0 12px 48px rgba(0, 0, 0, 0.15)',
          backdropFilter: 'blur(12px)',
          background: 'rgba(255, 255, 255, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.6)',
          borderRadius: '24px',
          pointerEvents: 'auto', // Re-enable pointer events for the card
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={4} style={{ color: token.colorPrimary }}>
             AutoKGS 智能构建中
          </Title>
          <Text type="secondary">{message}</Text>
        </div>
        
        <Steps
          current={step_index}
          direction="vertical"
          items={steps.map((step, index) => ({
            ...step,
            icon: index === step_index ? <LoadingOutlined /> : step.icon,
            status: index < step_index ? 'finish' : index === step_index ? 'process' : 'wait',
          }))}
        />
      </Card>
    </motion.div>
  );
};

export default AgentStatus;
