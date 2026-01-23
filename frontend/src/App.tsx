import { useState } from 'react';
import { AppBar, Toolbar, Typography, Button, Container, Box, IconButton } from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import HubIcon from '@mui/icons-material/Hub';
import HomeIcon from '@mui/icons-material/Home';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

// 引入组件
import Chat from './components/Chat';
import GraphView from './components/GraphView';
import Home from './components/Home';

function App() {
  // 状态：'home' | 'chat' | 'graph'
  const [currentView, setCurrentView] = useState('home');

  // 渲染顶部导航栏 (Home 页通常需要不同的导航栏，或者是透明的，这里为了统一先做成通用的)
  const renderNavbar = () => (
    <AppBar position="sticky" elevation={0} sx={{ bgcolor: '#fff', borderBottom: '1px solid #eee' }}>
      <Toolbar>
        {/* 如果不是主页，显示返回按钮 */}
        {currentView !== 'home' && (
          <IconButton edge="start" color="primary" onClick={() => setCurrentView('home')} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
        )}

        <Typography variant="h6" component="div" sx={{ flexGrow: 1, color: '#1a237e', fontWeight: 'bold', letterSpacing: 1 }}>
          RAG <span style={{ color: '#4db6ac' }}>KNOWLEDGE</span>
        </Typography>

        {/* 导航按钮 */}
        <Button
          startIcon={<HomeIcon />}
          onClick={() => setCurrentView('home')}
          sx={{ color: currentView === 'home' ? '#4db6ac' : '#555', fontWeight: 'bold' }}
        >
          首页
        </Button>
        <Button
          startIcon={<ChatIcon />}
          onClick={() => setCurrentView('chat')}
          sx={{ color: currentView === 'chat' ? '#4db6ac' : '#555', fontWeight: 'bold', ml: 1 }}
        >
          知识问答
        </Button>
        <Button
          startIcon={<HubIcon />}
          onClick={() => setCurrentView('graph')}
          sx={{ color: currentView === 'graph' ? '#4db6ac' : '#555', fontWeight: 'bold', ml: 1 }}
        >
          知识图谱
        </Button>
      </Toolbar>
    </AppBar>
  );

  return (
    <Box sx={{ bgcolor: '#fbfbfb', minHeight: '100vh' }}>
      {renderNavbar()}

      {/* 主内容区域 */}
      <Box>
        {currentView === 'home' && (
          <Home
            onStart={() => setCurrentView('chat')}
            onGraph={() => setCurrentView('graph')}
          />
        )}

        {currentView === 'chat' && (
          <Container maxWidth="xl" sx={{ mt: 4 }}>
            <Chat />
          </Container>
        )}

        {currentView === 'graph' && (
          <Container maxWidth="xl" sx={{ mt: 4 }}>
             <GraphView />
          </Container>
        )}
      </Box>
    </Box>
  );
}

export default App;
