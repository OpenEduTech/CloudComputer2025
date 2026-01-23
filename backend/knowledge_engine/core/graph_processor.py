import os
import json
import networkx as nx

class GraphProcessor:
    """
    从 LightRAG 的输出中提取图谱数据并标注领域
    """
    
    def process_lightrag_output(
        self, 
        working_dir: str, 
        documents: list, 
        concept: str,
        chunk_mapping: dict
    ) -> dict:
        """
        解析 LightRAG 输出,生成前端所需的 JSON
        
        参数:
        - working_dir: LightRAG 工作目录
        - documents: 原始文档列表
        - concept: 核心概念
        - chunk_mapping: {chunk_id: {doc_ids: [...], domains: [...]}}
        
        返回: {nodes: [...], edges: [...]}
        """
        graphml_path = os.path.join(working_dir, "graph_chunk_entity_relation.graphml")
        
        if not os.path.exists(graphml_path):
            raise FileNotFoundError(f"未找到图谱文件: {graphml_path}")
        
        # 1. 加载完整图谱
        G_full = nx.read_graphml(graphml_path)
        print(f"原始图谱: {len(G_full.nodes())} 节点, {len(G_full.edges())} 边")
        
        # 2. 【剪枝】保留与核心概念连通的子图
        G_pruned = self._prune_graph(G_full, concept)
        print(f"剪枝后: {len(G_pruned.nodes())} 节点, {len(G_pruned.edges())} 边")
        
        # 3. 解析节点（使用剪枝后的图）
        nodes = self._extract_nodes(G_pruned, concept, chunk_mapping)
        
        # 4. 解析边
        edges = self._extract_edges(G_pruned)
        
        return {
            "concept": concept,
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
    
    def _prune_graph(self, G_full: nx.Graph, center_concept: str) -> nx.Graph:
        """
        剪枝图谱,保留与核心概念连通的重要子图
        
        策略 :
        1. 保留核心概念节点及其邻居
        2. 保留高度数节点（度 > 1）
        3. 只保留与核心概念连通的节点
        
        参数:
        - G_full: 完整图谱
        - center_concept: 核心概念（如 "熵"）
        
        返回: 剪枝后的子图
        """
        # ========== 阶段 1: 初步筛选节点 ==========
        nodes_to_keep = set()
        
        # 策略 1: 保留核心概念及其直接邻居
        if center_concept in G_full.nodes():
            nodes_to_keep.add(center_concept)
            neighbors = list(G_full.neighbors(center_concept))
            nodes_to_keep.update(neighbors)
            print(f"核心概念 '{center_concept}' + 邻居: {len(neighbors) + 1} 个")
        else:
            print(f"核心概念 '{center_concept}' 不在图谱中，将保留所有高度数节点")
        
        # 策略 2: 保留高度数节点（度 > 1）
        high_degree = [n for n, d in G_full.degree() if d > 1]
        nodes_to_keep.update(high_degree)
        print(f"高度数节点 (度>1): {len(high_degree)} 个")
        
        # 初步筛选后的子图
        G_candidate = G_full.subgraph(nodes_to_keep).copy()
        
        # ========== 阶段 2: 【核心】只保留与中心概念连通的节点 ==========
        if center_concept in G_candidate.nodes():
            # 找出与核心概念在同一连通分量中的所有节点
            connected_nodes = self._get_connected_component(G_candidate, center_concept)
            print(f"🔗 与 '{center_concept}' 连通的节点: {len(connected_nodes)} 个")
            
            G_pruned = G_candidate.subgraph(connected_nodes).copy()
        else:
            # 如果核心概念不存在，返回最大连通分量
            print(f"⚠️  使用最大连通分量")
            G_pruned = self._get_largest_component(G_candidate)
        
        # ========== 如果要返回完整图谱 ==========
        # G_pruned = G_full.copy()
        
        return G_pruned
    
    def _get_connected_component(self, G: nx.Graph, node: str) -> set:
        """
        获取包含指定节点的连通分量
        
        参数:
        - G: 图对象
        - node: 节点 ID
        
        返回: 包含该节点的连通分量中的所有节点
        """
        # NetworkX 提供的连通分量查找
        for component in nx.connected_components(G):
            if node in component:
                return component
        
        return {node}  # 如果未找到，至少返回自己
    
    def _get_largest_component(self, G: nx.Graph) -> nx.Graph:
        """
        获取最大连通分量
        
        参数:
        - G: 图对象
        
        返回: 最大连通分量的子图
        """
        if len(G.nodes()) == 0:
            return G
        
        # 找到最大的连通分量
        largest_cc = max(nx.connected_components(G), key=len)
        print(f"📊 最大连通分量: {len(largest_cc)} 节点")
        
        return G.subgraph(largest_cc).copy()
    
    def _extract_nodes(self, G: nx.Graph, concept: str, chunk_mapping: dict) -> list:
        """提取节点信息"""
        nodes = []
        
        for node_id, node_data in G.nodes(data=True):
            # 解析 source_id
            source_ids_raw = node_data.get('source_id', '')
            source_chunks = self._parse_source_ids(source_ids_raw)
            
            # 反查领域（支持多领域）
            domains = self._resolve_domains(source_chunks, chunk_mapping)
            
            # 构建节点
            node = {
                "id": node_id,
                "label": node_data.get('entity_name', node_id),
                "description": node_data.get('description', '暂无描述'),
                "domains": domains,
                "source_chunks": source_chunks,
                "size": G.degree(node_id) + 1  # 前端可参考的节点大小，=deg+1
            }
            
            nodes.append(node)
        
        return nodes
    
    def _extract_edges(self, G: nx.Graph) -> list:
        """提取边信息"""
        edges = []
        
        for source, target, edge_data in G.edges(data=True):
            edge = {
                "source": source,
                "target": target,
                "relation": edge_data.get('label', 'related'),
                "description": edge_data.get('description', '')
            }
            edges.append(edge)
        
        return edges
    
    def _parse_source_ids(self, source_ids_raw: str) -> list:
        """解析 source_id 字符串"""
        if not source_ids_raw:
            return []
        
        # 尝试多种分隔符
        separators = ['<SEP>', ',', '\n']
        chunk_ids = [source_ids_raw]
        
        for sep in separators:
            temp = []
            for part in chunk_ids:
                temp.extend([p.strip() for p in part.split(sep) if p.strip()])
            chunk_ids = temp
        
        return chunk_ids
    
    def _resolve_domains(self, chunk_ids: list, chunk_mapping: dict) -> list:
        """
        通过 Chunk ID 反查领域（支持多领域）
        
        返回: ['物理学', '信息论'] 或 ['跨学科']
        """
        all_domains = set()
        
        for cid in chunk_ids:
            mapping_info = chunk_mapping.get(cid)
            if mapping_info:
                # 添加该 chunk 关联的所有领域
                all_domains.update(mapping_info['domains'])
        
        domains_list = sorted(list(all_domains))  # 排序保证一致性
        
        # 如果跨越多个领域,返回所有领域（前端可根据长度判断是否跨学科）
        if len(domains_list) > 1:
            return domains_list  # 如 ["信息论", "物理学"]
        elif len(domains_list) == 1:
            return domains_list
        else:
            return ["未知"]

graph_processor = GraphProcessor()