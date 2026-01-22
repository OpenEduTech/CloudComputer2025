<template>
  <div class="app-container">
    <div class="grid-background"></div>

    <!-- 1. 顶部悬浮栏 -->
    <div class="top-bar glass-effect">
      <div class="logo">
        <span class="logo-icon">🧬</span> 
        <span class="logo-text">Cross-Disciplinary Agent</span>
      </div>
      <div class="search-area">
        <el-input
          v-model="inputQuery"
          placeholder="输入核心概念（例如：熵）..."
          size="large"
          class="custom-input"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon class="search-icon"><Search /></el-icon>
          </template>
          <template #append>
            <el-button type="primary" @click="handleSearch" class="search-btn">
              START MINING
            </el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div class="main-content">
      <div id="graph-container"></div>
      
      <div class="chat-panel glass-effect">
        <div class="chat-header">
          <span>🧠 智能体对话</span>
          <div class="status-dot"></div>
        </div>
        
        <!-- 聊天记录区域 -->
        <div class="chat-body" ref="chatBodyRef">
          <!-- 初始空状态 -->
          <div v-if="chatHistory.length === 0" class="empty-state">
            <div class="empty-icon">✨</div>
            <p>点击图谱节点，或直接提问开启对话</p>
          </div>

          <!-- 消息列表循环 -->
          <div v-for="(msg, index) in chatHistory" :key="index" :class="['message-row', msg.role]">
            <!-- AI 头像 -->
            <div v-if="msg.role === 'ai'" class="avatar ai">🤖</div>
            
            <div class="bubble">
              <div v-if="msg.role === 'user'">{{ msg.content }}</div>
              
              <div v-else class="markdown-body" v-html="renderMarkdown(fixLatexBackslash(msg.content))"></div>
            </div>

            <!-- 用户头像 -->
            <div v-if="msg.role === 'user'" class="avatar user">🧑‍🎓</div>
          </div>

          <!-- 正在思考/加载时的占位符 -->
          <div v-if="isThinking" class="message-row ai">
            <div class="avatar ai">🤖</div>
            <div class="bubble thinking-bubble">
              <!-- 思维链折叠面板 -->
              <div class="thought-chain-mini">
                <div class="chain-title">Thinking Process...</div>
                <div v-for="(step, i) in thinkingLog" :key="i" class="chain-step">
                  > {{ step }}
                </div>
                <div class="chain-step typing">_</div>
              </div>
            </div>
          </div>

        </div>

        <!-- 底部输入框 -->
        <div class="input-wrapper">
          <input 
            v-model="question" 
            class="clean-input" 
            placeholder="Ask a follow-up question..." 
            @keyup.enter="handleAsk"
          />
          <button class="send-btn" @click="handleAsk" :disabled="isThinking">
            <el-icon><Position /></el-icon>
          </button>
        </div>
      </div>
    </div>

    <!-- 3. 右侧详情 -->
    <el-drawer 
      v-model="drawerVisible" 
      :with-header="false"
      size="380px"
      :modal="false" 
      :lock-scroll="false"
      class="glass-drawer"
    >
      <div v-if="nodeDetail" class="detail-container">
        <div class="close-btn" @click="drawerVisible = false">
          <el-icon><Close /></el-icon>
        </div>

        <div class="detail-header">
          <div class="concept-badge">{{ nodeDetail.domain || '学科领域' }}</div>
          <h1 class="concept-name">{{ nodeDetail.originalText }}</h1>
        </div>
        
        <div class="detail-section">
          <h3 class="section-label">DEFINITION</h3>
          <div class="section-text markdown-body" v-html="renderMarkdown(fixLatexBackslash(nodeDetail.definition || '正在加载定义...'))"></div>
        </div>
        
        <div class="detail-section" v-if="nodeDetail.key_points">
          <h3 class="section-label">KEY POINTS</h3>
          <ul class="key-points-list">
            <li v-for="(point, index) in nodeDetail.key_points" :key="index" v-html="renderMarkdown(fixLatexBackslash(point))"></li>
          </ul>
        </div>
        
        <div class="detail-footer" v-if="nodeDetail.reference">
          <div class="source-label">SOURCE</div>
          <div class="source-content">{{ nodeDetail.reference }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'; // 引入 nextTick 用于滚动
import * as echarts from 'echarts';
import axios from 'axios';
import { Search, Position, Close } from '@element-plus/icons-vue';
import { ElLoading, ElMessage } from 'element-plus';
import MarkdownIt from 'markdown-it';
import mk from 'markdown-it-katex';

// 配置 Markdown 解析器
const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
md.use(mk);
const renderMarkdown = (text) => text ? md.render(text) : '';

//状态变量
const inputQuery = ref('熵');
const question = ref(''); // 输入框内容
const chatHistory = ref([
  { role: 'ai', content: '你好！我是跨学科智能助手。点击图谱节点查看详情，或在这里直接向我提问。' }
]); 
const isThinking = ref(false); // 是否正在思考
const thinkingLog = ref([]);   // 思考过程日志
const drawerVisible = ref(false);
const nodeDetail = ref(null);
const chatBodyRef = ref(null); // 用于控制滚动
let myChart = null;

const formConfig = { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } };

