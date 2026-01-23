// 定义边强度到颜色的映射（用于可视化不同关联强度）
const map_dict = { 
  1: '#FFF9C4', // 淡黄
  2: '#FFF176', 
  3: '#FFEE58', 
  4: '#FFC107', // 橙黄
  5: '#F44336'  // 红色（Material Red）
};

// 从 finding_mode.js 导入寻路模式相关函数
import { change_to_finding_mode, out_finding_mode, startFindPath } from './finding_mode.js';

// 从 fetch_method.js 导入数据获取函数
import { fetch_gen, fetch_quick_search } from "./fetch_method.js";

// 标记当前是否处于“寻路模式”
let infinding = false;

/**
 * 预处理后端返回的数据，使其适配 G6 图结构要求
 * @param {Object} dt - 原始响应数据，包含 nodes 和 links
 * @returns {Object} - 转换后的图数据：{ nodes, edges }
 */
function preprocess(dt) {
  let data = dt['data'];
  // 将每个节点的 name 字段复制为 id 和 label（G6 要求）
  for (let t of data['nodes']) {
    t['id'] = t['name'];
    t['label'] = t['name'];
  }
  let new_dt = {};
  new_dt['edges'] = data['links']; // links → edges
  new_dt['nodes'] = data['nodes'];
  return new_dt;
}

/**
 * 将 graph2 的节点和边合并到 graph1 中（去重）
 * @param {G6.Graph} graph1 - 目标图实例
 * @param {Object} graph2 - 要合并的普通对象 { nodes: [...], edges: [...] }
 */
function mergeGraphs(graph1, graph2) {
  const nodes2 = graph2.nodes || [];
  const edges2 = graph2.edges || [];

  // 构建 graph1 中已存在的节点 ID 集合（用于去重）
  const existingNodeIds = new Set(
    graph1.getNodes().map(node => node.get('id'))
  );

  // 构建 graph1 中已存在的无向边集合（标准化 key，如 "A|B"）
  const existingEdgeKeys = new Set();
  graph1.getEdges().forEach(edge => {
    const source = edge.getSource().get('id');
    const target = edge.getTarget().get('id');
    const key = [source, target].sort().join('|'); // 无向边，排序保证唯一性
    existingEdgeKeys.add(key);
  });

  // 添加 graph2 中的新节点（跳过重复）
  nodes2.forEach(nodeModel => {
    if (nodeModel.id == null) {
      console.warn('跳过无 id 的节点:', nodeModel);
      return;
    }
    if (!existingNodeIds.has(nodeModel.id)) {
      graph1.addItem('node', { ...nodeModel });
      existingNodeIds.add(nodeModel.id); // 防止后续重复添加
    }
  });

  // 添加 graph2 中的新边（跳过重复，且确保两个端点都存在）
  edges2.forEach(edgeModel => {
    const { source, target } = edgeModel;
    if (source == null || target == null) {
      console.warn('跳过无效边（缺少 source 或 target）:', edgeModel);
      return;
    }
    // 只有当两个端点都已存在于图中时才添加边
    if (!existingNodeIds.has(source) || !existingNodeIds.has(target)) {
      console.warn(`跳过边  $ {source} ->  $ {target}：端点节点不存在`);
      return;
    }
    const edgeKey = [source, target].sort().join('|');
    if (!existingEdgeKeys.has(edgeKey)) {
      graph1.addItem('edge', { ...edgeModel });
      existingEdgeKeys.add(edgeKey);
    }
  });
}

/**
 * 更新图的视觉样式（边颜色）并刷新下拉选择框选项
 * @param {G6.Graph} graph - 图实例
 */
function update_graph(graph) {
  const edges = graph.getEdges();
  // 遍历所有边，根据 strength 设置颜色
  edges.forEach(edge => {
    graph.updateItem(edge, {
      style: {
        stroke: map_dict[edge.getModel().strength], // 使用 map_dict 映射颜色
      }
    });
  });

  // 清空两个下拉菜单（用于寻路起点/终点选择）
  select1.innerHTML = '';
  select2.innerHTML = '';

  // 为每个节点在两个下拉框中添加选项
  const nodes = graph.getNodes();
  nodes.forEach(node => {
    const option1 = document.createElement('option');
    option1.value = node.getModel().id;
    option1.textContent = node.getModel().id;
    select1.appendChild(option1);

    const option2 = document.createElement('option');
    option2.value = node.getModel().id;
    option2.textContent = node.getModel().id;
    select2.appendChild(option2);
  });
}

