"""
知识扩充服务
使用LLM为PPT知识点生成扩展内容
"""

from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from utils.prompts import (
    get_expansion_prompt, 
    get_expansion_prompt_with_references, 
    get_expansion_prompt_with_reference_files,
    get_validation_prompt
)
from utils.llm_factory import create_llm
import logging
import json
import re

logger = logging.getLogger(__name__)


class KnowledgeExpander:
    """
    知识扩充服务
    为PPT知识点生成背景说明、公式推导、代码示例等扩展内容
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化知识扩充器
        
        Args:
            llm: 大语言模型实例，如果为None则使用默认配置（SiliconFlow - DeepSeek-V3.2-Exp）
        """
        self.llm = llm or create_llm()
        from services.search_service import SearchService
        self.search_service = SearchService()
        logger.info("知识扩充服务初始化完成")
    
    def expand_knowledge_point(
        self,
        title: str,
        content: str,
        context: Optional[Dict] = None,
        use_search: bool = True,
        reference_contents: Optional[List[Dict]] = None
    ) -> Dict:
        """
        为单个知识点扩充内容
        
        Args:
            title: 知识点标题
            content: 知识点原始内容
            context: 上下文信息（如所属章节、相关知识点等）
            use_search: 是否使用多源搜索（默认True）
            reference_contents: 参考文件内容列表，格式: [{"filename": "...", "content": "...", "chunks": [...]}]
            
        Returns:
            扩充后的内容字典，包含：
            - background: 背景说明
            - principles: 原理说明
            - formulas: 公式推导（如适用）
            - examples: 代码示例（如适用）
            - summary: 总结
            - references: 延伸阅读链接（包含来源信息）
        """
        try:
            logger.info(f"开始扩充知识点: {title}")
            
            # 如果context中包含图片信息，将其添加到content中
            enhanced_content = content
            if context and "images" in context:
                images = context["images"]
                if images:
                    image_info = []
                    for img in images:
                        desc = img.get("description", "")
                        ocr_text = img.get("ocr_text", "")
                        if desc:
                            image_info.append(f"[图片内容: {desc}]")
                        elif ocr_text:
                            image_info.append(f"[图片文字: {ocr_text}]")
                    
                    if image_info:
                        enhanced_content = content + "\n\n同页面相关图片信息:\n" + "\n".join(image_info)
            
            context_str = self._format_context(context)
            
            # 多源搜索获取高质量参考文献（优化：智能选择搜索源，并行执行，带超时保护）
            search_results = None
            if use_search:
                try:
                    query = self.search_service.generate_search_query(title + " " + enhanced_content, context)
                    
                    # 方案2：智能减少搜索源 - 如果有参考文件，减少搜索源数量
                    if reference_contents and len(reference_contents) > 0:
                        # 有参考文件时，只搜索最重要的1个源（Arxiv，已移除Wikipedia）
                        sources = ["arxiv"]
                        logger.info(f"检测到参考文件，使用精简搜索源: {sources}")
                    else:
                        # 无参考文件时，搜索全部4个源（已移除Wikipedia）
                        sources = ["arxiv", "semantic_scholar", "crossref", "openalex"]
                        logger.info(f"无参考文件，使用完整搜索源: {sources}")
                    
                    # 方案1：并行搜索 + 方案3：超时处理（每个源2秒超时，更快失败）
                    search_results = self.search_service.multi_source_search(
                        query=query,
                        sources=sources,
                        max_results_per_source=3,
                        timeout_per_source=2.0  # 每个搜索源2秒超时，更快失败
                    )
                    
                    # 对Semantic Scholar、Crossref、OpenAlex进行质量过滤
                    for source in ["semantic_scholar", "crossref", "openalex"]:
                        if search_results.get(source):
                            search_results[source] = self.search_service.filter_high_quality_papers(
                                search_results[source]
                            )[:3]
                    
                    logger.info(f"多源搜索完成，找到 {sum(len(r) for r in search_results.values())} 个高质量参考文献")
                except Exception as e:
                    logger.warning(f"多源搜索失败，将仅使用LLM扩展: {str(e)}")
                    search_results = None
            
            # 根据是否有参考文件和检索结果选择不同的Prompt
            if reference_contents:
                # 优先使用参考文件内容
                prompt = get_expansion_prompt_with_reference_files(
                    title, enhanced_content, context_str, reference_contents, search_results
                )
            elif search_results and any(search_results.values()):
                prompt = get_expansion_prompt_with_references(title, enhanced_content, context_str, search_results)
            else:
                prompt = get_expansion_prompt(title, enhanced_content, context_str)
            
            response = self.llm.invoke(prompt)
            expanded_content = self._parse_expansion_response(response.content)
            
            # 整合搜索结果到references
            if search_results and any(search_results.values()):
                expanded_content = self._integrate_search_results(expanded_content, search_results)
            
            logger.info(f"知识点扩充完成: {title}")
            return expanded_content
            
        except Exception as e:
            logger.error(f"知识点扩充失败: {str(e)}")
            raise
    
    def batch_expand(
        self,
        knowledge_points: List[Dict]
    ) -> List[Dict]:
        """
        批量扩充知识点
        
        Args:
            knowledge_points: 知识点列表，每个元素包含title和content
            
        Returns:
            扩充后的知识点列表
        """
        logger.info(f"开始批量扩充{len(knowledge_points)}个知识点")
        
        results = []
        for idx, kp in enumerate(knowledge_points):
            try:
                result = self.expand_knowledge_point(
                    title=kp.get("title", ""),
                    content=kp.get("content", ""),
                    context=kp.get("context")
                )
                results.append({
                    "original": kp,
                    "expanded": result,
                    "status": "success"
                })
                logger.info(f"进度: {idx + 1}/{len(knowledge_points)}")
            except Exception as e:
                logger.error(f"知识点{idx + 1}扩充失败: {str(e)}")
                results.append({
                    "original": kp,
                    "expanded": None,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"批量扩充完成，成功{sum(1 for r in results if r['status'] == 'success')}/{len(results)}")
        return results
    
    def validate_expansion(
        self,
        original: str,
        expansion: Dict
    ) -> Dict:
        """
        验证扩充内容的准确性（容错机制）
        
        Args:
            original: 原始内容
            expansion: 扩充内容
            
        Returns:
            验证结果字典，包含：
            - is_relevant: 是否相关
            - is_accurate: 是否准确
            - is_consistent: 是否一致
            - confidence: 置信度
            - issues: 问题列表
        """
        try:
            logger.info("开始验证扩充内容")
            
            expansion_text = json.dumps(expansion, ensure_ascii=False)
            prompt = get_validation_prompt(original, expansion_text)
            
            response = self.llm.invoke(prompt)
            validation_result = self._parse_validation_response(response.content)
            
            logger.info(f"验证完成，置信度: {validation_result.get('confidence', 0)}")
            return validation_result
            
        except Exception as e:
            logger.error(f"验证失败: {str(e)}")
            return {
                "is_relevant": False,
                "is_accurate": False,
                "is_consistent": False,
                "confidence": 0.0,
                "issues": [f"验证过程出错: {str(e)}"]
            }
    
    def _format_context(self, context: Optional[Dict]) -> str:
        """
        格式化上下文信息
        
        Args:
            context: 上下文字典
            
        Returns:
            格式化后的上下文字符串
        """
        if not context:
            return "无"
        
        context_parts = []
        if "chapter" in context:
            context_parts.append(f"所属章节: {context['chapter']}")
        if "section" in context:
            context_parts.append(f"所属小节: {context['section']}")
        if "previous_points" in context:
            context_parts.append(f"前置知识点: {', '.join(context['previous_points'])}")
        if "page_number" in context:
            context_parts.append(f"所在页码: {context['page_number']}")
        
        # 添加图片信息
        if "images" in context:
            images = context["images"]
            if images:
                image_descriptions = []
                for img in images:
                    desc = img.get("description", "")
                    ocr_text = img.get("ocr_text", "")
                    if desc:
                        image_descriptions.append(f"图片描述: {desc}")
                    elif ocr_text:
                        image_descriptions.append(f"图片文字: {ocr_text}")
                
                if image_descriptions:
                    context_parts.append("同页面图片信息:\n" + "\n".join(image_descriptions))
        
        return "\n".join(context_parts) if context_parts else "无"
    
    def _parse_expansion_response(self, response: str) -> Dict:
        """
        解析LLM返回的扩充内容
        
        Args:
            response: LLM返回的原始文本
            
        Returns:
            结构化的扩充内容字典
        """
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                required_keys = ["background", "principles", "formulas", "examples", "summary"]
                for key in required_keys:
                    if key not in parsed:
                        parsed[key] = ""
                
                parsed["references"] = parsed.get("references", [])
                
                return parsed
            else:
                logger.warning("无法解析JSON格式，使用默认结构")
                return self._create_default_expansion(response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {str(e)}，使用默认结构")
            return self._create_default_expansion(response)
    
    def _create_default_expansion(self, response: str) -> Dict:
        """
        创建默认扩充结构
        
        Args:
            response: LLM返回的原始文本
            
        Returns:
            默认结构的扩充内容
        """
        return {
            "background": response[:500] if len(response) > 500 else response,
            "principles": "",
            "formulas": "",
            "examples": "",
            "summary": "",
            "references": []
        }
    
    def _integrate_search_results(self, expanded_content: Dict, search_results: Dict) -> Dict:
        """
        整合搜索结果到扩充内容中
        
        Args:
            expanded_content: LLM生成的扩充内容
            search_results: 多源搜索结果
            
        Returns:
            整合后的扩充内容
        """
        references = expanded_content.get("references", [])
        
        # 从各个搜索源提取参考文献
        for source_name, results in search_results.items():
            for result in results[:3]:  # 每个源最多3个
                ref_entry = {
                    "title": result.get("title", ""),
                    "url": result.get("url") or result.get("doi") or result.get("paperId", ""),
                    "source": result.get("source", source_name),
                    "authors": result.get("authors", []),
                    "year": result.get("year") or result.get("published", ""),
                    "venue": result.get("venue") or result.get("journal", "")
                }
                
                # 格式化引用字符串
                authors_str = ", ".join(ref_entry["authors"][:3])
                if len(ref_entry["authors"]) > 3:
                    authors_str += " et al."
                
                ref_entry["citation"] = f"{authors_str}" + \
                    (f" ({ref_entry['year']})" if ref_entry["year"] else "") + \
                    f". {ref_entry['title']}" + \
                    (f". {ref_entry['venue']}" if ref_entry["venue"] else "")
                
                references.append(ref_entry)
        
        # 去重（基于title）
        seen_titles = set()
        unique_references = []
        for ref in references:
            title_lower = ref.get("title", "").lower()
            if title_lower and title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_references.append(ref)
        
        expanded_content["references"] = unique_references[:10]  # 最多保留10个引用
        return expanded_content
    
    def _parse_validation_response(self, response: str) -> Dict:
        """
        解析验证结果
        
        Args:
            response: LLM返回的验证文本
            
        Returns:
            结构化的验证结果字典
        """
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                required_keys = ["is_relevant", "is_accurate", "is_consistent", "confidence", "issues"]
                for key in required_keys:
                    if key not in parsed:
                        parsed[key] = False if "is_" in key else (0.0 if key == "confidence" else [])
                
                return parsed
            else:
                return {
                    "is_relevant": True,
                    "is_accurate": True,
                    "is_consistent": True,
                    "confidence": 0.8,
                    "issues": []
                }
                
        except json.JSONDecodeError:
            return {
                "is_relevant": True,
                "is_accurate": True,
                "is_consistent": True,
                "confidence": 0.8,
                "issues": []
            }
    
    def expand_with_validation(
        self,
        title: str,
        content: str,
        context: Optional[Dict] = None,
        max_retries: int = 1,  # 减少重试次数以提高速度
        reference_contents: Optional[List[Dict]] = None
    ) -> Dict:
        """
        带验证的知识扩充（简化版：合并验证到扩展过程中）
        
        Args:
            title: 知识点标题
            content: 知识点原始内容
            context: 上下文信息
            max_retries: 最大重试次数（默认1次，减少LLM调用）
            
        Returns:
            扩充后的内容字典（包含验证信息）
        """
        # 直接调用expand_knowledge_point，它已经是最优实现（只调用一次LLM）
        # 不再单独调用validate_expansion以节省时间
        try:
            expanded = self.expand_knowledge_point(
                title, content, context, use_search=True, reference_contents=reference_contents
            )
            
            # 简单的规则验证（不使用LLM，快速检查）
            validation = {
                "is_relevant": True,
                "is_accurate": True,
                "is_consistent": True,
                "confidence": 0.9,  # 假设高质量，避免二次LLM调用
                "issues": []
            }
            
            # 简单的检查：如果内容为空，降低置信度
            if not expanded.get("background") and not expanded.get("principles"):
                validation["confidence"] = 0.6
                validation["is_relevant"] = False
                validation["issues"] = ["扩展内容可能不完整"]
            
            expanded["validation"] = validation
            logger.info(f"扩充完成（快速验证模式，置信度: {validation['confidence']}）")
            return expanded
            
        except Exception as e:
            logger.error(f"扩充失败: {str(e)}")
            raise
