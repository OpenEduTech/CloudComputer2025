import React from 'react';
import { Box, Typography, Button, Container, Grid } from '@mui/material';
import { motion } from 'framer-motion'; // 引入动画库

// 定义接收的属性：点击按钮后跳转到哪里
interface HomeProps {
  onStart: () => void;
  onGraph: () => void;
}

const Home: React.FC<HomeProps> = ({ onStart, onGraph }) => {
  return (
    <Box sx={{
      minHeight: '90vh',
      display: 'flex',
      alignItems: 'center',
      bgcolor: '#fff',
      overflow: 'hidden'
    }}>
      <Container maxWidth="xl">
        <Grid container spacing={4} alignItems="center">

          {/* 左侧文字区域 */}
          <Grid item xs={12} md={5}>
            <Box sx={{ textAlign: { xs: 'center', md: 'left' } }}>
              <Typography
                variant="h2"
                sx={{
                  fontWeight: 800,
                  color: '#1a237e', // 深蓝紫色
                  mb: 2,
                  letterSpacing: '-1px'
                }}
              >
                像乐高一样<br />
                <span style={{ color: '#1a237e' }}>构建知识图谱</span>
              </Typography>

              <Typography
                variant="body1"
                sx={{
                  color: '#757575',
                  fontSize: '1.1rem',
                  mb: 4,
                  maxWidth: '500px',
                  lineHeight: 1.8
                }}
              >
                好的设计，一定是有灵魂的。通过 RAG 技术与 Neo4j 图数据库，
                我们将文档转化为可视化的知识网络，让错题分析与知识检索变得直观、高效。
              </Typography>

              <Box sx={{ display: 'flex', gap: 2, justifyContent: { xs: 'center', md: 'flex-start' } }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={onStart} // 点击跳转问答
                  sx={{
                    bgcolor: '#4db6ac', // 类似图中的青绿色
                    borderRadius: '50px',
                    px: 4,
                    py: 1.5,
                    fontSize: '1rem',
                    boxShadow: '0 4px 14px 0 rgba(77,182,172,0.39)',
                    '&:hover': { bgcolor: '#26a69a' }
                  }}
                >
                  开始使用
                </Button>

                <Button
                  variant="outlined"
                  size="large"
                  onClick={onGraph} // 点击跳转图谱
                  sx={{
                    borderRadius: '50px',
                    px: 4,
                    py: 1.5,
                    fontSize: '1rem',
                    color: '#1a237e',
                    borderColor: '#e0e0e0',
                    '&:hover': { borderColor: '#1a237e', bgcolor: 'transparent' }
                  }}
                >
                  查看图谱
                </Button>
              </Box>
            </Box>
          </Grid>

          {/* 右侧图片区域 (带摇动特效) */}
          <Grid item xs={12} md={7}>
            <Box sx={{ display: 'flex', justifyContent: 'center', position: 'relative' }}>

              {/* 使用 Framer Motion 包装图片容器 */}
              <motion.div
                whileHover={{
                  rotate: [0, -2, 2, -2, 0], // 摇动关键帧
                  scale: 1.02, // 悬停时轻微放大
                  transition: { duration: 0.5 } // 动画时长
                }}
                style={{
                  cursor: 'pointer',
                  perspective: 1000
                }}
              >
                {/* 模拟平板电脑的外框 */}
                <Box sx={{
                  border: '12px solid #222',
                  borderRadius: '24px',
                  overflow: 'hidden',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
                  bgcolor: '#000',
                  maxWidth: '100%',
                  height: 'auto'
                }}>
                  {/* 这里放你的图片，可以是 assets 里的，也可以是网络图 */}
                  {/* 暂时用一个占位图，你需要换成你的 demo.png */}
                  <img
                    src="https://images.unsplash.com/photo-1550745165-9bc0b252726f?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80"
                    alt="Platform Preview"
                    style={{ display: 'block', width: '100%', height: 'auto', objectFit: 'cover' }}
                  />
                </Box>
              </motion.div>

              {/* 背景装饰圆圈 (类似图中的 love 背景) */}
              <Box sx={{
                position: 'absolute',
                zIndex: -1,
                top: '-10%',
                right: '-5%',
                width: '300px',
                height: '300px',
                borderRadius: '50%',
                background: 'linear-gradient(45deg, #e1bee7 30%, #fff 90%)',
                opacity: 0.5
              }} />
            </Box>
          </Grid>

        </Grid>
      </Container>
    </Box>
  );
};

export default Home;
