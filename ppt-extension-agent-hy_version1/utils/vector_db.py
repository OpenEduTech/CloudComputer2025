"""
向量数据库工具
使用Milvus进行向量存储和语义检索
"""

from typing import Dict, List, Optional
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class VectorDB:
    """
    向量数据库工具
    负责PPT切片的向量化、存储和语义检索
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        collection_name: str = None,
        embedding_model: str = None
    ):
        """
        初始化向量数据库
        
        Args:
            host: Milvus主机地址
            port: Milvus端口
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
        """
        self.host = host or settings.MILVUS_HOST
        self.port = port or settings.MILVUS_PORT
        self.collection_name = collection_name or settings.MILVUS_COLLECTION_NAME
        self.embedding_model_name = embedding_model or settings.EMBEDDING_MODEL
        
        self._connect()
        self._load_embedding_model()
        
        if not utility.has_collection(self.collection_name):
            self._create_collection()
        else:
            self.collection = Collection(self.collection_name)
            self.collection.load()
        
        logger.info("向量数据库初始化完成")
    
    def _connect(self):
        """连接到Milvus"""
        try:
            connections.connect(host=self.host, port=self.port)
            logger.info(f"成功连接到Milvus: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"连接Milvus失败: {str(e)}")
            raise
    
    def _load_embedding_model(self):
        """加载嵌入模型"""
        try:
            logger.info(f"加载嵌入模型: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("嵌入模型加载完成")
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {str(e)}")
            raise
    
    def _create_collection(self):
        """创建集合"""
        try:
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="page_number", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
            ]
            
            schema = CollectionSchema(
                fields=fields,
                description="PPT内容切片向量集合"
            )
            
            self.collection = Collection(
                name=self.collection_name,
                schema=schema
            )
            
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128}
            }
            
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            logger.info(f"集合创建成功: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            raise
    
    def insert_chunks(self, chunks: List[Dict]) -> bool:
        """
        插入文本切片
        
        Args:
            chunks: 文本切片列表，每个切片包含content, title, page_number
            
        Returns:
            是否成功
        """
        try:
            logger.info(f"开始插入{len(chunks)}个文本切片")
            
            ids = []
            contents = []
            titles = []
            page_numbers = []
            embeddings = []
            
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id", f"chunk_{len(ids)}")
                ids.append(chunk_id)
                contents.append(chunk.get("content", ""))
                titles.append(chunk.get("title", ""))
                page_numbers.append(chunk.get("page_number", 0))
                
                embedding = self._generate_embedding(chunk.get("content", ""))
                embeddings.append(embedding)
            
            data = [
                ids,
                contents,
                titles,
                page_numbers,
                embeddings
            ]
            
            self.collection.insert(data)
            self.collection.flush()
            
            logger.info(f"成功插入{len(chunks)}个文本切片")
            return True
            
        except Exception as e:
            logger.error(f"插入文本切片失败: {str(e)}")
            return False
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        page_number: Optional[int] = None
    ) -> List[Dict]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            page_number: 可选，限制在特定页码搜索
            
        Returns:
            搜索结果列表
        """
        try:
            logger.info(f"语义搜索: {query}")
            
            query_embedding = self._generate_embedding(query)
            query_embedding = query_embedding.reshape(1, -1)
            
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            if page_number is not None:
                expr = f"page_number == {page_number}"
            else:
                expr = None
            
            results = self.collection.search(
                data=query_embedding,
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["content", "title", "page_number"]
            )
            
            formatted_results = []
            for result in results[0]:
                formatted_results.append({
                    "content": result.entity.get("content"),
                    "title": result.entity.get("title"),
                    "page_number": result.entity.get("page_number"),
                    "score": result.score
                })
            
            logger.info(f"搜索完成，找到{len(formatted_results)}个结果")
            return formatted_results
            
        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            return []
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        生成文本向量
        
        Args:
            text: 输入文本
            
        Returns:
            向量数组
        """
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"生成向量失败: {str(e)}")
            raise
    
    def delete_by_page(self, page_number: int) -> bool:
        """
        删除特定页码的所有切片
        
        Args:
            page_number: 页码
            
        Returns:
            是否成功
        """
        try:
            expr = f"page_number == {page_number}"
            self.collection.delete(expr)
            logger.info(f"删除页码{page_number}的所有切片")
            return True
        except Exception as e:
            logger.error(f"删除切片失败: {str(e)}")
            return False
    
    def delete_all(self) -> bool:
        """
        删除所有数据
        
        Returns:
            是否成功
        """
        try:
            self.collection.delete(expr="id != ''")
            logger.info("删除所有切片")
            return True
        except Exception as e:
            logger.error(f"删除所有切片失败: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """
        获取集合统计信息
        
        Returns:
            统计信息字典
        """
        try:
            num_entities = self.collection.num_entities
            return {
                "collection_name": self.collection_name,
                "num_entities": num_entities,
                "status": "loaded" if self.collection.is_empty is False else "empty"
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "collection_name": self.collection_name,
                "num_entities": 0,
                "status": "error"
            }
    
    def close(self):
        """关闭连接"""
        try:
            connections.disconnect("default")
            logger.info("向量数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接失败: {str(e)}")
