import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  Avatar,
  CircularProgress,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import RefreshIcon from '@mui/icons-material/Refresh';
import AddIcon from '@mui/icons-material/Add';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';

// === 1. 引入 Markdown 渲染组件 ===
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// === 2. 🌟 数学公式插件 ===
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

// 定义消息类型
interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}

interface Citation {
  evidence_id: number;
  score: number;
  source: string;
  image_url?: string;
  type?: string;
}

const Chat: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: '你好！我是你的算法导师。你可以问我具体的算法问题，也可以让我为你出题（输入"出题"）。' }
  ]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const historyItems = [
    "N皇后问题",
    "动态规划相关题目讲解"
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000);

      const res = await fetch('http://127.0.0.1:8088/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMsg }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!res.ok) throw new Error('Network response was not ok');

      const data = await res.json();

      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: data.answer, citations: data.citations }
      ]);
    } catch (error) {
      console.error('Error:', error);
      let errMsg = '⚠️ 连接失败';
      if (error instanceof Error) {
          if (error.name === 'AbortError') errMsg = '⚠️ 生成超时';
          else errMsg = `⚠️ 错误: ${error.message}`;
      }
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: errMsg }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setMessages([
      { role: 'assistant', content: '你好！我是你的算法导师。你可以问我具体的算法问题，也可以让我为你出题（输入"出题"）。' }
    ]);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        width: '100%',
        height: 'calc(100vh - 64px)', // 🌟 适配顶部导航栏，全屏显示
        overflow: 'hidden',           // 防止出现双重滚动条
        bgcolor: 'white',             // 整体背景设为白，显得更干净
        borderTop: '1px solid #e0e0e0' // 顶部分割线
      }}
    >

      {/* 👈 左侧侧边栏 */}
      <Box
        sx={{
          width: 260,
          bgcolor: '#f9f9fa', // 稍微淡一点的灰色，与主内容区分
          borderRight: '1px solid #e0e0e0',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
          height: '100%'
        }}
      >
        {/* 新建聊天按钮区 */}
        <Box sx={{ p: 2 }}>
          <Button
            variant="contained" // 改为实心按钮更显眼
            fullWidth
            startIcon={<AddIcon />}
            onClick={handleNewChat}
            sx={{
              justifyContent: 'flex-start',
              textTransform: 'none',
              bgcolor: 'white',
              color: '#1976d2',
              boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
              '&:hover': { bgcolor: '#f0f0f0', boxShadow: '0 1px 2px rgba(0,0,0,0.2)' },
              py: 1.2
            }}
          >
            新对话
          </Button>
        </Box>

        <Typography variant="caption" sx={{ px: 2, pb: 1, color: '#888', fontWeight: 'bold', fontSize: '0.7rem', letterSpacing: '0.5px' }}>
          历史记录
        </Typography>

        <List sx={{ flexGrow: 1, overflowY: 'auto', px: 1 }}>
          {historyItems.map((item, index) => (
            <ListItem key={index} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                sx={{
                    borderRadius: 1,
                    py: 1,
                    '&:hover': { bgcolor: '#eef2f6' }
                }}
              >
                <ListItemIcon sx={{ minWidth: 30 }}>
                  <ChatBubbleOutlineIcon fontSize="small" sx={{ color: '#757575', fontSize: '1.1rem' }} />
                </ListItemIcon>
                <ListItemText
                  primary={item}
                  primaryTypographyProps={{ variant: 'body2', noWrap: true, sx: { color: '#444' } }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        <Divider />
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
            <Avatar sx={{ width: 30, height: 30, bgcolor: '#9c27b0', fontSize: 13 }}>U</Avatar>
            <Typography variant="body2" sx={{ ml: 1.5, color: '#444', fontWeight: 500 }}>我的账户</Typography>
        </Box>
      </Box>

      {/* 👉 右侧主聊天区域 */}
      <Box sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          bgcolor: 'white' // 保持白色背景
      }}>

        {/* 1. 顶部标题栏 - 调整为平整风格 (Square) */}
        <Paper
            square // 🌟 去除圆角
            elevation={0} // 🌟 去除阴影，改用边框
            sx={{
                p: 2,
                display: 'flex',
                alignItems: 'center',
                bgcolor: 'white',
                borderBottom: '1px solid #e0e0e0',
                height: 60 // 固定高度
            }}
        >
          <SmartToyIcon color="primary" sx={{ mr: 1.5, fontSize: 28 }} />
          <Typography variant="h6" color="text.primary" sx={{ fontWeight: 600, fontSize: '1.1rem', flexGrow: 1 }}>
            RAG 算法导师 <span style={{fontSize: '0.8em', color: '#888', fontWeight: 400}}>v2.1</span>
          </Typography>
          <Tooltip title="清空当前对话">
            <IconButton onClick={handleNewChat} size="small" sx={{ color: '#666' }}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Paper>

        {/* 2. 消息滚动区域 */}
        <Box sx={{
            flexGrow: 1,
            overflow: 'auto',
            p: 3,
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
            bgcolor: '#ffffff'
        }}>
          {messages.map((msg, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                alignItems: 'flex-start',
                maxWidth: '90%', // 限制最大宽度，防止太宽难阅读
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start'
              }}
            >
              {msg.role === 'assistant' && (
                <Avatar sx={{ bgcolor: '#1976d2', mr: 2, mt: 0.5, width: 32, height: 32 }}>
                  <SmartToyIcon sx={{ fontSize: 20 }} />
                </Avatar>
              )}

              <Box sx={{ maxWidth: '100%' }}>
                <Paper
                  elevation={0} // 去除卡片阴影，改用边框或背景色区分
                  sx={{
                    p: 2,
                    bgcolor: msg.role === 'user' ? '#1976d2' : '#f4f6f8', // 助手消息使用淡灰色背景
                    color: msg.role === 'user' ? 'white' : 'text.primary',
                    borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                    border: msg.role === 'user' ? 'none' : '1px solid #eef0f2',
                    // 样式微调
                    '& p': { m: 0, mb: 1, lineHeight: 1.7 },
                    '& img': { maxWidth: '100%', borderRadius: 1, my: 1 },
                    '& pre': { m: 0, p: 0, borderRadius: 1, overflow: 'hidden' },
                    '& .katex': { fontSize: '1.1em' }
                  }}
                >
                  {msg.role === 'user' ? (
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{msg.content}</Typography>
                  ) : (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        code({ inline, className, children, ...props }: any) {
                          const match = /language-(\w+)/.exec(className || '');
                          return !inline && match ? (
                            <SyntaxHighlighter
                              // eslint-disable-next-line @typescript-eslint/no-explicit-any
                              {...(props as any)}
                              style={vscDarkPlus}
                              language={match[1]}
                              PreTag="div"
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className={className} {...props} style={{ backgroundColor: 'rgba(0,0,0,0.05)', padding: '2px 4px', borderRadius: '4px' }}>
                              {children}
                            </code>
                          );
                        }
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </Paper>

                {/* 引用来源卡片 */}
                {msg.citations && msg.citations.length > 0 && (
                  <Box sx={{ mt: 1.5, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {msg.citations.slice(0, 3).map((cit, i) => (
                      <Card key={i} variant="outlined" sx={{
                          maxWidth: 240,
                          bgcolor: 'white',
                          borderRadius: 1,
                          borderColor: '#eee',
                          transition: 'all 0.2s',
                          '&:hover': { borderColor: '#1976d2', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }
                      }}>
                        <CardContent sx={{ p: '8px 12px !important' }}>
                          <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                            🔗 来源 [{cit.evidence_id}]
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              lineHeight: 1.3
                          }}>
                             {cit.source}
                          </Typography>
                          {cit.image_url && (
                            <Box
                              component="img"
                              src={cit.image_url}
                              sx={{ width: '100%', height: 80, objectFit: 'cover', mt: 1, borderRadius: 1 }}
                              onClick={() => window.open(cit.image_url, '_blank')}
                            />
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                )}
              </Box>

              {msg.role === 'user' && (
                <Avatar sx={{ bgcolor: '#9c27b0', ml: 2, mt: 0.5, width: 32, height: 32 }}>
                  <PersonIcon sx={{ fontSize: 20 }} />
                </Avatar>
              )}
            </Box>
          ))}
          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', ml: 7 }}>
              <CircularProgress size={16} sx={{ mr: 1.5 }} />
              <Typography variant="body2" color="text.secondary">算法导师正在思考...</Typography>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>

        {/* 3. 底部输入区 */}
        <Box sx={{
            p: 2,
            bgcolor: 'white',
            borderTop: '1px solid #e0e0e0', // 明确的分割线
            display: 'flex',
            gap: 1.5,
            alignItems: 'flex-end'
        }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            variant="outlined"
            placeholder="输入您的问题..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
              }
            }}
            size="small"
            sx={{
                '& .MuiOutlinedInput-root': {
                    borderRadius: 2, // 稍微圆润一点的输入框
                    bgcolor: '#f9f9fa'
                }
            }}
          />
          <Button
            variant="contained"
            endIcon={<SendIcon />}
            onClick={handleSend}
            disabled={loading || !input.trim()}
            sx={{
                height: 40,
                borderRadius: 2,
                px: 3,
                boxShadow: 'none',
                '&:hover': { boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }
            }}
          >
            发送
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

export default Chat;
