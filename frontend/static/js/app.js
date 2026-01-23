(() => {
  const chartDom = document.getElementById('chart');
  if (!chartDom) {
    console.error('未找到图表容器 #chart');
    throw new Error('找不到图表容器');
  }
  if (!window.echarts) {
    document.getElementById('infoPanel').textContent = 'ECharts 未加载成功，请检查网络或重试。';
    throw new Error('ECharts not loaded');
  }
  const myChart = echarts.init(chartDom);
  let currentGraph = { nodes: [], links: [] };

  function setInfo(text) {
    const panel = document.getElementById('infoPanel');
    if (panel) panel.textContent = text;
  }

  function renderGraph(data) {
    currentGraph = data;
    const categoriesArr = Array.from(new Set((data.nodes || []).map(n => n.discipline || '其他')));
    const categories = categoriesArr.map(name => ({ name }));

    const nodes = (data.nodes || []).map(n => ({
      id: n.id,
      name: n.name || n.id,
      symbolSize: 8 + (n.value || 8),
      category: categoriesArr.indexOf(n.discipline || '其他'),
      value: n.value || 1,
      description: n.description
    }));
    const links = (data.links || []).map(l => ({
      source: l.source,
      target: l.target,
      sourceName: l.sourseName,
      targetName: l.targetName,
      label: { show: true, formatter: l.relation || '' },
      description: l.description
    }));
    const option = { 
      tooltip: { 
        trigger: 'item',
        triggerOn: 'mousemove',
        position: function (point, params, dom, rect, size) {
          const tooltipWidth = size.viewSize[0] * 0.25;
          let x = point[0] - tooltipWidth / 2;
          x = Math.max(x, 10);
          x = Math.min(x, size.viewSize[0] - tooltipWidth - 10);
          let y = point[1] + 10;
          y = Math.min(y, size.viewSize[1] - dom.offsetHeight - 10);
          return [x, y];
        },
        extraCssText: `
          width: 25vw !important;
          max-width: 25vw !important;
          min-width: 25vw !important; /* 新增：强制宽度固定 */
          transform: translateX(0) !important;
          box-sizing: border-box !important;
          padding: 12px 15px !important;
          text-align: left !important;
          line-height: 1.5 !important;
          word-break: break-all !important;
          overflow: hidden !important; /* 新增：隐藏溢出内容（兜底） */
          display: block !important; /* 强制块级元素 */
        `,
        formatter: (params) => {
          const textContainerStyle = `
            style="
              width: 100% !important; 
              word-break: break-all !important; 
              white-space: normal !important; 
              line-height: 1.5 !important;
              font-size: 16px !important;
              font-weight: bold !important;
              color: #ffffff !important;
            "
          `;

          if (params.dataType === 'node') {
            const baseInfo = params.data.name || params.data.id;
            const desc = params.data.description || '暂无';
            return `
              <div ${textContainerStyle}>
                ${baseInfo}
                <br/><br/>📝 描述：${desc}
              </div>
            `;
          } else if (params.dataType === 'edge') {
            const { source, target, description } = params.data;
            const desc = params.data.description || '暂无';
            return `
              <div ${textContainerStyle}>
                <b>${source} → ${target}</b>
                <br/><br/>📝 关系描述：${desc}
              </div>
            `;
          }
          return `<div ${textContainerStyle}>${params.name || '暂无信息'}</div>`;
        },
        textStyle: { 
          color: '#ffffff',
          fontSize: 16,
          fontWeight: 'bold',
          whiteSpace: 'normal',
          wordWrap: 'break-word',
          wordBreak: 'break-all'
        },
        backgroundColor: 'rgba(0,0,0,0.7)',
        borderColor: '#ffffff',
        borderWidth: 1,
        padding: 0, 
        useHtml: true 
      },
      legend: [{ 
        data: categoriesArr,
        textStyle: { 
          color: '#ffffff',
          fontSize: 18,
          fontWeight: 'bold'
        }
      }],
      series: [{
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: nodes,
        links: links,
        categories,
        force: { 
          repulsion: 1300,
          edgeLength: [150, 200], // 
          gravity: 0.06,
          friction: 0.6
        },
        label: {
          show: true,
          position: 'inside',
          color: '#e8f3ee',
          fontSize: 20,   //
          backgroundColor: 'rgba(0,0,0,0)',
          padding: 0,
          formatter: (p) => p.data.name || '' 
        },
        emphasis: {
          focus: 'adjacency',
          scale: true,
          label: { show: true, fontSize: 16, fontWeight: 'bold' },
          lineStyle: { width: 2.5, opacity: 0.85 }
        },
        itemStyle: { 
          borderColor: 'rgba(255,255,255,0.35)',
          borderWidth: 1,      
          opacity: 0.9           
        },
        lineStyle: { 
          width: 5,   //
          opacity: 0.35,
          curveness: 0.4   //
        },
        category: {
          label: { 
            color: '#ffffff',
            fontSize: 100,  //
            fontWeight: 'bold'
          }
        },
        edgeLabel: {
          show: true,
          formatter: (p) => p.data?.relation || '',
          fontSize: 20,
          color: 'rgba(232,243,238,0.55)',
          backgroundColor: 'transparent',
          padding: 0,
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 6,
      }]
    };
  
  
    myChart.setOption(option);

    myChart.off('click');
    myChart.on('click', params => {
      if (params.dataType === 'node') showNodeInfo(params.data);
    });
  }

  function showNodeInfo(node) {
    const panel = document.getElementById('infoPanel');
    if (!panel) return;
    panel.innerHTML = '';
    const title = document.createElement('div');
    title.className = 'node-label';
    title.textContent = node.name || node.id;
    panel.appendChild(title);
    const details = document.createElement('div');
    details.innerHTML = `<b>ID:</b> ${node.id || ''}<br/><b>学科:</b> ${node.category || ''}<br/><b>值:</b> ${node.value || ''}`;
    panel.appendChild(details);
  }

  async function loadSample() {
    try {
      setInfo('正在加载本地样例...');
      const res = await fetch('/frontend/static/json/sample_data.json');
      if (!res.ok) throw new Error('样例文件未找到');
      const data = await res.json();
      renderGraph(data);
      setInfo('已加载本地样例，点击节点查看详情');
    } catch (err) {
      console.error('加载样例失败', err);
      setInfo('加载样例失败，请确认 sample_data.json 可访问');
      alert('加载样例失败，请检查 sample_data.json 是否存在并可访问');
    }
  }

  async function queryConcept(concept) {
    if (!concept) return alert('请输入概念');
    const skipBackend = document.getElementById('skipBackend')?.checked;
    if (skipBackend) {
      setInfo('离线模式：直接使用本地样例');
      await loadSample();
      return;
    }

    setInfo(`查询「${concept}」中...`);
    try {
      const controller = new AbortController();
      const timeout = setTimeout(()=>controller.abort(), 300000);
      const res = await fetch(`/api/graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept }),
        signal: controller.signal
      });
      clearTimeout(timeout);
      if (!res.ok) throw new Error('非 2xx 响应');
      const data = await res.json();
      const safeNodes = Array.isArray(data?.nodes) ? data.nodes : [];
      const safeLinks = Array.isArray(data?.links) ? data.links : [];

      if (safeNodes.length > 0) {
        renderGraph({ nodes: safeNodes, links: safeLinks });
        setInfo('已加载后端数据，点击节点查看详情');
        return;
      }

      console.warn('后端返回为空或无节点，改用本地样例', data);
      await loadSample();
      return;
    } catch (e) {
      console.warn('后端请求失败，使用本地样例。', e);
      setInfo('后端不可用，切换到本地样例...');
      await loadSample();
    }
  }

  function handleFileUpload(file) {
    const reader = new FileReader();
    reader.onload = e => {
      try {
        const data = JSON.parse(e.target.result);
        if (data.nodes && data.links) renderGraph(data);
        else alert('JSON 必须包含 nodes 与 links 字段');
      } catch (err) { alert('解析 JSON 失败'); }
    };
    reader.readAsText(file);
  }

  function exportJSON() {
    const blob = new Blob([JSON.stringify(currentGraph, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'graph_export.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  function bindEvents() {
    const queryBtn = document.getElementById('queryBtn');
    const loadSampleBtn = document.getElementById('loadSampleBtn');
    const fileInput = document.getElementById('fileInput');
    const exportBtn = document.getElementById('exportBtn');

    if (!queryBtn || !loadSampleBtn || !fileInput || !exportBtn) {
      console.error('按钮或输入控件未找到，无法绑定事件');
      setInfo('页面加载不完整，请刷新重试');
      return;
    }

    loadSampleBtn.addEventListener('click', loadSample);
    queryBtn.addEventListener('click', () => queryConcept(document.getElementById('conceptInput').value.trim()));
    fileInput.addEventListener('change', e => { if (e.target.files[0]) handleFileUpload(e.target.files[0]); });
    exportBtn.addEventListener('click', exportJSON);
  }

  window.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadSample();
  });
})();
