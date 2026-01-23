import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import axios from 'axios';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';

interface GraphNode {
    id: string;
    label: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
}

interface GraphLink {
    source: string;
    target: string;
    type: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

const GraphView: React.FC = () => {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  const [height, setHeight] = useState(600);

  // 🌟 核心修改 1: 添加 ResizeObserver 监听容器大小变化
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
            // 动态更新宽高，确保图谱始终填满容器
            setWidth(entry.contentRect.width);
            setHeight(entry.contentRect.height);
        }
    });

    resizeObserver.observe(containerRef.current);

    return () => {
        resizeObserver.disconnect();
    };
  }, []);

  // 核心：获取数据的函数
  const fetchData = useCallback(() => {
    setLoading(true);
    setErrorMsg(null);

    // 🌟 确保连接的是 127.0.0.1:8088
    axios.get('http://127.0.0.1:8088/graph/overview?limit=300')
      .then(res => {
        const data = res.data;
        // 检查后端是否返回了有效数据
        if (!data.nodes || data.nodes.length === 0) {
            setGraphData({ nodes: [], links: [] });
            setErrorMsg("✅ 连接成功，但数据库为空 (请先执行知识图谱构建)");
        } else {
            setGraphData(data);
        }
      })
      .catch(err => {
        console.error(err);
        const msg = err.response
            ? `服务器错误: ${err.response.status}`
            : "❌ 无法连接后端 (请检查端口 8088)";
        setErrorMsg(msg);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  // 组件加载时自动获取一次
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <Box
        ref={containerRef}
        sx={{
            // 🌟 核心修改 2: 样式调整，解决大小不对的问题
            width: '100%',                 // 强制占满父容器宽度
            height: "calc(100vh - 100px)", // 减去导航栏和间距，防止溢出产生滚动条
            border: "1px solid #ddd",
            borderRadius: 2,
            overflow: 'hidden',
            bgcolor: '#fcfcfc',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
            mt: 2 // 顶部增加一点间距
        }}
    >
        {/* 1. 顶部工具栏 (显示数量 + 刷新按钮) */}
        <Box sx={{
            p: 1.5,
            borderBottom: '1px solid #eee',
            bgcolor: 'white',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
        }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: '#555' }}>
                知识图谱概览 ({graphData.nodes.length} 节点 / {graphData.links.length} 关系)
            </Typography>
            <Button
                size="small"
                startIcon={<RefreshIcon />}
                onClick={fetchData}
                disabled={loading}
                variant="outlined"
            >
                刷新
            </Button>
        </Box>

        {/* 2. 内容区域 */}
        <Box sx={{ flexGrow: 1, position: 'relative' }}>

            {/* 状态 A: 加载中 */}
            {loading && (
                <Box sx={{
                    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                    textAlign: 'center', zIndex: 10
                }}>
                    <CircularProgress size={40} />
                    <Typography variant="body2" sx={{ mt: 2, color: '#666' }}>正在加载图谱数据...</Typography>
                </Box>
            )}

            {/* 状态 B: 出错或无数据 */}
            {!loading && (errorMsg || graphData.nodes.length === 0) && (
                <Box sx={{
                    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                    textAlign: 'center', width: '80%'
                }}>
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                        暂无图谱展示
                    </Typography>
                    <Typography variant="body2" color={errorMsg?.includes("✅") ? "warning.main" : "error"}>
                        {errorMsg || "未获取到节点数据"}
                    </Typography>
                </Box>
            )}

            {/* 状态 C: 显示图谱 */}
            {!loading && graphData.nodes.length > 0 && (
                <ForceGraph2D
                    // 🌟 核心修改 3: 使用动态监听到的宽高，减去顶部工具栏的高度(约50px)
                    width={width}
                    height={height - 52}
                    graphData={graphData}
                    nodeLabel="name" // 鼠标悬停显示 name
                    nodeAutoColorBy="label" // 根据 label 自动配色
                    linkDirectionalArrowLength={3.5}
                    linkDirectionalArrowRelPos={1}
                    backgroundColor="#fcfcfc"
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    onNodeClick={(node: any) => {
                        alert(`节点ID: ${node.id}\n名称: ${node.name}\n类型: ${node.label}`);
                    }}
                />
            )}
        </Box>
    </Box>
  );
};

export default GraphView;
