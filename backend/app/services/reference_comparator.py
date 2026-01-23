"""
参考文档对比服务
检测主文档与参考文档的相似度/引用关系
"""
import json
import logging
from typing import List, Dict, Any, Optional

from .llm_client import llm_client
from .redis_client import redis_client

logger = logging.getLogger(__name__)

# 对比 Prompt 模板
COMPARISON_PROMPT = """主文档段落：
{main_text}

参考文档段落：
{reference_text}

请判断：
1. 是否存在内容相似性（0-100%）
2. 相似类型：直接引用/改写/思想借鉴/无关
3. 如果是引用，是否需要标注来源

请以 JSON 格式返回：
{{
    "similarity_score": 85,
    "similarity_type": "改写",
    "needs_citation": true,
    "reason": "两段文字表达的核心观点相同，但措辞不同",
    "main_key_points": ["关键点1", "关键点2"],
    "reference_key_points": ["关键点1", "关键点2"]
}}
"""


class ReferenceComparator:
    """参考文档对比服务"""
    
    def __init__(self):
        self.llm_client = llm_client
        self.redis_client = redis_client
    
    async def compare_documents(
        self,
        main_doc_id: str,
        ref_doc_ids: List[str],
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        对比主文档与参考文档
        
        Args:
            main_doc_id: 主文档ID
            ref_doc_ids: 参考文档ID列表
            similarity_threshold: 相似度阈值（0-1）
        
        Returns:
            对比结果，包含相似段落列表
        """
        # 1. 获取主文档内容
        main_doc = self.redis_client.get_document_metadata(main_doc_id)
        if not main_doc:
            raise ValueError(f"主文档 {main_doc_id} 不存在")
        
        main_sections = main_doc.get('sections', [])
        if not main_sections:
            raise ValueError(f"主文档 {main_doc_id} 没有章节内容")
        
        # 2. 获取所有参考文档内容
        ref_docs = []
        for ref_id in ref_doc_ids:
            ref_doc = self.redis_client.get_document_metadata(ref_id)
            if ref_doc:
                ref_docs.append({
                    'document_id': ref_id,
                    'filename': ref_doc.get('filename', 'unknown'),
                    'sections': ref_doc.get('sections', [])
                })
        
        if not ref_docs:
            raise ValueError("没有找到有效的参考文档")
        
        logger.info(f"开始对比: 主文档 {main_doc_id} ({len(main_sections)} 章节) vs {len(ref_docs)} 个参考文档")
        
        # 3. 段落级对比
        similarities = []
        total_comparisons = 0
        
        for main_idx, main_section in enumerate(main_sections):
            main_text = main_section.get('content', '')
            if not main_text or len(main_text.strip()) < 50:  # 跳过太短的段落
                continue
            
            for ref_doc in ref_docs:
                for ref_idx, ref_section in enumerate(ref_doc['sections']):
                    ref_text = ref_section.get('content', '')
                    if not ref_text or len(ref_text.strip()) < 50:
                        continue
                    
                    total_comparisons += 1
                    
                    # 使用 LLM 判断相似度
                    try:
                        comparison_result = await self._compare_paragraphs(
                            main_text, ref_text
                        )
                        
                        if comparison_result:
                            similarity_score = comparison_result.get('similarity_score', 0) / 100.0
                            
                            if similarity_score >= similarity_threshold:
                                similarities.append({
                                    'main_section': {
                                        'title': main_section.get('title', ''),
                                        'content': main_text[:500],  # 截取前500字符
                                        'section_index': main_idx,
                                        'full_content_length': len(main_text)
                                    },
                                    'reference_section': {
                                        'document_id': ref_doc['document_id'],
                                        'filename': ref_doc['filename'],
                                        'title': ref_section.get('title', ''),
                                        'content': ref_text[:500],
                                        'section_index': ref_idx,
                                        'full_content_length': len(ref_text)
                                    },
                                    'similarity_score': comparison_result.get('similarity_score', 0),
                                    'similarity_type': comparison_result.get('similarity_type', '未知'),
                                    'needs_citation': comparison_result.get('needs_citation', False),
                                    'reason': comparison_result.get('reason', ''),
                                    'key_points': {
                                        'main': comparison_result.get('main_key_points', []),
                                        'reference': comparison_result.get('reference_key_points', [])
                                    }
                                })
                    except Exception as e:
                        logger.warning(f"段落对比失败 (主文档章节{main_idx} vs 参考文档{ref_doc['document_id']}章节{ref_idx}): {str(e)}")
                        continue
        
        logger.info(f"对比完成: 共 {total_comparisons} 次比较，发现 {len(similarities)} 个相似段落")
        
        # 4. 统计信息
        stats = {
            'total_main_sections': len(main_sections),
            'total_reference_docs': len(ref_docs),
            'total_comparisons': total_comparisons,
            'similar_sections_found': len(similarities),
            'similarity_types': {},
            'citation_needed_count': sum(1 for s in similarities if s.get('needs_citation', False))
        }
        
        for sim in similarities:
            sim_type = sim['similarity_type']
            stats['similarity_types'][sim_type] = stats['similarity_types'].get(sim_type, 0) + 1
        
        return {
            'main_document_id': main_doc_id,
            'reference_document_ids': ref_doc_ids,
            'similarities': similarities,
            'statistics': stats
        }
    
    async def _compare_paragraphs(
        self,
        main_text: str,
        ref_text: str
    ) -> Optional[Dict[str, Any]]:
        """对比两个段落"""
        prompt = COMPARISON_PROMPT.format(
            main_text=main_text[:2000],  # 限制长度
            reference_text=ref_text[:2000]
        )
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的文本相似度分析专家。请准确判断两段文本的相似性，并给出详细的判断依据。必须返回有效的 JSON 格式。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self.llm_client.chat(messages, temperature=0.2, max_tokens=2048)
            
            # 解析 JSON 响应
            response = response.strip()
            
            # 移除可能的 markdown 代码块
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # 尝试提取 JSON（可能包含在文本中）
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                response = response[start_idx:end_idx+1]
            
            result = json.loads(response)
            
            # 验证必需字段
            if 'similarity_score' not in result:
                logger.warning("LLM 返回结果缺少 similarity_score 字段")
                return None
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析对比结果 JSON 失败: {e}, 原始响应: {response[:200]}")
            return None
        except Exception as e:
            logger.error(f"段落对比失败: {str(e)}")
            return None


# 全局实例
reference_comparator = ReferenceComparator()

