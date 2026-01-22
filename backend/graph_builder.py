"""
知识图谱构建器
将LLM生成的关联数据转换为标准的图数据结构
"""

class GraphBuilder:
    def __init__(self):
        """初始化图构建器"""
        pass
    
    def build_graph(self, validated_data):
        """构建知识图谱数据结构"""
        core_concept = validated_data['core_concept']
        relations = validated_data['relations']
        
        # 构建节点
        nodes = self._build_nodes(core_concept, relations)
        
        # 构建边
        edges = self._build_edges(core_concept, relations)
        
        # 构建分类信息
        categories = self._build_categories(relations)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'categories': categories,
            'metadata': {
                'core_concept': core_concept,
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'disciplines': list(set(r['discipline'] for r in relations))
            }
        }
    
    def _build_nodes(self, core_concept, relations):
        """构建节点列表"""
        nodes = []
        
        # 核心概念节点（最大，圆形）
        nodes.append({
            'id': core_concept,
            'name': core_concept,
            'category': 'core',
            'symbolSize': 100,
            'value': 100,
            'symbol': 'circle',
            'label': {
                'show': True,
                'fontSize': 16,
                'fontWeight': 'bold'
            },
            'itemStyle': {
                'borderWidth': 3,
                'borderColor': '#60a5fa'
            }
        })
        
        # 相关概念节点（根据关系类型和学科设置不同大小和形状）
        relation_type_sizes = {
            '直接关联': 70,
            '理论基础': 65,
            '应用': 60,
            '类比': 55,
            '远亲概念': 50
        }
        
        discipline_shapes = {
            '数学': 'diamond',
            '物理学': 'triangle',
            '计算机科学': 'rect',
            '生物学': 'roundRect',
            '社会学': 'circle',
            '经济学': 'star',
            '心理学': 'pin',
            '信息论': 'arrow'
        }
        
        for idx, relation in enumerate(relations):
            relation_type = relation.get('relation_type', '应用')
            discipline = relation.get('discipline', '')
            
            # 根据关系类型确定大小
            base_size = relation_type_sizes.get(relation_type, 55)
            # 根据学科确定形状
            symbol_shape = discipline_shapes.get(discipline, 'circle')
            
            nodes.append({
                'id': relation['related_concept'],
                'name': relation['related_concept'],
                'category': discipline,
                'symbolSize': base_size,
                'value': base_size,
                'symbol': symbol_shape,
                'discipline': discipline,
                'description': relation['description'],
                'relation_type': relation_type,
                'bridge_concept': relation.get('bridge_concept', ''),
                'label': {
                    'show': True,
                    'fontSize': 12
                },
                'itemStyle': {
                    'borderWidth': 2,
                    'borderColor': '#94a3b8'
                }
            })
        
        return nodes
    
    def _build_edges(self, core_concept, relations):
        """构建边列表"""
        edges = []
        
        for relation in relations:
            edges.append({
                'source': core_concept,
                'target': relation['related_concept'],
                'label': relation['relation_type'],
                'description': relation['description'],
                'lineStyle': {
                    'curveness': 0.2
                }
            })
        
        return edges
    
    def _build_categories(self, relations):
        """构建分类信息"""
        disciplines = set(r['discipline'] for r in relations)
        
        categories = [{'name': 'core'}]
        for discipline in disciplines:
            categories.append({'name': discipline})
        
        return categories
    
    def to_echarts_format(self, graph_data):
        """转换为ECharts可用的格式"""
        return {
            'nodes': graph_data['nodes'],
            'links': graph_data['edges'],
            'categories': graph_data['categories']
        }

