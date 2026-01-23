"""
向量存储服务 
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError:
        raise ImportError("需要安装 langchain-chroma 或 langchain-community")

from src.agents.base import LLMConfig


class VectorStoreService:
    """
    向量存储服务 - 重新设计版本
    
    核心原则：
    1. 保持幻灯片完整性 - 每个幻灯片作为一个完整的文档存储
    2. 简化文本转换 - 直接使用PPT解析结果，不做多余处理
    3. 优化搜索策略 - 提高相关性，减少噪音
    """
    
    def __init__(self, llm_config: LLMConfig, vector_db_path: str = "./ppt_vector_db", embedding_model: Optional[str] = None):
        """初始化向量存储服务
        
        Args:
            llm_config: LLM配置
            vector_db_path: 向量数据库路径
            embedding_model: Embedding模型名称，如果为None则使用默认模型
        """
        self.llm_config = llm_config
        self.vector_db_path = vector_db_path

        # 初始化Embedding模型
        embedding_kwargs = {
            "api_key": llm_config.api_key,
            "base_url": llm_config.base_url
        }
        
        if embedding_model:
            try:
                embedding_kwargs["model"] = embedding_model
                self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
                print(f"✅ 使用配置的Embedding模型: {embedding_model}")
            except Exception as e:
                print(f"⚠️  使用配置的Embedding模型失败 ({embedding_model}): {e}")
                print(f"💡 尝试使用默认模型...")
                embedding_kwargs.pop("model", None)
                self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
        else:
            try:
                embedding_kwargs["model"] = "BAAI/bge-large-zh-v1.5"
                self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
                print(f"✅ 使用默认Embedding模型: BAAI/bge-large-zh-v1.5")
            except Exception as e:
                print(f"⚠️  默认Embedding模型不可用: {e}")
                print(f"💡 尝试使用API默认模型...")
                embedding_kwargs.pop("model", None)
                self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
                print(f"✅ 使用API默认Embedding模型")
        
        self.vectorstore: Optional[Chroma] = None
        try:
            self._initialize_vectorstore()
        except Exception as e:
            print(f"❌ 向量数据库服务初始化失败: {e}")
            self.vectorstore = None
    
    def _initialize_vectorstore(self):
        """初始化向量数据库"""
        try:
            os.makedirs(self.vector_db_path, exist_ok=True)
            
            if os.path.exists(self.vector_db_path) and os.listdir(self.vector_db_path):
                try:
                    self.vectorstore = Chroma(
                        persist_directory=self.vector_db_path,
                        embedding_function=self.embeddings
                    )
                    print(f"✅ 向量数据库初始化成功 (路径: {self.vector_db_path})")
                    return
                except Exception as e:
                    print(f"⚠️  加载现有数据库失败: {e}")
                    import shutil
                    shutil.rmtree(self.vector_db_path)
                    os.makedirs(self.vector_db_path, exist_ok=True)
            
            # 创建新数据库
            self.vectorstore = Chroma(
                persist_directory=self.vector_db_path,
                embedding_function=self.embeddings
            )
            print(f"✅ 向量数据库初始化成功 (路径: {self.vector_db_path})")
            
        except Exception as e:
            print(f"❌ 向量数据库初始化失败: {e}")
            raise
    
    def _extract_slide_text(self, slide: Dict[str, Any]) -> str:
        """
        从幻灯片中提取文本
        核心原则：简单、完整、保留原始信息
        """
        text_parts = []
        
        # 1. 标题
        title = slide.get("title", "").strip()
        if title:
            text_parts.append(title)
        
        # 2. 内容点
        raw_points = slide.get("raw_points", [])
        for point in raw_points:
            if isinstance(point, dict):
                text = point.get("text", "").strip()
                if text:
                    # 添加层级缩进
                    level = point.get("level", 0)
                    indent = "  " * level
                    text_parts.append(f"{indent}{text}")
            elif isinstance(point, str):
                text = point.strip()
                if text:
                    text_parts.append(text)
        
        # 组合文本
        full_text = "\n".join(text_parts)
        
        return full_text
    
    def _split_text_for_embedding(self, text: str, max_tokens: int = 400) -> List[str]:
        """
        将长文本分割成多个chunk，确保每个chunk不超过token限制
        
        Args:
            text: 原始文本
            max_tokens: 最大token数（保守估计：1个token ≈ 3个字符）
        
        Returns:
            分割后的文本块列表
        """
        max_chars = max_tokens * 3
        
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            
            if current_length + line_length > max_chars and current_chunk:
                # 当前chunk已满，保存
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length
        
        # 添加最后一个chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        final_chunks = []
        for chunk in chunks:
            if len(chunk) > max_chars:
                # 强制截断
                for i in range(0, len(chunk), max_chars):
                    final_chunks.append(chunk[i:i + max_chars])
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def store_document_slides(
        self,
        file_name: str,
        file_type: str,
        slides: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        存储文档的所有幻灯片到向量数据库
        
        核心策略：
        1. 每个幻灯片作为一个完整的文档（不分块）
        2. 保留所有原始信息
        3. 添加丰富的元数据便于过滤
        """
        if not self.vectorstore:
            raise Exception("向量数据库未初始化")
   
        if overwrite:
            self.delete_file_slides(file_name)
        
        documents = []
        ids = []
        stored_count = 0
        
        print(f"📝 开始存储文档: {file_name}，共 {len(slides)} 页")
        
        for slide in slides:
            # 提取文本
            slide_text = self._extract_slide_text(slide)
            
            # 调试信息
            page_num = slide.get('page_num', 0)
            print(f"  📄 页面 {page_num}: 提取文本 {len(slide_text)} 字符")
            
            # 过滤空内容
            if not slide_text or len(slide_text.strip()) < 10:
                print(f"  ⏭️  跳过页面 {page_num}：内容过短（{len(slide_text)} 字符）")
                continue
            
            # 如果文本太长，分割成多个chunk
            text_chunks = self._split_text_for_embedding(slide_text, max_tokens=400)
            
            if len(text_chunks) > 1:
                print(f"  ✂️  页面 {page_num} 文本较长，分割为 {len(text_chunks)} 个chunk")
            
            # 为每个chunk创建文档
            for chunk_idx, chunk_text in enumerate(text_chunks):
                doc_id = f"{file_name}_{page_num}_{chunk_idx}_{uuid.uuid4().hex[:6]}"
                
                doc = Document(
                    page_content=chunk_text,
                    metadata={
                        "file_name": file_name,
                        "file_type": file_type,
                        "page_num": page_num,
                        "slide_title": slide.get("title", ""),
                        "slide_type": slide.get("type", "content"),
                        "chunk_index": chunk_idx,
                        "total_chunks": len(text_chunks),
                        "stored_at": datetime.now().isoformat(),
                        **(metadata or {})
                    }
                )
                
                documents.append(doc)
                ids.append(doc_id)
            
            print(f"  ✓ 页面 {page_num} 已加入存储队列（{len(text_chunks)} 个chunk）")
        
        # 批量存储
        if documents:
            print(f"  📦 准备存储 {len(documents)} 个文档到向量数据库")
            try:
                batch_size = 5  
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i + batch_size]
                    batch_ids = ids[i:i + batch_size]
                    
                    print(f"  🔄 正在存储批次 {i//batch_size + 1}，包含 {len(batch_docs)} 个文档...")
                    
                    try:
                        self.vectorstore.add_documents(
                            documents=batch_docs,
                            ids=batch_ids
                        )
                        stored_count += len(batch_docs)
                        print(f"  ✅ 已存储 {stored_count}/{len(documents)} 页")
                    except Exception as batch_err:
                        print(f"  ⚠️ 批次存储失败，尝试逐个存储...")
                        for doc, doc_id in zip(batch_docs, batch_ids):
                            try:
                                self.vectorstore.add_documents(
                                    documents=[doc],
                                    ids=[doc_id]
                                )
                                stored_count += 1
                                print(f"    ✓ 页面 {doc.metadata.get('page_num')} 已存储")
                            except Exception as single_err:
                                error_msg = str(single_err)
                                if "512 tokens" in error_msg:
                                    print(f"    ✗ 页面 {doc.metadata.get('page_num')} 文本过长，跳过")
                                else:
                                    print(f"    ✗ 页面 {doc.metadata.get('page_num')} 存储失败: {single_err}")
                
                # 持久化
                try:
                    if hasattr(self.vectorstore, 'persist'):
                        self.vectorstore.persist()
                        print(f"  💾 数据已持久化")
                except Exception as persist_err:
                    pass  
                
                print(f"✅ 存储完成: {file_name}，共 {stored_count} 页")
                
            except Exception as e:
                print(f"❌ 存储失败: {e}")
                import traceback
                traceback.print_exc()
                raise
        else:
            print(f"⚠️  没有文档需要存储（所有页面可能都被过滤掉了）")
        
        return {
            "file_name": file_name,
            "file_type": file_type,
            "total_slides": len(slides),
            "total_chunks": stored_count, 
            "stored_at": datetime.now().isoformat()
        }
    
    def search_similar_slides(
        self,
        query: str,
        top_k: int = 10,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        语义搜索相似的幻灯片
        
        优化策略：
        1. 使用更宽松的搜索范围（搜索更多结果）
        2. 按页面去重（每个页面只返回一次）
        3. 使用更合理的相似度计算
        4. 按相似度排序
        5. 如果向量搜索失败，自动降级到关键词搜索
        """
        if not self.vectorstore:
            print("⚠️  向量数据库未初始化")
            return []
        
        # 调试信息
        print(f"\n🔍 开始搜索:")
        print(f"   查询: {query}")
        print(f"   top_k: {top_k}, min_score: {min_score}")
        print(f"   文件过滤: {file_name or '无'}")
        
        # 构建过滤条件
        where = {}
        if file_name:
            where["file_name"] = file_name
        if file_type:
            where["file_type"] = file_type
        
        try:
            # 搜索更多结果去重
            search_k = max(top_k * 2, 20)
            
            # 执行向量搜索
            if where:
                results = self.vectorstore.similarity_search_with_score(
                    query,
                    k=search_k,
                    filter=where
                )
            else:
                results = self.vectorstore.similarity_search_with_score(
                    query,
                    k=search_k
                )
            
            print(f"   原始结果数: {len(results)}")
            
            if results:
                print(f"   前5个结果的文件名:")
                for i, (doc, dist) in enumerate(results[:5]):
                    print(f"     {i+1}. {doc.metadata.get('file_name', 'unknown')} - 页 {doc.metadata.get('page_num', '?')} (距离: {dist:.3f})")
            
            page_best_results = {}  # {(file_name, page_num): best_result}
            filtered_count = 0
            
            # 提取查询关键词
            query_lower = query.lower().strip()
            query_keywords = set(query_lower.split())
            if len(query_lower) >= 2:
                query_keywords.add(query_lower)  
            
            for doc, distance in results:
                # 计算相似度
                similarity = 1.0 - (distance / 2.0)
                similarity = max(0.0, min(1.0, similarity))
                
                # 过滤低相似度结果
                if similarity < min_score:
                    filtered_count += 1
                    continue
                
                # 计算关键词匹配度
                content_lower = doc.page_content.lower()
                keyword_match_score = 0.0
                matched_keywords = 0
                full_query_matched = False
                
                # 首先检查完整查询是否匹配
                if query_lower in content_lower:
                    full_query_matched = True
                    count = content_lower.count(query_lower)
                    keyword_match_score += min(0.6, 0.4 + (count - 1) * 0.1)
                    matched_keywords += 1
                    print(f"   ✅ 完整匹配查询 '{query_lower}' 在 {doc.metadata.get('file_name', 'unknown')} 页{doc.metadata.get('page_num', '?')} (出现{count}次)")
                
                # 然后检查单个关键词匹配
                for keyword in query_keywords:
                    if keyword == query_lower:
                        continue  
                    if len(keyword) >= 2:  
                        count = content_lower.count(keyword)
                        if count > 0:
                            matched_keywords += 1
                            keyword_match_score += min(0.3, 0.2 + (count - 1) * 0.05)
                
                # 如果匹配了多个关键词，额外加分
                if matched_keywords >= 2:
                    keyword_match_score += 0.15
                
                # 如果没有匹配任何关键词，适当降分
                if matched_keywords == 0:
                    keyword_match_score = -0.1  # 降分0.1
                    print(f"   ⚠️ 无关键词匹配: {doc.metadata.get('file_name', 'unknown')} 页{doc.metadata.get('page_num', '?')} (语义分={similarity:.3f})")
                
                # 综合相似度 = 语义相似度 + 关键词匹配加分/降分
                final_similarity = max(0.0, min(1.0, similarity + keyword_match_score))
                
                metadata = doc.metadata
                page_key = (
                    metadata.get("file_name", ""),
                    metadata.get("page_num", 0)
                )
                
                # 去重
                if page_key in page_best_results:
                    if final_similarity > page_best_results[page_key]["score"]:
                        page_best_results[page_key] = {
                            "content": doc.page_content,
                            "metadata": metadata,
                            "score": final_similarity,
                            "distance": distance,
                            "semantic_score": similarity,  
                            "keyword_boost": keyword_match_score  
                        }
                else:
                    page_best_results[page_key] = {
                        "content": doc.page_content,
                        "metadata": metadata,
                        "score": final_similarity,
                        "distance": distance,
                        "semantic_score": similarity,
                        "keyword_boost": keyword_match_score
                    }
            
            # 转换为列表
            formatted_results = list(page_best_results.values())
            
            # 优化排序
            if file_name:
                for result in formatted_results:
                    if result["metadata"].get("file_name") == file_name:
                        result["score"] = min(1.0, result["score"] + 0.2)
                        result["boosted"] = True
            
            # 按相似度排序
            formatted_results.sort(key=lambda x: x["score"], reverse=True)
            
            # 调试信息
            print(f"   过滤掉 {filtered_count} 个低分结果")
            print(f"   去重后结果数: {len(formatted_results)}")
            if formatted_results:
                print(f"   最高分: {formatted_results[0]['score']:.3f} (语义: {formatted_results[0].get('semantic_score', 0):.3f}, 关键词加分: {formatted_results[0].get('keyword_boost', 0):.3f})")
                print(f"   最低分: {formatted_results[-1]['score']:.3f}")
                print(f"   前3个结果详情:")
                for i, r in enumerate(formatted_results[:3]):
                    print(f"     {i+1}. {r['metadata'].get('file_name', 'unknown')} 页{r['metadata'].get('page_num', '?')}: "
                          f"总分={r['score']:.3f} (语义={r.get('semantic_score', 0):.3f}, "
                          f"关键词={r.get('keyword_boost', 0):.3f})")
                file_distribution = {}
                for r in formatted_results:
                    fn = r['metadata'].get('file_name', 'unknown')
                    file_distribution[fn] = file_distribution.get(fn, 0) + 1
                print(f"   文件分布:")
                for fn, count in file_distribution.items():
                    is_target = " ⭐" if file_name and fn == file_name else ""
                    print(f"     - {fn}: {count} 个结果{is_target}")
            else:
                print(f"   ⚠️ 没有找到满足条件的结果！")
                if min_score > 0:
                    print(f"   💡 提示: 当前min_score={min_score}可能过高，尝试降低或设为0")
            
            return formatted_results[:top_k]
            
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  向量搜索失败: {error_msg}")

            if "500" in error_msg or "InternalServerError" in error_msg or "50500" in error_msg:
                print(f"❌ Embedding API 服务错误 (500)")
                print(f"   可能原因:")
                print(f"   1. Embedding模型不支持或配置错误")
                print(f"   2. API服务暂时不可用")
                print(f"   3. API Key权限不足")
                print(f"💡 自动降级到关键词搜索...")

                try:
                    keyword_results = self.search_by_keyword(
                        query=query,
                        top_k=top_k,
                        file_name=file_name
                    )
                    if keyword_results:
                        print(f"✅ 关键词搜索成功，返回 {len(keyword_results)} 个结果")
                        print(f"💡 提示: 关键词搜索基于文本匹配，可能不如语义搜索精确")
                        return keyword_results
                    else:
                        print(f"⚠️  关键词搜索也没有结果")
                except Exception as e2:
                    print(f"❌ 关键词搜索也失败: {e2}")
            else:
                print(f"❌ 向量搜索遇到未知错误: {error_msg}")
                print(f"💡 尝试降级到关键词搜索...")
                try:
                    keyword_results = self.search_by_keyword(
                        query=query,
                        top_k=top_k,
                        file_name=file_name
                    )
                    if keyword_results:
                        print(f"✅ 关键词搜索成功，返回 {len(keyword_results)} 个结果")
                        return keyword_results
                except Exception as e2:
                    print(f"❌ 关键词搜索也失败: {e2}")
            
            return []
    
    def search_by_keyword(
        self,
        query: str,
        top_k: int = 10,
        file_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        基于关键词的文本搜索（作为向量搜索的补充）
        适用于精确关键词匹配
        """
        if not self.vectorstore:
            return []
        
        try:
            # 获取所有文档
            all_results = self.vectorstore.get()
            if not all_results or "documents" not in all_results:
                return []
            
            documents = all_results["documents"]
            metadatas = all_results.get("metadatas", [])
            
            # 关键词搜索
            query_lower = query.lower()
            results = []
            
            for i, doc_text in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                
                # 文件过滤
                if file_name and metadata.get("file_name") != file_name:
                    continue
                
                doc_text_lower = doc_text.lower()
                
                # 计算关键词匹配度
                if query_lower in doc_text_lower:
                    match_count = doc_text_lower.count(query_lower)
                    score = min(match_count / 10, 1.0)  
                    
                    results.append({
                        "content": doc_text,
                        "metadata": metadata,
                        "score": score,
                        "match_count": match_count,
                        "method": "keyword"
                    })
                    
            results.sort(key=lambda x: (x["score"], x.get("match_count", 0)), reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            print(f"⚠️  关键词搜索失败: {e}")
            return []
    
    def search_hybrid(
        self,
        query: str,
        top_k: int = 10,
        file_name: Optional[str] = None,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        混合搜索：结合语义搜索和关键词搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            file_name: 限制搜索的文件
            semantic_weight: 语义搜索权重（0-1）
            keyword_weight: 关键词搜索权重（0-1）
        """
        # 执行两种搜索
        semantic_results = self.search_similar_slides(
            query=query,
            top_k=top_k * 2,
            file_name=file_name,
            min_score=0.0
        )
        
        keyword_results = self.search_by_keyword(
            query=query,
            top_k=top_k * 2,
            file_name=file_name
        )
        
        # 合并结果
        combined = {}
        
        # 添加语义搜索结果
        for result in semantic_results:
            page_key = (
                result["metadata"].get("file_name", ""),
                result["metadata"].get("page_num", 0)
            )
            combined[page_key] = {
                "content": result["content"],
                "metadata": result["metadata"],
                "semantic_score": result["score"] * semantic_weight,
                "keyword_score": 0,
                "final_score": result["score"] * semantic_weight
            }
        
        # 添加关键词搜索结果
        for result in keyword_results:
            page_key = (
                result["metadata"].get("file_name", ""),
                result["metadata"].get("page_num", 0)
            )
            keyword_score = result["score"] * keyword_weight
            
            if page_key in combined:
                combined[page_key]["keyword_score"] = keyword_score
                combined[page_key]["final_score"] += keyword_score
            else:
                combined[page_key] = {
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "semantic_score": 0,
                    "keyword_score": keyword_score,
                    "final_score": keyword_score
                }
        
        # 转换为列表并排序
        final_results = list(combined.values())
        final_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return final_results[:top_k]
    
    def search_by_file(self, file_name: str) -> List[Dict[str, Any]]:
        """获取特定文件的所有切片"""
        if not self.vectorstore:
            return []
        
        try:
            results = self.vectorstore.get(where={"file_name": file_name})
            
            formatted_results = []
            if results and "documents" in results:
                for i, doc_content in enumerate(results["documents"]):
                    metadata = results["metadatas"][i] if "metadatas" in results else {}
                    formatted_results.append({
                        "content": doc_content,
                        "metadata": metadata
                    })
            
            return formatted_results
        except Exception as e:
            print(f"⚠️  按文件搜索失败: {e}")
            return []
    
    def delete_file_slides(self, file_name: str) -> bool:
        """删除特定文件的所有切片"""
        if not self.vectorstore:
            return False
        
        try:
            results = self.vectorstore.get(where={"file_name": file_name})
            
            if results and "ids" in results:
                ids_to_delete = results["ids"]
                if ids_to_delete:
                    self.vectorstore.delete(ids=ids_to_delete)
                    try:
                        self.vectorstore.persist()
                    except:
                        pass
                    print(f"✅ 已删除文件 {file_name} 的 {len(ids_to_delete)} 个切片")
                    return True
            
            return False
        except Exception as e:
            print(f"⚠️  删除文件切片失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取向量数据库统计信息"""
        if not self.vectorstore:
            return {"total_documents": 0, "total_files": 0}
        
        try:
            all_results = self.vectorstore.get()
            
            total_docs = len(all_results.get("ids", [])) if all_results else 0
            
            # 统计信息
            file_types = defaultdict(int)
            file_names = set()
            page_count_by_file = defaultdict(int)
            
            if all_results and "metadatas" in all_results:
                for metadata in all_results["metadatas"]:
                    file_type = metadata.get("file_type", "unknown")
                    file_name = metadata.get("file_name", "unknown")
                    
                    file_types[file_type] += 1
                    file_names.add(file_name)
                    page_count_by_file[file_name] += 1
            
            stats = {
                "total_documents": total_docs,
                "total_files": len(file_names),
                "file_types": dict(file_types),
                "files": dict(page_count_by_file),
                "vector_db_path": self.vector_db_path
            }
            
            # 打印统计信息
            print(f"\n📊 向量数据库统计:")
            print(f"   总文档数: {total_docs}")
            print(f"   文件数: {len(file_names)}")
            if file_names:
                print(f"   文件列表:")
                for fn in file_names:
                    print(f"     - {fn}: {page_count_by_file[fn]} 页")
            
            return stats
        except Exception as e:
            print(f"⚠️  获取统计信息失败: {e}")
            return {"total_documents": 0, "error": str(e)}