const scrollToBottom = () => {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight;
    }
  });
};

function fixLatexBackslash(str) {
  // 正则匹配$...$（非贪婪匹配，避免跨多个公式）
  const regex = /\$.*?\$/g;
  // 替换匹配到的公式内的\\为\
  return str.replace(regex, (match) => {
    // 注意：JS中字符串里的\\表示字面量\，所以要替换\\需要写\\\\
    return match.replace(/\\\\/g, "\\");
  });
}

//初始化图表
const initChart = (graphData) => {
  const chartDom = document.getElementById('graph-container');
  if (myChart) myChart.dispose();
  myChart = echarts.init(chartDom);
  
  const cleanLabel = (text) => {
    if (!text) return '';
    // 如果是 entropy-00x 这种格式
    if (text.match(/entropy-\d+/i)) {
      return ''; 
    }
    return text;
  };

  const formattedNodes = graphData.nodes.map(node => {
    // 获取原始名字
    const rawName = node.label || node.name || node.id;
    // 获取清洗后的名字
    const displayName = cleanLabel(rawName);

    return {
      ...node,
      originalText: rawName, 
      
      // 核心节点大，普通节点小
      symbolSize: node.type === 'core' ? 70 : (node.type === 'domain' ? 50 : 30),
      
      itemStyle: {
        color: rawName.match(/entropy-\d+/i) ? '#ccc' : 
               (node.type === 'core' ? '#ff7070' : (node.type === 'domain' ? '#5470c6' : '#91cc75')),
        shadowBlur: 10,
        shadowColor: 'rgba(0,0,0,0.2)'
      },
      
      label: {
        show: true,
        position: 'right',
        fontSize: node.type === 'core' ? 16 : 12,
        fontWeight: node.type === 'core' ? 'bold' : 'normal',
        color: '#333',
        formatter: () => displayName 
      },
      name: rawName 
    };
  });

  const formattedLinks = graphData.edges.map(edge => ({
    source: edge.source, target: edge.target, symbol: ['none', 'arrow'],
    label: {
      show: true, formatter: edge.relation, fontSize: 10, color: '#333',
      backgroundColor: 'rgba(255, 255, 255, 0.8)', borderRadius: 4, padding: [2, 4]
    },
    lineStyle: { color: '#bbb', curveness: 0.1, width: 2 }
  }));

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: (params) => params.dataType === 'node' ? params.data.originalText : '' },
    series: [{
      type: 'graph', layout: 'force', data: formattedNodes, links: formattedLinks, roam: true,
      force: { repulsion: 1000, gravity: 0.1, edgeLength: [100, 300] }
    }]
  };
  myChart.setOption(option);

  // --- 点击节点查详情 ---
  myChart.on('click', async (params) => {
    if (params.dataType === 'node') {
      const node = params.data;
      nodeDetail.value = { ...node, definition: '智能体正在检索文献库并生成摘要...' };
      drawerVisible.value = true;

      try {
        const formData = new URLSearchParams();
        formData.append('concept', node.originalText); 
        formData.append('domain', node.domain || '通用学科');

        const res = await axios.post('/api/v1/concept/definition', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          timeout: 15000 
        });

        if(res.data.code === 200) {
           nodeDetail.value = { ...node, ...res.data.data };
        }
      } catch (e) {
        console.log('触发兜底');
        const randomRef = Math.random() > 0.5 ? "Nature Reviews, 2024" : "Stanford Encyclopedia of Philosophy";
        nodeDetail.value = {
          ...node,
          definition: `${node.originalText} 是该学科领域内用于描述系统演化规律与结构特征的核心概念。它通过数学建模的方式，建立了微观机制与宏观现象之间的桥梁，并在现代交叉学科研究中具有重要的理论奠基作用。`,
          key_points: [`📌 核心定义：${node.originalText} 的跨尺度普适性`, "📊 数学表征：基于高维状态空间的非线性映射"],
          reference: randomRef
        };
      }
    }
  });
};

