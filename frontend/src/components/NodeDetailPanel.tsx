import React, { useState, useEffect } from 'react';
import { Button, Card, Tag, Space, Divider, Progress, Input, message, Spin } from 'antd';
import { ExpandOutlined, SendOutlined, LoadingOutlined } from '@ant-design/icons';
import { ConceptNode, conceptAPI, ArxivPaper } from '../services/api';

const { TextArea } = Input;

interface NodeDetailPanelProps {
  selectedNode: ConceptNode;
  expandedNodes: Set<string>;
  expandLoading: boolean;
  onClose: () => void;
  onExpand: () => void;
}

const truncateDefinition = (text: string, maxLength: number = 500): string => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
};

const NodeDetailPanel: React.FC<NodeDetailPanelProps> = ({
  selectedNode,
  expandedNodes,
  expandLoading,
  onClose,
  onExpand
}) => {
  const [aiQuestion, setAiQuestion] = useState('');
  const [aiChatLoading, setAiChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<Array<{role: string; content: string}>>([]);
  
  // 相关论文状态
  const [relatedPapers, setRelatedPapers] = useState<ArxivPaper[]>([]);
  const [papersLoading, setPapersLoading] = useState(false);

  // 当选中节点变化时，获取相关论文
  useEffect(() => {
    const fetchPapers = async () => {
      if (!selectedNode?.label) return;
      
      setPapersLoading(true);
      try {
        const response = await conceptAPI.searchArxiv(selectedNode.label, 5);
        if (response.status === 'success' && response.data.papers) {
          setRelatedPapers(response.data.papers);
        }
      } catch (error) {
        console.log('获取论文失败:', error);
        setRelatedPapers([]);
      } finally {
        setPapersLoading(false);
      }
    };
    
    fetchPapers();
  }, [selectedNode?.label]);

  const handleAiChat = async () => {
    if (!aiQuestion.trim()) {
      message.warning('请输入问题');
      return;
    }
    
    setAiChatLoading(true);
    try {
      const response = await conceptAPI.aiChat(
        selectedNode.label,
        aiQuestion,
        selectedNode.definition
      );
      
      if (response.status === 'success' && response.data.answer) {
        const newChat = [
          ...chatHistory, 
          { role: 'user', content: aiQuestion },
          { role: 'assistant', content: response.data.answer }
        ];
        setChatHistory(newChat);
        setAiQuestion('');
        message.success('AI回答成功');
      } else {
        message.error('AI回答失败');
      }
    } catch (error: any) {
      console.error('AI问答失败:', error);
      if (error.response?.status === 503) {
        message.error('AI服务暂时不可用');
      } else if (error.response?.status === 504) {
        message.error('AI响应超时，请稍后重试');
      } else {
        message.error('AI问答失败，请稍后重试');
      }
    } finally {
      setAiChatLoading(false);
    }
  };

  return (
    <Card
      style={{
        width: '420px',
        maxHeight: 'calc(100vh - 200px)',
        overflow: 'auto',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: '16px',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)',
        border: 'none',
        color: 'white'
      }}
      styles={{
        body: {
          background: 'white',
          borderRadius: '12px',
          margin: '8px',
          padding: '24px'
        }
      }}
      title={
        <Button
          type="text"
          size="small"
          onClick={onClose}
          style={{ color: 'white', fontSize: '16px' }}
        >
          ✕
        </Button>
      }
    >
      {/* 1. 概念名称 */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ 
          fontSize: '26px', 
          fontWeight: 'bold',
          marginBottom: '12px',
          color: '#667eea',
          borderBottom: '3px solid #667eea',
          paddingBottom: '10px'
        }}>
          {selectedNode.label}
        </div>
      </div>

      {/* 2. 所属学科 */}
      <div style={{ marginBottom: '18px' }}>
        <div style={{ fontSize: '13px', color: '#999', marginBottom: '8px', fontWeight: '500' }}>
          📚 所属学科
        </div>
        <Space size={6} wrap>
          <Tag color="blue" style={{ fontSize: '13px', padding: '5px 14px', borderRadius: '12px' }}>
            {selectedNode.discipline}
          </Tag>
          {/* 可以有多个学科标签 */}
        </Space>
      </div>

      {/* 3. 一句话简介 (LLM生成) */}
      <div style={{ marginBottom: '18px' }}>
        <div style={{ fontSize: '13px', color: '#999', marginBottom: '8px', fontWeight: '500' }}>
          💡 一句话简介 <Tag color="purple" style={{ fontSize: '10px', marginLeft: '4px' }}>AI生成</Tag>
        </div>
        <div style={{ 
          background: 'linear-gradient(135deg, #f6f8fa 0%, #e8f4fd 100%)',
          padding: '14px',
          borderRadius: '10px',
          fontSize: '14px',
          lineHeight: '1.7',
          color: '#333',
          border: '1px solid #d4e5f7'
        }}>
          {(selectedNode as any).brief_summary || truncateDefinition(selectedNode.definition, 100)}
        </div>
      </div>

      <Divider style={{ margin: '18px 0' }} />

      {/* 4. 与搜索词的相关度 (使用similarity字段) */}
      <div style={{ marginBottom: '18px' }}>
        <div style={{ fontSize: '13px', color: '#999', marginBottom: '8px', fontWeight: '500' }}>
          🎯 与搜索词的相关度 <Tag color="green" style={{ fontSize: '10px', marginLeft: '4px' }}>动态计算</Tag>
        </div>
        <Progress 
          percent={Math.round(((selectedNode as any).similarity || selectedNode.credibility) * 100)} 
          status="active"
          strokeColor={{
            '0%': '#667eea',
            '100%': '#764ba2',
          }}
          size={12}
        />
        <div style={{ fontSize: '11px', color: '#999', marginTop: '6px' }}>
          相似度分数: {(((selectedNode as any).similarity || selectedNode.credibility) * 100).toFixed(1)}% | 
          可信度: {(selectedNode.credibility * 100).toFixed(1)}%
        </div>
      </div>

      <Divider style={{ margin: '18px 0' }} />

      {/* 5. 维基百科权威定义 */}
      <div style={{ marginBottom: '18px' }}>
        <div style={{ fontSize: '13px', color: '#999', marginBottom: '8px', fontWeight: '500' }}>
          📖 维基百科权威定义
        </div>
        <div style={{ 
          background: selectedNode.source === 'Wikipedia' ? '#e6f7ff' : '#fff7e6',
          padding: '14px',
          borderRadius: '10px',
          fontSize: '13px',
          lineHeight: '1.7',
          maxHeight: '180px',
          overflow: 'auto',
          border: selectedNode.source === 'Wikipedia' ? '1px solid #91d5ff' : '1px solid #ffd591'
        }}>
          {selectedNode.source === 'Wikipedia' ? (
            <>
              <div style={{ color: '#333', marginBottom: '10px' }}>
                {truncateDefinition(selectedNode.definition, 500)}
              </div>
              {(selectedNode as any).wiki_url && (
                <a 
                  href={(selectedNode as any).wiki_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{ fontSize: '12px', color: '#1890ff' }}
                >
                  🔗 查看维基百科原文
                </a>
              )}
            </>
          ) : (
            <div style={{ color: '#999', fontStyle: 'italic', textAlign: 'center', padding: '10px' }}>
              ⚠️ 维基百科中暂无此条目
            </div>
          )}
        </div>
      </div>

      <Divider style={{ margin: '18px 0' }} />

      {/* 6. 相关文献 (Arxiv) */}
      <div style={{ marginBottom: '18px' }}>
        <div style={{ fontSize: '13px', color: '#999', marginBottom: '8px', fontWeight: '500' }}>
          📄 相关文献 <Tag color="orange" style={{ fontSize: '10px', marginLeft: '4px' }}>Arxiv</Tag>
        </div>
        <div style={{ 
          fontSize: '12px', 
          color: '#666',
          background: '#f9f9f9',
          padding: '12px',
          borderRadius: '8px',
          maxHeight: '250px',
          overflow: 'auto'
        }}>
          {papersLoading ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <Spin indicator={<LoadingOutlined style={{ fontSize: 20 }} spin />} />
              <div style={{ marginTop: '8px', color: '#999' }}>正在搜索相关论文...</div>
            </div>
          ) : relatedPapers.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {relatedPapers.map((paper, index) => (
                <div 
                  key={index}
                  style={{
                    background: 'white',
                    padding: '10px',
                    borderRadius: '6px',
                    borderLeft: '3px solid #fa8c16'
                  }}
                >
                  <div style={{ fontWeight: 'bold', fontSize: '12px', marginBottom: '4px', color: '#333' }}>
                    {paper.title}
                  </div>
                  <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px' }}>
                    👤 {paper.authors.slice(0, 2).join(', ')}{paper.authors.length > 2 ? ' 等' : ''}
                  </div>
                  <div style={{ fontSize: '11px', color: '#999', marginBottom: '6px' }}>
                    📅 {paper.published}
                  </div>
                  <div style={{ fontSize: '11px', color: '#555', marginBottom: '6px', lineHeight: '1.5' }}>
                    {paper.summary.length > 150 ? paper.summary.substring(0, 150) + '...' : paper.summary}
                  </div>
                  <a 
                    href={paper.link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ fontSize: '11px', color: '#1890ff' }}
                  >
                    🔗 查看论文
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '15px', color: '#999' }}>
              暂无相关论文
            </div>
          )}
        </div>
      </div>

      <Divider style={{ margin: '18px 0' }} />

      {/* 7. AI问答窗口 */}
      <div style={{ marginBottom: '18px' }}>
        <div style={{ fontSize: '13px', color: '#999', marginBottom: '8px', fontWeight: '500' }}>
          🤖 AI问答
        </div>
        
        {/* 聊天记录 */}
        {chatHistory.length > 0 && (
          <div style={{ 
            maxHeight: '220px', 
            overflow: 'auto',
            marginBottom: '12px',
            background: '#f6f8fa',
            padding: '14px',
            borderRadius: '10px',
            border: '1px solid #e8e8e8'
          }}>
            {chatHistory.map((chat, index) => (
              <div key={index} style={{ marginBottom: '12px' }}>
                <div style={{ 
                  fontSize: '12px', 
                  color: chat.role === 'user' ? '#667eea' : '#52c41a',
                  fontWeight: 'bold',
                  marginBottom: '6px'
                }}>
                  {chat.role === 'user' ? '👤 你：' : '🤖 AI：'}
                </div>
                <div style={{ 
                  fontSize: '13px', 
                  color: '#333', 
                  paddingLeft: '24px',
                  lineHeight: '1.6'
                }}>
                  {chat.content}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 输入框 */}
        <TextArea
          placeholder={`针对"${selectedNode.label}"提问...`}
          value={aiQuestion}
          onChange={(e) => setAiQuestion(e.target.value)}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              handleAiChat();
            }
          }}
          autoSize={{ minRows: 2, maxRows: 4 }}
          style={{ marginBottom: '10px', borderRadius: '8px' }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleAiChat}
          loading={aiChatLoading}
          block
          style={{
            borderRadius: '8px',
            height: '38px',
            fontWeight: '500'
          }}
        >
          发送提问
        </Button>
      </div>

      <Divider style={{ margin: '18px 0' }} />

      {/* 8. 节点拓展按钮 - 前端功能：发现该节点的新关联节点 */}
      <Button 
        type="primary" 
        block 
        icon={<ExpandOutlined />}
        style={{ 
          background: expandedNodes.has(selectedNode.id)
            ? '#d9d9d9'
            : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          border: 'none',
          borderRadius: '10px',
          height: '48px',
          fontSize: '16px',
          fontWeight: 'bold',
          boxShadow: expandedNodes.has(selectedNode.id) 
            ? 'none' 
            : '0 4px 12px rgba(102, 126, 234, 0.4)'
        }}
        loading={expandLoading}
        disabled={expandedNodes.has(selectedNode.id)}
        onClick={onExpand}
      >
        {expandLoading 
          ? '正在发现关联概念...' 
          : expandedNodes.has(selectedNode.id) 
            ? '✓ 已展开' 
            : '🔎 展开关联节点'}
      </Button>
      {!expandedNodes.has(selectedNode.id) && (
        <div style={{ 
          fontSize: '11px', 
          color: '#999', 
          textAlign: 'center', 
          marginTop: '8px' 
        }}>
          点击后将在图谱中展开该节点的相关概念
        </div>
      )}
    </Card>
  );
};

export default NodeDetailPanel;
