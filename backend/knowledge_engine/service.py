import logging
from typing import List, Optional
from common.models import Chunk
from .core.rag_engine import rag_engine
from .core.graph_processor import graph_processor
from .core.storage import storage
from .core.neo4j_client import neo4j_client 
from lightrag import QueryParam

logger = logging.getLogger("knowledge-service")

class KnowledgeService:
    def __init__(self):
        self.rag = rag_engine
        self.processor = graph_processor
        self.storage = storage
        self.neo4j = neo4j_client

    async def ingest_and_build_graph(self, concept: str, chunks: List[Chunk]) -> dict:
        """
        [被 Search Agent 调用]
        将搜索到的 Chunks 入库并构建图谱
        """
        if not chunks:
            return {"status": "skipped", "reason": "no_chunks"}

        logger.info(f"Start building graph for '{concept}' with {len(chunks)} chunks.")
        
        # 1. 转换模型
        documents = []
        for chunk in chunks:
            documents.append({
                "doc_id": chunk.id,
                "domain": chunk.discipline,
                "content": chunk.content,
                "source": chunk.source.model_dump(),
                "relevance_score": chunk.relevance_score,
                "academic_value": chunk.academic_value,
            })
            
        # 2. 存储原始文档
        self.storage.save_documents(documents)
        
        # 3. LightRAG 构建
        try:
            working_dir, chunk_mapping = await self.rag.build_graph(concept, documents)
            
            # 4. 解析为前端图谱格式
            graph_data = self.processor.process_lightrag_output(
                working_dir, documents, concept, chunk_mapping
            )
            
             # 5. 保存图谱 JSON (文件存储 - 兼容旧逻辑)
            self.storage.save_graph(concept, graph_data)
            
            # 6. 同步保存到 Neo4j 
            try:
                logger.info(f"Syncing graph '{concept}' to Neo4j...")
                await self.neo4j.save_graph(
                    concept=concept, 
                    nodes=graph_data["nodes"], 
                    edges=graph_data["edges"]
                )
            except Exception as ne:
                logger.error(f"Failed to sync to Neo4j: {ne}") 
            
            logger.info(f"Graph built successfully: {concept}")
            return {"status": "success", "nodes_count": len(graph_data.get("nodes", []))}
            
        except Exception as e:
            logger.exception(f"Graph build failed for {concept}")
            raise e

    def get_graph(self, concept: str) -> Optional[dict]:
        """[被 Central Agent 调用] 获取图谱数据"""
        return self.storage.get_graph(concept)

    def get_chunk(self, chunk_id: str) -> Optional[dict]:
        """[被 Central Agent 调用] 获取原始文档片段"""
        return self.storage.get_document(chunk_id)

    def list_concepts(self) -> List[str]:
        """[被 Central Agent 调用] 列出已有图谱"""
        import os 
        graph_dir = "./data/graphs"
        if not os.path.exists(graph_dir):
            return []
        return [f.replace('.json', '') for f in os.listdir(graph_dir) if f.endswith('.json')]

    async def qa(self, concept: str, source: str, target: str, question: Optional[str] = None) -> str:
        """[被 Central Agent 调用] 知识问答"""
        if not question:
            question = f"请详细说明 '{source}' 和 '{target}' 之间的关系，并提供推理过程，100字左右。"
        else:
            question = f"在知识图谱中，关于 '{source}' 和 '{target}'：{question}"
            
        prompt = f"""
        1. 核心概念：{concept}
        2. 起始节点：{source}
        3. 目标节点：{target}
        请从知识图谱中检索信息回答：{question}
        """
        
        query_param = QueryParam(mode="hybrid")
        return await self.rag.query(concept, prompt, param=query_param)