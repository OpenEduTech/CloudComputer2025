import React, { useEffect, useRef, useCallback, useState } from "react";
import ReactECharts from "echarts-for-react";
import GraphVisualization3D from "./GraphVisualization3D";
import "./GraphVisualization.css";

// 扩展的颜色调色板 - 30种不同的颜色
const COLOR_PALETTE = [
  "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
  "#1abc9c", "#e67e22", "#34495e", "#16a085", "#27ae60",
  "#2980b9", "#8e44ad", "#c0392b", "#d35400", "#f1c40f",
  "#e91e63", "#9c27b0", "#673ab7", "#3f51b5", "#2196f3",
  "#00bcd4", "#009688", "#4caf50", "#8bc34a", "#cddc39",
  "#ff9800", "#ff5722", "#795548", "#607d8b", "#ec407a",
];

const DOMAIN_COLORS = {
  Mathematics: "#e74c3c",
  Physics: "#3498db",
  "Computer Science": "#2ecc71",
  Biology: "#f39c12",
  Sociology: "#9b59b6",
  数学: "#e74c3c",
  物理学: "#3498db",
  计算机科学: "#2ecc71",
  生物学: "#f39c12",
  社会学: "#9b59b6",
  Unknown: "#95a5a6",
};

// 动态分配颜色的函数
const getDomainColor = (domain, allDomains) => {
  if (DOMAIN_COLORS[domain]) {
    return DOMAIN_COLORS[domain];
  }
  const domainList = Array.from(allDomains).sort();
  const index = domainList.indexOf(domain);
  return COLOR_PALETTE[index % COLOR_PALETTE.length];
};

function GraphVisualization({ data, onNodeClick, onNodeRightClick, loading }) {
  const chartRef = useRef(null);
  const lastClickTimeRef = useRef(0);
  const clickTimeoutRef = useRef(null);
  const [is3D, setIs3D] = useState(false);

  const getOption = () => {
    if (!data || !data.nodes || !data.edges) {
      return {};
    }

    // 获取所有学科
    const allDomains = new Set(data.nodes.map((n) => n.domain));

    // 转换节点数据
    const nodes = data.nodes.map((node) => ({
      id: node.id,
      name: node.label || node.id,
      symbolSize: node.type === "center" ? 80 : 50,
      itemStyle: {
        color: getDomainColor(node.domain, allDomains),
      },
      label: {
        show: true,
        fontSize: node.type === "center" ? 14 : 11,
        fontWeight: node.type === "center" ? "bold" : "normal",
      },
      category: node.domain,
      value: node.definition || node.domain,
      tooltip: {
        formatter: (params) => {
          return `
            <div style="padding: 10px;">
              <strong style="font-size: 16px;">${params.data.name}</strong><br/>
              <span style="color: #666;">学科：${node.domain}</span><br/>
              ${node.definition ? `<span style="color: #888; font-size: 12px;">${node.definition}</span>` : ""}
            </div>
          `;
        },
      },
    }));

    // 转换边数据
    const links = data.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      lineStyle: {
        width: Math.max(1, edge.strength / 2),
        opacity: 0.6,
        curveness: 0.2,
      },
      label: {
        show: false,
        formatter: edge.relation_type,
      },
      tooltip: {
        formatter: () => {
          return `
            <div style="padding: 10px; max-width: 300px;">
              <strong>${edge.relation_type}</strong><br/>
              <span style="color: #666;">强度：${edge.strength}/10</span><br/>
              <span style="color: #888; font-size: 12px;">${edge.explanation}</span>
            </div>
          `;
        },
      },
    }));

    // 获取所有学科类别
    const categories = Array.from(allDomains)
      .sort()
      .map((domain) => ({
        name: domain,
        itemStyle: {
          color: getDomainColor(domain, allDomains),
        },
      }));

    return {
      title: {
        text: "跨学科知识图谱",
        left: "center",
        top: 10,
        textStyle: {
          fontSize: 20,
          fontWeight: "bold",
          color: "#333",
        },
      },
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(255, 255, 255, 0.95)",
        borderColor: "#ddd",
        borderWidth: 1,
        textStyle: {
          color: "#333",
        },
      },
      legend: [
        {
          data: categories.map((c) => c.name),
          orient: "vertical",
          left: 10,
          top: 60,
          textStyle: {
            fontSize: 12,
          },
        },
      ],
      animationDuration: 1500,
      animationEasingUpdate: "quinticInOut",
      series: [
        {
          type: "graph",
          layout: "force",
          data: nodes,
          links: links,
          categories: categories,
          roam: true,
          label: {
            position: "bottom",
            show: true,
          },
          force: {
            repulsion: 300,
            gravity: 0.1,
            edgeLength: [100, 200],
            layoutAnimation: true,
            friction: 0.6,
          },
          emphasis: {
            focus: "adjacency",
            lineStyle: {
              width: 4,
            },
            label: {
              fontSize: 16,
            },
          },
          lineStyle: {
            color: "source",
            curveness: 0.2,
          },
        },
      ],
    };
  };

  const handleChartClick = useCallback(
    (params) => {
      if (params.dataType === "node" && !loading) {
        const nodeId = params.data.id;
        if (onNodeClick) {
          onNodeClick(nodeId);
        }
      }
    },
    [loading, onNodeClick],
  );

  const handleChartRightClick = useCallback(
    (params) => {
      if (params.event?.event) {
        params.event.event.preventDefault();
        params.event.event.stopPropagation();
      }

      const now = Date.now();
      if (now - lastClickTimeRef.current < 300) {
        console.log("防抖：忽略重复的右键点击");
        return false;
      }
      lastClickTimeRef.current = now;

      if (clickTimeoutRef.current) {
        clearTimeout(clickTimeoutRef.current);
      }

      clickTimeoutRef.current = setTimeout(() => {
        if (params.dataType === "node" && !loading) {
          const nodeId = params.data.id;
          console.log("执行右键点击处理:", nodeId);
          if (onNodeRightClick) {
            onNodeRightClick(nodeId);
          }
        }
      }, 50);

      return false;
    },
    [loading, onNodeRightClick],
  );

  const onEvents = {
    click: handleChartClick,
    contextmenu: handleChartRightClick,
  };

  useEffect(() => {
    return () => {
      if (clickTimeoutRef.current) {
        clearTimeout(clickTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className={`graph-visualization ${is3D ? "is-3d" : ""}`}>
      <div className="graph-controls">
        <button
          className={`toggle-3d-btn ${is3D ? "active" : ""}`}
          onClick={() => setIs3D((s) => !s)}
          title={is3D ? "切换回 2D 视图" : "切换到 3D 视图"}
        >
          {is3D ? "🌐 3D" : "📊 2D"}
        </button>
      </div>

      {is3D ? (
        <GraphVisualization3D
          data={data}
          onNodeClick={onNodeClick}
          onNodeRightClick={onNodeRightClick}
          loading={loading}
        />
      ) : data && data.nodes && data.nodes.length > 0 ? (
        <ReactECharts
          ref={chartRef}
          option={getOption()}
          style={{ height: "600px", width: "100%" }}
          onEvents={onEvents}
          notMerge={false}
          lazyUpdate={true}
        />
      ) : (
        <div className="no-data">
          <p>暂无数据</p>
        </div>
      )}

      {loading && (
        <div className="graph-loading-overlay">
          <div className="graph-spinner"></div>
          <p>正在扩展节点...</p>
        </div>
      )}
    </div>
  );
}

export default GraphVisualization;
