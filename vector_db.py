import os
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

import numpy as np
from sentence_transformers import SentenceTransformer
from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility
)

from parser import SlideContent, SlideStructure

logger = logging.getLogger(__name__)


class VectorDBService:
    """基于 Milvus 的向量数据库服务"""

    def __init__(self, host: str = "localhost", port: int = 19530):
        self.host = host
        self.port = port
        self.collection_name = "ppt_content"
        self.dim = 384  # MiniLM 模型维度
        self.collection = None
        self.embedding_model = None

        # 初始化嵌入模型
        self._init_embedding_model()

        # 连接 Milvus
        self._connect_milvus()

        # 创建或获取集合
        self._init_collection()

    def _init_embedding_model(self):
        """初始化嵌入模型"""
        try:
            # 使用多语言 MiniLM 模型
            self.embedding_model = SentenceTransformer(
                'paraphrase-multilingual-MiniLM-L12-v2'
            )
            logger.info("✅ 嵌入模型加载成功")
        except Exception as e:
            logger.error(f"❌ 嵌入模型加载失败: {e}")
            raise

    def _connect_milvus(self):
        """连接 Milvus"""
        try:
            # 检查是否已连接
            if not connections.has_connection("default"):
                connections.connect(
                    alias="default",
                    host=self.host,
                    port=self.port,
                    timeout=30
                )
            logger.info(f"✅ 连接到 Milvus: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"❌ 连接 Milvus 失败: {e}")
            raise

    def _init_collection(self):
        """初始化集合"""
        try:
            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                logger.info(f"✅ 集合已存在: {self.collection_name}")
                self.collection = Collection(self.collection_name)
            else:
                # 定义字段
                fields = [
                    FieldSchema(
                        name="id",
                        dtype=DataType.VARCHAR,
                        max_length=64,
                        is_primary=True
                    ),
                    FieldSchema(
                        name="embedding",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=self.dim
                    ),
                    FieldSchema(
                        name="document",
                        dtype=DataType.VARCHAR,
                        max_length=65535
                    ),
                    FieldSchema(
                        name="element_type",
                        dtype=DataType.VARCHAR,
                        max_length=50
                    ),
                    FieldSchema(
                        name="slide_num",
                        dtype=DataType.INT64
                    ),
                    FieldSchema(
                        name="file_id",
                        dtype=DataType.VARCHAR,
                        max_length=36
                    ),
                    FieldSchema(
                        name="chunk_num",
                        dtype=DataType.INT64
                    ),
                    FieldSchema(
                        name="metadata",
                        dtype=DataType.JSON
                    ),
                    FieldSchema(
                        name="timestamp",
                        dtype=DataType.INT64
                    )
                ]

                # 创建集合
                schema = CollectionSchema(
                    fields,
                    description="PPT内容向量存储",
                    enable_dynamic_field=True
                )

                # 索引参数
                index_params = {
                    "metric_type": "IP",  # 内积相似度
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }

                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema,
                    consistency_level="Strong"
                )

                # 创建索引
                self.collection.create_index(
                    field_name="embedding",
                    index_params=index_params
                )

                logger.info(f"✅ 创建集合: {self.collection_name}")

            # 加载集合到内存
            self.collection.load()
            logger.info("✅ 集合加载到内存")

        except Exception as e:
            logger.error(f"❌ 初始化集合失败: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """生成文本向量"""
        try:
            if not text or not text.strip():
                return [0.0] * self.dim

            # 生成嵌入向量
            embedding = self.embedding_model.encode(text)

            # 【关键修复】进行L2归一化
            # 这样内积的范围就能控制在[-1, 1]之间
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ 生成向量失败: {e}")
            return [0.0] * self.dim

    def index_slide(self, file_id: str, slide: SlideContent, slide_structure: SlideStructure = None):
        """索引单张幻灯片"""
        try:
            logger.info(f"索引幻灯片: {slide.slide_number}")

            # 准备要索引的内容
            content_chunks = []

            # 1. 索引标题
            if slide.title and slide.title.strip():
                content_chunks.append({
                    "text": f"标题: {slide.title}",
                    "type": "title",
                    "metadata": {
                        "original_content": slide.title,
                        "slide_num": slide.slide_number
                    }
                })

            # 2. 索引正文内容（分块）
            for i, content in enumerate(slide.content):
                if content and content.strip():
                    chunks = self._chunk_text(content, max_length=200)
                    for chunk_num, chunk in enumerate(chunks):
                        content_chunks.append({
                            "text": f"正文{i + 1}_块{chunk_num + 1}: {chunk}",
                            "type": "content",
                            "metadata": {
                                "original_content": chunk,
                                "slide_num": slide.slide_number,
                                "chunk_num": chunk_num,
                                "original_index": i
                            }
                        })

            # 3. 索引项目符号
            for i, bullet in enumerate(slide.bullet_points):
                if bullet and bullet.strip():
                    content_chunks.append({
                        "text": f"项目符号{i + 1}: {bullet}",
                        "type": "bullet",
                        "metadata": {
                            "original_content": bullet,
                            "slide_num": slide.slide_number,
                            "bullet_index": i
                        }
                    })

            # 4. 索引备注
            if slide.notes and slide.notes.strip():
                content_chunks.append({
                    "text": f"备注: {slide.notes}",
                    "type": "notes",
                    "metadata": {
                        "original_content": slide.notes,
                        "slide_num": slide.slide_number
                    }
                })

            # 如果没有内容可索引
            if not content_chunks:
                logger.warning(f"幻灯片 {slide.slide_number} 没有可索引的内容")
                return False

            # 准备批量插入数据
            ids = []
            embeddings = []
            documents = []
            element_types = []
            slide_nums = []
            file_ids = []
            chunk_nums = []
            metadatas = []
            timestamps = []

            current_time = int(datetime.now().timestamp())

            for i, chunk_info in enumerate(content_chunks):
                chunk_id = f"{file_id}_slide_{slide.slide_number}_chunk_{i}"
                text = chunk_info["text"]

                # 生成向量
                embedding = self.generate_embedding(text)

                # 准备数据
                ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(text)
                element_types.append(chunk_info["type"])
                slide_nums.append(slide.slide_number)
                file_ids.append(file_id)
                chunk_nums.append(chunk_info["metadata"].get("chunk_num", 0))
                metadatas.append(chunk_info["metadata"])
                timestamps.append(current_time)

            # 批量插入
            data = [
                ids,
                embeddings,
                documents,
                element_types,
                slide_nums,
                file_ids,
                chunk_nums,
                metadatas,
                timestamps
            ]

            insert_result = self.collection.insert(data)

            logger.info(f"✅ 索引幻灯片 {slide.slide_number}: {len(content_chunks)} 个内容块")
            return True

        except Exception as e:
            logger.error(f"❌ 索引幻灯片失败: {e}")
            return False

    def index_slide_structure(self, file_id: str, slide_structure: SlideStructure):
        """索引幻灯片结构信息"""
        try:
            # 准备结构信息
            structure_text = f"幻灯片结构: {slide_structure.content_type}"
            if slide_structure.parent_titles:
                structure_text += f", 父级路径: {' > '.join(slide_structure.parent_titles)}"

            metadata = {
                "content_type": slide_structure.content_type,
                "hierarchical_level": slide_structure.hierarchical_level,
                "slide_num": slide_structure.slide_number,
                "parent_titles": slide_structure.parent_titles,
                "is_title_page": slide_structure.is_title_page,
                "is_toc": slide_structure.is_toc,
                "has_images": slide_structure.has_images,
                "has_tables": slide_structure.has_tables,
                "has_code": slide_structure.has_code
            }

            # 生成向量
            embedding = self.generate_embedding(structure_text)

            # 插入数据
            structure_id = f"{file_id}_structure_{slide_structure.slide_number}"
            current_time = int(datetime.now().timestamp())

            data = [
                [structure_id],
                [embedding],
                [structure_text],
                ["structure"],
                [slide_structure.slide_number],
                [file_id],
                [0],
                [metadata],
                [current_time]
            ]

            self.collection.insert(data)

            logger.info(f"✅ 索引幻灯片结构: {slide_structure.slide_number}")
            return True

        except Exception as e:
            logger.error(f"❌ 索引幻灯片结构失败: {e}")
            return False

    def index_file(self, file_id: str, slides: List[SlideContent], structures: List[SlideStructure] = None):
        """索引整个文件"""
        try:
            logger.info(f"开始索引文件: {file_id}, 幻灯片数: {len(slides)}")

            indexed_count = 0
            for slide in slides:
                # 查找对应的结构信息
                slide_structure = None
                if structures:
                    for structure in structures:
                        if structure.slide_number == slide.slide_number:
                            slide_structure = structure
                            break

                if self.index_slide(file_id, slide, slide_structure):
                    indexed_count += 1

                # 索引结构信息
                if slide_structure:
                    self.index_slide_structure(file_id, slide_structure)

            # 刷新索引
            self.collection.flush()

            logger.info(f"✅ 文件索引完成: {indexed_count}/{len(slides)} 张幻灯片")
            return indexed_count

        except Exception as e:
            logger.error(f"❌ 文件索引失败: {e}")
            return 0

    def search(
            self,
            query: str,
            file_id: Optional[str] = None,
            n_results: int = 10,
            similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        try:
            # 生成查询向量
            query_embedding = self.generate_embedding(query)

            # 构建搜索参数
            search_params = {
                "metric_type": "IP",
                "params": {"nprobe": 10}
            }

            # 构建过滤条件
            expr = None
            if file_id:
                expr = f'file_id == "{file_id}"'

            # 执行搜索
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=n_results,
                expr=expr,
                output_fields=["document", "element_type", "slide_num", "file_id", "metadata"],
                consistency_level="Strong"
            )

            # 处理结果
            search_results = []
            if results:
                for hits in results:
                    for hit in hits:
                        # 【修改这里】直接使用 Milvus 返回的相似度分数
                        similarity = hit.score  # 不要用 (hit.score + 1) / 2

                        # 边界保护（可选，但推荐）
                        similarity = max(0.0, min(1.0, similarity))  # 确保在0-1之间

                        if similarity >= similarity_threshold:
                            entity = hit.entity
                            search_results.append({
                                "document": entity.get("document"),
                                "element_type": entity.get("element_type"),
                                "slide_number": entity.get("slide_num"),
                                "file_id": entity.get("file_id"),
                                "metadata": entity.get("metadata"),
                                "similarity": float(similarity),
                                "id": hit.id
                            })

            # 按相似度排序
            search_results.sort(key=lambda x: x["similarity"], reverse=True)

            logger.info(f"✅ 搜索完成: '{query}' -> {len(search_results)} 个结果")
            return search_results

        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            return []

    def search_similar_slides(
            self,
            slide_content: str,
            file_id: Optional[str] = None,
            n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """搜索相似的幻灯片"""
        try:
            # 搜索内容
            search_results = self.search(
                query=slide_content,
                file_id=file_id,
                n_results=n_results * 3  # 多搜一些用于分组
            )

            # 按幻灯片分组
            slide_results = {}
            for result in search_results:
                slide_num = result["slide_number"]
                if slide_num not in slide_results:
                    slide_results[slide_num] = {
                        "slide_number": slide_num,
                        "file_id": result["file_id"],
                        "elements": [],
                        "max_similarity": 0.0,
                        "avg_similarity": 0.0
                    }

                slide_results[slide_num]["elements"].append({
                    "content": result["document"],
                    "element_type": result["element_type"],
                    "similarity": result["similarity"]
                })

                # 更新相似度统计
                slide_results[slide_num]["max_similarity"] = max(
                    slide_results[slide_num]["max_similarity"],
                    result["similarity"]
                )

            # 转换为列表并按最大相似度排序
            sorted_results = sorted(
                slide_results.values(),
                key=lambda x: x["max_similarity"],
                reverse=True
            )

            # 计算平均相似度
            for result in sorted_results[:n_results]:
                similarities = [elem["similarity"] for elem in result["elements"]]
                result["avg_similarity"] = sum(similarities) / len(similarities) if similarities else 0

            return sorted_results[:n_results]

        except Exception as e:
            logger.error(f"❌ 相似幻灯片搜索失败: {e}")
            return []

    def get_slide_context(self, file_id: str, slide_number: int, context_size: int = 2):
        """获取幻灯片上下文"""
        try:
            # 搜索当前幻灯片的内容作为查询
            slide_query = f"slide_{slide_number}"

            # 搜索相关的幻灯片
            results = self.collection.query(
                expr=f'file_id == "{file_id}"',
                output_fields=["slide_num"],
                limit=100
            )

            # 提取幻灯片编号
            slide_nums = [r.get("slide_num") for r in results if r.get("slide_num") is not None]
            slide_nums = list(set(slide_nums))
            slide_nums.sort()

            # 获取当前幻灯片附近的范围
            try:
                current_index = slide_nums.index(slide_number)
                start = max(0, current_index - context_size)
                end = min(len(slide_nums), current_index + context_size + 1)
                context_slides = slide_nums[start:end]
            except ValueError:
                # 如果当前幻灯片不在结果中
                context_slides = slide_nums[:context_size * 2 + 1]

            return context_slides

        except Exception as e:
            logger.error(f"❌ 获取幻灯片上下文失败: {e}")
            return []

    def get_collection_stats(self):
        """获取集合统计信息"""
        try:
            stats = {
                "collection_name": self.collection_name,
                "total_entities": self.collection.num_entities,
                "is_loaded": self.collection.is_loaded,
                "status": "active"
            }

            return stats

        except Exception as e:
            return {"error": str(e)}

    def delete_file(self, file_id: str) -> bool:
        """删除文件的所有向量"""
        try:
            expr = f'file_id == "{file_id}"'

            # 执行删除
            delete_result = self.collection.delete(expr)

            logger.info(f"✅ 删除文件向量: {file_id}, 数量: {delete_result.delete_count}")
            return True

        except Exception as e:
            logger.error(f"❌ 删除文件向量失败: {e}")
            return False

    def _chunk_text(self, text: str, max_length: int = 200, overlap: int = 50):
        """将文本分块"""
        if len(text) <= max_length:
            return [text]

        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space

            if current_length + word_length > max_length:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))

                # 保留重叠部分
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:]
                    current_length = sum(len(w) + 1 for w in current_chunk)
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(word)
            current_length += word_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def close(self):
        """关闭连接"""
        try:
            if self.collection:
                self.collection.release()
            connections.disconnect("default")
            logger.info("✅ Milvus 连接已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭连接失败: {e}")


# 全局向量数据库实例
vector_db = VectorDBService(
    host=os.getenv("MILVUS_HOST", "localhost"),
    port=int(os.getenv("MILVUS_PORT", "19530"))
)