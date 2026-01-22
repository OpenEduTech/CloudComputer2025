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
        const confidenceValue = typeof node.confidence === 'number' ? node.confidence : 0.6;
        const isLowConfidence = confidenceValue < 0.66;
        
        node.itemStyle = {
            color: color,
            borderColor: isLowConfidence ? '#ff4d4f' : '#fff', // Red border for low confidence
            borderWidth: isLowConfidence ? 4 : 2,
            shadowBlur: 5,
            shadowColor: 'rgba(0,0,0,0.1)',
            opacity: 0.65 + (confidenceValue * 0.35)
        };

        // Highlight label as well
        node.label = {
            color: isLowConfidence ? '#cf1322' : '#333',
            fontWeight: isLowConfidence ? 'bold' : 'bold', // Always bold for mindmap, but maybe extra?
            textBorderColor: '#fff',
            textBorderWidth: 3,
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
        // 策略调整：在外层强制固定宽度，确保 ECharts 能正确计算位置
        extraCssText: 'width: 260px !important; max-width: 260px !important; white-space: normal !important; word-wrap: break-word !important; word-break: break-word !important; box-shadow: 0 6px 16px rgba(0,0,0,0.12); border-radius: 8px;',
        textStyle: {
            color: '#333',
            fontSize: 13
        },
        formatter: (params) => {
            if (params.seriesType === 'scatter') return '';

            const node = params.data;
            if (node.name) {
                const relationInfo = node.relationToParent 
                    ? `<div style="padding-bottom: 8px; border-bottom: 1px dashed #eee; margin-bottom: 8px;">
                          <div style="color: #999; font-size: 11px; margin-bottom: 2px;">INCOMING RELATION</div>
                          <div style="font-weight: 600; color: #1677ff; background: #e6f7ff; padding: 2px 6px; border-radius: 4px; display: inline-block; font-size: 12px;">${node.relationToParent}</div>
                          ${node.relationDesc ? `<div style="font-size: 12px; color: #666; margin-top: 4px; line-height: 1.4;">${node.relationDesc}</div>` : ''}
                          ${node.relationCitation ? `<div style="font-size: 11px; color: #999; margin-top: 4px; background: #f9f9f9; padding: 4px; border-radius: 4px;">Ref: ${node.relationCitation}</div>` : ''}
                        </div>` 
                    : '';
                
                return `
                    <div style="width: 100%; max-height: 300px; overflow-y: auto; padding-right: 5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
                        ${relationInfo}
                        <div style="font-weight: 600; font-size: 15px; margin-bottom: 6px; color: #333; line-height: 1.4;">
                           ${node.name}
                        </div>
                        <div style="font-size: 12px; margin-bottom: 6px; color: #666; display: flex; align-items: center;">
                           <span style="font-weight: 600; margin-right: 4px;">Type:</span> 
                           <span style="background: ${node.source_type === 'paper' ? '#e6f7ff' : '#f6ffed'}; color: ${node.source_type === 'paper' ? '#1890ff' : '#52c41a'}; padding: 1px 6px; border-radius: 4px; font-size: 11px;">
                             ${node.source_type === 'paper' ? 'PAPER' : 'TEXTBOOK'}
                           </span>
                        </div>
                        <div style="font-size: 13px; color: #444; line-height: 1.6; margin-bottom: 8px;">${node.info || ''}</div>
                        <div style="font-size: 12px; color: #999; border-top: 1px solid #f0f0f0; padding-top: 8px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600; color: ${(node.confidence * 100) > 80 ? '#52c41a' : '#faad14'}">${(node.confidence * 100).toFixed(0)}% Confidence</span>
                            ${node.url ? `<a href="${node.url}" target="_blank" style="color: #1677ff; text-decoration: none; font-weight: 600;">Open Link →</a>` : ''}
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