/**
 * 为图添加双击节点扩展功能：点击节点后自动请求其关联概念并合并到图中
 * @param {G6.Graph} graph - 图实例
 */
function addnodes(graph) {
  graph.on('node:dblclick', async function (e) {
    let concept = e.item.getModel().id; // 获取被双击节点的名称
    let d = await fetch_quick_search(concept); // 请求该概念的关联数据
    if (d.code > 200) {
      alert(d.detail); // 若请求失败，弹出错误信息
      return;
    }
    let data = preprocess(d); // 预处理数据
    graph.setAutoPaint(false); // 暂停自动重绘以提升性能
    mergeGraphs(graph, data); // 合并新数据
    graph.setAutoPaint(true);
    graph.layout(); // 重新布局
    update_graph(graph); // 更新样式和下拉框
  });
}

/**
 * 主绘图函数：基于输入数据创建并渲染 G6 图谱
 * @param {Object} input - 原始图数据（含 nodes 和 links）
 * @returns {G6.Graph} - 创建的图实例
 */
function draw_main(input) {
  let data = preprocess(input);

  // 创建 Tooltip 插件：鼠标悬停显示节点/边详情
  const tooltip = new G6.Tooltip({
    offsetX: 10,
    offsetY: 10,
    fixToNode: [1, 0.5],
    itemTypes: ['node', 'edge'],
    getContent: (e) => {
      const outDiv = document.createElement('div');
      outDiv.style.width = 'fit-content';
      outDiv.style.height = 'fit-content';
      const model = e.item.getModel();
      if (e.item.getType() === 'node') {
        // 节点提示：显示名称和领域
        outDiv.innerHTML = `名称：  $ {model.name}<br/>领域： $ {model.domain}`;
      } else {
        // 边提示：显示源、目标、关系描述和强度
        const edge = e.item;
        const source = e.item.getSource();
        const target = e.item.getTarget();
        outDiv.innerHTML = `来源： $ {source.getModel().name}<br/>去向： $ {target.getModel().name}<br/>关联：  $ {edge.getModel().relation}<br/>强度:  $ {edge.getModel().strength}`;
      }
      return outDiv;
    },
  });

  // 初始化 G6 图实例
  var graph = new G6.Graph({
    container: 'mountNode', // 渲染容器
    width: window.innerWidth,
    height: window.innerHeight,
    fitView: true, // 自动缩放以适应画布
    layout: {
      type: 'force', // 力导向布局
      edgeStrength: 0.7,
    },
    plugins: [tooltip], // 启用 tooltip
    modes: {
      default: ['drag-canvas', 'zoom-canvas'], // 默认交互模式
    },
    defaultNode: {
      size: 30,
      color: 'steelblue',
      style: { lineWidth: 2, fill: '#fff' },
      labelCfg: {
        style: { fontSize: 8, fontWeight: 'normal' }
      }
    },
    defaultEdge: {
      style: { stroke: '#e2e2e2', lineWidth: 2 }
    },
    // 定义不同状态下的样式（如高亮、变暗、寻路路径等）
    nodeStateStyles: {
      highlight: { opacity: 1 },
      dark: { opacity: 0.2 },
      findingPath: { opacity: 0.2 },
      tracePath: { stroke: '#ff0000', opacity: 1 }
    },
    edgeStateStyles: {
      highlight: { opacity: 1 },
      dark: { opacity: 0.2 },
      findingPath: { stroke: '#00ff00', opacity: 0.2 },
      tracePath: { stroke: '#ff0000', opacity: 1 }
    },
  });

  graph.data(data); // 加载数据

  /**
   * 清除所有节点和边的状态（恢复默认）
   */
  function clearAllStats() {
    graph.setAutoPaint(false);
    graph.getNodes().forEach(function (node) {
      graph.clearItemStates(node);
    });
    graph.getEdges().forEach(function (edge) {
      graph.clearItemStates(edge);
    });
    graph.paint();
    graph.setAutoPaint(true);
  }

  // 鼠标进入节点：高亮该节点及其邻居，其余变暗
  graph.on('node:mouseenter', function (e) {
    if (infinding) return; // 寻路模式下禁用此交互
    const item = e.item;
    graph.setAutoPaint(false);
    // 所有节点先变暗
    graph.getNodes().forEach(function (node) {
      graph.clearItemStates(node);
      graph.setItemState(node, 'dark', true);
    });
    // 当前节点高亮
    graph.setItemState(item, 'dark', false);
    graph.setItemState(item, 'highlight', true);
    // 高亮与当前节点相连的边和邻居节点
    graph.getEdges().forEach(function (edge) {
      if (edge.getSource() === item) {
        graph.setItemState(edge.getTarget(), 'dark', false);
        graph.setItemState(edge.getTarget(), 'highlight', true);
        graph.setItemState(edge, 'highlight', true);
        edge.toFront();
      } else if (edge.getTarget() === item) {
        graph.setItemState(edge.getSource(), 'dark', false);
        graph.setItemState(edge.getSource(), 'highlight', true);
        graph.setItemState(edge, 'highlight', true);
        edge.toFront();
      } else {
        graph.setItemState(edge, 'highlight', false);
        graph.setItemState(edge, 'dark', true);
      }
    });
    graph.paint();
    graph.setAutoPaint(true);
  });

  // 鼠标离开节点：清除所有高亮状态
  graph.on('node:mouseleave', function (e) {
    if (infinding) return;
    clearAllStats();
  });

  // 点击画布空白处：清除状态
  graph.on('canvas:click', clearAllStats);

  // 鼠标进入边：高亮该边及其两端节点，其余变暗
  graph.on('edge:mouseenter', function (e) {
    // 同步边信息到表单字段（用于编辑？）
    document.getElementById('edge_source').value = e.item.getModel().source;
    document.getElementById('edge_target').value = e.item.getModel().target;
    document.getElementById('relation').value = e.item.getModel().relation;
    document.getElementById('strength').value = e.item.getModel().strength;

    if (infinding) return;
    const item = e.item;
    const sourceNode = item.getSource();
    const targetNode = item.getTarget();
    graph.setAutoPaint(false);

    // 所有节点变暗，除了该边的两个端点
    graph.getNodes().forEach(function (node) {
      if (node !== sourceNode && node !== targetNode) {
        graph.setItemState(node, 'dark', true);
        graph.setItemState(node, 'hightlight', false); // 注意：此处拼写应为 highlight（但不影响功能）
      }
    });

    // 所有边变暗，除了当前边
    graph.getEdges().forEach(function (edge) {
      if (edge != item) {
        graph.setItemState(edge, 'dark', true);
        graph.setItemState(edge, 'hightlight', false); // 同上
      }
    });

    // 高亮两个端点和当前边
    [sourceNode, targetNode].forEach(function (node) {
      graph.setItemState(node, 'dark', false);
      graph.setItemState(node, 'highlight', true);
    });
    graph.setItemState(item, 'dark', false);
    graph.setItemState(item, 'highlight', true);
    graph.paint();
    graph.setAutoPaint(true);
  });

  // 鼠标离开边：清除状态
  graph.on('edge:mouseleave', function (e) {
    if (infinding) return;
    clearAllStats();
  });

  // 启用双击扩展功能
  addnodes(graph);

  // 渲染图
  graph.render();

  // 初始更新样式和下拉框
  update_graph(graph);

  return graph;
}

// 页面加载完成后绑定搜索按钮事件
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('searchbtn').addEventListener('click', async (e) => {
    const concept = document.getElementById('search').value; // 获取用户输入的概念
    let resp = await fetch_gen(concept); // 请求主图谱数据
    if (resp.code > 200) {
      alert(resp.detail);
      return;
    }
    let graph = draw_main(resp); // 绘制主图

    // 为“寻路”按钮绑定事件（启动路径查找）
    document.getElementById('findbtn').addEventListener('click', () => startFindPath(graph));

    // 为“寻路模式”复选框绑定状态切换
    document.getElementById('findMode').addEventListener('change', function () {
      if (this.checked) {
        change_to_finding_mode(graph); // 进入寻路模式
        infinding = true;
      } else {
        out_finding_mode(graph); // 退出寻路模式
        infinding = false;
      }
    });
  });
});