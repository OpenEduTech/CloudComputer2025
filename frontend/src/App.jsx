import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
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
  Statistic,
  message,
  Select, 
  Radio, // Import Radio
  Divider,
  Slider,
  Modal,
  List,
  Empty
} from 'antd';
import { 
  BookOutlined, 
  FileTextOutlined, 
  LinkOutlined, 
  ShareAltOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  ApartmentOutlined, // For Mind Map icon
  DeploymentUnitOutlined, // For Graph icon
  HistoryOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { motion, AnimatePresence } from 'framer-motion';

// Custom Hooks & Components
import useGraphOption from './useGraphOption';
import useMindMapOption from './useMindMapOption';
import AgentStatus from './components/AgentStatus';
import { createTask, getTaskStatus, getGraphData } from './api';

const { Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { Search } = Input;
const HISTORY_STORAGE_KEY = 'autokgs_search_history';

function App() {
  // --- State ---
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [searchDepth, setSearchDepth] = useState(2); // Default depth
  const [viewMode, setViewMode] = useState('graph'); // 'graph' or 'mindmap'
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [graphLayer, setGraphLayer] = useState('main');
  const [mainConfidenceMin, setMainConfidenceMin] = useState(70);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);
  
  // Simulation State
  const [taskStatus, setTaskStatus] = useState({
    status: 'IDLE',
    step_index: 0,
    progress: 0,
    message: ''
  });

  const pollingTimerRef = useRef(null);
  const searchDepthRef = useRef(searchDepth);

  // --- Theme ---
  const { token } = theme.useToken();
  const echartsRef = useRef(null);
  
  const getNodeConfidence = useCallback((node) => {
    return typeof node?.confidence === 'number' ? node.confidence : 0.6;
  }, []);

  const layeredGraphData = useMemo(() => {
    if (!graphData) return null;
    if (graphLayer === 'explore') return graphData;

    const threshold = mainConfidenceMin / 100;
    const nodeMap = new Map(graphData.nodes.map(node => [node.id, node]));
    const links = graphData.links.filter(link => {
      const sourceNode = nodeMap.get(link.source);
      const targetNode = nodeMap.get(link.target);
      const sourceConfidence = getNodeConfidence(sourceNode);
      const targetConfidence = getNodeConfidence(targetNode);
      return Math.min(sourceConfidence, targetConfidence) >= threshold;
    });

    const nodeIdSet = new Set();
    links.forEach(link => {
      nodeIdSet.add(link.source);
      nodeIdSet.add(link.target);
    });

    let nodes = graphData.nodes.filter(node => nodeIdSet.has(node.id));
    if (nodes.length === 0) {
      nodes = graphData.nodes.filter(node => getNodeConfidence(node) >= threshold);
    }
    return { nodes, links };
  }, [graphData, graphLayer, mainConfidenceMin, getNodeConfidence]);

  // Custom ECharts Option
  const graphOption = useGraphOption(layeredGraphData, token);
  const mindMapOption = useMindMapOption(layeredGraphData, searchValue);

  const option = useMemo(() => {
      return viewMode === 'mindmap' ? mindMapOption : graphOption;
  }, [viewMode, graphOption, mindMapOption]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          setSearchHistory(parsed);
        }
      }
    } catch (error) {
      console.warn('Failed to load search history:', error);
    }
  }, []);

  const persistHistory = useCallback((entries) => {
    setSearchHistory(entries);
    try {
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(entries));
    } catch (error) {
      console.warn('Failed to save search history:', error);
    }
  }, []);

  // --- Handlers ---
  const handleSearch = async (value, depthOverride) => {
    if (!value) return;
    const depthUsed = typeof depthOverride === 'number' ? depthOverride : searchDepthRef.current;
    if (typeof depthOverride === 'number') {
      setSearchDepth(depthUsed);
      searchDepthRef.current = depthUsed;
    }
    setSearchValue(value);
    setIsSearching(true);
    setHasSearched(true);
    setGraphData(null); 
    setSelectedNode(null);
    setSelectedEdge(null);
    setDrawerVisible(false);
    setGraphLayer('main');
    setMainConfidenceMin(70);

    try {
        // 1. Send Task Creation Request
        const { task_id } = await createTask(value, { depth: depthUsed });
        console.log(`Task created with ID: ${task_id}`);

        const newEntry = { keyword: value, depth: depthUsed, time: Date.now() };
        const nextHistory = [newEntry, ...searchHistory.filter(entry => !(entry.keyword === value && entry.depth === depthUsed))].slice(0, 20);
        persistHistory(nextHistory);

        // 2. Start Polling
        startPolling(task_id);

    } catch (error) {
        console.error("Search failed:", error);
        message.error("Failed to start search task. Please check backend connection.");
        setIsSearching(false);
    }
  };

  const startPolling = (taskId) => {
    if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);

    pollingTimerRef.current = setInterval(async () => {
        try {
            const statusData = await getTaskStatus(taskId);
            setTaskStatus(statusData);

            if (statusData.status === 'SUCCESS') {
                clearInterval(pollingTimerRef.current);
                fetchGraph(statusData.result_node_id || searchValue);
            } else if (statusData.status === 'FAILED') {
                clearInterval(pollingTimerRef.current);
                setIsSearching(false);
                message.error(statusData.error || "Task processing failed.");
            }
        } catch (error) {
            console.error("Polling error:", error);
        }
    }, 1000);
  };

  // Cleanup on unmount
  useEffect(() => {
      return () => {
          if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
      };
  }, []);

  const fetchGraph = async (nodeId) => {
    try {
        const data = await getGraphData(nodeId, searchDepthRef.current);
        
        if (data.nodes && data.nodes.length > 0) {
            setGraphData(data);
            setGraphLayer('main');
            setMainConfidenceMin(70);
        } else {
            message.warning("No graph data found for this concept.");
        }
    } catch (error) {
        console.error("Failed to fetch graph:", error);
        message.error("Failed to load knowledge graph.");
    } finally {
        setIsSearching(false);
    }
  };

  const handleExportJson = () => {
    if (!layeredGraphData) return;
    const filename = `autokgs_${searchValue || 'graph'}.json`;
    const blob = new Blob([JSON.stringify(layeredGraphData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleUseHistory = (entry) => {
    setHistoryVisible(false);
    handleSearch(entry.keyword, entry.depth);
  };

  const handleClearHistory = () => {
    persistHistory([]);
  };

  const onChartClick = useCallback((params) => {
    if (params.dataType === 'node') {
      const node = params.data;
      
      if (node.url && node.url.startsWith('http')) {
        window.open(node.url, '_blank', 'noopener,noreferrer');
      } else {
        setSelectedNode(node);
        setSelectedEdge(null);
        setDrawerVisible(true);
      }
    } else if (params.dataType === 'edge') {
      setSelectedEdge(params.data);
      setSelectedNode(null);
      setDrawerVisible(true);
    }
  }, []);

  const onEvents = {
    'click': onChartClick
  };

  // --- Render Helpers ---
  const renderDrawerContent = () => {
    if (!selectedNode && !selectedEdge) return null;

    if (selectedEdge) {
      const hasCitation = Boolean(selectedEdge.citation);
      return (
        <div style={{ paddingBottom: 20 }}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Tag color={hasCitation ? 'orange' : 'default'} style={{ marginBottom: 8 }}>
                {hasCitation ? 'Evidence-Backed' : 'No Citation'}
              </Tag>
              <Title level={4} style={{ margin: 0 }}>
                {selectedEdge.source} → {selectedEdge.target}
              </Title>
              <Text type="secondary">{selectedEdge.relation}</Text>
            </div>

            <Card size="small" style={{ background: '#f8f9fa' }}>
              <Text strong style={{ display: 'block', marginBottom: 6 }}>Relation Description</Text>
              <Text style={{ color: '#555' }}>
                {selectedEdge.desc || 'No description available.'}
              </Text>
            </Card>

            <Card
              size="small"
              title={<Space><FileTextOutlined /> Citation</Space>}
            >
              <Text style={{ color: hasCitation ? '#333' : '#999' }}>
                {selectedEdge.citation || 'No citation provided.'}
              </Text>
            </Card>
          </Space>
        </div>
      );
    }

    const isPaper = selectedNode.source_type === 'paper';
    const confidenceValue = typeof selectedNode.confidence === 'number' ? selectedNode.confidence : 0.6;
    const confidenceScore = (confidenceValue * 100).toFixed(0);
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

          <div style={{ flex: 1, maxWidth: 800, margin: '0 24px', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <Radio.Group 
                value={viewMode} 
                onChange={(e) => setViewMode(e.target.value)}
                buttonStyle="solid"
                disabled={isSearching}
            >
                <Radio.Button value="graph"><DeploymentUnitOutlined /> Graph</Radio.Button>
                <Radio.Button value="mindmap"><ApartmentOutlined /> Mind Map</Radio.Button>
            </Radio.Group>

             <Select
                defaultValue={2}
                style={{ width: 120 }}
                onChange={(value) => {
                  setSearchDepth(value);
                  searchDepthRef.current = value;
                }}
                disabled={isSearching}
                options={[
                  { value: 1, label: 'Depth: 1' },
                  { value: 2, label: 'Depth: 2' },
                  { value: 3, label: 'Depth: 3' },
                  { value: 4, label: 'Depth: 4' },
                  { value: 5, label: 'Depth: 5' },
                ]}
              />
            <Search 
              placeholder="输入科学概念开启探索，例如：Transformer Architecture..." 
              allowClear 
              enterButton="Generate Graph" 
              size="large"
              onSearch={handleSearch}
              disabled={isSearching}
              style={{ flex: 1 }}
            />
          </div>

          <Space>
             <Button type="text" icon={<LinkOutlined />}>Docs</Button>
             <Button type="primary" ghost icon={<HistoryOutlined />} onClick={() => setHistoryVisible(true)}>
               History
             </Button>
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

          {/* Layer Panel */}
          {graphData && (
            <Card
              size="small"
              style={{
                position: 'absolute',
                top: 16,
                left: 16,
                width: 300,
                zIndex: 10,
                background: 'rgba(255,255,255,0.95)',
                boxShadow: '0 6px 18px rgba(0,0,0,0.08)'
              }}
            >
              <Title level={5} style={{ marginBottom: 8 }}>Graph Layer</Title>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div>
                  <Radio.Group
                    value={graphLayer}
                    onChange={(e) => setGraphLayer(e.target.value)}
                    buttonStyle="solid"
                    disabled={isSearching}
                  >
                    <Radio.Button value="main">Main</Radio.Button>
                    <Radio.Button value="explore">Explore</Radio.Button>
                  </Radio.Group>
                </div>

                {graphLayer === 'main' && (
                  <div>
                    <Text type="secondary">Main Confidence ≥ {mainConfidenceMin}%</Text>
                    <Slider
                      min={50}
                      max={95}
                      value={mainConfidenceMin}
                      onChange={setMainConfidenceMin}
                      disabled={isSearching}
                    />
                  </div>
                )}

                <Divider style={{ margin: '8px 0' }} />
                <Space>
                  <Button size="small" type="primary" onClick={handleExportJson}>
                    Export JSON
                  </Button>
                </Space>
              </Space>
            </Card>
          )}

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

          <Modal
            title="Search History"
            open={historyVisible}
            onCancel={() => setHistoryVisible(false)}
            footer={[
              <Button key="clear" onClick={handleClearHistory} disabled={searchHistory.length === 0}>
                Clear
              </Button>,
              <Button key="close" type="primary" onClick={() => setHistoryVisible(false)}>
                Close
              </Button>
            ]}
          >
            {searchHistory.length === 0 ? (
              <Empty description="No search history yet" />
            ) : (
              <List
                dataSource={searchHistory}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button type="link" key="use" onClick={() => handleUseHistory(item)}>
                        Use
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      title={`${item.keyword} (Depth: ${item.depth})`}
                      description={new Date(item.time).toLocaleString()}
                    />
                  </List.Item>
                )}
              />
            )}
          </Modal>

        </Content>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
