import React, { useState, useRef, useCallback, useEffect } from 'react';
import { 
  Layout, 
  Input, 
  Drawer, 
  ConfigProvider, 
  theme, 
  Typography, 
  Tag, 
  Progress, 
  Button, 
  Space, 
  Card,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  SearchOutlined, 
  BookOutlined, 
  FileTextOutlined, 
  LinkOutlined, 
  ShareAltOutlined,
  ExperimentOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { motion, AnimatePresence } from 'framer-motion';

// Custom Hooks & Data
import useGraphOption from './useGraphOption';
import { mockGraphData } from './mockGraphData';
import AgentStatus from './components/AgentStatus';

const { Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

function App() {
  // --- State ---
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false); // Used to toggle between intro and graph
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  
  // Simulation State
  const [taskStatus, setTaskStatus] = useState({
    status: 'IDLE',
    step_index: 0,
    progress: 0,
    message: ''
  });

  // --- Theme ---
  const { token } = theme.useToken();
  const echartsRef = useRef(null);
  
  // Custom ECharts Option
  const option = useGraphOption(graphData, token);

  // --- Handlers ---
  const handleSearch = (value) => {
    if (!value) return;
    setSearchValue(value);
    setIsSearching(true);
    setHasSearched(true);
    setGraphData(null); // Clear previous data
    setSelectedNode(null);
    setDrawerVisible(false);

    // Start Simulation of Backend Polling
    simulateBackendProcessing();
  };

  const simulateBackendProcessing = () => {
    // Defines the sequence of status updates from "Backend"
    const sequence = [
      { status: 'PROCESSING', step_index: 0, progress: 5, message: '任务已发送至 Redis 队列...' },
      { status: 'PROCESSING', step_index: 1, progress: 20, message: 'AI Worker (Agent) 已接单...' },
      { status: 'PROCESSING', step_index: 2, progress: 45, message: '正在检索 ArXiv 和教科书...' },
      { status: 'PROCESSING', step_index: 3, progress: 70, message: '正在提取实体与关系...' },
      { status: 'PROCESSING', step_index: 4, progress: 90, message: '图谱构建完成，正在渲染...' },
      { status: 'SUCCESS', step_index: 5, progress: 100, message: 'Completed' }
    ];

    let currentIndex = 0;

    const interval = setInterval(() => {
      if (currentIndex >= sequence.length) {
        clearInterval(interval);
        return;
      }

      const statusUpdate = sequence[currentIndex];
      setTaskStatus(statusUpdate);

      if (statusUpdate.status === 'SUCCESS') {
        handleAgentComplete();
        clearInterval(interval);
      }

      currentIndex++;
    }, 1500); // Update every 1.5s to simulate work
  };

  const handleAgentComplete = () => {
    setIsSearching(false);
    // In a real app, we would fetch data here.
    // For now, load mock data.
    setGraphData(mockGraphData);
  };

  const onChartClick = useCallback((params) => {
    if (params.dataType === 'node') {
      setSelectedNode(params.data);
      setDrawerVisible(true);
    }
  }, []);

  const onEvents = {
    'click': onChartClick
  };

  // --- Render Helpers ---
  const renderDrawerContent = () => {
    if (!selectedNode) return null;

    const isPaper = selectedNode.source_type === 'paper';
    const confidenceScore = (selectedNode.confidence * 100).toFixed(0);
    const confidenceColor = confidenceScore >= 90 ? '#52c41a' : confidenceScore >= 80 ? '#faad14' : '#f5222d';

    return (
      <div style={{ paddingBottom: 20 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Header Section */}
          <div>
             <Tag color="geekblue" style={{ marginBottom: 8 }}>
                {selectedNode.group || 'Unknown Group'}
             </Tag>
             <Title level={2} style={{ margin: 0 }}>{selectedNode.label}</Title>
          </div>

          {/* Confidence Meter */}
          <Card size="small" style={{ background: '#f8f9fa' }}>
             <Row align="middle" gutter={16}>
               <Col span={8}>
                 <Statistic 
                   title="Confidence Score" 
                   value={confidenceScore} 
                   suffix="%" 
                   valueStyle={{ color: confidenceColor }}
                   prefix={<ThunderboltOutlined />}
                 />
               </Col>
               <Col span={16}>
                 <Progress 
                    percent={confidenceScore} 
                    strokeColor={confidenceColor} 
                    showInfo={false} 
                    strokeWidth={10}
                  />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Based on citation analysis and entity extraction confidence.
                  </Text>
               </Col>
             </Row>
          </Card>

          {/* Source Card */}
          <Card 
            title={<Space><BookOutlined /> Source Origin</Space>} 
            extra={isPaper && selectedNode.url && <Button type="link" size="small" href={selectedNode.url} target="_blank" icon={<LinkOutlined />}>View ArXiv</Button>}
          >
             <Space align="start">
                <div style={{ 
                    width: 40, height: 40, 
                    borderRadius: '50%', 
                    background: isPaper ? '#e6f7ff' : '#f6ffed',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: isPaper ? '#1890ff' : '#52c41a',
                    fontSize: 20
                }}>
                   {isPaper ? <FileTextOutlined /> : <BookOutlined />}
                </div>
                <div>
                   <Text strong style={{ display: 'block', fontSize: 16 }}>{selectedNode.source}</Text>
                   <Tag color={isPaper ? 'blue' : 'green'}>{selectedNode.source_type.toUpperCase()}</Tag>
                </div>
             </Space>
          </Card>

          {/* Abstract / Info */}
          <div>
            <Title level={5}>Description</Title>
            <Paragraph style={{ color: '#555', lineHeight: 1.8 }}>
              {selectedNode.info}
            </Paragraph>
          </div>

          {/* Related Actions */}
          <Space>
             <Button icon={<ShareAltOutlined />}>Share Node</Button>
             <Button icon={<ExperimentOutlined />}>Explore Related</Button>
          </Space>
        </Space>
      </div>
    );
  };

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1677ff',
          fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        },
        components: {
          Layout: {
            headerBg: 'rgba(255, 255, 255, 0.8)',
          }
        }
      }}
    >
      <Layout style={{ height: '100vh', overflow: 'hidden' }}>
        {/* --- Header --- */}
        <Header 
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            backdropFilter: 'blur(10px)',
            borderBottom: '1px solid rgba(0,0,0,0.05)',
            zIndex: 100,
            padding: '0 24px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ 
              width: 32, height: 32, background: 'linear-gradient(135deg, #1890ff 0%, #001529 100%)', 
              borderRadius: 6, marginRight: 12 
            }} />
            <Title level={4} style={{ margin: 0, letterSpacing: -0.5 }}>AutoKGS</Title>
          </div>

          <div style={{ flex: 1, maxWidth: 600, margin: '0 24px' }}>
            <Search 
              placeholder="输入科学概念开启探索，例如：Transformer Architecture..." 
              allowClear 
              enterButton="Generate Graph" 
              size="large"
              onSearch={handleSearch}
              disabled={isSearching}
              style={{
                boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                borderRadius: 8
              }}
            />
          </div>

          <Space>
             <Button type="text" icon={<LinkOutlined />}>Docs</Button>
             <Button type="primary" ghost>Login</Button>
          </Space>
        </Header>

        {/* --- Main Content --- */}
        <Content style={{ position: 'relative', background: '#f0f2f5' }}>
          
          {/* 1. Intro State */}
          {!hasSearched && !isSearching && (
            <div style={{ 
              position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
              textAlign: 'center', opacity: 0.6 
            }}>
               <ExperimentOutlined style={{ fontSize: 64, color: '#ccc', marginBottom: 24 }} />
               <Title level={3} style={{ color: '#999' }}>Start your scientific discovery</Title>
               <Text type="secondary">Enter a keyword above to generate a knowledge graph</Text>
            </div>
          )}

          {/* 2. Loading State */}
          <AnimatePresence>
            {isSearching && (
               <AgentStatus statusData={taskStatus} />
            )}
          </AnimatePresence>

          {/* 3. Graph Canvas */}
          {graphData && (
             <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8 }}
                style={{ height: '100%', width: '100%' }}
             >
                <ReactECharts 
                  ref={echartsRef}
                  option={option} 
                  style={{ height: '100%', width: '100%' }}
                  onEvents={onEvents}
                  notMerge={true}
                  lazyUpdate={true}
                />
             </motion.div>
          )}

          {/* --- Detail Drawer --- */}
          <Drawer
            title={null}
            placement="right"
            closable={true}
            onClose={() => setDrawerVisible(false)}
            open={drawerVisible}
            width={480}
            mask={false}
            style={{ 
              boxShadow: '-4px 0 24px rgba(0,0,0,0.1)',
            }}
            styles={{
                header: { borderBottom: 'none' },
                body: { padding: '24px 32px' }
            }}
          >
            {renderDrawerContent()}
          </Drawer>

        </Content>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
