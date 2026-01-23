import os
from typing import List, Dict, Any, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.tools import Tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.llms.tongyi import Tongyi
from .models import QueryRewrite, ArticleScore, ContentChunk
from .utils import get_logger
from .content_cleaner import clean_content
from .web_reader import read_webpage

logger = get_logger(__name__)

class SearchAgent:
    def __init__(self, api_key: Optional[str] = None, dashscope_api_key: Optional[str] = None):
        # 配置Tavily API KEY
        tavily_api_key = api_key or "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"
        if tavily_api_key:
            os.environ["TAVILY_API_KEY"] = tavily_api_key
        dashscope_api_key = dashscope_api_key or 'sk-d64798271c204eb28e0744db0a8a480b'
        if dashscope_api_key:
            os.environ["DASHSCOPE_API_KEY"] = dashscope_api_key
        self.llm = Tongyi(
            model_name="qwen-turbo",
            temperature=0.1,
        )
        # 兼容新版和老版TavilySearchResults
        try:
            self.search_tool = TavilySearchResults(max_results=10, tavily_api_key=tavily_api_key)
        except TypeError:
            self.search_tool = TavilySearchResults(max_results=10)

    # 已移除agent相关内容，所有流程直接在run等方法中实现

    def rewrite_query(self, query: str, num_rewrites: int = 3) -> List[str]:
        logger.info(f"改写查询: {query}")
        template = """
        请将以下行业调研主题，改写为{num_rewrites}个更细分、更专业、更有深度的行业调研子问题，覆盖市场、技术、政策、应用、竞争格局等不同角度。
        原始查询: {query}
        请以JSON格式输出，格式为：
        {{
            "queries": [
                "改写查询1",
                "改写查询2",
                "改写查询3"
            ]
        }}
        只返回JSON格式，不要有其他文字。
        """
        prompt = PromptTemplate(
            template=template,
            input_variables=["query", "num_rewrites"],
            partial_variables={"num_rewrites": num_rewrites}
        )
        try:
            parser = PydanticOutputParser(pydantic_object=QueryRewrite)
            chain = prompt | self.llm | parser
            result = chain.invoke({"query": query, "num_rewrites": num_rewrites})
            all_queries = [query] + result.queries
        except Exception as e:
            logger.warning(f"解析器链失败: {e}，使用备用方案")
            response = self.llm.invoke(prompt.format(query=query, num_rewrites=num_rewrites))
            try:
                import json
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    rewritten_queries = data.get("queries", [])
                else:
                    rewritten_queries = re.findall(r'"([^"]+)"', response)
                if not rewritten_queries:
                    rewritten_queries = [
                        f"{query} 最新信息",
                        f"{query} 分析",
                        f"{query} 评价"
                    ][:num_rewrites]
                all_queries = [query] + rewritten_queries
            except Exception as e2:
                logger.error(f"备用解析也失败: {e2}，使用默认改写")
                all_queries = [
                    query,
                    f"{query} 最新信息",
                    f"{query} 分析",
                    f"{query} 评价"
                ][:num_rewrites+1]
        logger.info(f"改写结果: {all_queries}")
        return all_queries

    def search(self, queries: List[str]) -> List[Dict[str, Any]]:
        logger.info(f"执行搜索: {queries}")
        all_results = []
        for query in queries:
            results = self.search_tool.invoke(query)
            all_results.extend(results)
        return all_results

    def score_results(self, query: str, results: List[Dict[str, Any]]) -> List[ArticleScore]:
        logger.info(f"评分筛选结果，共{len(results)}条")
        if not results:
            logger.warning("没有搜索结果可供评分")
            return []
        template = """
        请根据原始查询，对以下搜索结果进行相关性评分(0-10分)。
        原始查询: {query}
        搜索结果:
        {results}
        请以JSON格式输出评分结果，格式为：
        [
            {{
                "title": "文章标题1",
                "url": "文章链接1",
                "snippet": "文章摘要1",
                "score": 8.5
            }},
            {{
                "title": "文章标题2",
                "url": "文章链接2",
                "snippet": "文章摘要2",
                "score": 7.2
            }}
        ]
        只返回JSON格式，不要有其他文字。
        """
        # 限制传递给LLM的结果数，避免输出过长导致截断
        max_results_for_llm = 8
        results_text = "\n\n".join([
            f"标题: {r.get('title', 'N/A')}\n链接: {r.get('url', 'N/A')}\n摘要: {r.get('content', 'N/A')}"
            for r in results[:max_results_for_llm]
        ])
        prompt = PromptTemplate(
            template=template,
            input_variables=["query", "results"]
        )
        try:
            chain = prompt | self.llm
            result = chain.invoke({"query": query, "results": results_text})
            import json
            import re
            try:
                scored_results = json.loads(result)
            except json.JSONDecodeError:
                logger.warning("直接JSON解析失败，尝试提取JSON部分")
                # 非贪婪匹配第一个合法JSON数组
                json_match = re.search(r'\[.*?\]', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        scored_results = json.loads(json_str)
                    except Exception as e2:
                        logger.error(f"正则提取后依然解析失败: {e2}")
                        scored_results = []
                else:
                    logger.error("无法提取JSON，使用默认评分")
                    scored_results = []
                    for r in results[:10]:
                        scored_results.append({
                            "title": r.get("title", "未知标题"),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", "无摘要"),
                            "score": 5.0
                        })
            scored_articles = []
            total_scored = len(scored_results)
            for i, item in enumerate(scored_results):
                print(f"正在评分第 {i+1}/{total_scored} 条内容...", flush=True)
                try:
                    if "title" not in item:
                        item["title"] = "未知标题"
                    if "url" not in item:
                        item["url"] = ""
                    if "snippet" not in item:
                        item["snippet"] = item.get("content", "无摘要")
                    if "score" not in item:
                        item["score"] = 5.0
                    if isinstance(item["score"], str):
                        item["score"] = float(item["score"].replace(",", "."))
                    scored_articles.append(ArticleScore(**item))
                except Exception as e:
                    logger.warning(f"处理评分项失败: {e}, 项: {item}")
            scored_articles.sort(key=lambda x: x.score, reverse=True)
            top_articles = scored_articles[:10]
            logger.info(f"筛选出{len(top_articles)}篇相关文章")
            return top_articles
        except Exception as e:
            logger.error(f"评分过程失败: {e}")
            default_articles = []
            for r in results[:10]:
                default_articles.append(ArticleScore(
                    title=r.get("title", "未知标题"),
                    url=r.get("url", ""),
                    snippet=r.get("content", "无摘要"),
                    score=5.0
                ))
            return default_articles

    def chunk_content(self, article: ArticleScore) -> ContentChunk:
        logger.info(f"分块文章: {article.title}")
        content = read_webpage(article.url)
        content = clean_content(content, llm=self.llm)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        chunks = text_splitter.split_text(content)
        if len(chunks) < 5:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100,
                length_function=len,
            )
            chunks = text_splitter.split_text(content)
        chunks = chunks[:10]
        logger.info(f"文章分块完成，共{len(chunks)}个块")
        return ContentChunk(
            title=article.title,
            url=article.url,
            chunks=chunks
        )

    def run(self, query: str, num_rewrites: int = 3) -> dict:
        import datetime
        import re
        from urllib.parse import urlparse

        logger.info(f"开始调研: {query}")

        skip_domains = ["baidu.com", "dji.com", "wikipedia.org", "baike.baidu.com"]

        def is_skip_url(url: str) -> bool:
            return any(domain in (url or "") for domain in skip_domains)

        domain_map = {
            "finance.sina.com.cn": "新浪财经",
            "sina.com.cn": "新浪",
            "thepaper.cn": "澎湃新闻",
            "people.com.cn": "人民日报",
            "kpmg.com": "毕马威",
            "finebi.com": "FineBI",
            "mofcom.gov.cn": "商务部",
            "ruc.edu.cn": "中国人民大学",
            "zzyuam.com": "低空经济网",
        }

        def extract_source(url: str) -> str:
            try:
                netloc = urlparse(url).netloc.lower()
                if not netloc:
                    return "unknown"
                for k, v in domain_map.items():
                    if k in netloc:
                        return v
                parts = [p for p in netloc.split(".") if p]
                if len(parts) >= 2:
                    if len(parts) >= 3 and parts[-2] in {"com", "edu", "gov", "org", "net"}:
                        return ".".join(parts[-3:])
                    return ".".join(parts[-2:])
                return netloc
            except Exception:
                return "unknown"

        def normalize_date_str(date_str: str) -> str:
            s = (date_str or "").strip()
            s = s.replace("年", "-").replace("月", "-").replace("日", "")
            s = s.replace("/", "-").replace(".", "-")
            return s

        def extract_date_from_text(text: str) -> Optional[str]:
            if not text:
                return None
            # 1) YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD / YYYY年M月D日
            m = re.search(r"(20\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2})", text)
            if m:
                return normalize_date_str(m.group(1))
            # 2) YYYYMMDD
            m = re.search(r"\b(20\d{2})(\d{2})(\d{2})\b", text)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            # 3) YYYY-MM 或 YYYY年M月（仅到月）
            m = re.search(r"(20\d{2}[-年/.]\d{1,2})(?:\b|月)", text)
            if m:
                return normalize_date_str(m.group(1))
            return None

        def extract_date_from_url(url: str) -> Optional[str]:
            if not url:
                return None
            # 常见 URL 形态：.../2026-01-06/... 或 .../20260106/...
            m = re.search(r"(20\d{2}[-_/]\d{1,2}[-_/]\d{1,2})", url)
            if m:
                return normalize_date_str(m.group(1))
            m = re.search(r"\b(20\d{2})(\d{2})(\d{2})\b", url)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            return None

        # 固定爬取数据prompt
        fixed_prompt = (
            f"{query} 行业定义与边界、核心细分领域、产业链结构、商业模式、核心参与者、关键指标体系、"
            f"行业生命周期、竞争格局、PEST 驱动因素、行业机会与风险、未来发展趋势"
        )

        queries = self.rewrite_query(fixed_prompt, num_rewrites)
        raw_results = self.search(queries)  # Tavily: List[Dict]

        # 建立 url -> published_at 映射（优先用搜索结果字段）
        url_to_published: dict[str, str] = {}
        for r in raw_results:
            try:
                url = r.get("url")
                if not url:
                    continue
                published = (
                    r.get("published_date")
                    or r.get("published_at")
                    or r.get("publish_date")
                    or r.get("published")
                    or r.get("date")
                    or r.get("published_time")
                    or r.get("publishedTime")
                    or r.get("publishedAt")
                )
                if isinstance(published, str) and published.strip():
                    url_to_published[url] = normalize_date_str(published)
            except Exception:
                continue

        scored_articles = self.score_results(query, raw_results)

        items: list[dict] = []
        # 找不到发布日期时返回 None（JSON 为 null），避免误填“今天”
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        # 先尝试用评分后的文章做深度抓取/分块
        for article in scored_articles:
            if is_skip_url(article.url):
                logger.info(f"跳过无用网站: {article.url}")
                continue
            try:
                chunked = self.chunk_content(article)
                if not chunked.chunks or any(
                    (isinstance(c, str) and (c.startswith("读取失败") or c.startswith("PDF处理失败")))
                    for c in chunked.chunks
                ):
                    logger.info(f"跳过解析失败网页: {article.url}")
                    continue
                content_summary = chunked.chunks[0] if chunked.chunks else article.snippet

                published_at = (
                    url_to_published.get(article.url)
                    or extract_date_from_text(article.snippet)
                    or extract_date_from_text(content_summary)
                    or extract_date_from_url(article.url)
                    or None
                )

                items.append(
                    {
                        "title": article.title,
                        "content": content_summary,
                        "source": extract_source(article.url),
                        "url": article.url,
                        "published_at": published_at,
                    }
                )
            except Exception as e:
                logger.warning(f"处理文章失败，跳过: {e} | {article.url}")
                continue

        # 若深度处理后为空，则降级：直接输出原始搜索结果（避免 items 为空）
        if not items:
            logger.info("深度抓取结果为空，降级使用原始搜索结果")
            for r in raw_results[:10]:
                url = r.get("url", "")
                if is_skip_url(url):
                    continue
                title = r.get("title", "未知标题")
                snippet = r.get("content") or r.get("snippet") or ""
                published_at = (
                    url_to_published.get(url)
                    or extract_date_from_text(snippet)
                    or extract_date_from_url(url)
                    or None
                )
                items.append(
                    {
                        "title": title,
                        "content": snippet,
                        "source": extract_source(url),
                        "url": url,
                        "published_at": published_at,
                    }
                )

        result = {
            "keyword": query,
            "collected_at": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "items": items,
        }
        logger.info(f"调研完成，共处理{len(items)}篇文章")
        return result