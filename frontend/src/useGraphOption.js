import { useMemo } from 'react';

const useGraphOption = (data, themeToken) => {
  const option = useMemo(() => {
    if (!data || !data.nodes) return {};

    // Filter out isolated nodes
    const connectedNodeIds = new Set();
    data.links.forEach(link => {
      connectedNodeIds.add(link.source);
      connectedNodeIds.add(link.target);
    });

    const visibleNodes = data.nodes.filter(node => connectedNodeIds.has(node.id));

    // Extract unique groups for legend
    const categories = Array.from(new Set(visibleNodes.map(n => n.group))).map(name => ({ name }));
    
    // Tech/Scientific Color Palette
    const colors = [
      '#5470c6', // Deep Blue
      '#91cc75', // Light Green
      '#fac858', // Yellow
      '#ee6666', // Red
      '#73c0de', // Light Blue
      '#3ba272', // Green
      '#fc8452', // Orange
      '#9a60b4', // Purple
      '#ea7ccc', // Pink
    ];

    return {
      title: {
        text: '',
        top: 'bottom',
        left: 'right'
      },
      tooltip: {
        trigger: 'item',
        confine: true,
        enterable: true,
        backgroundColor: 'rgba(255, 255, 255, 0.96)', // 微调透明度以确认更新
        borderColor: '#e8e8e8',
        borderWidth: 1,
        // 策略调整：在外层强制固定宽度，确保 ECharts 能正确计算位置
        extraCssText: 'width: 260px !important; max-width: 260px !important; white-space: normal !important; word-wrap: break-word !important; word-break: break-word !important; box-shadow: 0 6px 16px rgba(0,0,0,0.12); border-radius: 8px;',
        textStyle: {
          color: '#333',
          fontSize: 13
        },
        formatter: (params) => {
            if (params.dataType === 'node') {
                const node = params.data;
                const color = params.color || '#5470c6';
                const sourceInfo = node.url 
                    ? `<a href="${node.url}" target="_blank" style="color: #1677ff; text-decoration: none;">${node.source} 🔗</a>` 
                    : node.source;
                
                return `
                    <div style="width: 100%; max-height: 300px; overflow-y: auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
                        <div style="font-weight: 600; font-size: 15px; margin-bottom: 8px; color: ${color}; line-height: 1.4;">
                           ${node.label}
                        </div>
                        <div style="font-size: 12px; margin-bottom: 6px; color: #666; display: flex; align-items: center;">
                           <span style="font-weight: 600; margin-right: 4px;">Type:</span> 
                           <span style="background: ${node.source_type === 'paper' ? '#e6f7ff' : '#f6ffed'}; color: ${node.source_type === 'paper' ? '#1890ff' : '#52c41a'}; padding: 1px 6px; border-radius: 4px; font-size: 11px;">
                             ${node.source_type === 'paper' ? 'PAPER' : 'TEXTBOOK'}
                           </span>
                        </div>
                        <div style="font-size: 12px; margin-bottom: 6px; color: #666; line-height: 1.4;">
                           <span style="font-weight: 600;">Source:</span> ${sourceInfo}
                        </div>
                        <div style="font-size: 12px; margin-bottom: 10px; color: #666;">
                           <span style="font-weight: 600;">Confidence:</span> 
                           <span style="color: ${(node.confidence * 100) > 80 ? '#52c41a' : '#faad14'}; font-weight: 600;">${(node.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div style="font-size: 13px; color: #444; padding-top: 10px; border-top: 1px solid #f0f0f0; line-height: 1.6;">
                           ${node.info || 'No description available.'}
                        </div>
                    </div>
                `;
            } else if (params.dataType === 'edge') {
                 const citationInfo = params.data.citation
                    ? `<div style="margin-top: 8px; padding: 8px; background: #f9f9f9; border-radius: 4px; color: #666; font-size: 12px; line-height: 1.4;">
                         <span style="font-weight: 600; color: #999;">Citation:</span> ${params.data.citation}
                       </div>`
                    : '';
                 
                 return `
                    <div style="width: 100%; max-height: 300px; overflow-y: auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
                        <div style="color: #999; margin-bottom: 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Relationship</div>
                        <div style="font-size: 13px; margin-bottom: 8px; line-height: 1.4; color: #333;">
                            <span style="font-weight: 600;">${params.data.source}</span> 
                            <span style="color: #bbb; margin: 0 6px;">➜</span> 
                            <span style="font-weight: 600;">${params.data.target}</span>
                        </div>
                        <div style="font-size: 12px; color: #1677ff; background: #e6f7ff; padding: 4px 8px; border-radius: 4px; display: inline-block; margin-bottom: 8px;">
                            ${params.data.relation}
                        </div>
                        ${params.data.desc ? `<div style="margin-top: 4px; font-size: 13px; color: #444; line-height: 1.6;">${params.data.desc}</div>` : ''}
                        ${citationInfo}
                    </div>
                 `;
            }
            return '';
        }
      },
      legend: {
        data: categories.map(function (a) {
          return a.name;
        }),
        orient: 'vertical',
        right: 20,
        bottom: 20,
        backgroundColor: 'rgba(255,255,255,0.8)',
        borderRadius: 8,
        padding: 12,
        textStyle: {
            color: '#333' 
        },
      },
      animationDurationUpdate: 1500,
      animationEasingUpdate: 'quinticInOut',
      series: [
        {
          name: 'Knowledge Graph',
          type: 'graph',
          layout: 'force',
          draggable: true, // Enable dragging
          data: visibleNodes.map(node => {
            const confidenceScore = typeof node.confidence === 'number' ? node.confidence : 0.6;
            const emphasisSize = Math.round(confidenceScore * 12);
            // Highlight low confidence nodes with red border or color
            const isLowConfidence = confidenceScore < 0.66;
            
            return {
            ...node,
            name: node.id, // Use UUID as unique identifier for linking
            displayName: node.label, // Store label for display
            category: categories.findIndex(c => c.name === node.group),
            // Distinct shapes with meaning
            symbol: node.source_type === 'textbook' ? 'circle' : 'diamond', 
            // Dynamic sizing based on confidence/importance
            symbolSize: (node.size || 30) + emphasisSize, 
            itemStyle: {
                // If low confidence, override border color to RED
                borderColor: isLowConfidence ? '#ff4d4f' : '#fff',
                borderWidth: isLowConfidence ? 4 : 2,
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.2)',
                opacity: 0.65 + (confidenceScore * 0.35)
            },
            label: {
                show: true,
                position: 'right', // Put labels on the right to reduce overlap
                formatter: (params) => params.data.displayName, // Display the label text
                fontSize: 12,
                color: isLowConfidence ? '#cf1322' : '#333', // Red text for low confidence
                fontWeight: isLowConfidence ? 'bold' : 'normal',
                backgroundColor: 'rgba(255,255,255,0.7)',
                borderRadius: 4,
                padding: [2, 4]
            }
            };
          }),
          links: data.links.map(link => {
              const hasCitation = Boolean(link.citation);
              return {
              ...link,
              value: link.relation,
              lineStyle: {
                      color: hasCitation ? '#fa8c16' : '#9e9e9e',
                  curveness: 0.2,
                      opacity: hasCitation ? 0.8 : 0.35,
                      width: hasCitation ? 2.2 : 1.2
              },
              symbol: ['none', 'arrow'], // Add arrows
              symbolSize: 8
              };
          }),
          categories: categories,
          roam: true,
          label: {
            position: 'right',
            formatter: '{b}'
          },
          lineStyle: {
            color: '#9e9e9e',
            curveness: 0.3
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 4
            },
            label: {
                show: true
            }
          },
          force: {
            repulsion: 800, // Significantly increased from 300 to spread nodes
            edgeLength: [100, 250], // Longer edges
            gravity: 0.05, // Lower gravity
            layoutAnimation: true
          }
        }
      ]
    };
  }, [data, themeToken]);

  return option;
};

export default useGraphOption;
