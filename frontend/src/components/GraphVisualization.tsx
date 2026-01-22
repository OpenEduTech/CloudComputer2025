import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ConceptNode, ConceptEdge } from '../services/api';
import './GraphVisualization.css';

interface GraphProps {
  nodes: ConceptNode[];
  edges: ConceptEdge[];
  onNodeClick?: (node: ConceptNode) => void;
}

const GraphVisualization: React.FC<GraphProps> = ({ nodes, edges, onNodeClick }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [zoomLevel, setZoomLevel] = useState(0.65);
  const zoomRef = useRef<any>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const width = 1200;
    const height = 600;  // 调整高度以匹配实际画布

    // 清空之前的内容
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('style', 'max-width: 100%; height: auto;');

    const g = svg.append('g');

    // 添加缩放功能
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        setZoomLevel(event.transform.k);
      });

    zoomRef.current = zoom;
    svg.call(zoom as any);
    
    // 设置初始缩放为65%，并将画布中心对齐到视口中心
    const initialScale = 0.65;
    const translateX = (width * (1 - initialScale)) / 2;
    const translateY = (height * (1 - initialScale)) / 2;
    svg.call(zoom.transform as any, d3.zoomIdentity.translate(translateX, translateY).scale(initialScale));

    // 学科颜色映射
    const colorScale = d3.scaleOrdinal<string>()
      .domain(['数学', '物理', '化学', '生物', '计算机', '社会学'])
      .range(['#FF6B6B', '#4ECDC4', '#95E1D3', '#F38181', '#AA96DA', '#FCBAD3']);

    // 识别节点类型
    const inputNodes = nodes.filter((n: any) => n.is_input);  // 输入节点（功能3）
    const bridgeNodes = nodes.filter((n: any) => n.is_bridge);  // 桥接节点（功能3）
    const isBridgeMode = inputNodes.length > 0;  // 如果有输入节点，说明是bridge模式
    
    // 根节点（非bridge模式使用）
    const rootNode = isBridgeMode ? null : (nodes.find((n: any) => n.depth === 0) || nodes[0]);
    
    console.log('[Graph] Bridge模式:', isBridgeMode);
    console.log('[Graph] 输入节点数:', inputNodes.length);
    console.log('[Graph] 桥接节点数:', bridgeNodes.length);
    if (rootNode) {
      console.log('[Graph] 根节点:', rootNode.id, rootNode.label);
    }
    console.log('[Graph] 总节点数:', nodes.length);
    console.log('[Graph] 总边数:', edges.length);
    console.log('[Graph] 边列表:', edges.map((e: any) => `${e.source} -> ${e.target}`));
    console.log('[Graph] 边详细信息 - 完整数据:', edges);
    console.log('[Graph] 第一条边的完整数据:', edges[0]);
    console.log('[Graph] 第一条边的reasoning字段:', edges[0]?.reasoning);
    console.log('[Graph] 节点ID列表:', nodes.map((n: any) => n.id));
    
    // 检查第一条边的source和target具体值
    if (edges.length > 0) {
      const firstEdge = edges[0];
      const sourceId = typeof firstEdge.source === 'object' ? (firstEdge.source as any).id : firstEdge.source;
      const targetId = typeof firstEdge.target === 'object' ? (firstEdge.target as any).id : firstEdge.target;
      console.log('[Graph] 第一条边 - sourceId:', sourceId, 'targetId:', targetId);
    }
    
    // 检查边的source和target是否存在于节点中
    const nodeIds = new Set(nodes.map((n: any) => n.id));
    console.log('[Graph] 所有节点ID:', JSON.stringify(Array.from(nodeIds)));
    
    const edgesValid = edges.every((e: any) => {
      // 边的source/target可能是字符串ID或对象引用，需要提取ID
      const sourceId = typeof e.source === 'object' ? (e.source as any).id : e.source;
      const targetId = typeof e.target === 'object' ? (e.target as any).id : e.target;
      const sourceExists = nodeIds.has(sourceId);
      const targetExists = nodeIds.has(targetId);
      
      if (!sourceExists || !targetExists) {
        console.error('[Graph] 边引用了不存在的节点:',
          'sourceId=' + sourceId, 'sourceExists=' + sourceExists,
          'targetId=' + targetId, 'targetExists=' + targetExists);
        return false;
      }
      return true;
    });
    
    if (!edgesValid) {
      console.error('[Graph] 发现无效的边，跳过渲染');
      return;
    }
    
    // 为每个节点计算目标半径（根据深度）
    const getTargetRadius = (node: any) => {
      if (isBridgeMode) {
        // Bridge模式：输入节点在外圈，桥接节点在内圈
        if (node.is_input) return 200;  // 输入节点在外圈
        if (node.is_bridge) return 0;   // 桥接节点在中心区域
        return 150;  // 其他节点
      } else {
        // 普通模式：根据depth设置半径
        const depth = node.depth || (rootNode && node.id === rootNode.id ? 0 : 1);
        if (depth === 0) return 0; // 根节点在中心
        return 150 * depth; // 每一层距离中心150px
      }
    };

    // 设置初始位置
    if (isBridgeMode) {
      // Bridge模式：输入节点均匀分布在外圈
      inputNodes.forEach((node: any, index: number) => {
        const angle = (index / inputNodes.length) * 2 * Math.PI;
        const radius = 200;
        node.x = width / 2 + radius * Math.cos(angle);
        node.y = height / 2 + radius * Math.sin(angle);
      });
      // 桥接节点在中心区域随机分布
      bridgeNodes.forEach((node: any) => {
        const angle = Math.random() * 2 * Math.PI;
        const radius = Math.random() * 80;
        node.x = width / 2 + radius * Math.cos(angle);
        node.y = height / 2 + radius * Math.sin(angle);
      });
    } else {
      // 普通模式：子节点围绕根节点均匀分布
      const childNodes = nodes.filter((n: any) => rootNode && n.id !== rootNode.id);
      childNodes.forEach((node: any, index: number) => {
        const angle = (index / childNodes.length) * 2 * Math.PI;
        const radius = 150;
        node.x = width / 2 + radius * Math.cos(angle);
        node.y = (height / 2 - 190) + radius * Math.sin(angle);
      });
    }
    
    // 力导向图模拟
    const centerY = isBridgeMode ? height / 2 : height / 2 - 190;  // Bridge模式居中，普通模式偏上
    
    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(edges)
        .id((d: any) => d.id)
        .distance((d: any) => {
          if (isBridgeMode) {
            // Bridge模式：输入节点到桥接节点的距离
            const source = d.source as any;
            const target = d.target as any;
            if ((source.is_input && target.is_bridge) || (source.is_bridge && target.is_input)) {
              return 150;  // 输入节点到桥接节点
            }
            return 100;
          } else {
            // 普通模式：根据层级调整边长度
            const sourceDepth = (d.source as any).depth || 0;
            const targetDepth = (d.target as any).depth || 0;
            return 60 + Math.abs(targetDepth - sourceDepth) * 30;
          }
        })
        .strength(1.2))
      .force('charge', d3.forceManyBody().strength(isBridgeMode ? -500 : -300))  // Bridge模式排斥力更强
      .force('center', d3.forceCenter(width / 2, centerY))
      .force('collision', d3.forceCollide().radius(50))
      // 径向力：将节点推向各自层级的圆环上
      .force('radial', d3.forceRadial((d: any) => getTargetRadius(d), width / 2, centerY).strength(isBridgeMode ? 0.8 : 1.0));

    // 固定根节点位置（仅普通模式）
    if (!isBridgeMode && rootNode) {
      simulation.nodes().forEach((node: any) => {
        if (node.id === rootNode.id) {
          node.fx = width / 2;
          node.fy = centerY;
        }
      });
    }

    // 绘制边（每条边包含line和title）
    const linkGroup = g.append('g')
      .attr('class', 'links')
      .selectAll('g')
      .data(edges)
      .enter()
      .append('g');

    // 添加连线
    linkGroup.append('line')
      .attr('class', 'link')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.5)
      .attr('stroke-width', (d) => Math.max(2, d.weight * 5))
      .style('cursor', 'help');  // 鼠标悬停时显示帮助图标
    
    // 为连线添加tooltip显示关联解释
    linkGroup.append('title')
      .text((d: any) => {
        const sourceLabel = typeof d.source === 'object' ? d.source.label : d.source;
        const targetLabel = typeof d.target === 'object' ? d.target.label : d.target;
        console.log('[Tooltip] Edge:', sourceLabel, '->', targetLabel, 'reasoning:', d.reasoning);
        
        // 直接返回reasoning字段，如果为空才使用默认文本
        if (d.reasoning && d.reasoning.trim()) {
          // 在tooltip中同时显示边的两端节点和关联描述
          return `${sourceLabel} → ${targetLabel}\n\n${d.reasoning}`;
        }
        // 如果没有reasoning，使用默认文本
        return `${sourceLabel} 与 ${targetLabel} 存在概念上的关联`;
      });

    // 绘制节点组
    const nodeGroup = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .call(d3.drag<any, any>()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));

    // 绘制节点圆圈（增强动画和交互效果，根据类型调整大小）
    nodeGroup.append('circle')
      .attr('r', (d: any) => {
        // Bridge模式：输入节点大，桥接节点中等
        if (d.is_input) {
          return 30 + (d.credibility || 0) * 5;  // 输入节点最大
        }
        if (d.is_bridge) {
          return 20 + (d.credibility || 0) * 3;  // 桥接节点中等
        }
        // 普通模式：根据深度计算节点大小
        const depth = d.depth || 0;
        const baseSize = depth === 0 ? 35 : (depth === 1 ? 18 : 12);  // 根节点35，一级子节点18，二级+12
        const credibilityBonus = d.credibility ? d.credibility * 5 : 0;
        return baseSize + credibilityBonus;
      })
      .attr('fill', (d) => colorScale(d.discipline))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('filter', 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2))')
      .on('click', function(event, d) {
        event.stopPropagation();
        // 移除之前的选中状态
        svg.selectAll('.node').classed('selected', false);
        // 添加当前选中状态
        d3.select((this as any).parentNode).classed('selected', true);
        if (onNodeClick) onNodeClick(d);
      })
      .on('mouseenter', function(_event, d: any) {
        const element = d3.select(this);
        element.interrupt(); // 中断之前的动画
        
        // 计算当前半径
        let currentRadius;
        if (d.is_input) {
          currentRadius = 30 + (d.credibility || 0) * 5;
        } else if (d.is_bridge) {
          currentRadius = 20 + (d.credibility || 0) * 3;
        } else {
          const depth = d.depth || 0;
          const baseSize = depth === 0 ? 35 : (depth === 1 ? 18 : 12);
          const credibilityBonus = d.credibility ? d.credibility * 5 : 0;
          currentRadius = baseSize + credibilityBonus;
        }
        
        element
          .transition()
          .duration(200)
          .attr('r', currentRadius * 1.3)
          .attr('stroke-width', 4)
          .style('filter', 'drop-shadow(0 8px 16px rgba(102, 126, 234, 0.5))');
      })
      .on('mouseleave', function(_event, d: any) {
        const isSelected = d3.select((this as any).parentNode).classed('selected');
        if (!isSelected) {
          const element = d3.select(this);
          element.interrupt(); // 中断之前的动画
          
          // 计算当前半径
          let currentRadius;
          if (d.is_input) {
            currentRadius = 30 + (d.credibility || 0) * 5;
          } else if (d.is_bridge) {
            currentRadius = 20 + (d.credibility || 0) * 3;
          } else {
            const depth = d.depth || 0;
            const baseSize = depth === 0 ? 35 : (depth === 1 ? 18 : 12);
            const credibilityBonus = d.credibility ? d.credibility * 5 : 0;
            currentRadius = baseSize + credibilityBonus;
          }
          
          element
            .transition()
            .duration(200)
            .attr('r', currentRadius)
            .attr('stroke-width', 2)
            .style('filter', 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2))');
        }
      });

    // 节点标签（Bridge模式所有节点居中，普通模式根节点居中、子节点右侧）
    nodeGroup.append('text')
      .text((d) => d.label)
      .attr('font-size', 13)
      .attr('font-weight', 600)
      .attr('dx', (d: any) => {
        // Bridge模式：所有节点文本居中
        if (isBridgeMode) return 0;
        // 普通模式：根节点居中，子节点右侧
        const depth = d.depth || 0;
        if (depth === 0) return 0;
        return (d.credibility ? 10 + d.credibility * 8 : 15) + 8;
      })
      .attr('dy', (d: any) => {
        // Bridge模式：所有节点文本垂直居中
        if (isBridgeMode) return 5;
        // 普通模式：根节点居中，子节点正常
        const depth = d.depth || 0;
        if (depth === 0) return 5;
        return 4;
      })
      .attr('text-anchor', (d: any) => {
        // Bridge模式：所有节点居中对齐
        if (isBridgeMode) return 'middle';
        // 普通模式：根节点居中，子节点左对齐
        const depth = d.depth || 0;
        return depth === 0 ? 'middle' : 'start';
      })
      .attr('fill', '#333')
      .attr('pointer-events', 'none')
      .style('text-shadow', '0 2px 4px rgba(255, 255, 255, 0.8)');

    // 添加标题（悬浮提示）
    nodeGroup.append('title')
      .text((d) => `${d.label}\n学科: ${d.discipline}\n定义: ${d.definition}\n可信度: ${(d.credibility * 100).toFixed(0)}%`);

    // 更新位置
    simulation.on('tick', () => {
      linkGroup.selectAll('line')
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      nodeGroup.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    // 拖拽函数
    function dragStarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragEnded(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    // 清理函数
    return () => {
      simulation.stop();
    };
  }, [nodes, edges, onNodeClick]);

  return (
    <div className="graph-container">
      <svg ref={svgRef}></svg>
      <div className="zoom-controls">
        <button
          className="zoom-btn"
          onClick={() => {
            if (!svgRef.current || !zoomRef.current) return;
            const svg = d3.select(svgRef.current);
            svg.transition().duration(300).call(zoomRef.current.scaleBy, 1.2);
          }}
          title="放大"
        >
          +
        </button>
        <span className="zoom-level">{Math.round(zoomLevel * 100)}%</span>
        <button
          className="zoom-btn"
          onClick={() => {
            if (!svgRef.current || !zoomRef.current) return;
            const svg = d3.select(svgRef.current);
            svg.transition().duration(300).call(zoomRef.current.scaleBy, 0.833);
          }}
          title="缩小"
        >
          −
        </button>
        <button
          className="zoom-btn reset-btn"
          onClick={() => {
            if (!svgRef.current || !zoomRef.current) return;
            const svg = d3.select(svgRef.current);
            svg.transition().duration(300).call(zoomRef.current.transform, d3.zoomIdentity);
          }}
          title="重置"
        >
          ⟲
        </button>
      </div>
    </div>
  );
};

export default GraphVisualization;
