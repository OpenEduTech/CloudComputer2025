import React from "react";
import type { Node, Edge } from "../api";

interface EntityCardProps {
  node: Node;
  edges: Edge[];
  onClose: () => void;
  onExpand: () => void;
  busy: boolean;
  style?: React.CSSProperties;
}

export function EntityCard({ node, edges, onClose, onExpand, busy, style }: EntityCardProps) {
  // 获取与当前节点相关的所有边
  const relatedEdges = edges.filter(edge => edge.source === node.id || edge.target === node.id);
  
  // 获取相关节点
  const getRelatedNode = (nodeId: string) => {
    // 从edges中查找相关节点的名称
    const relatedEdge = edges.find(edge => 
      (edge.source === nodeId && edge.target === node.id) || 
      (edge.target === nodeId && edge.source === node.id)
    );
    return relatedEdge ? (relatedEdge.source === node.id ? relatedEdge.target : relatedEdge.source) : nodeId;
  };
  
  // 按关系类型分组边
  const edgesByRelation = relatedEdges.reduce((acc, edge) => {
    if (!acc[edge.relation]) {
      acc[edge.relation] = [];
    }
    acc[edge.relation].push(edge);
    return acc;
  }, {} as Record<string, Edge[]>);

  return (
    <div className="entity-card" style={{
      backgroundColor: "rgba(2, 6, 23, 0.9)",
      borderRadius: "12px",
      border: "1px solid rgba(34, 211, 238, 0.2)",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
      backdropFilter: "blur(8px)",
      overflow: "hidden",
      color: "#e5e7eb",
      flex: 1,
      display: "flex",
      flexDirection: "column",
      ...style
    }}>
      {/* 卡片头部 */}
      <div className="card-header" style={{
        padding: "16px 20px",
        borderBottom: "1px solid rgba(34, 211, 238, 0.1)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
      }}>
        <div>
          <span className="pill" style={{
            backgroundColor: "rgba(34, 211, 238, 0.1)",
            color: "#22d3ee",
            padding: "4px 8px",
            borderRadius: "12px",
            fontSize: "11px",
            fontWeight: "bold",
            textTransform: "uppercase"
          }}>
            KNOWLEDGE NODE
          </span>
          <h1 className="title" style={{
            margin: "8px 0 0 0",
            fontSize: "20px",
            color: "#ffffff"
          }}>
            {node.name.replace(/\s*\([^\)]*\)\s*.*$/g, '')}
          </h1>
        </div>
        <button 
          onClick={onClose}
          style={{
            backgroundColor: "transparent",
            border: "none",
            color: "#94a3b8",
            cursor: "pointer",
            fontSize: "20px",
            padding: "4px"
          }}
        >
          ×
        </button>
      </div>

      {/* 卡片内容 */}
      <div className="card-content" style={{
        padding: "20px",
        overflowY: "auto",
        flex: 1
      }}>
        {/* 基本属性 */}
        <div className="basic-info" style={{
          marginBottom: "20px"
        }}>
          <h2 style={{
            fontSize: "16px",
            color: "#22d3ee",
            marginBottom: "12px",
            borderBottom: "1px solid rgba(34, 211, 238, 0.1)",
            paddingBottom: "6px"
          }}>
            Basic Information
          </h2>
          <div className="kv-grid" style={{
            display: "grid",
            gridTemplateColumns: "1fr 2fr",
            gap: "8px 16px"
          }}>
            <div style={{
              color: "#94a3b8",
              fontWeight: "bold"
            }}>
              Domain
            </div>
            <div>
              {node.domain}
            </div>
            <div style={{
              color: "#94a3b8",
              fontWeight: "bold"
            }}>
              Confidence
            </div>
            <div>
              {node.confidence.toFixed(2)}
              <div style={{
                width: "100%",
                height: "4px",
                backgroundColor: "rgba(255, 255, 255, 0.1)",
                borderRadius: "2px",
                marginTop: "4px",
                overflow: "hidden"
              }}>
                <div style={{
                  width: `${(node.confidence * 100)}%`,
                  height: "100%",
                  backgroundColor: "#22d3ee",
                  borderRadius: "2px"
                }} />
              </div>
            </div>
            <div style={{
              color: "#94a3b8",
              fontWeight: "bold"
            }}>
              Definition
            </div>
            <div>
              {node.definition || "No definition available"}
            </div>
          </div>
        </div>

        {/* 相关关系 */}
        {Object.keys(edgesByRelation).length > 0 && (
          <div className="relations" style={{
            marginBottom: "20px"
          }}>
            <h2 style={{
              fontSize: "16px",
              color: "#22d3ee",
              marginBottom: "12px",
              borderBottom: "1px solid rgba(34, 211, 238, 0.1)",
              paddingBottom: "6px"
            }}>
              Related Concepts
            </h2>
            {Object.entries(edgesByRelation).map(([relation, relationEdges]) => (
              <div key={relation} style={{
                marginBottom: "12px"
              }}>
                <h3 style={{
                  fontSize: "14px",
                  color: "#f59e0b",
                  marginBottom: "8px"
                }}>
                  {relation.replace("_", " ").toUpperCase()}
                </h3>
                <div style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "8px"
                }}>
                  {relationEdges.map(edge => {
                    const relatedNodeId = edge.source === node.id ? edge.target : edge.source;
                    return (
                      <div key={edge.id || `${edge.source}-${edge.target}`} style={{
                        backgroundColor: "rgba(34, 211, 238, 0.1)",
                        padding: "6px 12px",
                        borderRadius: "16px",
                        fontSize: "12px"
                      }}>
                        {relatedNodeId}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 来源证据 */}
        <div className="evidence" style={{
          marginBottom: "20px"
        }}>
          <h2 style={{
            fontSize: "16px",
            color: "#22d3ee",
            marginBottom: "12px",
            borderBottom: "1px solid rgba(34, 211, 238, 0.1)",
            paddingBottom: "6px"
          }}>
            Evidence & Sources
          </h2>
          {relatedEdges.slice(0, 3).map(edge => (
            <div key={edge.id || `${edge.source}-${edge.target}`} style={{
              backgroundColor: "rgba(255, 255, 255, 0.05)",
              padding: "12px",
              borderRadius: "8px",
              marginBottom: "8px"
            }}>
              <div style={{
                fontSize: "12px",
                color: "#94a3b8",
                marginBottom: "4px"
              }}>
                {edge.evidence.title}
              </div>
              <div style={{
                fontSize: "11px",
                color: "#cbd5e1",
                marginBottom: "4px"
              }}>
                {edge.evidence.snippet}
              </div>
              {edge.evidence.url && (
                <div style={{
                  fontSize: "10px",
                  color: "#38bdf8"
                }}>
                  <a href={edge.evidence.url} target="_blank" rel="noopener noreferrer">
                    {edge.evidence.url}
                  </a>
                </div>
              )}
            </div>
          ))}
          {relatedEdges.length > 3 && (
            <div style={{
              fontSize: "12px",
              color: "#94a3b8",
              textAlign: "center"
            }}>
              ...and {relatedEdges.length - 3} more sources
            </div>
          )}
        </div>
      </div>

      {/* 卡片底部 */}
      <div className="card-footer" style={{
        padding: "16px 20px",
        borderTop: "1px solid rgba(34, 211, 238, 0.1)",
        display: "flex",
        gap: "8px"
      }}>
        <button 
          onClick={onExpand}
          disabled={busy}
          style={{
            flex: 1,
            padding: "10px 16px",
            backgroundColor: "#22d3ee",
            color: "#0f172a",
            border: "none",
            borderRadius: "8px",
            fontWeight: "bold",
            cursor: busy ? "not-allowed" : "pointer",
            opacity: busy ? 0.7 : 1,
            transition: "all 0.2s ease"
          }}
        >
          {busy ? "Expanding..." : "Expand (2-hop)"}
        </button>
      </div>
    </div>
  );
}