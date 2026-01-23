/**
 * 清除图中所有节点和边的状态（如高亮、变暗等），恢复默认样式
 * @param {G6.Graph} graph - AntV G6 图实例
 */
function clearAllStats(graph) {
  graph.setAutoPaint(false); // 暂停自动重绘以提升性能

  // 清除所有节点的状态
  graph.getNodes().forEach(function (node) {
    graph.clearItemStates(node);
  });

  // 清除所有边的状态
  graph.getEdges().forEach(function (edge) {
    graph.clearItemStates(edge);
  });

  graph.paint(); // 手动触发一次重绘
  graph.setAutoPaint(true); // 恢复自动重绘
}

/**
 * 进入“寻路模式”：
 *   - 清除当前所有状态
 *   - 将所有节点和边设置为 'findingPath' 状态（通常表现为半透明）
 *   - 为后续路径选择做准备（下拉菜单已由调用方处理）
 * @param {G6.Graph} graph - AntV G6 图实例
 */
export function change_to_finding_mode(graph) {
  clearAllStats(graph); // 先清除已有状态

  // 将所有边设为 'findingPath' 状态（例如变绿、半透明）
  graph.getEdges().forEach(function (edge) {
    graph.setItemState(edge, 'findingPath', true);
  });

  // 将所有节点设为 'findingPath' 状态
  graph.getNodes().forEach(function (node) {
    graph.setItemState(node, 'findingPath', true);
  });

  // 获取两个下拉选择框元素（虽然未使用，但保留原逻辑）
  const select1 = document.getElementById('node1');
  const select2 = document.getElementById('node2');
}

/**
 * 退出“寻路模式”：清除所有状态，恢复默认视图
 * @param {G6.Graph} graph - AntV G6 图实例
 */
export function out_finding_mode(graph) {
  clearAllStats(graph);
}

/**
 * 找到从节点 a 到节点 b 的最大瓶颈路径（即路径上最小 strength 值尽可能大）
 * 使用改进的 Dijkstra 算法（优先队列按 bottleneck 降序）
 * 假设图为无向图，所有边双向连通
 *
 * @param {string} a - 起始节点 ID
 * @param {string} b - 目标节点 ID
 * @param {Object} graph - AntV G6 Graph 实例
 * @returns {{ nodes: string[], edges: string[] } | null} 
 *          返回路径上的节点 ID 列表和边 ID 列表；若不可达则返回 null
 */
function findMaxBottleneckPath(a, b, graph) {
  // 边界情况：检查起止节点是否存在
  const nodeMap = new Set(graph.getNodes().map(node => node.get('id')));
  if (!nodeMap.has(a) || !nodeMap.has(b)) {
    return null; // 节点不存在
  }

  // 构建邻接表（无向图）
  const adj = {};
  nodeMap.forEach(id => adj[id] = []);
  const edges = graph.getEdges();
  edges.forEach(edge => {
    const source = edge.getModel().source;
    const target = edge.getModel().target;
    const edgeId = edge.getModel().id;
    // 安全获取 strength：直接从 model 读取
    const strength = edge.getModel().strength;

    // 无向图：双向添加邻接关系
    adj[source].push({ target, edgeId, strength });
    adj[target].push({ target: source, edgeId, strength });
  });

  // 记录到达每个节点时的最大 bottleneck 值（用于剪枝优化）
  const maxBottleneckTo = {};
  nodeMap.forEach(id => maxBottleneckTo[id] = -Infinity);
  maxBottleneckTo[a] = Infinity; // 起点瓶颈为无穷大

  // 优先队列：按 bottleneck 降序排列（模拟最大堆）
  const pq = [{ nodeId: a, bottleneck: Infinity }];

  // 用于重建路径：记录每个节点的前驱及所经边
  const parent = {};
  parent[a] = null;

  // 主循环：类似 Dijkstra，但按 bottleneck 最大优先
  while (pq.length > 0) {
    // 简单排序模拟优先队列（实际项目中建议用堆结构优化）
    pq.sort((x, y) => y.bottleneck - x.bottleneck);
    const current = pq.shift();
    const u = current.nodeId;
    const currentBottleneck = current.bottleneck;

    // 剪枝：如果当前路径不如已记录的优，跳过
    if (currentBottleneck < maxBottleneckTo[u]) continue;

    // 遍历邻居
    for (const { target: v, edgeId, strength } of adj[u]) {
      // 新路径的瓶颈 = min(当前路径瓶颈, 当前边强度)
      const newBottleneck = Math.min(currentBottleneck, strength);

      // 如果找到更大的 bottleneck 到达 v，则更新
      if (newBottleneck > maxBottleneckTo[v]) {
        maxBottleneckTo[v] = newBottleneck;
        parent[v] = { from: u, viaEdge: edgeId };
        pq.push({ nodeId: v, bottleneck: newBottleneck });
      }
    }
  }

  // 若目标节点不可达
  if (maxBottleneckTo[b] === -Infinity) {
    return null;
  }

  // 从终点回溯重建路径
  const pathNodes = [];
  const pathEdges = [];
  let cur = b;
  while (cur !== null) {
    pathNodes.unshift(cur); // 节点插入开头
    const p = parent[cur];
    if (p && p.viaEdge) {
      pathEdges.unshift(p.viaEdge); // 边也插入开头
    }
    cur = p ? p.from : null;
  }

  return { nodes: pathNodes, edges: pathEdges };
}

/**
 * 高亮指定路径：为路径上的节点和边设置 'tracePath' 状态（通常为红色高亮）
 * @param {G6.Graph} graph - 图实例
 * @param {string[]} nodeIds - 路径上的节点 ID 列表
 * @param {string[]} edgeIds - 路径上的边 ID 列表
 */
function highlightPath(graph, nodeIds, edgeIds) {
  // 高亮节点
  nodeIds.forEach(id => {
    const node = graph.findById(id);
    if (node) {
      graph.setItemState(node, 'tracePath', true);
    }
  });

  // 高亮边
  edgeIds.forEach(id => {
    const edge = graph.findById(id);
    if (edge) {
      graph.setItemState(edge, 'tracePath', true);
    }
  });
}

/**
 * 启动路径查找流程：
 *   - 从页面下拉框获取起点和终点
 *   - 校验输入有效性
 *   - 调用 findMaxBottleneckPath 查找路径
 *   - 若成功则高亮路径，否则弹出错误提示
 * @param {G6.Graph} graph - 图实例
 */
export function startFindPath(graph) {
  let id1 = '';
  let id2 = '';

  // 从 DOM 获取用户选择的起点和终点
  const selectElement1 = document.getElementById('node1');
  if (selectElement1) {
    id1 = selectElement1.value;
  }
  const selectElement2 = document.getElementById('node2');
  if (selectElement2) {
    id2 = selectElement2.value;
  }

  // 输入校验
  if (id1 === id2) {
    alert('两个节点不能一样');
    return;
  }
  if (id1 === 'default' || id2 === 'default') {
    alert('有一个节点未作出选择');
    return;
  }

  // 查找最大瓶颈路径
  let result = findMaxBottleneckPath(id1, id2, graph);

  if (result) {
    // 高亮返回的路径
    highlightPath(graph, result['nodes'], result['edges']);
  } else {
    alert('节点不可达');
  }
}