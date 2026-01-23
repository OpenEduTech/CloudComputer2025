from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import json

class VectorStore:
    def __init__(self, host: str = "localhost", port: str = "19530"):
        """
        初始化Milvus向量数据库连接
        """
        self.host = host
        self.port = port
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 连接Milvus
        connections.connect(host=host, port=port)
        
        # 定义集合结构
        self.collection_name = "ppt_slides"
        self._create_collection_if_not_exists()
        
        # 加载集合
        self.collection = Collection(self.collection_name)
        
    def _create_collection_if_not_exists(self):
        """创建集合（如果不存在）"""
        if not connections.has_collection(self.collection_name):
            # 定义字段
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="ppt_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="page_num", dtype=DataType.INT64),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=10000),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            
            # 创建模式
            schema = CollectionSchema(fields=fields, description="PPT幻灯片向量存储")
            
            # 创建集合
            collection = Collection(
                name=self.collection_name,
                schema=schema,
                using='default',
                shards_num=2
            )
            
            # 创建索引
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            print(f"Collection '{self.collection_name}' created successfully.")
    
    def add_document(self, text: str, metadata: Dict = None) -> int:
        """
        添加文档到向量数据库
        返回: 文档ID
        """
        # 生成嵌入向量
        embedding = self.embedding_model.encode(text).tolist()
        
        # 准备数据
        data = [
            [metadata.get("ppt_id", "")] if metadata else [""],
            [metadata.get("page_num", 0)] if metadata else [0],
            [metadata.get("title", "")] if metadata else [""],
            [text],
            [embedding],
            [json.dumps(metadata) if metadata else "{}"]
        ]
        
        # 插入数据
        insert_result = self.collection.insert(data)
        
        # 刷新集合
        self.collection.flush()
        
        return insert_result.primary_keys[0]
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        语义搜索相似内容
        """
        # 生成查询向量
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # 搜索参数
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        
        # 执行搜索
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["content", "title", "page_num", "ppt_id", "metadata"]
        )
        
        # 格式化结果
        formatted_results = []
        for hits in results:
            for hit in hits:
                formatted_results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.entity.get("content"),
                    "title": hit.entity.get("title"),
                    "page_num": hit.entity.get("page_num"),
                    "metadata": json.loads(hit.entity.get("metadata", "{}"))
                })
        
        return formatted_results
    
    def get_by_id(self, doc_id: int) -> Dict:
        """根据ID获取文档"""
        results = self.collection.query(
            expr=f"id == {doc_id}",
            output_fields=["content", "title", "page_num", "ppt_id", "metadata"]
        )
        
        if results:
            result = results[0]
            return {
                "id": doc_id,
                "content": result.get("content"),
                "title": result.get("title"),
                "page_num": result.get("page_num"),
                "metadata": json.loads(result.get("metadata", "{}"))
            }
        return None
    
    def delete_by_ppt_id(self, ppt_id: str):
        """删除指定PPT的所有文档"""
        self.collection.delete(expr=f'ppt_id == "{ppt_id}"')
        self.collection.flush()