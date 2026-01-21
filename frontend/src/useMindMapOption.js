import { useMemo } from 'react';
import { convertGraphToTree } from './utils/graphToTree';

const useMindMapOption = (data, rootId) => {
  const option = useMemo(() => {
    if (!data || !data.nodes) return {};

    // 1. 获取树状数据
    const rawTreeData = convertGraphToTree(data, rootId);
    if (!rawTreeData) return {};
    
    const treeData = JSON.parse(JSON.stringify(rawTreeData));

    // 2. 生成颜色映射
    const groups = Array.from(new Set(data.nodes.map(n => n.group)));
    const colorPalette = [
      '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
    ];
    const groupColorMap = {};
    groups.forEach((g, i) => {
        groupColorMap[g] = colorPalette[i % colorPalette.length];
    });

    // 3. 递归注入样式到数据节点
    const injectStyle = (node) => {
        const color = groupColorMap[node.group] || '#ccc';
        
        node.itemStyle = {
            color: color,
            borderColor: '#fff',
            borderWidth: 2,
            shadowBlur: 5,
            shadowColor: 'rgba(0,0,0,0.1)'
        };

        node.symbol = node.source_type === 'paper' ? 'rect' : 'circle';
        
        if (node.children) {
            node.children.forEach(injectStyle);
        }
    };
    injectStyle(treeData);

    // 4. 构建虚拟 Series 用于显示图例
    // 关键修正：data 为空以隐藏图表上的点，但 itemStyle 保持不透明以显示图例颜色
    const legendSeries = groups.map(g => ({
        name: g,
        type: 'scatter', 
        coordinateSystem: 'cartesian2d',
        data: [], // 空数据，图表上不显示任何点
        itemStyle: {
            color: groupColorMap[g],
            opacity: 1 // 确保图例图标不透明
        },
        symbol: 'circle'
    }));

    return {
      animationDuration: 550,
      animationDurationUpdate: 750,

      // 隐藏的坐标系，支撑 scatter series
      grid: {
          show: false,
          top: 0, left: 0, right: 0, bottom: 0
      },
      xAxis: { show: false, type: 'value' },
      yAxis: { show: false, type: 'value' },

      legend: {
        // 显式指定图例项的 icon，确保即使 series data 为空也能显示图标
        data: groups.map(g => ({
            name: g,
            icon: 'circle'
        })),
        bottom: 20,
        right: 20,
        orient: 'vertical',
        backgroundColor: 'rgba(255,255,255,0.9)',
        borderColor: '#eee',
        borderWidth: 1,
        borderRadius: 4,
        padding: 10,
        textStyle: {
            fontSize: 12,
            color: '#666'
        },
        selectedMode: false
      },

      tooltip: {
        trigger: 'item',
        triggerOn: 'mousemove',
        enterable: true,
        hideDelay: 200,
        confine: true,
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        borderColor: '#ddd',
        borderWidth: 1,
        extraCssText: 'max-width: 300px; white-space: normal; word-break: break-word; box-shadow: 0 4px 12px rgba(0,0,0,0.15);',
        textStyle: {
            color: '#333'
        },
        formatter: (params) => {
            if (params.seriesType === 'scatter') return '';

            const node = params.data;
            if (node.name) {
                const relationInfo = node.relationToParent 
                    ? `<div style="padding: 4px 0; border-bottom: 1px dashed #eee; margin-bottom: 8px;">
                          <span style="color: #888; font-size: 12px;">Incoming Relation:</span><br/>
                          <b>${node.relationToParent}</b>
                          ${node.relationDesc ? `<div style="font-size: 11px; color: #666; margin-top: 2px;">${node.relationDesc}</div>` : ''}
                        </div>` 
                    : '';
                
                return `
                    <div style="padding: 4px;">
                        ${relationInfo}
                        <div style="font-weight: bold; font-size: 14px; margin-bottom: 6px; color: #333;">
                           ${node.name}
                        </div>
                        <div style="font-size: 12px; margin-bottom: 4px;">
                           <span style="color: #666;">Type:</span> 
                           <b>${node.source_type === 'paper' ? '📄 Paper' : '📘 Textbook'}</b>
                        </div>
                        <div style="font-size: 12px; color: #555; line-height: 1.4; margin-bottom: 6px;">${node.info || ''}</div>
                        <div style="font-size: 12px; color: #999; border-top: 1px solid #f0f0f0; padding-top: 6px; display: flex; justify-content: space-between; align-items: center;">
                            <span>Confidence: ${(node.confidence * 100).toFixed(0)}%</span>
                            ${node.url ? `<a href="${node.url}" target="_blank" style="color: #1677ff; text-decoration: none; font-weight: bold; cursor: pointer;">Open Link 🔗</a>` : ''}
                        </div>
                    </div>
                `;
            }
            return '';
        }
      },

      series: [
        {
          type: 'tree',
          data: [treeData],
          top: '5%',
          left: '10%',
          bottom: '5%',
          right: '20%',
          
          symbolSize: (value, params) => {
              if (!params.data.relationToParent) return 24;
              return 16;
          },
          
          label: {
            position: 'left',
            verticalAlign: 'middle',
            align: 'right',
            fontSize: 14,
            fontWeight: 'bold',
            color: '#333',
            textBorderColor: '#fff',
            textBorderWidth: 3,
            formatter: '{b}'
          },

          leaves: {
            label: {
              position: 'right',
              verticalAlign: 'middle',
              align: 'left'
            }
          },

          emphasis: {
            focus: 'descendant',
            itemStyle: {
                shadowBlur: 10,
                shadowColor: 'rgba(0,0,0,0.3)'
            }
          },

          expandAndCollapse: true,
          
          edgeShape: 'polyline', 
          lineStyle: {
              color: '#ccc',
              width: 1.5
          },
          
          labelLayout: {
              hideOverlap: true
          },
          
          initialTreeDepth: -1 
        },
        ...legendSeries 
      ]
    };
  }, [data, rootId]);

  return option;
};

export default useMindMapOption;
