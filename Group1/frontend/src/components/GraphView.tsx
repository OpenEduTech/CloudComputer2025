import React from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import type { Edge, Node } from "../api";

const DOMAIN_COLORS: Record<string, string> = {
  Core: "#f59e0b", // 核心节点使用琥珀色
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

export function GraphView(props: {
  nodes: Node[];
  edges: Edge[];
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string | null, source: string, target: string, relation: string) => void;
  focusNodeId?: string | null;
  dimToPathEdgeIds?: Set<string>;
  enableEdgeFlow?: boolean;
}) {
  const chartRef = React.useRef<ReactECharts>(null);

  // 粒子流动动画逻辑
  const updateEdgeFlow = React.useCallback(() => {
    if (!props.enableEdgeFlow) return;
    const chart = chartRef.current?.getEchartsInstance?.();
    if (!chart) return;

    try {
      const option = chart.getOption();
      const series = (option.series as any[])?.[0] || {};
      const nodes = series.data || [];
      const posById = new Map<string, { x: number; y: number }>();

      nodes.forEach((node: any, index: number) => {
        if (node.id) {
          try {
            const position = chart.convertToPixel({ seriesIndex: 0, dataIndex: index }, [0, 0]);
            if (Array.isArray(position)) {
              posById.set(String(node.id), { x: position[0], y: position[1] });
            }
          } catch {
            posById.set(String(node.id), { x: 0, y: 0 });
          }
        }
      });

      let edgesToFlow = props.edges.slice(0, 30);
      const elements: any[] = [];

      edgesToFlow.forEach((e, idx) => {
        const s = posById.get(e.source);
        const t = posById.get(e.target);
        if (!s || !t) return;
        const isConflict = (e.flags || []).includes("conflict");
        const baseColor = isConflict ? "#ef4444" : "#22d3ee";
        const secondaryColor = isConflict ? "#f87171" : "#38bdf8";
        const baseId = `flow:${e.id ?? `${e.source}-${e.target}-${idx}`}`;
        
        // 计算连线角度（弧度）
        const angle = Math.atan2(t.y - s.y, t.x - s.x);

        // 增加粒子数量到3个，使流动更密集
        for (let k = 0; k < 3; k++) {
          const id = `${baseId}:${k}`;
          elements.push({
            id,
            type: "circle", // 改为圆形，更有科技感
            silent: true,
            z: 100,
            shape: { 
              cx: 0,  // 圆心位置
              cy: 0, 
              r: 2    // 半径
            },
            style: { 
              fill: baseColor, 
              opacity: 0.9, 
              shadowBlur: 20, 
              shadowColor: baseColor,
              // 添加描边效果
              stroke: secondaryColor,
              lineWidth: 1
            },
            x: s.x,
            y: s.y,
            rotation: angle, // 根据连线方向适度旋转
            origin: [0, 0], // 旋转原点
            keyframeAnimation: {
              duration: 2000 + (idx % 5) * 200,
              delay: (idx * 100 + k * 400) % 1800,
              loop: true,
              keyframes: [
                { percent: 0, x: s.x, y: s.y, style: { opacity: 0, shadowBlur: 5, fill: baseColor } },
                { percent: 0.2, style: { opacity: 1, shadowBlur: 20, fill: secondaryColor } },
                { percent: 0.5, style: { opacity: 0.9, shadowBlur: 15, fill: baseColor } },
                { percent: 0.8, style: { opacity: 0.7, shadowBlur: 10 } },
                { percent: 1, x: t.x, y: t.y, style: { opacity: 0, shadowBlur: 5, fill: secondaryColor } }
              ]
            }
          });
          
          // 添加拖尾效果
          for (let trail = 0; trail < 2; trail++) {
            const trailId = `${id}:trail${trail}`;
            elements.push({
              id: trailId,
              type: "circle",
              silent: true,
              z: 99,
              shape: { 
                cx: 0, 
                cy: 0, 
                r: 1.5 - trail * 0.5
              },
              style: { 
                fill: baseColor, 
                opacity: 0.5 - trail * 0.2,
                shadowBlur: 10, 
                shadowColor: baseColor
              },
              x: s.x,
              y: s.y,
              rotation: angle,
              origin: [0, 0],
              keyframeAnimation: {
                duration: 2000 + (idx % 5) * 200,
                delay: (idx * 100 + k * 400 + trail * 50) % 1800,
                loop: true,
                keyframes: [
                  { percent: 0, x: s.x, y: s.y, style: { opacity: 0 } },
                  { percent: 0.1 + trail * 0.05, style: { opacity: 0.4 - trail * 0.2 } },
                  { percent: 0.9, style: { opacity: 0.1 - trail * 0.05 } },
                  { percent: 1, x: t.x, y: t.y, style: { opacity: 0 } }
                ]
              }
            });
          }
        }
      });

      chart.setOption({ graphic: { elements } }, { replaceMerge: ["graphic"] as any });
    } catch (e) { /* ignore */ }
  }, [props.enableEdgeFlow, props.edges]);

  // 自动重绘监听
  React.useEffect(() => {
    const chart = chartRef.current?.getEchartsInstance?.();
    if (!chart) return;
    let t: any = null;
    const schedule = () => {
      if (t) clearTimeout(t);
      t = setTimeout(() => updateEdgeFlow(), 30); // 提高更新频率
    };
    chart.on("graphRoam", schedule);
    chart.on("finished", schedule);
    
    // 初始启动动画
    updateEdgeFlow();
    
    return () => {
      chart.off("graphRoam", schedule);
      chart.off("finished", schedule);
      if (t) clearTimeout(t);
    };
  }, [updateEdgeFlow]);
  
  // 添加固定时间间隔的动画更新
  React.useEffect(() => {
    if (!props.enableEdgeFlow) return;
    
    const timer = setInterval(updateEdgeFlow, 100);
    return () => clearInterval(timer);
  }, [props.enableEdgeFlow, updateEdgeFlow]);

  const option = React.useMemo(() => {
    const data = props.nodes.map((n) => {
      const baseName = n.name.replace(/\s*\([^)]*\)\s*.*$/g, '').replace(/\s*in\s+[a-zA-Z\s]+(?:\([a-zA-Z\s]+\))?$/i, '');
      const isCentral = baseName === "Entropy" || n.domain === "Core";
      const color = colorFor(n.domain);
      
      return {
        id: n.id,
        name: `${baseName} (${n.domain})`,
        symbolSize: isCentral ? 70 : 35 + (n.confidence || 0) * 20,
        itemStyle: {
          // 星球立体感：径向渐变
          color: new echarts.graphic.RadialGradient(0.3, 0.3, 1, [
            { offset: 0, color: "#fff" }, 
            { offset: 0.2, color: color },
            { offset: 1, color: "rgba(0,0,0,0.6)" }
          ]),
          shadowBlur: isCentral ? 40 : 15,
          shadowColor: color,
          borderWidth: 1,
          borderColor: "rgba(255,255,255,0.3)",
          // 添加丰富的动态效果
          emphasis: {
            shadowBlur: isCentral ? 80 : 50,
            shadowColor: `${color}80`, // 增加透明度
            borderWidth: 3,
            borderColor: color,
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
          position: "inside",
          color: "#e5e7eb",
          fontSize: isCentral ? 14 : 11,
          fontWeight: isCentral ? "bold" : "normal",
          textShadowBlur: 4,
          textShadowColor: color,
          align: "center",
          verticalAlign: "middle",
          emphasis: {
            color: "#ffffff",
            fontSize: isCentral ? 16 : 13,
            fontWeight: "bold",
            textShadowBlur: 10,
            textShadowColor: `${color}FF`,
            animation: {
              type: 'scale',
              duration: 300,
              easing: 'ease-out'
            }
          }
        },
        emphasis: {
          label: {
            show: true
          }
        },
        // 添加入场动画
        animationDelay: Math.random() * 1000,
        animationDuration: 1500,
        animationEasing: 'cubicOut'
      };
    });

    const links = props.edges.map((e, index) => {
        const isHighlighted = props.dimToPathEdgeIds?.has(String(e.id));
        const color = (e.flags || []).includes("conflict") ? "#ef4444" : "#22d3ee";
        
        return {
          source: e.source,
          target: e.target,
          value: e.relation,
          lineStyle: {
            color: color,
            width: isHighlighted ? 3 : 1.2,
            opacity: props.dimToPathEdgeIds ? (isHighlighted ? 0.9 : 0.1) : 0.6,
            curveness: 0.3, // 星轨弧度优化为0.3
            shadowBlur: isHighlighted ? 15 : 8,
            shadowColor: color,
            // 添加脉冲动画效果
            emphasis: {
              width: isHighlighted ? 4 : 2,
              opacity: 1,
              shadowBlur: 25,
              shadowColor: color,
              animation: {
                type: 'pulse',
                duration: 1500,
                easing: 'ease-in-out',
                loop: true
              }
            }
          },
          // 使用自定义的科幻风格箭头路径
          symbol: ["none", "path://M0,0 L12,6 L0,12 L3,6 Z"],
          symbolSize: [0, 12],
          // 为箭头添加发光效果
          itemStyle: {
            color: color,
            shadowBlur: 15,
            shadowColor: color
          },
          // 添加入场动画
          animationDelay: 500 + index * 50,
          animationDuration: 1500,
          animationEasing: 'cubicOut'
        };
      });

    return {
      backgroundColor: "transparent",
      tooltip: {
        show: true,
        backgroundColor: "rgba(5, 8, 20, 0.9)",
        borderColor: "rgba(34, 211, 238, 0.3)",
        textStyle: { color: "#e5e7eb", fontSize: 12 },
        padding: 8,
        maxWidth: 200,
        position: function(point: any, params: any, dom: any, rect: any, size: any) {
          // 自定义tooltip位置，确保在可视区域内且不影响点击
          const x = point[0];
          const y = point[1];
          const viewWidth = size.viewSize[0];
          const viewHeight = size.viewSize[1];
          const tooltipWidth = dom.offsetWidth;
          const tooltipHeight = dom.offsetHeight;
          
          // 默认显示在鼠标右侧
          let posX = x + 10;
          let posY = y - tooltipHeight / 2;
          
          // 确保不超出右边界
          if (posX + tooltipWidth > viewWidth) {
            posX = x - tooltipWidth - 10;
          }
          
          // 确保不超出上下边界
          if (posY < 0) {
            posY = 0;
          } else if (posY + tooltipHeight > viewHeight) {
            posY = viewHeight - tooltipHeight;
          }
          
          return [posX, posY];
        }
      },
      series: [
        {
          type: "graph",
          layout: "force",
          force: {
            repulsion: 800,
            edgeLength: [120, 200],
            gravity: 0.08
          },
          roam: true,
          draggable: true,
          emphasis: {
            focus: "adjacency",
            itemStyle: {
              shadowBlur: 30,
              shadowColor: "#22d3ee"
            },
            lineStyle: { 
              width: 4, 
              opacity: 1,
              shadowBlur: 15,
              shadowColor: "#22d3ee"
            },
            label: {
              fontSize: 12,
              fontWeight: "bold",
              textShadowBlur: 8,
              textShadowColor: "#22d3ee"
            }
          },
          data,
          links,
          lineStyle: { curveness: 0.3 } // 保持与links中的curveness一致
        }
      ]
    };
  }, [props.nodes, props.edges, props.dimToPathEdgeIds]);

  return (
    <ReactECharts
      ref={chartRef}
      option={option}
      style={{ height: "100%", width: "100%" }}
      onEvents={{
        click: (params: any) => {
          if (params.dataType === "node") props.onNodeClick?.(params.data.id);
          if (params.dataType === "edge") props.onEdgeClick?.(params.data.id, params.data.source, params.data.target, params.data.value);
        }
      }}
    />
  );
}