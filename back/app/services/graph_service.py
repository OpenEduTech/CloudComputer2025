import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
import asyncio
from app.core.db import neo4j_driver, redis_client
from app.core.config import settings
from app.core.schema import validator
import logging

logger = logging.getLogger(__name__)

class GraphService:
    """图谱服务"""
    
    def __init__(self):
        self.cache_prefix = "graph:"
        self.agent_client = None
        self.agent_long_client = None
    
    async def _get_agent_client(self):
        """获取Agent HTTP客户端（用于快速API调用）"""
        if self.agent_client is None:
            self.agent_client = httpx.AsyncClient(
                timeout=settings.AGENT_TIMEOUT,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self.agent_client

    async def _get_agent_long_client(self):
        """获取Agent HTTP客户端（用于后台长时间任务）"""
        if self.agent_long_client is None:
            self.agent_long_client = httpx.AsyncClient(
                timeout=settings.AGENT_LONG_TIMEOUT,  # 使用长时间超时
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self.agent_long_client
    
    async def generate_graph(self, concept: str) -> Dict[str, Any]:
        """生成知识图谱（优先使用Agent服务）"""
        
        if settings.USE_MOCK:
            logger.info(f"使用Mock模式生成图谱: {concept}")
            return self.generate_mock_graph(concept)
        
        try:
            logger.info(f"调用Agent服务生成图谱: {concept}")
            
            # 调用 A 同学的 Agent 服务 - 根据A的API修正端点和参数
            client = await self._get_agent_client()
            response = await client.post(
                f"{settings.AGENT_SERVICE_URL}/graph/build",  # 修正端点：/generate_graph -> /graph/build
                json={
                    "concept": concept,
                    "debug": False,  # 生产环境关闭debug
                    "trace_id": None,  # 添加A需要的参数
                    "cfg": None  # 添加A需要的参数
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 检查A服务是否成功（根据A的API，成功时ok=true）
                if result.get("ok") and "graph" in result:
                    data = result["graph"]
                    logger.info(f"Agent服务成功返回数据，节点数: {len(data.get('nodes', []))}")
                    
                    # 验证数据格式
                    if self._validate_graph_data(data):
                        # 标准化处理
                        normalized_data = self.normalize_graph(data)
                        
                        # 更新元数据，添加A的trace_id等信息
                        normalized_data["meta"] = {
                            **normalized_data.get("meta", {}),
                            "source": "agent-service",
                            "generated_at": datetime.now().isoformat(),
                            "concept": concept,
                            "trace_id": result.get("trace_id", ""),
                            "elapsed_ms": result.get("elapsed_ms", 0)
                        }
                        
                        logger.info(f"Agent服务成功生成图谱: {concept}")
                        return normalized_data
                    else:
                        logger.warning(f"Agent服务返回数据格式异常，降级到Mock模式")
                        return self.generate_mock_graph(concept)
                else:
                    # A服务返回了错误
                    error_info = result.get("error", {})
                    logger.error(f"Agent服务返回失败: {error_info.get('stage', 'unknown')} - {error_info.get('message', '未知错误')}")
                    return self.generate_mock_graph(concept)
            else:
                logger.error(f"Agent服务调用失败: {response.status_code}, {response.text}")
                return self.generate_mock_graph(concept)
                
        except httpx.TimeoutException:
            logger.error(f"Agent服务调用超时，降级到Mock模式")
            return self.generate_mock_graph(concept)
        except httpx.RequestError as e:
            logger.error(f"Agent服务请求错误: {str(e)}，降级到Mock模式")
            return self.generate_mock_graph(concept)
        except Exception as e:
            logger.error(f"调用Agent服务异常: {str(e)}")
            return self.generate_mock_graph(concept)

    async def generate_graph_long(self, concept: str) -> Dict[str, Any]:
        """
        长时间调用Agent服务（用于后台任务）
        失败时抛出异常，不降级到Mock
        """
        if settings.USE_MOCK:
            logger.info(f"后台任务使用Mock模式生成图谱: {concept}")
            return self.generate_mock_graph(concept)

        try:
            logger.info(f"后台任务长时间调用Agent服务生成图谱: {concept}")

            # 使用长时间任务客户端
            client = await self._get_agent_long_client()
            response = await client.post(
                f"{settings.AGENT_SERVICE_URL}/graph/build",
                json={
                    "concept": concept,
                    "debug": False,
                    "trace_id": None,
                    "cfg": None
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("ok") and "graph" in result:
                    data = result["graph"]
                    logger.info(f"Agent服务成功返回数据，节点数: {len(data.get('nodes', []))}")

                    if self._validate_graph_data(data):
                        normalized_data = self.normalize_graph(data)

                        normalized_data["meta"] = {
                            **normalized_data.get("meta", {}),
                            "source": "agent-service",
                            "generated_at": datetime.now().isoformat(),
                            "concept": concept,
                            "trace_id": result.get("trace_id", ""),
                            "elapsed_ms": result.get("elapsed_ms", 0)
                        }

                        logger.info(f"Agent服务成功生成图谱: {concept}")
                        return normalized_data
                    else:
                        raise Exception(f"Agent返回数据格式异常")
                else:
                    # Agent服务返回了错误
                    error_info = result.get("error", {})
                    raise Exception(f"Agent服务返回失败: {error_info.get('stage', 'unknown')} - {error_info.get('message', '未知错误')}")
            else:
                raise Exception(f"Agent服务调用失败: {response.status_code}, {response.text}")

        except httpx.TimeoutException:
            logger.error(f"Agent服务长时间调用超时")
            raise Exception("Agent服务调用超时")
        except httpx.RequestError as e:
            logger.error(f"Agent服务请求错误: {str(e)}")
            raise Exception(f"Agent服务请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"长时间调用Agent服务异常: {str(e)}")
            raise Exception(f"Agent服务调用失败: {str(e)}")

    def _validate_graph_data(self, data: Dict[str, Any]) -> bool:
        """验证Agent返回的数据格式"""
        try:
            # 验证必需字段
            required_keys = ["meta", "nodes", "edges"]
            if not all(key in data for key in required_keys):
                logger.warning(f"数据缺少必需字段: {required_keys}")
                return False
            
            # 验证节点格式
            nodes = data.get("nodes", [])
            if not isinstance(nodes, list):
                logger.warning("nodes字段不是列表")
                return False
            
            for node in nodes:
                if not isinstance(node, dict):
                    logger.warning("节点不是字典格式")
                    return False
                if "id" not in node or "label" not in node:
                    logger.warning(f"节点缺少id或label字段: {node}")
                    return False
            
            # 验证边格式
            edges = data.get("edges", [])
            if not isinstance(edges, list):
                logger.warning("edges字段不是列表")
                return False
            
            for edge in edges:
                if not isinstance(edge, dict):
                    logger.warning("边不是字典格式")
                    return False
                if "source" not in edge or "target" not in edge:
                    logger.warning(f"边缺少source或target字段: {edge}")
                    return False
            
            # 使用Schema验证器进一步验证
            is_valid, message = validator.validate(data)
            if not is_valid:
                logger.warning(f"Schema验证失败: {message}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"数据验证异常: {str(e)}")
            return False
    
    def save_to_neo4j(self, graph_data: Dict[str, Any]) -> bool:
        """保存图谱到Neo4j"""
        try:
            with neo4j_driver.session() as session:
                # 清空旧数据（根据实际情况调整）
                session.run("MATCH (n) DETACH DELETE n")
                
                # 创建节点
                for node in graph_data.get("nodes", []):
                    query = """
                    CREATE (n:Concept {id: $id, label: $label, field: $field, type: $type})
                    SET n.summary = $summary,
                        n.importance = $importance,
                        n.confidence = $confidence
                    """
                    session.run(query, **node)
                
                # 创建关系
                for edge in graph_data.get("edges", []):
                    query = """
                    MATCH (a:Concept {id: $source})
                    MATCH (b:Concept {id: $target})
                    CREATE (a)-[r:RELATES_TO {
                        relation: $relation,
                        relation_type: $relation_type,
                        confidence: $confidence,
                        evidence: $evidence,
                        direction: $direction
                    }]->(b)
                    """
                    session.run(query, **edge)
                
                # 保存元数据
                meta = graph_data.get("meta", {})
                meta_query = """
                CREATE (m:GraphMeta {
                    core_concept: $core_concept,
                    normalized_concept: $normalized_concept,
                    version: $version,
                    generated_at: $generated_at,
                    source: $source
                })
                """
                meta_params = {
                    "core_concept": meta.get("core_concept", ""),
                    "normalized_concept": meta.get("normalized_concept", ""),
                    "version": meta.get("version", "1.0"),
                    "generated_at": meta.get("generated_at", datetime.now().isoformat()),
                    "source": meta.get("source", "unknown")
                }
                session.run(meta_query, **meta_params)
                
                logger.info(f"✅ 图谱已保存到Neo4j: {meta.get('core_concept')}")
                return True
                
        except Exception as e:
            logger.error(f"保存到Neo4j失败: {e}")
            return False
    
    def save_to_cache(self, concept: str, graph_data: Dict[str, Any]) -> bool:
        """保存图谱到Redis缓存"""
        try:
            cache_key = f"{self.cache_prefix}{concept}"
            redis_client.setex(
                cache_key,
                settings.CACHE_TTL,
                json.dumps(graph_data, ensure_ascii=False)
            )
            logger.info(f"✅ 图谱已缓存: {concept}")
            return True
        except Exception as e:
            logger.error(f"缓存失败: {e}")
            return False
    
    def get_from_cache(self, concept: str) -> Optional[Dict[str, Any]]:
        """从Redis缓存获取图谱"""
        try:
            cache_key = f"{self.cache_prefix}{concept}"
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            return None
    
    def generate_mock_graph(self, concept: str) -> Dict[str, Any]:
        """生成Mock图谱数据（降级方案）"""
        import random
        from datetime import datetime, timezone
        
        logger.warning(f"使用Mock数据生成图谱: {concept}")
        
        # 预设学科域
        domains = ["数学", "物理", "计算机/AI", "生物/神经科学", "社会科学/经济学"]
        selected_domains = random.sample(domains, random.randint(2, 4))
        
        # 生成节点
        nodes = []
        node_count = random.randint(10, 15)
        
        # 核心节点
        nodes.append({
            "id": "core_1",
            "label": concept,
            "field": "核心",
            "type": "core",
            "summary": f"{concept}的核心概念",
            "importance": 1.0,
            "confidence": 0.95
        })
        
        # 其他节点
        for i in range(1, node_count):
            domain = random.choice(selected_domains + ["核心"])
            node_type = random.choice(["normal", "bridge", "normal", "normal"])
            
            # 生成相关概念名称
            if domain == "数学":
                labels = ["微积分", "概率论", "线性代数", "拓扑学", "群论"]
            elif domain == "物理":
                labels = ["热力学", "量子力学", "相对论", "电磁学", "统计力学"]
            elif domain == "计算机/AI":
                labels = ["机器学习", "神经网络", "算法", "数据结构", "深度学习"]
            elif domain == "生物/神经科学":
                labels = ["神经元", "认知科学", "进化论", "遗传学", "生态学"]
            elif domain == "社会科学/经济学":
                labels = ["博弈论", "宏观经济学", "心理学", "社会学", "行为经济学"]
            else:
                labels = ["相关概念", "衍生概念", "应用实例"]
            
            nodes.append({
                "id": f"node_{i}",
                "label": f"{random.choice(labels)}",
                "field": domain,
                "type": node_type,
                "summary": f"与{concept}相关的{domain}概念",
                "importance": random.uniform(0.3, 0.9),
                "confidence": random.uniform(0.7, 0.95)
            })
        
        # 生成边
        edges = []
        edge_count = random.randint(15, 25)
        relation_types = ["直接关联", "类比关联", "数学关联", "应用关联"]
        
        for i in range(edge_count):
            source = random.choice(nodes)["id"]
            target = random.choice([n for n in nodes if n["id"] != source])["id"]
            
            edges.append({
                "source": source,
                "target": target,
                "relation": random.choice(["形式化为", "应用于", "类比于", "推导出", "相关于"]),
                "relation_type": random.choice(relation_types),
                "confidence": random.uniform(0.6, 0.95),
                "evidence": f"这是{source}和{target}之间的关系依据",
                "direction": "directed"
            })
        
        # 构建完整的GraphJSON
        graph_data = {
            "meta": {
                "core_concept": concept,
                "normalized_concept": concept.lower(),
                "domains": selected_domains,
                "version": "mock-v1",
                "source": "mock-service",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "stats": {
                    "num_nodes": len(nodes),
                    "num_edges": len(edges),
                    "num_domains_covered": len(selected_domains)
                },
                "notes": "这是Mock数据，用于降级方案"
            },
            "nodes": nodes,
            "edges": edges
        }
        
        # 验证数据
        is_valid, message = validator.validate(graph_data)
        if not is_valid:
            logger.warning(f"Mock数据验证警告: {message}")
        
        return graph_data
    
    def normalize_graph(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """图谱标准化处理（去重、合并、规模控制）"""
        try:
            nodes = graph_data.get("nodes", [])
            edges = graph_data.get("edges", [])
            
            # 1. 去重：基于id去重节点
            unique_nodes = {}
            for node in nodes:
                node_id = node.get("id")
                if node_id and node_id not in unique_nodes:
                    unique_nodes[node_id] = node
            
            # 2. 验证边连接的有效性
            valid_edges = []
            node_ids = set(unique_nodes.keys())
            
            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                
                if source in node_ids and target in node_ids:
                    valid_edges.append(edge)
                else:
                    logger.warning(f"移除无效边: {source} -> {target}")
            
            # 3. 控制规模
            max_nodes = settings.AGENT_CONFIG["constraints"]["max_nodes"]
            max_edges = settings.AGENT_CONFIG["constraints"]["max_edges"]
            
            if len(unique_nodes) > max_nodes:
                # 按重要性排序，保留最重要的节点
                sorted_nodes = sorted(unique_nodes.values(), 
                                    key=lambda x: x.get("importance", 0), 
                                    reverse=True)
                unique_nodes = {node["id"]: node for node in sorted_nodes[:max_nodes]}
                logger.info(f"节点数从{len(nodes)}裁剪到{len(unique_nodes)}")
            
            if len(valid_edges) > max_edges:
                # 按置信度排序，保留最高置信度的边
                valid_edges = sorted(valid_edges, 
                                   key=lambda x: x.get("confidence", 0), 
                                   reverse=True)[:max_edges]
                logger.info(f"边数从{len(edges)}裁剪到{len(valid_edges)}")
            
            # 更新图数据
            normalized_data = {
                "meta": {
                    **graph_data.get("meta", {}),
                    "normalized": True,
                    "normalized_at": datetime.now().isoformat(),
                    "stats": {
                        "num_nodes": len(unique_nodes),
                        "num_edges": len(valid_edges),
                        "num_domains_covered": len(set(node.get("field", "") for node in unique_nodes.values()))
                    }
                },
                "nodes": list(unique_nodes.values()),
                "edges": valid_edges
            }
            
            return normalized_data
            
        except Exception as e:
            logger.error(f"图谱标准化失败: {str(e)}")
            return graph_data
    
    async def close(self):
        """关闭HTTP客户端"""
        if self.agent_client:
            await self.agent_client.aclose()

graph_service = GraphService()