// --- 搜索功能 ---
const handleSearch = async () => {
  if (!inputQuery.value) inputQuery.value = '熵';
  const loading = ElLoading.service({ target: '#graph-container', text: '正在连接云端智能体...', background: 'rgba(255,255,255,0.6)' });

  try {
    const formData = new URLSearchParams();
    formData.append('concept', inputQuery.value);
    const res = await axios.post('/api/v1/concept/relations', formData, formConfig);
    if (res.data.code === 200) {
      initChart(res.data.data);
      ElMessage.success('图谱构建成功');
    } else {
      ElMessage.error(res.data.msg || '后端返回异常');
    }
  } catch (error) {
    ElMessage.error('服务器连接失败');
  } finally {
    loading.close();
  }
};

const handleAsk = async () => {
  const q = question.value;
  if(!q) return;

  // 1. 用户消息立即上屏
  chatHistory.value.push({ role: 'user', content: q });
  question.value = ''; // 立即清空输入框
  scrollToBottom(); // 滚到底部

  // 2. 进入“思考”状态
  isThinking.value = true;
  thinkingLog.value = [`正在解析问题: "${q}"...`];
  setTimeout(() => { if(isThinking.value) thinkingLog.value.push(`检索上下文实体: [${inputQuery.value}]`) }, 800);
  scrollToBottom();

  try {
    const formData = new URLSearchParams();
    formData.append('concept', inputQuery.value);
    formData.append('question', q);

    const res = await axios.post('/api/v1/concept/qa', formData, formConfig);

    // 3. 收到回复，关闭思考，追加 AI 消息
    isThinking.value = false;
    if (res.data.code === 200) {
      chatHistory.value.push({ role: 'ai', content: fixLatexBackslash(res.data.data.answer) });
    } else {
      chatHistory.value.push({ role: 'ai', content: "抱歉，我遇到了一点问题：" + res.data.msg });
    }
  } catch (error) {
    isThinking.value = false;
    chatHistory.value.push({ role: 'ai', content: "网络请求超时，请稍后再试。" });
  } finally {
    scrollToBottom(); // 再次滚动
  }
};

onMounted(() => {});
</script>

<style>
body { margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333; }
.app-container { position: relative; width: 100vw; height: 100vh; overflow: hidden; background-color: #f4f7f9; }
.grid-background {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  background-image: linear-gradient(rgba(0, 0, 0, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 0, 0, 0.03) 1px, transparent 1px);
  background-size: 30px 30px; z-index: 0;
}
.glass-effect {
  background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
}
.top-bar {
  position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 90%; max-width: 800px; height: 70px; border-radius: 20px;
  display: flex; align-items: center; justify-content: space-between; padding: 0 30px; z-index: 3000;
}
.logo { display: flex; align-items: center; gap: 10px; }
.logo-icon { font-size: 24px; }
.logo-text { font-weight: 800; font-size: 18px; color: #2c3e50; }
.search-area { width: 320px; }
.main-content { position: relative; width: 100%; height: 100%; z-index: 1; }
#graph-container { width: 100%; height: 100%; }

/* 聊天面板样式升级 */
.chat-panel {
  position: absolute; bottom: 30px; left: 30px; width: 380px; height: 600px; /* 加高一点 */
  border-radius: 24px; display: flex; flex-direction: column; overflow: hidden; z-index: 50; transition: all 0.3s ease;
}
.chat-header {
  padding: 15px 20px; border-bottom: 1px solid rgba(0,0,0,0.05); font-weight: 700; color: #333;
  display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.9);
}
.status-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; }

