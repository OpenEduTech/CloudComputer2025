"""
搜索服务
整合Arxiv、Semantic Scholar、Crossref、OpenAlex等外部知识源（Wikipedia已禁用）
"""

from typing import Dict, List, Optional
# import wikipedia  # Wikipedia已禁用
import arxiv
import requests
import logging
import json
import xml.etree.ElementTree as ET
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
import time
import re
from utils.llm_factory import create_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class SearchService:
    """
    搜索服务
    整合多个外部知识源，为PPT内容提供权威参考资料
    """
    
    def __init__(self, wikipedia_lang: str = "zh"):
        """
        初始化搜索服务
        
        Args:
            wikipedia_lang: Wikipedia语言设置（已禁用，保留参数以兼容）
        """
        # wikipedia.set_lang(wikipedia_lang)  # Wikipedia已禁用
        # 初始化LLM用于生成搜索关键词
        self.llm = create_llm(temperature=0.3)  # 使用较低温度确保关键词提取的准确性
        logger.info(f"搜索服务初始化完成（Wikipedia已禁用）")
    
    # Wikipedia搜索已禁用（太慢且容易失败）
    # def search_wikipedia(self, query: str, max_results: int = 3) -> List[Dict]:
    #     """
    #     在Wikipedia中搜索相关内容（优化：处理查询词格式，避免网络错误）
    #     
    #     Args:
    #         query: 搜索查询词
    #         max_results: 最大返回结果数
    #         
    #     Returns:
    #         搜索结果列表，每个结果包含：
    #         - title: 标题
    #         - summary: 摘要
    #         - url: 链接
    #         - relevance: 相关度
    #     """
    #     try:
    #         logger.info(f"在Wikipedia搜索: {query[:50]}...")
    #         
    #         # 优化：提取中文关键词（Wikipedia中文版主要支持中文）
    #         # 提取中文字符和常见英文单词
    #         chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', query)
    #         english_words = re.findall(r'\b[a-zA-Z]{3,}\b', query)
    #         
    #         # 优先使用中文关键词
    #         if chinese_words:
    #             wiki_query = " ".join(chinese_words[:3])  # 最多3个中文词
    #         elif english_words:
    #             wiki_query = " ".join(english_words[:3])  # 最多3个英文词
    #         else:
    #             wiki_query = query[:30]  # 如果都没有，使用前30个字符
    #         
    #         if not wiki_query or len(wiki_query) < 2:
    #             logger.warning("Wikipedia查询词过短，跳过搜索")
    #             return []
    #         
    #         search_results = wikipedia.search(wiki_query, results=max_results)
    #         results = []
    #         
    #         for title in search_results:
    #             try:
    #                 page = wikipedia.page(title, auto_suggest=False)
    #                 
    #                 results.append({
    #                     "title": page.title,
    #                     "summary": page.summary[:500] + "..." if len(page.summary) > 500 else page.summary,
    #                     "url": page.url,
    #                     "relevance": self._calculate_relevance(query, page.title, page.summary)
    #                 })
    #             except wikipedia.exceptions.DisambiguationError as e:
    #                 logger.warning(f"Wikipedia消歧义: {e.options}")
    #                 continue
    #             except wikipedia.exceptions.PageError:
    #                 logger.warning(f"Wikipedia页面不存在: {title}")
    #                 continue
    #         
    #         results.sort(key=lambda x: x["relevance"], reverse=True)
    #         logger.info(f"Wikipedia搜索完成，找到{len(results)}个结果")
    #         return results
    #         
    #     except Exception as e:
    #         logger.error(f"Wikipedia搜索失败: {str(e)}")
    #         return []
    
    def search_arxiv(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        在Arxiv中搜索相关论文（优化：处理查询词格式，避免HTTP 400错误）
        
        Args:
            query: 搜索查询词
            max_results: 最大返回结果数
            
        Returns:
            搜索结果列表，每个结果包含：
            - title: 论文标题
            - authors: 作者列表
            - summary: 摘要
            - url: 链接
            - published: 发表日期
            - relevance: 相关度
        """
        try:
            logger.info(f"在Arxiv搜索: {query[:50]}...")
            
            # 优化：Arxiv查询词需要特殊处理
            # 1. 去除中文字符（Arxiv主要支持英文）
            arxiv_query = re.sub(r'[\u4e00-\u9fa5]', '', query).strip()
            # 2. 如果去除中文后为空，使用原始查询的前50个字符
            if not arxiv_query or len(arxiv_query) < 3:
                arxiv_query = re.sub(r'[^\w\s]', ' ', query)[:50].strip()
            # 3. 限制长度，避免URL过长
            if len(arxiv_query) > 100:
                arxiv_query = arxiv_query[:100]
            
            if not arxiv_query or len(arxiv_query) < 3:
                logger.warning("Arxiv查询词过短，跳过搜索")
                return []
            
            search = arxiv.Search(
                query=arxiv_query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            results = []
            for result in search.results():
                results.append({
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "summary": result.summary[:500] + "..." if len(result.summary) > 500 else result.summary,
                    "url": result.entry_id,
                    "published": result.published.strftime("%Y-%m-%d"),
                    "source": "Arxiv",
                    "relevance": self._calculate_relevance(query, result.title, result.summary)
                })
            
            results.sort(key=lambda x: x["relevance"], reverse=True)
            logger.info(f"Arxiv搜索完成，找到{len(results)}篇论文")
            return results
            
        except Exception as e:
            logger.error(f"Arxiv搜索失败: {str(e)}")
            return []
    
    def search_bing(self, query: str, max_results: int = 3, api_key: str = "") -> List[Dict]:
        """
        使用Bing搜索API（可选，需要API密钥）
        
        Args:
            query: 搜索查询词
            max_results: 最大返回结果数
            api_key: Bing API密钥
            
        Returns:
            搜索结果列表
        """
        if not api_key:
            logger.warning("Bing API密钥未提供，跳过Bing搜索")
            return []
        
        try:
            logger.info(f"在Bing搜索: {query}")
            
            endpoint = "https://api.bing.microsoft.com/v7.0/search"
            headers = {"Ocp-Apim-Subscription-Key": api_key}
            params = {
                "q": query,
                "count": max_results,
                "mkt": "zh-CN"
            }
            
            response = requests.get(endpoint, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("webPages", {}).get("value", []):
                results.append({
                    "title": item.get("name", ""),
                    "summary": item.get("snippet", ""),
                    "url": item.get("url", ""),
                    "relevance": self._calculate_relevance(query, item.get("name", ""), item.get("snippet", ""))
                })
            
            logger.info(f"Bing搜索完成，找到{len(results)}个结果")
            return results
            
        except Exception as e:
            logger.error(f"Bing搜索失败: {str(e)}")
            return []
    
    def _search_with_timeout(self, search_func, source_name: str, query: str, max_results: int, timeout: float = 2.0) -> List[Dict]:
        """
        带超时的搜索包装函数
        
        Args:
            search_func: 搜索函数
            source_name: 搜索源名称（用于日志）
            query: 搜索查询词
            max_results: 最大结果数
            timeout: 超时时间（秒）
            
        Returns:
            搜索结果列表，超时或失败时返回空列表
        """
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(search_func, query, max_results)
                result = future.result(timeout=timeout)
                logger.info(f"{source_name}搜索完成，找到{len(result)}个结果")
                return result
        except FutureTimeoutError:
            logger.warning(f"{source_name}搜索超时（{timeout}秒），跳过")
            return []
        except Exception as e:
            logger.error(f"{source_name}搜索失败: {str(e)}")
            return []
    
    def multi_source_search(
        self,
        query: str,
        sources: List[str] = None,
        max_results_per_source: int = 3,
        timeout_per_source: float = 3.0
    ) -> Dict[str, List[Dict]]:
        """
        多源并行搜索（优化：使用线程池并行执行，带超时保护）
        
        Args:
            query: 搜索查询词
            sources: 搜索源列表（可选：["arxiv", "bing", "semantic_scholar", "crossref", "openalex"]，Wikipedia已禁用）
            max_results_per_source: 每个源的最大结果数
            timeout_per_source: 每个搜索源的超时时间（秒，默认3秒）
            
        Returns:
            各搜索源的结果字典
        """
        if sources is None:
            sources = ["arxiv"]  # Wikipedia已禁用
        
        logger.info(f"开始并行多源搜索: {query[:50]}...，搜索源: {sources}，超时: {timeout_per_source}秒/源")
        start_time = time.time()
        
        # 定义搜索任务映射（Wikipedia已禁用）
        search_tasks = {}
        # if "wikipedia" in sources:
        #     search_tasks["wikipedia"] = (self.search_wikipedia, "Wikipedia")
        if "arxiv" in sources:
            search_tasks["arxiv"] = (self.search_arxiv, "Arxiv")
        if "bing" in sources:
            search_tasks["bing"] = (self.search_bing, "Bing")
        if "semantic_scholar" in sources:
            search_tasks["semantic_scholar"] = (self.search_semantic_scholar, "Semantic Scholar")
        if "crossref" in sources:
            search_tasks["crossref"] = (self.search_crossref, "Crossref")
        if "openalex" in sources:
            search_tasks["openalex"] = (self.search_openalex, "OpenAlex")
        
        # 并行执行所有搜索任务
        results = {}
        with ThreadPoolExecutor(max_workers=len(search_tasks)) as executor:
            # 提交所有任务
            future_to_source = {}
            for source_name, (search_func, display_name) in search_tasks.items():
                future = executor.submit(
                    self._search_with_timeout,
                    search_func,
                    display_name,
                    query,
                    max_results_per_source,
                    timeout_per_source
                )
                future_to_source[future] = source_name
            
            # 收集结果
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    results[source_name] = future.result()
                except Exception as e:
                    logger.error(f"获取{source_name}搜索结果时出错: {str(e)}")
                    results[source_name] = []
        
        elapsed_time = time.time() - start_time
        total_results = sum(len(r) for r in results.values())
        logger.info(f"并行多源搜索完成，耗时{elapsed_time:.2f}秒，共找到{total_results}个结果")
        
        return results
    
    def _calculate_relevance(self, query: str, title: str, summary: str) -> float:
        """
        计算搜索结果的相关度
        
        Args:
            query: 搜索查询词
            title: 结果标题
            summary: 结果摘要
            
        Returns:
            相关度分数（0-1）
        """
        query_lower = query.lower()
        title_lower = title.lower()
        summary_lower = summary.lower()
        
        score = 0.0
        
        query_words = set(query_lower.split())
        
        title_words = set(title_lower.split())
        title_match = len(query_words & title_words) / len(query_words) if query_words else 0
        score += title_match * 0.6
        
        summary_words = set(summary_lower.split())
        summary_match = len(query_words & summary_words) / len(query_words) if query_words else 0
        score += summary_match * 0.4
        
        return min(score, 1.0)
    
    # Wikipedia功能已禁用
    # def get_wikipedia_page(self, title: str) -> Optional[Dict]:
    #     """
    #     获取Wikipedia页面完整内容
    #     
    #     Args:
    #         title: 页面标题
    #         
    #     Returns:
    #         页面内容字典
    #     """
    #     try:
    #         page = wikipedia.page(title, auto_suggest=False)
    #         return {
    #             "title": page.title,
    #             "content": page.content[:2000] + "..." if len(page.content) > 2000 else page.content,
    #             "summary": page.summary,
    #             "url": page.url,
    #             "images": page.images[:5] if page.images else [],
    #             "categories": page.categories[:10] if page.categories else []
    #         }
    #     except Exception as e:
    #         logger.error(f"获取Wikipedia页面失败: {str(e)}")
    #         return None
    
    def get_arxiv_paper(self, paper_id: str) -> Optional[Dict]:
        """
        获取Arxiv论文详细信息
        
        Args:
            paper_id: 论文ID
            
        Returns:
            论文详细信息字典
        """
        try:
            search = arxiv.Search(id_list=[paper_id])
            result = next(search.results(), None)
            
            if result:
                return {
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "summary": result.summary,
                    "published": result.published.strftime("%Y-%m-%d"),
                    "url": result.entry_id,
                    "pdf_url": result.pdf_url,
                    "primary_category": result.primary_category
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取Arxiv论文失败: {str(e)}")
            return None
    
    def generate_search_query(self, content: str, context: Optional[Dict] = None) -> str:
        """
        使用LLM生成优化的搜索查询关键词
        
        Args:
            content: 原始内容
            context: 上下文信息
            
        Returns:
            优化后的搜索查询词（由LLM生成的关键词）
        """
        try:
            # 构建Prompt，让LLM提取关键词
            # 限制内容长度避免token过多
            content_preview = content[:500] if len(content) > 500 else content
            prompt = f"""你是一个专业的学术搜索助手。请从以下内容中提取3-5个最核心的关键词，用于学术文献检索。

要求：
1. 提取最能代表内容核心概念的关键词
2. 优先提取专业术语、技术名词、核心概念
3. 关键词可以是中文或英文
4. 去除停用词（如"的"、"是"、"在"等）
5. 去除数学公式和特殊符号
6. 只输出关键词，用空格分隔，不要其他解释

内容：
{content_preview}

请直接输出关键词，用空格分隔："""

            # 调用LLM生成关键词
            logger.info(f"开始调用LLM生成关键词，原始内容: {content_preview[:100]}...")
            response = self.llm.invoke([HumanMessage(content=prompt)])
            raw_keywords = response.content.strip()
            logger.info(f"LLM原始响应: {raw_keywords}")
            
            # 清理和验证关键词
            # 去除可能的标点符号和多余空格
            keywords = re.sub(r'[^\w\s\u4e00-\u9fa5]', ' ', raw_keywords)
            keywords = ' '.join(keywords.split())  # 规范化空格
            
            # 限制长度（避免URL过长）
            if len(keywords) > 100:
                keywords = keywords[:100]
            
            # 如果LLM返回为空或太短，使用备用方案
            if not keywords or len(keywords) < 3:
                logger.warning(f"LLM生成的关键词为空或太短（原始响应: {raw_keywords}, 清理后: {keywords}），使用备用方案")
                return self._generate_fallback_query(content)
            
            logger.info(f"LLM生成搜索查询成功: 原始内容长度={len(content)}, LLM原始响应={raw_keywords}, 清理后关键词={keywords}, 关键词长度={len(keywords)}")
            return keywords
            
        except Exception as e:
            logger.error(f"LLM生成搜索查询失败: {str(e)}，使用备用方案")
            return self._generate_fallback_query(content)
    
    def _generate_fallback_query(self, content: str) -> str:
        """
        备用方案：使用规则提取关键词（当LLM失败时使用）
        
        Args:
            content: 原始内容
            
        Returns:
            优化后的搜索查询词
        """
        # 1. 去除数学公式、特殊符号、括号内容
        content = re.sub(r'\$[^$]+\$', '', content)
        content = re.sub(r'\$\$[^$]+\$\$', '', content)
        content = re.sub(r'\([^)]*\)', '', content)
        content = re.sub(r'（[^）]*）', '', content)
        content = re.sub(r'[××*×|×]', '', content)
        content = re.sub(r'[:：=]\s*[^，。\n]+', '', content)
        
        # 2. 提取关键词（中文和英文）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,10}', content)
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', content)
        
        # 3. 过滤停用词
        stopwords = {"的", "是", "在", "和", "与", "或", "以及", "一个", "这个", "那个", 
                     "the", "a", "an", "and", "or", "is", "are", "was", "were", "be", "been"}
        
        keywords = []
        for word in chinese_words:
            if word not in stopwords and len(word) >= 2:
                keywords.append(word)
        
        for word in english_words:
            word_lower = word.lower()
            if word_lower not in stopwords and len(word) >= 3:
                keywords.append(word)
        
        # 4. 去重并限制长度
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
                if len(unique_keywords) >= 5:
                    break
        
        # 5. 组合成查询
        if unique_keywords:
            query = " ".join(unique_keywords)
        else:
            query = re.sub(r'[^\w\s\u4e00-\u9fa5]', '', content)[:50]
        
        if len(query) > 100:
            query = query[:100]
        
        logger.info(f"备用方案生成搜索查询: {query}")
        return query
    
    def search_semantic_scholar(self, query: str, limit: int = 10) -> List[Dict]:
        """
        在Semantic Scholar中搜索相关学术论文（优化：限制查询词长度，避免429错误）
        
        Args:
            query: 搜索查询词
            limit: 最大返回结果数
            
        Returns:
            搜索结果列表
        """
        try:
            # 优化：限制查询词长度，避免429错误
            # 提取英文关键词（Semantic Scholar主要支持英文）
            english_words = re.findall(r'\b[a-zA-Z]{3,}\b', query)
            if english_words:
                clean_query = " ".join(english_words[:5])  # 最多5个英文词
            else:
                clean_query = query[:50]  # 如果没有英文，使用前50个字符
            
            if len(clean_query) > 100:
                clean_query = clean_query[:100]
            
            if not clean_query or len(clean_query) < 3:
                logger.warning("Semantic Scholar查询词过短，跳过搜索")
                return []
            
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": clean_query,
                "limit": limit,
                "fields": "paperId,title,authors,year,venue,url,abstract"
            }
            headers = {
                "User-Agent": "ppt-extension-agent/1.0"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            results = []
            for paper in data.get("data", []):
                results.append({
                    "paperId": paper.get("paperId"),
                    "title": paper.get("title"),
                    "authors": [f"{a.get('name', '')}" for a in paper.get("authors", [])],
                    "year": paper.get("year"),
                    "venue": paper.get("venue"),
                    "url": paper.get("url") or f"https://www.semanticscholar.org/paper/{paper.get('paperId')}",
                    "abstract": paper.get("abstract", ""),
                    "source": "Semantic Scholar"
                })
            logger.info(f"Semantic Scholar搜索完成，找到{len(results)}篇论文")
            return results
        except Exception as e:
            logger.error(f"Semantic Scholar搜索失败: {str(e)}")
            return []
    
    def search_crossref(self, query: str, limit: int = 10) -> List[Dict]:
        """
        在Crossref中搜索相关学术论文（优化：限制查询词长度，避免400错误）
        
        Args:
            query: 搜索查询词
            limit: 最大返回结果数
            
        Returns:
            搜索结果列表
        """
        try:
            # 优化：限制查询词长度
            # 提取英文关键词（Crossref主要支持英文）
            english_words = re.findall(r'\b[a-zA-Z]{3,}\b', query)
            if english_words:
                clean_query = " ".join(english_words[:5])  # 最多5个英文词
            else:
                clean_query = query[:50]  # 如果没有英文，使用前50个字符
            
            if len(clean_query) > 100:
                clean_query = clean_query[:100]
            
            if not clean_query or len(clean_query) < 3:
                logger.warning("Crossref查询词过短，跳过搜索")
                return []
            
            url = "https://api.crossref.org/works"
            params = {
                "query": clean_query,
                "rows": limit
            }
            headers = {
                "User-Agent": "ppt-extension-agent/1.0 (mailto:contact@example.com)"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            results = []
            for item in data.get("message", {}).get("items", []):
                authors = []
                for author in item.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    authors.append(f"{given} {family}".strip())
                
                # 处理发布日期
                published = None
                if "published-print" in item:
                    date_parts = item["published-print"]["date-parts"][0]
                    published = "-".join(str(d) for d in date_parts)
                elif "published-online" in item:
                    date_parts = item["published-online"]["date-parts"][0]
                    published = "-".join(str(d) for d in date_parts)
                
                journal = item.get("container-title", [""])[0] if item.get("container-title") else None
                
                results.append({
                    "doi": item.get("DOI"),
                    "title": " ".join(item.get("title", [])),
                    "authors": authors,
                    "published": published,
                    "url": item.get("URL") or (f"https://doi.org/{item.get('DOI')}" if item.get("DOI") else None),
                    "journal": journal,
                    "source": "Crossref"
                })
            logger.info(f"Crossref搜索完成，找到{len(results)}篇论文")
            return results
        except Exception as e:
            logger.error(f"Crossref搜索失败: {str(e)}")
            return []
    
    def search_openalex(self, query: str, limit: int = 10) -> List[Dict]:
        """
        在OpenAlex中搜索相关学术论文（优化：限制查询词长度，避免400错误）
        
        Args:
            query: 搜索查询词
            limit: 最大返回结果数
            
        Returns:
            搜索结果列表
        """
        try:
            # 优化：限制查询词长度
            # 提取英文关键词（OpenAlex主要支持英文）
            english_words = re.findall(r'\b[a-zA-Z]{3,}\b', query)
            if english_words:
                clean_query = " ".join(english_words[:5])  # 最多5个英文词
            else:
                clean_query = query[:50]  # 如果没有英文，使用前50个字符
            
            if len(clean_query) > 100:
                clean_query = clean_query[:100]
            
            if not clean_query or len(clean_query) < 3:
                logger.warning("OpenAlex查询词过短，跳过搜索")
                return []
            
            url = "https://api.openalex.org/works"
            params = {
                "search": clean_query,
                "per-page": limit
            }
            headers = {
                "User-Agent": "ppt-extension-agent/1.0 (mailto:contact@example.com)"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            results = []
            for work in data.get("results", []):
                authors = []
                for author in work.get("authorships", []):
                    author_name = author.get("author", {}).get("display_name", "")
                    if author_name:
                        authors.append(author_name)
                
                results.append({
                    "id": work.get("id"),
                    "title": work.get("title"),
                    "authors": authors,
                    "year": work.get("publication_year"),
                    "url": work.get("primary_location", {}).get("landing_page_url") or work.get("doi"),
                    "abstract": work.get("abstract", ""),
                    "venue": work.get("primary_location", {}).get("source", {}).get("display_name"),
                    "source": "OpenAlex"
                })
            logger.info(f"OpenAlex搜索完成，找到{len(results)}篇论文")
            return results
        except Exception as e:
            logger.error(f"OpenAlex搜索失败: {str(e)}")
            return []
    
    def _is_high_quality_journal(self, venue: Optional[str], journal: Optional[str]) -> bool:
        """
        判断是否为高质量期刊/会议
        
        Args:
            venue: 会议/期刊名称
            journal: 期刊名称
            
        Returns:
            是否为高质量期刊
        """
        if not venue and not journal:
            return False
        
        # 高质量期刊关键词列表（可根据需要扩展）
        high_quality_keywords = [
            "Nature", "Science", "Cell", "Lancet", "NEJM", "IEEE", "ACM",
            "NeurIPS", "ICML", "ICLR", "AAAI", "CVPR", "ECCV", "ICCV",
            "NIPS", "IJCAI", "KDD", "WWW", "SIGIR", "ACL", "EMNLP", "NAACL",
            "Physical Review", "Nature", "Science", "Cell", "JAMA", "BMJ"
        ]
        
        venue_journal = (venue or "").lower() + " " + (journal or "").lower()
        
        for keyword in high_quality_keywords:
            if keyword.lower() in venue_journal:
                return True
        
        return False
    
    def filter_high_quality_papers(self, results: List[Dict], min_score: float = 0.5) -> List[Dict]:
        """
        过滤高质量期刊/会议论文
        
        Args:
            results: 搜索结果列表
            min_score: 最小相关度分数（可选）
            
        Returns:
            过滤后的结果列表
        """
        filtered = []
        
        for result in results:
            # 检查是否有venue或journal字段
            venue = result.get("venue") or result.get("journal")
            
            # 优先保留高质量期刊/会议
            if self._is_high_quality_journal(venue, result.get("journal")):
                result["quality_score"] = 1.0
                filtered.append(result)
            elif venue:  # 有venue但没有匹配到高质量关键词的，也保留
                result["quality_score"] = 0.7
                filtered.append(result)
            # 对于没有venue/journal的（如Arxiv），保留前几个（Wikipedia已禁用）
            elif result.get("source") in ["Arxiv"]:
                result["quality_score"] = 0.6
                filtered.append(result)
        
        # 按质量分数排序
        filtered.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        
        logger.info(f"期刊过滤完成，从{len(results)}个结果中筛选出{len(filtered)}个高质量结果")
        return filtered
    
    def search_all_sources(self, query: str, max_results_per_source: int = 5, filter_quality: bool = True) -> Dict[str, List[Dict]]:
        """
        在所有知识源中搜索，并过滤高质量论文
        
        Args:
            query: 搜索查询词
            max_results_per_source: 每个源的最大结果数
            filter_quality: 是否过滤高质量期刊
            
        Returns:
            整合后的搜索结果字典
        """
        results = {}
        
        # 搜索各个知识源（Wikipedia已禁用）
        # try:
        #     results["wikipedia"] = self.search_wikipedia(query, max_results_per_source)
        # except Exception as e:
        #     logger.warning(f"Wikipedia搜索失败: {str(e)}")
        #     results["wikipedia"] = []
        
        try:
            results["arxiv"] = self.search_arxiv(query, max_results_per_source)
        except Exception as e:
            logger.warning(f"Arxiv搜索失败: {str(e)}")
            results["arxiv"] = []
        
        try:
            semantic_results = self.search_semantic_scholar(query, max_results_per_source * 2)
            if filter_quality:
                semantic_results = self.filter_high_quality_papers(semantic_results)
                semantic_results = semantic_results[:max_results_per_source]
            results["semantic_scholar"] = semantic_results
        except Exception as e:
            logger.warning(f"Semantic Scholar搜索失败: {str(e)}")
            results["semantic_scholar"] = []
        
        try:
            crossref_results = self.search_crossref(query, max_results_per_source * 2)
            if filter_quality:
                crossref_results = self.filter_high_quality_papers(crossref_results)
                crossref_results = crossref_results[:max_results_per_source]
            results["crossref"] = crossref_results
        except Exception as e:
            logger.warning(f"Crossref搜索失败: {str(e)}")
            results["crossref"] = []
        
        try:
            openalex_results = self.search_openalex(query, max_results_per_source * 2)
            if filter_quality:
                openalex_results = self.filter_high_quality_papers(openalex_results)
                openalex_results = openalex_results[:max_results_per_source]
            results["openalex"] = openalex_results
        except Exception as e:
            logger.warning(f"OpenAlex搜索失败: {str(e)}")
            results["openalex"] = []
        
        total_results = sum(len(r) for r in results.values())
        logger.info(f"多源搜索完成，共找到{total_results}个结果（已过滤高质量期刊）")
        
        return results
