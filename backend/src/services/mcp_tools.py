"""
MCP (Model Context Protocol) 工具集成
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
import xml.etree.ElementTree as ET
import re
from urllib.parse import quote

# 尝试导入 LLM 配置
try:
    from src.config import ConfigManager
    from langchain_openai import ChatOpenAI
    _llm_available = True
except ImportError:
    _llm_available = False
    print("⚠️  LLM 配置不可用，翻译功能将被禁用")


def _translate_to_english(text: str) -> str:
    """将中文翻译成英文"""
    if not _llm_available:
        return text
    
    if not re.search(r'[\u4e00-\u9fff]', text):
        return text  
    
    try:
        config_manager = ConfigManager()
        llm_config = config_manager.get_llm_config()
        
        llm = ChatOpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            model=llm_config.model,
            temperature=0.3,
            max_retries=2
        )
        
        prompt = f"""请将以下中文查询翻译成英文，用于学术论文搜索。只返回英文翻译，不要添加任何解释。

中文查询：{text}

英文翻译："""
        
        response = llm.invoke(prompt)
        translated = response.content.strip()
        
        # 清理翻译结果
        translated = re.sub(r'^["\']|["\']$', '', translated)
        translated = translated.split('\n')[0].strip()
        
        if translated and len(translated) > 0:
            print(f"      🌐 翻译: '{text}' -> '{translated}'")
            return translated
        else:
            print(f"      ⚠️  翻译失败，使用原始查询")
            return text
    except Exception as e:
        print(f"      ⚠️  翻译失败: {e}，使用原始查询")
        return text


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    content: str
    url: str
    source: str
    metadata: Dict[str, Any]


class WikipediaMCP:
    """维基百科 MCP 工具"""
    
    def __init__(self, language: str = "zh"):
        self.language = language
        self.api_url = f"https://{language}.wikipedia.org/w/api.php"
        self.headers = {
            "User-Agent": "PPTAS-Bot/1.0 (https://github.com/user/pptas)"
        }
    
    def search(self, query: str, limit: int = 3) -> List[Document]:
        """搜索维基百科"""
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": limit
        }
        
        try:
            response = requests.get(self.api_url, params=params, timeout=10, headers=self.headers)
            response.raise_for_status()  # 检查 HTTP 状态
            
            # 检查响应是否为空
            if not response.text:
                print(f"Wikipedia search error: Empty response for query '{query}'")
                return []
            
            data = response.json()
            
            documents = []
            for item in data.get("query", {}).get("search", []):
                content = self._get_page_content(item["title"])
                if content:
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": "Wikipedia",
                            "title": item["title"],
                            "url": f"https://{self.language}.wikipedia.org/wiki/{item['title'].replace(' ', '_')}"
                        }
                    ))
            
            return documents
        except Exception as e:
            print(f"Wikipedia search error: {type(e).__name__}: {e}")
            return []
    
    def _get_page_content(self, title: str) -> Optional[str]:
        """获取页面内容摘要"""
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "titles": title
        }
        
        try:
            response = requests.get(self.api_url, params=params, timeout=10, headers=self.headers)
            response.raise_for_status()
            
            if not response.text:
                return None
            
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            
            for page in pages.values():
                content = page.get("extract", "")
                if content:
                    return content[:1000]  
            
            return None
        except Exception as e:
            print(f"Get Wikipedia page content error: {type(e).__name__}: {e}")
            return None


class ArxivMCP:
    """Arxiv MCP 工具"""
    
    def __init__(self):
        self.api_url = "http://export.arxiv.org/api/query"
    
    def search(self, query: str, max_results: int = 3) -> List[Document]:
        """搜索 Arxiv 论文"""
        # 如果查询是中文，先翻译成英文
        original_query = query.strip()
        query_clean = _translate_to_english(original_query)

        query_clean = query_clean.strip()
        # 如果查询包含多个词，使用OR连接
        if " " in query_clean:
            words = query_clean.split()
            search_query = " OR ".join([f"all:{word}" for word in words[:3]])  
        else:
            search_query = f"all:{query_clean}"
        
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        print(f"      Arxiv API URL: {self.api_url}")
        print(f"      Arxiv 搜索查询: {search_query}")
        
        try:
            response = requests.get(self.api_url, params=params, timeout=15)
            print(f"      Arxiv HTTP状态: {response.status_code}")
            
            if response.status_code != 200:
                print(f"      ⚠️  Arxiv API返回错误状态码: {response.status_code}")
                print(f"      响应内容: {response.text[:200]}")
                return []
            
            if not response.content:
                print(f"      ⚠️  Arxiv API返回空响应")
                return []
            
            root = ET.fromstring(response.content)
            
            documents = []
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
            print(f"      Arxiv 找到 {len(entries)} 个条目")
            
            if len(entries) == 0:
                print(f"      ⚠️  Arxiv 没有找到匹配的论文")
                print(f"      可能原因:")
                print(f"      1. 查询词不匹配（Arxiv主要收录英文论文）")
                print(f"      2. 查询词太具体或太新")
                print(f"      3. 网络问题")
            
            for entry in entries:
                try:
                    title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
                    summary_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
                    id_elem = entry.find("{http://www.w3.org/2005/Atom}id")
                    
                    if title_elem is None or summary_elem is None or id_elem is None:
                        continue
                    
                    title = title_elem.text.strip() if title_elem.text else ""
                    summary = summary_elem.text.strip() if summary_elem.text else ""
                    link = id_elem.text.strip() if id_elem.text else ""
                    
                    if not title:
                        continue
                    
                    authors = []
                    for author in entry.findall("{http://www.w3.org/2005/Atom}author"):
                        name_elem = author.find("{http://www.w3.org/2005/Atom}name")
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text)
                    
                    documents.append(Document(
                        page_content=f"{title}\n\n{summary[:800]}",
                        metadata={
                            "source": "Arxiv",
                            "title": title,
                            "authors": ", ".join(authors) if authors else "",
                            "url": link
                        }
                    ))
                except Exception as e:
                    print(f"      ⚠️  解析Arxiv条目失败: {e}")
                    continue
            
            print(f"      ✅ Arxiv 成功解析 {len(documents)} 个文档")
            return documents
        except requests.exceptions.RequestException as e:
            print(f"      ❌ Arxiv 网络请求失败: {type(e).__name__}: {e}")
            return []
        except ET.ParseError as e:
            print(f"      ❌ Arxiv XML解析失败: {e}")
            print(f"      响应内容前500字符: {response.content[:500] if 'response' in locals() else 'N/A'}")
            return []
        except Exception as e:
            print(f"      ❌ Arxiv 搜索失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return []


class GoogleScholarMCP:
    """Google Scholar MCP 工具"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def search(self, query: str, num_results: int = 3) -> List[Document]:
        """搜索 Google Scholar
        注意：这是简化版，生产环境建议使用 SerpAPI 等服务
        """
        url = f"https://scholar.google.com/scholar?q={query}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            documents = []
            results = soup.find_all('div', class_='gs_ri')[:num_results]
            
            for result in results:
                title_elem = result.find('h3', class_='gs_rt')
                title = title_elem.get_text() if title_elem else "Unknown"
                
                snippet_elem = result.find('div', class_='gs_rs')
                snippet = snippet_elem.get_text() if snippet_elem else ""
                
                link_elem = title_elem.find('a') if title_elem else None
                link = link_elem['href'] if link_elem else ""
                
                documents.append(Document(
                    page_content=f"{title}\n\n{snippet[:500]}",
                    metadata={
                        "source": "Google Scholar",
                        "title": title,
                        "url": link
                    }
                ))
            
            return documents
        except Exception as e:
            print(f"Google Scholar search error: {e}")
            return []


