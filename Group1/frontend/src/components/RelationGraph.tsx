import React from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import type { Node, Edge } from "../api";

interface RelationGraphProps {
  selectedNode: Node;
  nodes: Node[];
  edges: Edge[];
}

const DOMAIN_COLORS: Record<string, string> = {
  Core: "#f59e0b",
  Mathematics: "#6366f1",
  Physics: "#a78bfa",
  "Computer Science": "#22d3ee",
  Biology: "#f472b6",
  Economics: "#fbbf24",
  Bridge: "#38bdf8"
};

function colorFor(domain: string): string {
  return DOMAIN_COLORS[domain] || "#94a3b8";
}

export function RelationGraph({ selectedNode, nodes, edges }: RelationGraphProps) {
  // 获取与选中节点直接相关的边
  const relatedEdges = edges.filter(edge => 
    edge.source === selectedNode.id || edge.target === selectedNode.id
  );
  
  // 获取所有相关的节点ID
  const relatedNodeIds = new Set<string>();
  relatedNodeIds.add(selectedNode.id);
  
  relatedEdges.forEach(edge => {
    relatedNodeIds.add(edge.source);
    relatedNodeIds.add(edge.target);
  });
  
  // 创建节点映射
  const nodeMap = new Map<string, Node>();
  nodes.forEach(node => {
    if (relatedNodeIds.has(node.id)) {
      nodeMap.set(node.id, node);
    }
  });
  
  // 准备图表数据
  const chartNodes = Array.from(nodeMap.values()).map(node => {
    const isSelected = node.id === selectedNode.id;
    return {
      id: node.id,
      name: node.name.replace(/\s*\([^\)]*\)\s*.*$/g, '')
        .replace(/\s*in\s+[a-zA-Z\s]+(?:\([a-zA-Z\s]+\))?$/i, ''),
      symbolSize: isSelected ? 80 : 40,
      itemStyle: {
        color: new echarts.graphic.RadialGradient(0.3, 0.3, 1, [
          { offset: 0, color: "#fff" },
          { offset: 0.2, color: colorFor(node.domain) },
          { offset: 1, color: "rgba(0,0,0,0.6)" }
        ]),
        shadowBlur: isSelected ? 40 : 15,
        shadowColor: colorFor(node.domain),
        emphasis: {
          shadowBlur: isSelected ? 80 : 50,
          shadowColor: `${colorFor(node.domain)}80`, // 增加透明度
          borderWidth: 3,
          borderColor: colorFor(node.domain),
          // 脉冲动画
          animation: {
            type: 'pulse',
            duration: 2000,
            easing: 'ease-in-out',
            loop: true
          },
          // 发光边框动画
          animationDelay: 0,
          animationDuration: 1000,
          animationEasing: 'ease-out'
        }
      },
      label: {
        show: true,
        formatter: `${node.name.replace(/\s*\([^\)]*\)\s*.*$/g, '').replace(/\s*in\s+[a-zA-Z\s]+(?:\([a-zA-Z\s]+\))?$/i, '')} (${node.domain})`,
        position: "inside",
        color: "#ffffff",
        fontSize: isSelected ? 14 : 12,
        fontWeight: isSelected ? 'bold' : 'normal',
        align: "center",
        verticalAlign: "middle"
      },
      emphasis: {
        label: {
          show: true,
          formatter: `{b}\n${node.domain}`,
          color: "#ffffff",
          fontSize: isSelected ? 16 : 14,
          fontWeight: 'bold',
          lineHeight: 20,
          textShadowBlur: 10,
          textShadowColor: `${colorFor(node.domain)}FF`,
          animation: {
            type: 'scale',
            duration: 300,
            easing: 'ease-out'
          }
        }
      },
      value: 1,
      domain: node.domain
    };
  });
  
  const chartEdges = relatedEdges.map(edge => {
    const sourceNode = nodeMap.get(edge.source);
    const targetNode = nodeMap.get(edge.target);
    const lineColor = new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      {
        offset: 0, 
        color: sourceNode ? colorFor(sourceNode.domain) : "#94a3b8"
      },
      {
        offset: 1, 
        color: targetNode ? colorFor(targetNode.domain) : "#94a3b8"
      }
    ]);
    
    return {
      source: edge.source,
      target: edge.target,
      value: edge.confidence,
      label: {
        show: true,
        formatter: edge.relation.replace("_", " "),
        color: "#94a3b8",
        fontSize: 11,
        fontWeight: 'bold',
        backgroundColor: "rgba(2, 6, 23, 0.7)",
        padding: [2, 6],
        borderRadius: 4
      },
      lineStyle: {
        width: 2,
        color: lineColor,
        curveness: 0.3,
        emphasis: {
          width: 2,
          color: lineColor
        }
      },
      emphasis: {
        label: {
          show: false
        }
      }
    };
  });
  
  const option = {
    backgroundColor: "transparent",
    tooltip: {
      show: false
    },
    series: [
      {
        type: 'graph',
        layout: 'circular',
        animation: true,
        animationDuration: 1500,
        animationEasingUpdate: 'quinticInOut',
        data: chartNodes,
        links: chartEdges,
        roam: true,
        draggable: true,
        label: {
          show: true,
          position: 'right'
        },
        force: {
          repulsion: 1000,
          edgeLength: [100, 200]
        },
        lineStyle: {
          curveness: 0.3,
          opacity: 0.6
        }
      }
    ]
  };
  
  return (
    <div style={{
      width: "100%",
      height: "100%",
      minHeight: "300px",
      border: "1px solid rgba(34, 211, 238, 0.2)",
      borderRadius: "12px",
      overflow: "hidden"
    }}>
      <ReactECharts 
        option={option} 
        style={{ height: "100%", width: "100%" }} 
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
}