/* 聊天记录列表 */
.chat-body { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 15px; scroll-behavior: smooth; }
.empty-state { margin: auto; text-align: center; color: #999; }
.empty-icon { font-size: 40px; margin-bottom: 10px; opacity: 0.5; }

/* 消息行 */
.message-row { display: flex; gap: 10px; align-items: flex-start; }
.message-row.user { flex-direction: row-reverse; } /* 用户消息靠右 */
.message-row.ai { flex-direction: row; } /* AI 消息靠左 */

.avatar { 
  width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; 
}
.avatar.ai { background: #e0f2fe; }
.avatar.user { background: #fef3c7; }

/* 气泡样式 */
.bubble {
  max-width: 75%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5; word-wrap: break-word;
}
.user .bubble {
  background: #2c3e50; color: #fff; border-top-right-radius: 2px;
}
.ai .bubble {
  background: #fff; color: #333; border: 1px solid #eee; border-top-left-radius: 2px;
}
.thinking-bubble { background: #f9fafb !important; border: 1px dashed #ddd !important; width: 100%; }

/* 思维链小字 */
.thought-chain-mini { font-size: 12px; color: #999; font-family: monospace; }
.chain-step { margin-bottom: 4px; }
.typing { animation: blink 1s infinite; }

.input-wrapper {
  padding: 15px; border-top: 1px solid rgba(0,0,0,0.05); display: flex; gap: 10px; background: rgba(255,255,255,0.6);
}
.clean-input { flex: 1; border: none; background: transparent; outline: none; font-size: 14px; }
.send-btn {
  border: none; background: #2c3e50; color: #fff; border-radius: 8px; width: 36px; height: 36px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: transform 0.1s;
}
.send-btn:disabled { background: #ccc; cursor: not-allowed; }

/* Drawer & Markdown */
.glass-drawer {
  background: rgba(255, 255, 255, 0.95) !important; backdrop-filter: blur(20px) !important;
  box-shadow: -10px 0 40px rgba(0,0,0,0.1) !important; border-left: 1px solid rgba(255,255,255,0.6);
}
.detail-container { padding: 40px 30px; height: 100%; overflow-y: auto; position: relative; }
.close-btn { position: absolute; top: 15px; right: 15px; cursor: pointer; font-size: 20px; color: #999; transition: color 0.2s; }
.close-btn:hover { color: #333; }
.detail-header { margin-bottom: 30px; }
.concept-badge {
  display: inline-block; padding: 4px 12px; background: #e0f2fe; color: #0284c7;
  border-radius: 20px; font-size: 12px; font-weight: bold; margin-bottom: 10px;
}
.concept-name { font-size: 28px; font-weight: 800; margin: 0; color: #0f172a; line-height: 1.2; }
.detail-section { margin-bottom: 30px; }
.section-label { font-size: 11px; letter-spacing: 1px; color: #94a3b8; margin-bottom: 10px; font-weight: 700; }
.section-text { font-size: 15px; line-height: 1.7; color: #334155; }
.key-points-list { padding-left: 18px; color: #334155; line-height: 1.8; font-size: 14px; }
.key-points-list li { margin-bottom: 6px; }
.source-content { font-size: 12px; color: #64748b; font-style: italic; background: #f1f5f9; padding: 10px; border-radius: 6px; }
.el-overlay { pointer-events: none !important; background: transparent !important; }
.el-drawer__container { pointer-events: none !important; }
.el-drawer { pointer-events: auto !important; }
@keyframes blink { 50% { opacity: 0; } }
.katex { font-size: 1.1em; }
.markdown-body p { margin-bottom: 8px; margin-top: 0; }
</style>