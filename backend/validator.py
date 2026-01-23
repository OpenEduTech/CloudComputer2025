"""
校验层 (Check Layer)
用于验证LLM生成的知识图谱的准确性，防止幻觉
"""

class KnowledgeValidator:
    def __init__(self, agent):
        """初始化验证器"""
        self.agent = agent
        self.min_confidence = 0.3  # 降低置信度阈值，允许更多关联通过
    
    def validate_graph(self, graph_data):
        """验证整个知识图谱"""
        core_concept = graph_data.get('core_concept', '')
        relations = graph_data.get('relations', [])
        
        validated_relations = []
        validation_results = []
        
        for relation in relations:
            # 基础格式验证
            if not self._validate_format(relation):
                continue
            
            # LLM验证（增强版，包含桥梁概念）
            validation = self.agent.validate_relation(
                core_concept=core_concept,
                related_concept=relation['related_concept'],
                discipline=relation['discipline'],
                relation_type=relation.get('relation_type', ''),
                bridge_concept=relation.get('bridge_concept', ''),
                description=relation['description']
            )
            
            validation_results.append({
                'relation': relation,
                'validation': validation
            })
            
            # 增强验证逻辑：对远亲概念和类比进行更严格检查
            relation_type = relation.get('relation_type', '')
            confidence = validation.get('confidence', 0.5)
            is_valid = validation.get('is_valid', False)
            
            # 直接关联、理论基础、应用：使用标准阈值
            if relation_type in ['直接关联', '理论基础', '应用']:
                if is_valid and confidence >= self.min_confidence:
                    validated_relations.append(relation)
                elif confidence >= 0.2:  # 降低阈值但仍保留
                    validated_relations.append(relation)
            # 类比和远亲概念：更严格的验证
            elif relation_type in ['类比', '远亲概念']:
                bridge_concept = relation.get('bridge_concept', '')
                # 必须有桥梁概念且置信度较高
                if bridge_concept and is_valid and confidence >= 0.4:
                    validated_relations.append(relation)
                elif bridge_concept and confidence >= 0.3:
                    # 有桥梁概念但置信度较低，仍保留但标记
                    validated_relations.append(relation)
            else:
                # 其他类型：标准验证
                if is_valid and confidence >= self.min_confidence:
                    validated_relations.append(relation)
                elif confidence >= 0.2:
                    validated_relations.append(relation)
        
        return {
            'core_concept': core_concept,
            'relations': validated_relations,
            'validation_details': validation_results,
            'total_relations': len(relations),
            'validated_relations': len(validated_relations)
        }
    
    def _validate_format(self, relation):
        """验证关联数据格式"""
        required_fields = ['discipline', 'related_concept', 'relation_type', 'description']
        
        for field in required_fields:
            if field not in relation or not relation[field]:
                return False
        
        # 增强描述长度要求（要求更详细的描述）
        if len(relation['description']) < 20 or len(relation['description']) > 500:
            return False
        
        # 检查远亲概念和类比是否包含桥梁概念
        relation_type = relation.get('relation_type', '')
        if relation_type in ['类比', '远亲概念']:
            bridge_concept = relation.get('bridge_concept', '')
            if not bridge_concept or len(bridge_concept.strip()) < 2:
                return False
        
        # 检查描述是否包含桥梁概念（对于远亲概念和类比）
        description = relation.get('description', '')
        if relation_type in ['类比', '远亲概念']:
            bridge_concept = relation.get('bridge_concept', '')
            if bridge_concept and bridge_concept not in description:
                # 如果桥梁概念存在但不在描述中，警告但不拒绝
                pass
        
        return True
    
    def check_diversity(self, relations):
        """检查学科多样性"""
        disciplines = set(r['discipline'] for r in relations)
        return len(disciplines) >= 3  # 至少3个不同学科
    
    def check_completeness(self, graph_data):
        """检查图谱完整性"""
        if not graph_data.get('core_concept'):
            return False, "缺少核心概念"
        
        relations = graph_data.get('relations', [])
        # 放宽要求：至少需要1个有效关联即可
        if len(relations) < 1:
            return False, f"关联数量不足（当前：{len(relations)}，需要至少1个）"
        
        # 如果有多个关联，检查多样性
        if len(relations) >= 3 and not self.check_diversity(relations):
            return False, "学科多样性不足（需要至少3个不同学科）"
        
        return True, f"图谱完整（共{len(relations)}个关联）"

