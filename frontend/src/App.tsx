import React, { useState, useCallback } from 'react';
import { Input, Button, Spin, message, Card, Tag, Space, Modal, Divider } from 'antd';
import { SearchOutlined, ReloadOutlined, FileTextOutlined } from '@ant-design/icons';
import GraphVisualization from './components/GraphVisualization';
import NodeDetailPanel from './components/NodeDetailPanel';
import { conceptAPI, ConceptNode, ConceptEdge, ArxivPaper } from './services/api';
import './App.css';

// 定义截断工具函数（前端最终保障，确保≤500字）
const truncateDefinition = (text: string, maxLength: number = 500): string => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
};

const App: React.FC = () => {
  const [concept, setConcept] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandLoading, setExpandLoading] = useState(false);
  const [nodes, setNodes] = useState<ConceptNode[]>([]);
  const [edges, setEdges] = useState<ConceptEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<ConceptNode | null>(null);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [searchArxivPapers, setSearchArxivPapers] = useState<ArxivPaper[]>([]);  // 搜索结果的相关论文
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [conceptDetail, setConceptDetail] = useState<{
    detailed_introduction: string;
    wiki_definition: string | null;
    wiki_url: string | null;
    related_papers: ArxivPaper[];
  } | null>(null);
  
  // 新增：功能模式选择
  const [searchMode, setSearchMode] = useState<'auto' | 'disciplined' | 'bridge'>('auto');
  const [disciplines, setDisciplines] = useState<string[]>([]);
  const [bridgeConcepts, setBridgeConcepts] = useState<string[]>(['', '']);
  const [bridgeAnalysis, setBridgeAnalysis] = useState<any>(null);  // 桥接路径分析数据

  const handleSearch = async () => {
    if (!concept.trim() && searchMode !== 'bridge') {
      message.warning('请输入概念名称');
      return;
    }
    
    if (searchMode === 'bridge') {
      const validConcepts = bridgeConcepts.filter(c => c.trim());
      if (validConcepts.length < 2) {
        message.warning('概念关联探索至少需要2个概念');
        return;
      }
    }
    
    setLoading(true);
    setSelectedNode(null);
    setExpandedNodes(new Set());
    
    try {
      let response;
      
      // 根据模式调用不同API
      if (searchMode === 'disciplined') {
        // 功能2：限定学科发现
        if (disciplines.length === 0) {
          message.warning('请至少选择一个学科');
          setLoading(false);
          return;
        }
        response = await conceptAPI.discoverDisciplined(concept, disciplines);
      } else if (searchMode === 'bridge') {
        // 功能3：桥接概念发现
        const validConcepts = bridgeConcepts.filter(c => c.trim());
        response = await conceptAPI.discoverBridge(validConcepts);
      } else {
        // 功能1：自动跨学科发现
        response = await conceptAPI.discover(concept);
      }
      
      if (response.status === 'success') {
        // 确保所有节点定义都被截断
        const processedNodes = response.data.nodes.map((node, index) => ({
          ...node,
          definition: truncateDefinition(node.definition, 500),
          // 对于bridge模式，保留后端返回的depth、is_input、is_bridge属性
          // 对于其他模式，第一个节点是根节点（depth=0），其他为1
          depth: searchMode === 'bridge' ? node.depth : (index === 0 ? 0 : 1)
        }));
        
        // 使用后端返回的边数据（包含LLM生成的reasoning）
        const processedEdges: ConceptEdge[] = response.data.edges || [];
        
        console.log('初始搜索 - 节点列表:', processedNodes.map(n => ({ id: n.id, label: n.label, depth: n.depth })));
        console.log('初始搜索 - 边列表:', processedEdges.map(e => ({ source: e.source, target: e.target, reasoning: e.reasoning })));
        
        setNodes(processedNodes);
        setEdges(processedEdges);
        
        // 保存桥接路径分析数据（仅bridge模式）
        if (searchMode === 'bridge' && response.data.metadata?.bridge_analysis) {
          setBridgeAnalysis(response.data.metadata.bridge_analysis);
        } else {
          setBridgeAnalysis(null);
        }
        
        // 保存arxiv论文信息
        if (response.data.metadata?.arxiv_papers) {
          setSearchArxivPapers(response.data.metadata.arxiv_papers);
        } else {
          setSearchArxivPapers([]);
        }
        
        message.success({
          content: `发现 ${processedNodes.length} 个相关概念，${processedEdges.length} 个关联关系`,
          duration: 3,
          icon: '🎉'
        });
        
        // 添加到搜索历史
        if (!searchHistory.includes(concept)) {
          setSearchHistory(prev => [concept, ...prev].slice(0, 5));
        }
      } else {
        message.error('概念挖掘失败');
      }
    } catch (error: any) {
      console.error('搜索失败:', error);
      if (error.response?.status === 504) {
        message.error('Agent服务超时，请稍后重试');
      } else if (error.response?.status === 500) {
        message.error('服务器错误，请检查Agent服务是否正常运行');
      } else {
        message.error('网络错误，请检查后端服务是否启动');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = useCallback((node: ConceptNode) => {
    // 确保显示的定义已截断
    setSelectedNode({
      ...node,
      definition: truncateDefinition(node.definition, 500)
    });
    console.log('点击节点:', node);
  }, []);

  // 展开节点 - 以当前节点为新的搜索词，重新discover
  const handleExpandNode = async () => {
    if (!selectedNode) return;
    
    // 检查是否已展开
    if (expandedNodes.has(selectedNode.id)) {
      message.info('该节点已展开过');
      return;
    }
    
    setExpandLoading(true);
    
    try {
      // 以当前节点为新的搜索词，重新discover
      console.log(`以 "${selectedNode.label}" 为新根节点进行搜索...`);
      const response = await conceptAPI.discover(selectedNode.label);
      
      if (response.status === 'success') {
        // 获取当前节点的深度
        const currentDepth = selectedNode.depth || 0;
        
        // 处理新节点，设置它们的深度为父节点+1
        const newNodes = response.data.nodes
          .map(node => ({
            ...node,
            definition: truncateDefinition(node.definition, 500),
            depth: currentDepth + 1,  // 设置子节点深度
            parentId: selectedNode.id  // 记录父节点
          }))
          .filter(newNode => 
            newNode.label !== selectedNode.label && // 排除同名节点（根据label判断）
            !nodes.some(existing => existing.label === newNode.label) // 排除已存在的同名节点
          );
        
        if (newNodes.length === 0) {
          message.info('没有发现新的相关概念');
          setExpandedNodes(prev => new Set([...prev, selectedNode.id]));
          return;
        }
        
        // 合并节点
        const allNodes = [...nodes, ...newNodes];
        
        // 处理边：将所有新节点连接到当前被展开的节点，形成树状结构
        // discover返回的第一个节点是新的中心节点，其他节点连接到它
        // 但我们需要将这些连接改为从selectNode出发
        const newEdges: ConceptEdge[] = newNodes.map(newNode => ({
          source: selectedNode.id,  // 从当前节点出发
          target: newNode.id,       // 连接到每个新节点
          relation: 'expanded_from',
          weight: 0.8,
          reasoning: `从 ${selectedNode.label} 展开发现`
        }));
        
        // 合并边
        const allEdges = [...edges, ...newEdges];
        
        console.log('展开节点 - 父节点:', { id: selectedNode.id, label: selectedNode.label, depth: selectedNode.depth });
        console.log('展开节点 - 新子节点:', newNodes.map(n => ({ id: n.id, label: n.label, depth: n.depth })));
        console.log('展开节点 - 新边:', newEdges.map(e => ({ source: e.source, target: e.target })));
        
        setNodes(allNodes);
        setEdges(allEdges);
        setExpandedNodes(prev => new Set([...prev, selectedNode.id]));
        
        message.success(`展开成功！发现 ${newNodes.length} 个新概念`);
      } else {
        message.error('展开失败');
      }
    } catch (error) {
      console.error('展开失败:', error);
      message.error('展开失败，请稍后重试');
    } finally {
      setExpandLoading(false);
    }
  };

  const handleReset = () => {
    setNodes([]);
    setEdges([]);
    setSelectedNode(null);
    setExpandedNodes(new Set());
    setSearchArxivPapers([]);
    setConceptDetail(null);
    setBridgeAnalysis(null);  // 清空桥接分析数据
    // 不重置搜索模式和输入框内容，只清空画布
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>ConceptGraph AI</h1>
        <p className="subtitle">跨学科知识图谱智能体</p>
      </header>

      <div className="search-section">
        {nodes.length > 0 && (
          <div style={{ 
            position: 'absolute', 
            top: '20px', 
            right: '20px',
            display: 'flex',
            gap: '12px',
            zIndex: 10
          }}>
            <Card 
              size="small" 
              style={{ 
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#667eea' }}>
                  {nodes.length}
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>概念节点</div>
              </div>
            </Card>
            <Card 
              size="small" 
              style={{ 
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#764ba2' }}>
                  {edges.length}
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>关联关系</div>
              </div>
            </Card>
            {searchArxivPapers.length > 0 && (
              <Card 
                size="small" 
                style={{ 
                  background: 'rgba(255, 255, 255, 0.95)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
                }}
              >
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#fa8c16' }}>
                    {searchArxivPapers.length}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>相关论文</div>
                </div>
              </Card>
            )}
          </div>
        )}
        
        {/* 功能模式选择 */}
        <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'center', gap: '12px' }}>
          <Button 
            type={searchMode === 'auto' ? 'primary' : 'default'}
            onClick={() => setSearchMode('auto')}
            style={{ borderRadius: '20px' }}
          >
            🔍 全学科搜索
          </Button>
          <Button 
            type={searchMode === 'disciplined' ? 'primary' : 'default'}
            onClick={() => setSearchMode('disciplined')}
            style={{ borderRadius: '20px' }}
          >
            🎯 指定学科搜索
          </Button>
          <Button 
            type={searchMode === 'bridge' ? 'primary' : 'default'}
            onClick={() => setSearchMode('bridge')}
            style={{ borderRadius: '20px' }}
          >
            🌉 概念关联探索
          </Button>
        </div>
        
        {/* 根据模式显示不同的输入 */}
        {searchMode === 'disciplined' && (
          <div style={{ marginBottom: '16px' }}>
            <Space wrap>
              <span style={{ color: '#666' }}>限定学科：</span>
              {['计算机科学', '物理学', '数学', '生物学', '心理学', '经济学', '社会学'].map(d => (
                <Tag.CheckableTag
                  key={d}
                  checked={disciplines.includes(d)}
                  onChange={(checked) => {
                    setDisciplines(checked 
                      ? [...disciplines, d] 
                      : disciplines.filter(x => x !== d)
                    );
                  }}
                >
                  {d}
                </Tag.CheckableTag>
              ))}
            </Space>
          </div>
        )}
        
        {searchMode === 'bridge' && (
          <div style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '600px', margin: '0 auto 16px' }}>
            {bridgeConcepts.map((c, idx) => (
              <Input
                key={idx}
                placeholder={`概念 ${idx + 1}`}
                value={c}
                onChange={(e) => {
                  const newConcepts = [...bridgeConcepts];
                  newConcepts[idx] = e.target.value;
                  setBridgeConcepts(newConcepts);
                }}
                size="large"
              />
            ))}
            <Button 
              onClick={() => setBridgeConcepts([...bridgeConcepts, ''])}
              style={{ alignSelf: 'flex-start' }}
            >
              + 添加概念
            </Button>
          </div>
        )}
        
        {searchMode !== 'bridge' && (
        <Space.Compact style={{ width: '100%', maxWidth: '600px' }}>
          <Input
            placeholder={
              searchMode === 'auto' 
                ? "输入概念（如：熵、神经网络、量子纠缠）"
                : "输入概念，将在限定学科中搜索"
            }
            value={concept}
            onChange={(e) => setConcept(e.target.value)}
            onPressEnter={handleSearch}
            size="large"
            disabled={loading}
          />
          <Button
            type="primary"
            size="large"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            loading={loading}
          >
            搜索
          </Button>
          <Button
            size="large"
            icon={<ReloadOutlined />}
            onClick={handleReset}
            disabled={loading}
          >
            重置
          </Button>
        </Space.Compact>
        )}
        
        {searchMode === 'bridge' && (
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <Button
            type="primary"
            size="large"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            loading={loading}
          >
            搜索概念间的关联
          </Button>
          <Button
            size="large"
            icon={<ReloadOutlined />}
            onClick={handleReset}
            disabled={loading}
          >
            重置
          </Button>
        </div>
        )}
        
        {searchHistory.length > 0 && nodes.length === 0 && (
          <div style={{ 
            marginTop: '20px',
            textAlign: 'center'
          }}>
            <div style={{ 
              color: 'white',
              fontSize: '14px',
              marginBottom: '10px',
              opacity: 0.9
            }}>
              搜索历史:
            </div>
            <Space wrap>
              {searchHistory.map((item, index) => (
                <Tag 
                  key={index}
                  color="purple"
                  style={{ 
                    cursor: 'pointer',
                    fontSize: '14px',
                    padding: '6px 12px',
                    borderRadius: '16px',
                    transition: 'all 0.3s ease'
                  }}
                  onClick={() => {
                    setConcept(item);
                    setTimeout(handleSearch, 100);
                  }}
                >
                  {item}
                </Tag>
              ))}
            </Space>
          </div>
        )}
      </div>

      {loading ? (
        <div className="loading-container">
          <Spin size="large" tip="正在挖掘跨学科关联...">
            <div style={{ padding: '50px', textAlign: 'center' }}></div>
          </Spin>
        </div>
      ) : nodes.length > 0 ? (
        <div className="content-section" style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
          <div className="graph-section" style={{ 
            flex: (bridgeAnalysis || selectedNode) ? '1 1 70%' : '1 1 100%',
            minHeight: 'auto'
          }}>
            <GraphVisualization
              nodes={nodes}
              edges={edges}
              onNodeClick={handleNodeClick}
            />
          </div>
          
          {/* 右侧面板：优先显示节点详情，无节点详情时显示桥接路径分析 */}
          {(selectedNode || bridgeAnalysis) && (
            <div style={{ 
              flex: '0 0 380px', 
              display: 'flex',
              flexDirection: 'column',
              height: '600px'
            }}>
              {/* 节点详情面板 - 优先级更高 */}
              {selectedNode ? (
                <NodeDetailPanel
                  selectedNode={selectedNode}
                  expandedNodes={expandedNodes}
                  expandLoading={expandLoading}
                  onClose={() => setSelectedNode(null)}
                  onExpand={handleExpandNode}
                />
              ) : (
                /* 桥接路径分析面板（仅在无节点选中时显示） */
                bridgeAnalysis && (
                  <Card 
                    style={{ 
                      background: 'rgba(255, 255, 255, 0.95)',
                      backdropFilter: 'blur(10px)',
                      borderRadius: '12px',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column'
                    }}
                    styles={{
                      body: {
                        overflowY: 'auto',
                        flex: 1,
                        padding: '16px'
                      }
                    }}
                    title={
                      <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#667eea' }}>
                        🌉 桥接路径分析
                      </div>
                    }
                  >
                    <div style={{ marginBottom: '12px' }}>
                      <strong>输入概念：</strong>
                      <div style={{ marginTop: '8px' }}>
                        {bridgeAnalysis.input_concepts.map((c: string, idx: number) => (
                          <span key={idx}>
                            <span style={{ 
                              padding: '4px 12px', 
                              background: '#e6f7ff', 
                              borderRadius: '4px',
                              margin: '4px',
                              color: '#1890ff',
                              display: 'inline-block'
                            }}>
                              {c}
                            </span>
                            {idx < bridgeAnalysis.input_concepts.length - 1 && (
                              <div style={{ textAlign: 'center', margin: '4px 0' }}>↕</div>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                    
                    <div style={{ marginBottom: '12px', padding: '8px', background: '#f0f0f0', borderRadius: '4px' }}>
                      <strong>桥接概念：</strong> {bridgeAnalysis.total_bridges} 个
                    </div>
                    
                    {Object.entries(bridgeAnalysis.bridges_by_type).map(([type, bridges]: [string, any]) => (
                      <div key={type} style={{ marginTop: '16px' }}>
                        <div style={{ 
                          fontWeight: 'bold', 
                          color: type === '直接桥梁' ? '#52c41a' : (type === '间接桥梁' ? '#faad14' : '#8c8c8c'),
                          marginBottom: '8px',
                          fontSize: '14px'
                        }}>
                          【{type}】({bridges.length}个)
                        </div>
                        {bridges.map((bridge: any, idx: number) => (
                          <div key={idx} style={{ 
                            marginLeft: '8px', 
                            marginBottom: '12px',
                            padding: '10px',
                            background: '#fafafa',
                            borderRadius: '6px',
                            borderLeft: '3px solid ' + (type === '直接桥梁' ? '#52c41a' : (type === '间接桥梁' ? '#faad14' : '#8c8c8c'))
                          }}>
                            <div style={{ fontWeight: 'bold', marginBottom: '6px', color: '#333' }}>
                              • {bridge.name}
                            </div>
                            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                              <strong>连接:</strong> {bridge.connected.join(' + ')}
                            </div>
                            <div style={{ fontSize: '12px', color: '#666', lineHeight: '1.5' }}>
                              <strong>原理:</strong> {bridge.principle}
                            </div>
                          </div>
                        ))}
                      </div>
                    ))}
                    
                    <div style={{ marginTop: '16px', padding: '10px', background: '#e6f7ff', borderRadius: '6px', fontSize: '13px' }}>
                      <strong>💡 总结：</strong> {bridgeAnalysis.summary}
                    </div>
                  </Card>
                )
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="empty-state">
          <div style={{ fontSize: '72px', marginBottom: '20px' }}>🧠</div>
          <p style={{ marginBottom: '12px', fontSize: '28px', fontWeight: '300' }}>
            输入概念开始探索知识图谱
          </p>
          <p style={{ fontSize: '16px', opacity: '0.8', fontWeight: '300' }}>
            例如：熵、神经网络、量子纠缠、黑洞、区块链
          </p>
        </div>
      )}

      {/* 概念详情弹窗 */}
      <Modal
        title={
          <span style={{ fontSize: '18px' }}>
            📚 {selectedNode?.label} - 详细概念介绍
          </span>
        }
        open={showDetailModal}
        onCancel={() => setShowDetailModal(false)}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        {conceptDetail && (
          <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
            {/* 维基百科定义 */}
            {conceptDetail.wiki_definition && (
              <div style={{ marginBottom: '24px' }}>
                <h3 style={{ color: '#667eea', marginBottom: '12px' }}>
                  📖 维基百科定义
                </h3>
                <Card size="small" style={{ background: '#f6f8fa' }}>
                  <p style={{ margin: 0, lineHeight: 1.8 }}>
                    {conceptDetail.wiki_definition}
                  </p>
                  {conceptDetail.wiki_url && (
                    <a 
                      href={conceptDetail.wiki_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      style={{ fontSize: '12px', marginTop: '8px', display: 'block' }}
                    >
                      🔗 查看维基百科原文
                    </a>
                  )}
                </Card>
              </div>
            )}
            
            <Divider />
            
            {/* 大模型生成的详细介绍 */}
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ color: '#764ba2', marginBottom: '12px' }}>
                🤖 AI 生成的详细介绍
              </h3>
              <div 
                style={{ 
                  lineHeight: 2,
                  whiteSpace: 'pre-wrap',
                  background: '#fafafa',
                  padding: '16px',
                  borderRadius: '8px'
                }}
                dangerouslySetInnerHTML={{ 
                  __html: conceptDetail.detailed_introduction
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/### (.*)/g, '<h4 style="color: #667eea; margin-top: 16px;">$1</h4>')
                    .replace(/- \*\*(.*?)\*\*：/g, '<li><strong>$1</strong>：')
                    .replace(/\n/g, '<br/>')
                }}
              />
            </div>
            
            <Divider />
            
            {/* Arxiv论文 */}
            {conceptDetail.related_papers && conceptDetail.related_papers.length > 0 && (
              <div>
                <h3 style={{ color: '#fa8c16', marginBottom: '12px' }}>
                  <FileTextOutlined /> 相关学术论文 (Arxiv)
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {conceptDetail.related_papers.map((paper, index) => (
                    <Card 
                      key={index} 
                      size="small"
                      style={{ borderLeft: '3px solid #fa8c16' }}
                    >
                      <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                        {paper.title}
                      </div>
                      <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                        作者: {paper.authors.join(', ')}
                      </div>
                      <div style={{ fontSize: '12px', color: '#999', marginBottom: '8px' }}>
                        发表时间: {paper.published}
                      </div>
                      <div style={{ fontSize: '13px', color: '#555' }}>
                        {paper.summary}
                      </div>
                      <a 
                        href={paper.link} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{ fontSize: '12px', marginTop: '8px', display: 'inline-block' }}
                      >
                        🔗 查看论文
                      </a>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      <footer className="app-footer">
        <p>提示：点击节点查看详情 | 定义来源于维基百科 | 点击"详细介绍"查看AI生成的扩展内容</p>
      </footer>
    </div>
  );
};

export default App;