class BaiduBaikeMCP:
    """百度百科 MCP 工具"""
    
    def __init__(self):
        self.base_url = "https://baike.baidu.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def search(self, query: str, fallback: bool = True) -> List[Document]:
        """搜索百度百科"""
        # 生成多个搜索关键词变体
        search_variants = self._generate_search_variants(query)
        
        print(f"      Baike 查询: '{query}'")
        print(f"      Baike 搜索变体: {search_variants}")
        
        all_documents = []
        seen_urls = set()
        
        for variant in search_variants:
            if len(all_documents) >= 3: 
                break
            
            variant_clean = variant.strip()
            if not variant_clean:
                continue
            
            # URL编码
            encoded_query = quote(variant_clean.encode('utf-8'))
            search_url = f"{self.base_url}/search?word={encoded_query}"
            
            try:
                response = requests.get(search_url, headers=self.headers, timeout=10)
                print(f"      🔍 搜索变体 '{variant_clean}': HTTP {response.status_code}")
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 方法1: 尝试直接访问词条页面
                direct_url = f"{self.base_url}/item/{encoded_query}"
                try:
                    direct_response = requests.get(direct_url, headers=self.headers, timeout=10)
                    if direct_response.status_code == 200:
                        direct_soup = BeautifulSoup(direct_response.text, 'html.parser')
                        summary = direct_soup.find('div', class_='lemma-summary')
                        if summary:
                            content = summary.get_text().strip()[:1000]
                            title_elem = direct_soup.find('h1', class_='lemmaWgt-lemmaTitle-title')
                            title = title_elem.get_text().strip() if title_elem else variant_clean
                            
                            doc_url = direct_url
                            if doc_url not in seen_urls:
                                seen_urls.add(doc_url)
                                all_documents.append(Document(
                                    page_content=content,
                                    metadata={
                                        "source": "Baidu Baike",
                                        "title": title,
                                        "url": doc_url
                                    }
                                ))
                                print(f"      ✅ 直接访问成功: {title}")
                                continue
                except Exception:
                    pass
                
                # 方法2: 从搜索结果页面获取多个结果
                links = soup.find_all('a', href=re.compile(r'/item/'))
                if links:
                    print(f"      找到 {len(links)} 个词条链接")
                    for link_elem in links[:5]:  
                        if len(all_documents) >= 3:
                            break
                        
                        href = link_elem.get('href', '')
                        if not href:
                            continue
                        
                        if href.startswith('//'):
                            full_url = 'https:' + href
                        elif href.startswith('/'):
                            full_url = self.base_url + href
                        else:
                            full_url = href
                        
                        if full_url in seen_urls:
                            continue
                        
                        try:
                            content_response = requests.get(full_url, headers=self.headers, timeout=10)
                            if content_response.status_code == 200:
                                content_soup = BeautifulSoup(content_response.text, 'html.parser')
                                summary = content_soup.find('div', class_='lemma-summary')
                                if summary:
                                    content = summary.get_text().strip()[:1000]
                                    title_elem = content_soup.find('h1', class_='lemmaWgt-lemmaTitle-title')
                                    title = title_elem.get_text().strip() if title_elem else link_elem.get_text().strip()
                                    
                                    if title and content:
                                        seen_urls.add(full_url)
                                        all_documents.append(Document(
                                            page_content=content,
                                            metadata={
                                                "source": "Baidu Baike",
                                                "title": title,
                                                "url": full_url
                                            }
                                        ))
                                        print(f"      ✅ 获取词条: {title}")
                        except Exception:
                            continue
                
                # 方法3: 如果还没找到，尝试从搜索结果页面提取文本摘要
                if len(all_documents) == 0:
                    result_items = soup.find_all(['div', 'dd'], class_=re.compile(r'search|result|item'))
                    for item in result_items[:3]:
                        text = item.get_text().strip()
                        if text and len(text) > 50:  
                            title_elem = item.find(['a', 'h3', 'h4'])
                            title = title_elem.get_text().strip() if title_elem else query
                            
                            link_elem = item.find('a', href=re.compile(r'/item/'))
                            if link_elem:
                                href = link_elem.get('href', '')
                                if href.startswith('//'):
                                    full_url = 'https:' + href
                                elif href.startswith('/'):
                                    full_url = self.base_url + href
                                else:
                                    full_url = href
                            else:
                                full_url = f"{self.base_url}/search?word={encoded_query}"
                            
                            if full_url not in seen_urls:
                                seen_urls.add(full_url)
                                all_documents.append(Document(
                                    page_content=text[:1000],
                                    metadata={
                                        "source": "Baidu Baike",
                                        "title": title,
                                        "url": full_url
                                    }
                                ))
                                print(f"      ✅ 从搜索结果提取: {title}")
                                break
                
            except requests.exceptions.RequestException:
                continue
            except Exception:
                continue
        
        # 保底使用通用词条
        if len(all_documents) == 0 and fallback:
            print(f"      ⚠️  未找到直接匹配，尝试保底搜索...")
            core_concepts = self._extract_core_concepts(query)
            for concept in core_concepts[:2]: 
                if len(all_documents) > 0:
                    break
                try:
                    encoded = quote(concept.encode('utf-8'))
                    fallback_url = f"{self.base_url}/item/{encoded}"
                    response = requests.get(fallback_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        summary = soup.find('div', class_='lemma-summary')
                        if summary:
                            content = summary.get_text().strip()[:1000]
                            title_elem = soup.find('h1', class_='lemmaWgt-lemmaTitle-title')
                            title = title_elem.get_text().strip() if title_elem else concept
                            
                            all_documents.append(Document(
                                page_content=content,
                                metadata={
                                    "source": "Baidu Baike",
                                    "title": title,
                                    "url": fallback_url
                                }
                            ))
                            print(f"      ✅ 保底搜索成功: {title}")
                except Exception:
                    continue
        
        print(f"      ✅ Baike 总共找到 {len(all_documents)} 条结果")
        return all_documents[:3]  # 最多返回3个
    
    def _extract_core_concepts(self, query: str) -> List[str]:
        """提取核心概念（用于保底搜索）"""
        concepts = []
        
        # 移除常见修饰词
        cleaned = re.sub(r'(在|的|中|和|与|及|应用|方法|技术|系统|模型|攻击|安全|隐私)', ' ', query)
        words = [w for w in cleaned.split() if len(w) >= 2]
        
        # 优先选择较长的词
        words.sort(key=len, reverse=True)
        concepts.extend(words[:3])
        
        # 如果查询本身是单个词，也加入
        if len(query.split()) == 1 and query not in concepts:
            concepts.insert(0, query)
        
        return concepts[:3]  
    
    def _generate_search_variants(self, query: str) -> List[str]:
        """生成搜索关键词变体"""
        variants = []
        
        # 1. 原始查询
        variants.append(query.strip())
        
        # 2. 移除括号内容
        no_brackets = re.sub(r'[（(].*?[）)]', '', query).strip()
        if no_brackets and no_brackets != query:
            variants.append(no_brackets)
        
        # 3. 提取核心词（移除"的"、"在"、"中"等助词）
        core_words = re.sub(r'[的在中的和与及]', ' ', query)
        core_words = ' '.join([w for w in core_words.split() if len(w) > 1])
        if core_words and core_words != query:
            variants.append(core_words)
        
        # 4. 只取第一个词
        first_word = query.split()[0] if query.split() else query
        if first_word and first_word != query and len(first_word) >= 2:
            variants.append(first_word)
        
        # 5. 提取关键词
        keywords = re.sub(r'(在|的|中|和|与|及|应用|方法|技术|系统|模型)', ' ', query)
        keywords = ' '.join([w for w in keywords.split() if len(w) > 1])
        if keywords and keywords != query:
            variants.append(keywords)
        
        # 去重并保持顺序
        seen = set()
        unique_variants = []
        for v in variants:
            if v and v not in seen:
                seen.add(v)
                unique_variants.append(v)
        
        return unique_variants[:5]  


class MCPRouter:
    """MCP 工具路由器"""
    
    def __init__(self):
        self.tools = {
            "wikipedia": WikipediaMCP(),
            "arxiv": ArxivMCP(),
            "scholar": GoogleScholarMCP(),
            "baike": BaiduBaikeMCP()
        }
        # 启用所有源
        self.enabled_sources = ["arxiv", "wikipedia", "baike"]  
    
    def search(self, query: str, preferred_sources: List[str] = None) -> List[Document]:
        """智能搜索
        
        Args:
            query: 搜索查询
            preferred_sources: 优先使用的源，如 ["arxiv", "wikipedia"]
        """
        all_documents = []
        
        # 使用指定优先源
        if preferred_sources:
            print(f"🔍 MCPRouter: 使用指定源 {preferred_sources} 搜索 '{query}'")
            for source in preferred_sources:
                if source not in self.tools:
                    print(f"   ⚠️  源 '{source}' 不存在，跳过")
                    continue
                
                try:
                    print(f"   🔍 正在搜索 {source}...")
                    if source == "arxiv":
                        docs = self.tools[source].search(query, max_results=3)
                    elif source == "baike":
                        # 百度作为保底
                        docs = self.tools[source].search(query, fallback=True)
                    elif source == "wikipedia":
                        docs = self.tools[source].search(query, limit=3)
                    else:
                        docs = self.tools[source].search(query)
                    
                    print(f"   ✅ {source} 返回 {len(docs)} 条结果")
                    all_documents.extend(docs)
                except Exception as e:
                    print(f"   ❌ {source} 搜索失败: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        else:
            # 优先使用 Arxiv
            print(f"🔍 MCPRouter: 自动选择源搜索 '{query}'")
            try:
                docs = self.tools["arxiv"].search(query, max_results=3)
                all_documents.extend(docs)
                print(f"   ✅ arxiv 返回 {len(docs)} 条结果")
            except Exception as e:
                print(f"   ❌ Arxiv 搜索失败: {e}")
        
        if not all_documents:
            print(f"   ⚠️  所有源都没有找到结果")
        
        # 去重
        seen_urls = set()
        unique_docs = []
        for doc in all_documents:
            url = doc.metadata.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_docs.append(doc)
            elif not url:
                unique_docs.append(doc)
        
        return unique_docs[:5] 
    
    def _is_academic_query(self, query: str) -> bool:
        """判断是否为学术查询"""
        academic_keywords = [
            "algorithm", "model", "neural", "learning", "theory",
            "算法", "模型", "神经", "学习", "理论", "公式", "证明"
        ]
        return any(keyword in query.lower() for keyword in academic_keywords)
