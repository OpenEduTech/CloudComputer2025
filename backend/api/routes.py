"""API路由定义"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import uuid
import sys
import asyncio
import os
import wikipedia
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 加载环境变量
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ==================== LLM客户端 ====================
_llm_client = None

def get_llm_client():
    """获取LLM客户端单例"""
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            _llm_client = AsyncOpenAI(
                api_key=api_key,
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            )
            print("[INFO] LLM客户端已初始化")
    return _llm_client


async def translate_to_english(chinese_text: str) -> str:
    """使用LLM将中文学术术语翻译成英文"""
    client = get_llm_client()
    if not client:
        return chinese_text
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {"role": "system", "content": "你是一个专业的学术翻译助手，擅长将中文学术术语翻译成精准的英文。"},
                    {"role": "user", "content": f"将以下中文学术术语翻译成英文（只输出英文，不要解释）：{chinese_text}"}
                ],
                temperature=0.1,
                max_tokens=50,
                extra_body={"reasoning": {"enabled": True}}
            ),
            timeout=10.0
        )
        
        if response and response.choices:
            translation = response.choices[0].message.content.strip().strip('"\'""\'\'')
            print(f"[SUCCESS] 翻译: {chinese_text} -> {translation}")
            return translation
    except Exception as e:
        print(f"[WARNING] 翻译失败: {chinese_text}, {str(e)}")
    
    return chinese_text


async def generate_brief_summary(concept: str, wiki_definition: str = "") -> str:
    """使用LLM生成一句话简介"""
    client = get_llm_client()
    if not client:
        if wiki_definition:
            return wiki_definition[:100] + "..." if len(wiki_definition) > 100 else wiki_definition
        return f"{concept}是一个重要的跨学科概念。"
    
    try:
        prompt = f"""请为学术概念"{concept}"生成一句完整的简介说明（40-100字），要求：
1. 必须是完整的句子，有明确的主谓宾结构
2. 简洁精准，突出核心特征和应用价值
3. 通俗易懂，适合非专业读者理解
4. 不要使用"是指"、"是一种"等生硬开头
5. 确保句子完整，不要中途截断

{f'参考定义：{wiki_definition[:200]}' if wiki_definition else ''}

直接输出完整的简介句子，不要引号和其他标点。"""

        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {"role": "system", "content": "你是一个学术概念解释专家，擅长用简洁的语言解释复杂概念。务必输出完整句子，不要截断。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                extra_body={"reasoning": {"enabled": False}}
            ),
            timeout=15.0
        )
        
        if response and response.choices:
            summary = response.choices[0].message.content.strip()
            # 清理各种不需要的标记和格式
            summary = summary.strip('"\'""\'\'')
            # 移除可能的草稿标记
            summary = summary.replace("*Draft*:", "").replace("*Draft 2*:", "").replace("*Draft 1*:", "")
            summary = summary.replace("Draft:", "").replace("Draft 2:", "").replace("Draft 1:", "")
            # 移除星号
            summary = summary.replace("*", "").strip()
            # 如果以"："或":"开头，移除它
            summary = summary.lstrip("：:").strip()
            print(f"[SUCCESS] LLM生成简介: {concept} -> {summary[:50]}...")
            return summary
    except asyncio.TimeoutError:
        print(f"[WARNING] LLM生成简介超时: {concept}")
    except Exception as e:
        print(f"[WARNING] LLM生成简介失败: {concept}, {str(e)}")
    
    if wiki_definition:
        return wiki_definition[:100] + "..." if len(wiki_definition) > 100 else wiki_definition
    return f"{concept}是一个重要的跨学科概念。"


async def generate_bridge_edge_reasoning(
    input_concept: str,
    bridge_concept: str,
    overall_principle: str
) -> str:
    """
    为桥接概念的边生成单独的reasoning
    
    Args:
        input_concept: 输入概念（如"熵"）
        bridge_concept: 桥梁概念（如"信息论"）
        overall_principle: 整体连接原理
        
    Returns:
        专门解释这两个概念关系的reasoning
    """
    client = get_llm_client()
    if not client:
        return f"{input_concept}通过{bridge_concept}建立跨学科联系"
    
    try:
        prompt = f"""请用一句话（30-60字）精确解释"{input_concept}"如何与"{bridge_concept}"相关联。

整体背景：{overall_principle}

要求：
1. **必须明确说明{input_concept}在这个关联中的具体作用或特点**
2. 突出{input_concept}与{bridge_concept}之间的独特关系
3. 不要泛泛而谈，要针对{input_concept}这个特定概念
4. 简洁精准，30-60字
5. **必须是完整句子，句号结尾**

直接输出解释，不要引号和额外文字。"""

        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {"role": "system", "content": f"你是跨学科知识专家。请专门解释'{input_concept}'与'{bridge_concept}'的关联，确保每个输入概念的解释都是独特的。输出必须是完整的句子。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000,
                extra_body={"reasoning": {"enabled": False}}
            ),
            timeout=15.0
        )
        
        if response and response.choices:
            reasoning = response.choices[0].message.content.strip().strip('"\'""\'\'')
            print(f"[DEBUG] LLM原始返回 ({input_concept}->{bridge_concept}): '{reasoning}' (长度: {len(reasoning)})")
            if reasoning and len(reasoning) > 10:
                return reasoning
    except asyncio.TimeoutError:
        print(f"[WARNING] 生成边reasoning超时: {input_concept}-{bridge_concept}")
    except Exception as e:
        print(f"[WARNING] 生成边reasoning失败: {input_concept}-{bridge_concept}, 错误类型: {type(e).__name__}, 详情: {str(e)}")
    
    # 使用overall_principle或默认值
    return overall_principle if overall_principle else f"{input_concept}通过{bridge_concept}建立跨学科联系"


# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 是否启用外部验证
ENABLE_EXTERNAL_VERIFICATION = os.getenv("ENABLE_EXTERNAL_VERIFICATION", "false").lower() == "true"
print(f"[INFO] 外部验证状态: {'启用' if ENABLE_EXTERNAL_VERIFICATION else '禁用'}")

try:
    from backend.database.neo4j_client import neo4j_client
    from backend.database.redis_client import redis_client
    from backend.config import settings
    from shared.schemas.concept_node import ConceptNode
    from shared.schemas.concept_edge import ConceptEdge
except ImportError:
    class MockClient:
        async def get(self, key): return None
        async def set(self, key, value, ex=None): pass
        async def query(self, query, params=None): return []
        async def create_concept_node(self, node): pass
        async def create_concept_edge(self, edge): pass
    neo4j_client = MockClient()
    redis_client = MockClient()
    
    class MockSettings:
        AGENT_API_URL = "http://localhost:5000"
        REDIS_CACHE_TTL = 3600
    settings = MockSettings()
    
    ConceptNode = dict
    ConceptEdge = dict

router = APIRouter()


async def get_wikipedia_definition(concept: str, max_length: int = 500) -> Dict[str, Any]:
    """从维基百科获取概念的权威定义"""
    if not ENABLE_EXTERNAL_VERIFICATION:
        return {"definition": "", "exists": False, "url": "", "source": "LLM"}
    
    print(f"[INFO] 正在查询Wikipedia: {concept}")
    loop = asyncio.get_event_loop()
    
    try:
        # 添加10秒超时
        wikipedia.set_lang("zh")
        page = await asyncio.wait_for(
            loop.run_in_executor(None, wikipedia.page, concept),
            timeout=10.0
        )
        summary = page.summary[:max_length] if len(page.summary) > max_length else page.summary
        print(f"[SUCCESS] 中文Wikipedia找到: {concept}")
        return {"definition": summary, "exists": True, "url": page.url, "source": "Wikipedia"}
    except asyncio.TimeoutError:
        print(f"[WARNING] 中文Wikipedia查询超时: {concept}")
    except wikipedia.exceptions.DisambiguationError as e:
        if e.options:
            try:
                page = await asyncio.wait_for(
                    loop.run_in_executor(None, wikipedia.page, e.options[0]),
                    timeout=10.0
                )
                summary = page.summary[:max_length] if len(page.summary) > max_length else page.summary
                return {"definition": summary, "exists": True, "url": page.url, "source": "Wikipedia"}
            except Exception:
                pass
    except wikipedia.exceptions.PageError:
        pass
    except Exception as e:
        print(f"[WARNING] 中文Wikipedia查询失败: {e}")
    
    try:
        wikipedia.set_lang("en")
        page = await asyncio.wait_for(
            loop.run_in_executor(None, wikipedia.page, concept),
            timeout=10.0
        )
        summary = page.summary[:max_length] if len(page.summary) > max_length else page.summary
        print(f"[SUCCESS] 英文Wikipedia找到: {concept}")
        return {"definition": summary, "exists": True, "url": page.url, "source": "Wikipedia"}
    except asyncio.TimeoutError:
        print(f"[WARNING] 英文Wikipedia查询超时: {concept}")
    except wikipedia.exceptions.DisambiguationError as e:
        if e.options:
            try:
                page = await asyncio.wait_for(
                    loop.run_in_executor(None, wikipedia.page, e.options[0]),
                    timeout=10.0
                )
                summary = page.summary[:max_length] if len(page.summary) > max_length else page.summary
                return {"definition": summary, "exists": True, "url": page.url, "source": "Wikipedia"}
            except Exception:
                pass
    except wikipedia.exceptions.PageError:
        pass
    except Exception as e:
        print(f"[WARNING] 英文Wikipedia查询失败: {e}")
    
    print(f"[WARNING] Wikipedia未找到: {concept}")
    return {"definition": "", "exists": False, "url": "", "source": "LLM"}


async def search_arxiv_papers(query: str, max_results: int = 5, max_retries: int = 2) -> tuple[List[Dict[str, Any]], str]:
    """在Arxiv搜索相关论文（带重试机制）"""
    if not ENABLE_EXTERNAL_VERIFICATION:
        return [], "Arxiv查询已禁用"
    
    if any('\u4e00' <= char <= '\u9fff' for char in query):
        print(f"[INFO] 检测到中文查询，正在翻译: {query}")
        query = await translate_to_english(query)
        print(f"[INFO] 翻译后查询: {query}")
    
    print(f"[INFO] 正在查询Arxiv论文: {query}")
    import xml.etree.ElementTree as ET
    
    arxiv_url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    
    for attempt in range(max_retries):
        try:
            # 使用细粒度超时配置
            timeout = httpx.Timeout(
                connect=5.0,  # 连接超时
                read=15.0,    # 读取超时
                write=5.0,    # 写入超时
                pool=5.0      # 连接池超时
            )
            
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(arxiv_url, params=params)
                if response.status_code != 200:
                    error_msg = f"Arxiv API返回状态码 {response.status_code}"
                    print(f"[WARNING] {error_msg}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))  # 指数退避
                        continue
                    return [], error_msg
                
                root = ET.fromstring(response.text)
                ns = {
                    'atom': 'http://www.w3.org/2005/Atom',
                    'arxiv': 'http://arxiv.org/schemas/atom'
                }
                
                papers = []
                for entry in root.findall('atom:entry', ns):
                    title = entry.find('atom:title', ns)
                    summary = entry.find('atom:summary', ns)
                    link = entry.find('atom:id', ns)
                    published = entry.find('atom:published', ns)
                    
                    authors = []
                    for author in entry.findall('atom:author', ns):
                        name = author.find('atom:name', ns)
                        if name is not None:
                            authors.append(name.text.strip())
                    
                    papers.append({
                        "title": title.text.strip() if title is not None else "",
                        "authors": authors[:3],
                        "summary": (summary.text.strip()[:200] + "...") if summary is not None and len(summary.text.strip()) > 200 else (summary.text.strip() if summary is not None else ""),
                        "link": link.text.strip() if link is not None else "",
                        "published": published.text.strip()[:10] if published is not None else ""
                    })
                
                print(f"[SUCCESS] Arxiv查询成功，找到{len(papers)}篇论文")
                return papers, None
                
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            error_msg = f"Arxiv API超时/连接错误: {str(e)}"
            print(f"[ERROR] {error_msg} (尝试 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))  # 指数退避
                continue
            return [], error_msg
        except httpx.HTTPError as e:
            error_msg = f"Arxiv API网络错误: {str(e)}"
            print(f"[ERROR] {error_msg}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            return [], error_msg
        except ET.ParseError as e:
            error_msg = f"Arxiv XML解析错误: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return [], error_msg
        except Exception as e:
            error_msg = f"Arxiv搜索异常: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return [], error_msg
    
    return [], "Arxiv查询失败，已达最大重试次数"


def truncate_definition(text: str, max_length: int = 500) -> str:
    """截断定义文本"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


async def get_real_discovery_result(concept: str, max_concepts: int = 5) -> dict:
    """
    使用真实LLM生成概念挖掘结果 + 语义相似度排序
    
    数据流:
    1. LLM生成相关概念（生成2倍候选）
    2. 计算每个概念与输入概念的语义相似度
    3. 按相似度排序，选择top-N
    4. 获取Wikipedia定义验证
    5. 计算动态可信度
    """
    print(f"[INFO] 开始概念发现: {concept} (使用真实LLM)")
    
    # 尝试导入真实生成器
    try:
        from backend.api.real_node_generator import (
            generate_related_concepts,
            compute_similarity,
            compute_credibility
        )
        use_real_llm = True
        print("[INFO] 真实生成器导入成功")
    except ImportError as e:
        print(f"[WARNING] 无法导入real_node_generator: {e}，使用预定义概念")
        use_real_llm = False
    
    nodes = []
    
    # 添加中心节点（输入概念本身）
    center_wiki = await get_wikipedia_definition(concept, max_length=500)
    center_node = {
        "id": f"{concept.replace(' ', '_')}_跨学科_0",
        "label": concept,
        "discipline": "跨学科",
        "definition": center_wiki["definition"] if center_wiki["exists"] else f"{concept}是一个跨学科的学术概念。",
        "brief_summary": await generate_brief_summary(concept, center_wiki.get("definition", "")),
        "credibility": 0.95 if center_wiki["exists"] else 0.80,
        "similarity": 1.0,  # 中心节点相似度为1
        "source": "Wikipedia" if center_wiki["exists"] else "LLM",
        "wiki_url": center_wiki.get("url", ""),
        "depth": 0
    }
    nodes.append(center_node)
    
    if use_real_llm:
        # 使用真实LLM生成相关概念
        try:
            # 固定生成20个候选概念，确保有足够样本进行相似度筛选
            candidates = await generate_related_concepts(
                parent_concept=concept,
                existing_concepts=[concept],
                max_count=20  # 固定生成20个，后续通过相似度筛选
            )
            
            if candidates:
                print(f"[INFO] LLM生成了{len(candidates)}个候选概念")
                
                # 批量计算语义相似度
                print("[INFO] 批量计算语义相似度...")
                from backend.api.real_node_generator import compute_similarities_batch
                
                concept_names = [c["name"] for c in candidates]
                similarities = await compute_similarities_batch(concept_names, concept)
                
                # 组合候选概念和相似度
                candidates_with_similarity = []
                for candidate, similarity in zip(candidates, similarities):
                    candidates_with_similarity.append({
                        **candidate,
                        "similarity": similarity
                    })
                
                # 按语义相似度降序排列
                candidates_with_similarity.sort(key=lambda x: x["similarity"], reverse=True)
                print("[INFO] 按语义相似度排序")
                
                # 动态阈值筛选：保证3-9个节点
                SIMILARITY_THRESHOLD = 0.65  # 只选择真正相似度高的概念
                MIN_NODES = 3
                MAX_NODES = min(9, max_concepts - 1)  # 不超过请求的max_concepts
                
                # 先筛选高于阈值的
                high_quality = [c for c in candidates_with_similarity if c["similarity"] >= SIMILARITY_THRESHOLD]
                
                # 确保数量在合理范围内
                if len(high_quality) < MIN_NODES:
                    # 如果太少，补充到最小数量
                    top_candidates = candidates_with_similarity[:MIN_NODES]
                    print(f"[INFO] 阈值筛选结果不足{MIN_NODES}个，取相似度最高的{MIN_NODES}个")
                elif len(high_quality) > MAX_NODES:
                    # 如果太多，限制到最大数量
                    top_candidates = high_quality[:MAX_NODES]
                    print(f"[INFO] 阈值筛选结果超过{MAX_NODES}个，取相似度最高的{MAX_NODES}个")
                else:
                    # 数量合适
                    top_candidates = high_quality
                    print(f"[INFO] 阈值筛选结果: {len(high_quality)}个 (阈值={SIMILARITY_THRESHOLD})")
                
                print(f"[INFO] 选择了相似度最高的{len(top_candidates)}个概念:")
                for c in top_candidates:
                    print(f"   - {c['name']} (语义相似度: {c['similarity']:.3f}, 学科: {c['discipline']})")
                
                # 为每个候选概念创建节点
                for idx, candidate in enumerate(top_candidates, 1):
                    term = candidate["name"]
                    discipline = candidate["discipline"]
                    similarity_score = candidate["similarity"]  # 使用已计算的相似度
                    cross_principle = candidate.get("cross_principle", "")  # 获取跨学科原理
                    
                    # 获取Wikipedia定义
                    term_wiki = await get_wikipedia_definition(term, max_length=500)
                    
                    # 计算动态可信度（传入已有的相似度，避免重复计算）
                    credibility = await compute_credibility(
                        concept=term,
                        parent_concept=concept,
                        has_wikipedia=term_wiki["exists"],
                        similarity=similarity_score  # 传入已计算的相似度
                    )
                    
                    # 生成简介
                    brief_summary = await generate_brief_summary(term, term_wiki.get("definition", ""))
                    
                    node_id = f"{term.replace(' ', '_')}_{discipline.replace(' ', '_')}_{idx}"
                    
                    nodes.append({
                        "id": node_id,
                        "label": term,
                        "discipline": discipline,
                        "definition": term_wiki["definition"] if term_wiki["exists"] else f"{term}是与{concept}相关的学术概念。",
                        "similarity": round(similarity_score, 3),  # 使用已有的相似度
                        "brief_summary": brief_summary,
                        "credibility": round(credibility, 3),
                        "source": "Wikipedia" if term_wiki["exists"] else "LLM",
                        "wiki_url": term_wiki.get("url", ""),
                        "depth": 1,
                        "cross_principle": cross_principle  # 保存跨学科原理
                    })
            else:
                print("[WARNING] LLM未生成任何概念，使用预定义")
                use_real_llm = False
                
        except Exception as e:
            print(f"[ERROR] LLM生成失败: {str(e)}，使用预定义概念")
            import traceback
            traceback.print_exc()
            use_real_llm = False
    
    # 如果LLM失败，使用预定义概念作为回退
    if not use_real_llm or len(nodes) == 1:
        print("[INFO] 使用预定义概念回退方案")
        predefined = [
            {"label": f"{concept}理论", "discipline": "理论基础"},
            {"label": f"{concept}应用", "discipline": "应用领域"},
            {"label": f"{concept}方法", "discipline": "方法论"},
        ]
        
        for idx, item in enumerate(predefined[:max_concepts - 1], 1):
            term = item["label"]
            term_wiki = await get_wikipedia_definition(term, max_length=500)
            
            node_id = f"{term.replace(' ', '_')}_{item['discipline'].replace(' ', '_')}_{idx}"
            
            nodes.append({
                "id": node_id,
                "label": term,
                "discipline": item["discipline"],
                "definition": term_wiki["definition"] if term_wiki["exists"] else f"{term}是与{concept}相关的概念。",
                "brief_summary": await generate_brief_summary(term, term_wiki.get("definition", "")),
                "credibility": 0.90 if term_wiki["exists"] else 0.70,
                "similarity": 0.75,  # 预定义概念固定相似度
                "source": "Wikipedia" if term_wiki["exists"] else "LLM",
                "wiki_url": term_wiki.get("url", ""),
                "depth": 1
            })
    
    # 创建边（从中心节点到其他节点）
    edges = []
    center_node = nodes[0]
    for node in nodes[1:]:
        # 使用节点中保存的cross_principle作为reasoning
        reasoning = node.get("cross_principle", "")
        print(f"[DEBUG] 节点 {node['label']} 的 cross_principle: '{reasoning}'")
        
        if not reasoning or not reasoning.strip():
            # 如果没有cross_principle，使用默认文本
            reasoning = f"{center_node['label']}与{node['label']}相关（相似度: {node.get('similarity', 0.75):.2f}）"
            print(f"[DEBUG] 使用默认reasoning: '{reasoning}'")
        else:
            print(f"[DEBUG] 使用LLM生成的reasoning: '{reasoning}'")
        
        edge = {
            "source": center_node["id"],
            "target": node["id"],
            "relation": "related_to",
            "weight": round(node.get("similarity", 0.75) * 0.9 + 0.1, 2),  # 基于相似度的权重
            "reasoning": reasoning
        }
        edges.append(edge)
    
    # 计算元数据
    avg_similarity = sum(n.get("similarity", 0.75) for n in nodes) / len(nodes) if nodes else 0
    avg_credibility = sum(n["credibility"] for n in nodes) / len(nodes) if nodes else 0
    
    print(f"[SUCCESS] 概念发现完成: {len(nodes)}个节点, {len(edges)}条边")
    print(f"   平均相似度: {avg_similarity:.3f}")
    print(f"   平均可信度: {avg_credibility:.3f}")
    
    return {
        "status": "success",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "verified_nodes": sum(1 for n in nodes if n["source"] == "Wikipedia"),
                "avg_credibility": round(avg_credibility, 3),
                "avg_similarity": round(avg_similarity, 3),
                "generation_method": "LLM + Similarity Ranking" if use_real_llm else "Predefined Fallback"
            }
        }
    }


class DiscoverRequest(BaseModel):
    """概念挖掘请求模型（功能1）"""
    concept: str = Field(..., min_length=1, max_length=100)
    depth: int = Field(default=2, ge=1, le=3)
    max_concepts: int = Field(default=30, ge=10, le=100)


class DiscoverDisciplinedRequest(BaseModel):
    """指定学科的概念挖掘请求模型（功能2）"""
    concept: str = Field(..., min_length=1, max_length=100)
    disciplines: List[str] = Field(..., min_items=1, max_items=10)
    max_concepts: int = Field(default=10, ge=3, le=30)


class BridgeRequest(BaseModel):
    """多概念桥梁发现请求模型（功能3）"""
    concepts: List[str] = Field(..., min_items=2, max_items=5)
    max_bridges: int = Field(default=10, ge=5, le=20)


class DiscoverResponse(BaseModel):
    """概念挖掘响应模型"""
    status: str
    request_id: str
    data: Dict[str, Any]


class GraphResponse(BaseModel):
    """图谱查询响应模型"""
    status: str
    data: Dict[str, Any]


class ExpandRequest(BaseModel):
    """展开请求模型"""
    node_id: str = Field(...)
    node_label: str = Field(...)
    existing_nodes: List[str] = Field(default=[])
    max_new_nodes: int = Field(default=10, ge=1, le=20)


@router.post("/discover", response_model=DiscoverResponse)
async def discover_concepts(request: DiscoverRequest):
    """概念挖掘接口 - 使用真实LLM生成 + 语义相似度排序"""
    request_id = str(uuid.uuid4())
    
    # 1. 优先从Neo4j读取（持久化存储）
    print(f"[INFO] 步骤1：检查Neo4j持久化数据: {request.concept}")
    neo4j_data = await neo4j_client.get_graph_by_concept(request.concept, max_depth=request.depth)
    if neo4j_data and neo4j_data.get("nodes"):
        print(f"[SUCCESS] ✅ Neo4j命中！从持久化存储加载: {request.concept}")
        print(f"[INFO] 加载了{len(neo4j_data['nodes'])}个节点, {len(neo4j_data['edges'])}条边")
        return DiscoverResponse(
            status="success",
            request_id=request_id,
            data={
                "nodes": neo4j_data["nodes"],
                "edges": neo4j_data["edges"],
                "metadata": {
                    "source": "neo4j",
                    "cached": True,
                    "concept": request.concept
                }
            }
        )
    
    # 2. Neo4j未命中，检查Redis缓存（临时缓存）
    cache_key = f"discover:v2:{request.concept}"
    print(f"[INFO] 步骤2：检查Redis缓存: {cache_key}")
    cached = await redis_client.get(cache_key)
    if cached:
        print(f"[SUCCESS] ✅ Redis缓存命中！: {request.concept}")
        print(f"[INFO] 跳过LLM调用，节省时间和成本")
        return DiscoverResponse(
            status="success",
            request_id=request_id,
            data=cached
        )
    
    # 3. 缓存都未命中，使用LLM生成新数据
    print(f"[INFO] 步骤3：缓存未命中，使用LLM生成: {request.concept}")
    
    # 使用真实LLM生成（取代mock数据）
    result = await get_real_discovery_result(request.concept, max_concepts=min(request.max_concepts, 10))
    
    if result.get("status") == "success":
        nodes = result["data"]["nodes"]
        edges = result["data"]["edges"]
        
        # 保存到Neo4j（持久化存储）
        try:
            saved = await neo4j_client.save_graph_data(nodes, edges)
            if saved:
                print(f"[SUCCESS] ✅ 已保存到Neo4j持久化存储")
        except Exception as e:
            print(f"[WARNING] Neo4j保存失败: {e}")
        
        # 保存到Redis缓存（临时缓存，1小时）
        try:
            await redis_client.set(cache_key, result["data"], ex=3600)
            print(f"[SUCCESS] ✅ 已保存到Redis缓存")
        except Exception as e:
            print(f"[WARNING] Redis缓存失败: {e}")
    
    return DiscoverResponse(status=result.get("status", "success"), request_id=request_id, data=result.get("data", {}))


@router.post("/discover/disciplined", response_model=DiscoverResponse)
async def discover_concepts_disciplined(request: DiscoverDisciplinedRequest):
    """
    功能2：指定学科的概念挖掘
    
    输入：
    - concept: 单个概念（如"神经网络"）
    - disciplines: 学科列表（如["生物学", "数学"]）
    
    逻辑：只在指定学科中挖掘关联概念
    """
    print(f"[INFO] 功能2 - 指定学科挖掘: {request.concept}, 学科: {request.disciplines}")
    
    # 生成缓存key（包含concept和disciplines的组合）
    sorted_disciplines = sorted(request.disciplines)  # 排序保证一致性
    disciplines_str = "_".join(sorted_disciplines)
    cache_key = f"discover:disciplined:v2:{request.concept}:{disciplines_str}"
    
    # 检查Redis缓存
    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            print(f"[SUCCESS] ✅ 缓存命中 - 功能2: {cache_key}")
            return DiscoverResponse(
                status="success",
                request_id=str(uuid.uuid4()),
                data=cached_result
            )
        else:
            print(f"[INFO] ❌ 缓存未命中 - 功能2: {cache_key}")
    except Exception as e:
        print(f"[WARNING] Redis缓存读取失败: {e}")
    
    # 导入功能2生成器
    try:
        from backend.api.multi_function_generator import generate_concepts_with_disciplines
        from backend.api.real_node_generator import compute_similarity, compute_credibility
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"生成器导入失败: {str(e)}")
    
    request_id = str(uuid.uuid4())
    
    # 1. 添加中心节点
    center_wiki = await get_wikipedia_definition(request.concept, max_length=500)
    center_node = {
        "id": f"{request.concept.replace(' ', '_')}_center",
        "label": request.concept,
        "discipline": "跨学科",
        "definition": center_wiki["definition"] if center_wiki["exists"] else f"{request.concept}是一个跨学科的学术概念。",
        "brief_summary": await generate_brief_summary(request.concept, center_wiki.get("definition", "")),
        "credibility": 0.95 if center_wiki["exists"] else 0.80,
        "similarity": 1.0,
        "source": "Wikipedia" if center_wiki["exists"] else "LLM",
        "wiki_url": center_wiki.get("url", ""),
        "depth": 0
    }
    
    nodes = [center_node]
    edges = []
    
    # 2. LLM生成指定学科的概念（强制生成20个候选）
    candidates = await generate_concepts_with_disciplines(
        parent_concept=request.concept,
        disciplines=request.disciplines,
        max_count=20  # 强制生成20个候选概念
    )
    
    if not candidates:
        return DiscoverResponse(
            status="error",
            request_id=request_id,
            data={"message": "未生成任何概念，请检查学科设置"}
        )
    
    print(f"[INFO] LLM生成了{len(candidates)}个候选概念")
    
    # 3. 批量计算相似度并排序
    from backend.api.real_node_generator import compute_similarities_batch
    
    concept_names = [c["name"] for c in candidates]
    similarities = await compute_similarities_batch(concept_names, request.concept)
    
    candidates_with_similarity = []
    for candidate, similarity in zip(candidates, similarities):
        candidates_with_similarity.append({
            **candidate,
            "similarity": similarity
        })
    
    # 按相似度排序
    candidates_with_similarity.sort(key=lambda x: x["similarity"], reverse=True)
    
    print(f"[INFO] 按语义相似度排序")
    
    # 动态阈值筛选：保持3-9个节点
    SIMILARITY_THRESHOLD = 0.65  # 只选择真正相似度高的概念
    MIN_NODES = 3
    MAX_NODES = min(9, request.max_concepts)
    
    # 先筛选高于阈值的
    high_quality = [c for c in candidates_with_similarity if c["similarity"] >= SIMILARITY_THRESHOLD]
    
    # 确保数量在合理范围内
    if len(high_quality) < MIN_NODES:
        top_candidates = candidates_with_similarity[:MIN_NODES]
        print(f"[INFO] 阈值筛选结果不足{MIN_NODES}个，取相似度最高的{MIN_NODES}个")
    elif len(high_quality) > MAX_NODES:
        top_candidates = high_quality[:MAX_NODES]
        print(f"[INFO] 阈值筛选结果超过{MAX_NODES}个，取相似度最高的{MAX_NODES}个")
    else:
        top_candidates = high_quality
        print(f"[INFO] 阈值筛选结果: {len(high_quality)}个 (阈值={SIMILARITY_THRESHOLD})")
    
    print(f"[INFO] 选择了相似度最高的{len(top_candidates)}个概念:")
    for c in top_candidates:
        print(f"   - {c['name']} (语义相似度: {c['similarity']:.3f}, 学科: {c['discipline']})")
    
    # 4. 为每个概念创建节点
    for idx, candidate in enumerate(top_candidates, 1):
        term = candidate["name"]
        discipline = candidate["discipline"]
        similarity_score = candidate["similarity"]  # 使用已计算的相似度
        
        term_wiki = await get_wikipedia_definition(term, max_length=500)
        credibility = await compute_credibility(
            concept=term,
            parent_concept=request.concept,
            has_wikipedia=term_wiki["exists"],
            similarity=similarity_score  # 传入已计算的相似度
        )
        brief_summary = await generate_brief_summary(term, term_wiki.get("definition", ""))
        
        node_id = f"{term.replace(' ', '_')}_{discipline.replace(' ', '_')}_{idx}"
        
        nodes.append({
            "id": node_id,
            "label": term,
            "discipline": discipline,
            "definition": term_wiki["definition"] if term_wiki["exists"] else f"{term}是与{request.concept}相关的学术概念。",
            "brief_summary": brief_summary,
            "credibility": round(credibility, 3),
            "similarity": round(similarity_score, 3),  # 使用已有的相似度
            "source": "Wikipedia" if term_wiki["exists"] else "LLM",
            "wiki_url": term_wiki.get("url", ""),
            "depth": 1
        })
        
        edges.append({
            "source": center_node["id"],
            "target": node_id,
            "relation": candidate.get("relation", "related_to"),
            "weight": round(candidate["similarity"] * 0.9 + 0.1, 2),
            "reasoning": candidate.get("cross_principle") or candidate.get("reasoning") or f"{request.concept}与{term}在{discipline}领域存在关联"
        })
    
    result = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "function": "disciplined_discovery",
            "input_concept": request.concept,
            "disciplines": request.disciplines,
            "total_concepts": len(nodes) - 1
        }
    }
    
    print(f"[SUCCESS] 功能2完成: 生成{len(nodes)-1}个概念")
    
    # 保存到Redis缓存（3600秒 = 1小时）
    try:
        await redis_client.set(cache_key, result, ex=3600)
        print(f"[INFO] ✅ 已缓存功能2结果: {cache_key}")
    except Exception as e:
        print(f"[WARNING] Redis缓存保存失败: {e}")
    
    # 保存到Neo4j（如果配置了）
    try:
        if hasattr(neo4j_client, 'save_graph_data'):
            await neo4j_client.save_graph_data(nodes, edges)
            print(f"[INFO] ✅ 已保存到Neo4j")
    except Exception as e:
        print(f"[WARNING] Neo4j保存失败: {e}")
    
    return DiscoverResponse(status="success", request_id=request_id, data=result)


@router.post("/discover/bridge", response_model=DiscoverResponse)
async def discover_bridge_concepts(request: BridgeRequest):
    """
    功能3：多概念桥梁发现
    
    输入：
    - concepts: 多个概念（如["熵", "最小二乘法"]）
    
    逻辑：寻找连接这些概念的"桥梁概念"节点
    """
    print(f"[INFO] 功能3 - 桥梁发现: {request.concepts}")
    
    # 生成缓存key（包含所有concepts的组合）
    sorted_concepts = sorted(request.concepts)  # 排序保证一致性
    concepts_str = "_".join(sorted_concepts)
    cache_key = f"discover:bridge:v2:{concepts_str}:{request.max_bridges}"
    
    # 检查Redis缓存
    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            print(f"[SUCCESS] ✅ 缓存命中 - 功能3: {cache_key}")
            return DiscoverResponse(
                status="success",
                request_id=str(uuid.uuid4()),
                data=cached_result
            )
        else:
            print(f"[INFO] ❌ 缓存未命中 - 功能3: {cache_key}")
    except Exception as e:
        print(f"[WARNING] Redis缓存读取失败: {e}")
    
    # 导入功能3生成器
    try:
        from backend.api.multi_function_generator import find_bridge_concepts
        from backend.api.real_node_generator import compute_similarity, compute_credibility
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"生成器导入失败: {str(e)}")
    
    request_id = str(uuid.uuid4())
    
    nodes = []
    edges = []
    
    # 1. 为每个输入概念创建中心节点
    center_nodes = []
    for i, concept in enumerate(request.concepts):
        wiki = await get_wikipedia_definition(concept, max_length=500)
        node_id = f"{concept.replace(' ', '_')}_input_{i}"
        
        center_node = {
            "id": node_id,
            "label": concept,
            "discipline": "输入概念",
            "definition": wiki["definition"] if wiki["exists"] else f"{concept}是一个学术概念。",
            "brief_summary": await generate_brief_summary(concept, wiki.get("definition", "")),
            "credibility": 0.95 if wiki["exists"] else 0.80,
            "source": "Wikipedia" if wiki["exists"] else "LLM",
            "wiki_url": wiki.get("url", ""),
            "depth": 0,
            "is_input": True
        }
        
        center_nodes.append(center_node)
        nodes.append(center_node)
    
    # 2. LLM生成桥梁概念
    bridges = await find_bridge_concepts(
        concepts=request.concepts,
        max_bridges=request.max_bridges
    )
    
    if not bridges:
        return DiscoverResponse(
            status="error",
            request_id=request_id,
            data={"message": "未找到桥梁概念，请尝试其他概念组合"}
        )
    
    # 3. 为每个桥梁概念创建节点
    for idx, bridge in enumerate(bridges):
        bridge_name = bridge["name"]
        bridge_type = bridge["bridge_type"]
        
        wiki = await get_wikipedia_definition(bridge_name, max_length=500)
        brief_summary = await generate_brief_summary(bridge_name, wiki.get("definition", ""))
        
        node_id = f"{bridge_name.replace(' ', '_')}_bridge_{idx}"
        
        # 计算平均可信度（基于与所有输入概念的关联）
        avg_credibility = 0.0
        for input_concept in request.concepts:
            cred = await compute_credibility(
                concept=bridge_name,
                parent_concept=input_concept,
                has_wikipedia=wiki["exists"]
            )
            avg_credibility += cred
        avg_credibility /= len(request.concepts)
        
        nodes.append({
            "id": node_id,
            "label": bridge_name,
            "discipline": "桥梁概念",
            "bridge_type": bridge_type,
            "definition": wiki["definition"] if wiki["exists"] else f"{bridge_name}是连接概念的桥梁。",
            "brief_summary": brief_summary,
            "credibility": round(avg_credibility, 3),
            "source": "Wikipedia" if wiki["exists"] else "LLM",
            "wiki_url": wiki.get("url", ""),
            "depth": 1,
            "is_bridge": True,
            "connection_principle": bridge["connection_principle"]
        })
        
        # 4. 创建边：为每个输入概念到桥梁概念生成单独的reasoning
        for input_concept in bridge["connected_concepts"]:
            # 找到对应的输入节点
            source_node = next((n for n in center_nodes if n["label"] == input_concept.strip()), None)
            if source_node:
                # 为这条边生成专门的reasoning，解释这个输入概念与桥梁概念的关系
                edge_reasoning = await generate_bridge_edge_reasoning(
                    input_concept=input_concept.strip(),
                    bridge_concept=bridge_name,
                    overall_principle=bridge["connection_principle"]
                )
                
                print(f"[DEBUG] 边 {input_concept} → {bridge_name} 的reasoning: {edge_reasoning}")
                
                edges.append({
                    "source": source_node["id"],
                    "target": node_id,
                    "relation": "桥梁连接",
                    "weight": 0.85 if bridge_type == "直接桥梁" else (0.75 if bridge_type == "间接桥梁" else 0.65),
                    "reasoning": edge_reasoning
                })
    
    # 5. 构建桥接路径分析数据（用于前端展示）
    bridges_by_type = {}
    for b in bridges:
        btype = b["bridge_type"]
        if btype not in bridges_by_type:
            bridges_by_type[btype] = []
        bridges_by_type[btype].append({
            "name": b["name"],
            "connected": b["connected_concepts"],
            "principle": b["connection_principle"]
        })
    
    bridge_analysis = {
        "input_concepts": request.concepts,
        "total_bridges": len(bridges),
        "bridges_by_type": bridges_by_type,
        "summary": f"通过{len(bridges)}个桥接概念连接了{len(request.concepts)}个输入概念"
    }
    
    print(f"[SUCCESS] 功能3完成: 找到{len(bridges)}个桥梁概念")
    
    result = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "function": "bridge_discovery",
            "input_concepts": request.concepts,
            "total_bridges": len(bridges),
            "bridge_types": {bt: sum(1 for b in bridges if b["bridge_type"] == bt) for bt in ["直接桥梁", "间接桥梁", "原理性桥梁"]},
            "bridge_analysis": bridge_analysis  # 添加桥接路径分析数据
        }
    }
    
    # 保存到Redis缓存（3600秒 = 1小时）
    try:
        await redis_client.set(cache_key, result, ex=3600)
        print(f"[INFO] ✅ 已缓存功能3结果: {cache_key}")
    except Exception as e:
        print(f"[WARNING] Redis缓存保存失败: {e}")
    
    # 保存到Neo4j（如果配置了）
    try:
        if hasattr(neo4j_client, 'save_graph_data'):
            await neo4j_client.save_graph_data(nodes, edges)
            print(f"[INFO] ✅ 已保存到Neo4j")
    except Exception as e:
        print(f"[WARNING] Neo4j保存失败: {e}")
    
    return DiscoverResponse(status="success", request_id=request_id, data=result)


@router.get("/graph/{concept_id}", response_model=GraphResponse)
async def get_graph(concept_id: str):
    """查询图谱"""
    try:
        graph_data = await neo4j_client.query_graph(concept_id)
        return GraphResponse(status="success", data=graph_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/arxiv/search")
async def search_arxiv(query: str = Query(...), max_results: int = Query(default=10, ge=1, le=50)):
    """搜索Arxiv论文"""
    papers, error_msg = await search_arxiv_papers(query, max_results=max_results)
    return {
        "status": "success" if error_msg is None else "partial",
        "data": {"query": query, "total": len(papers), "papers": papers, "error": error_msg}
    }


@router.post("/expand")
async def expand_node(request: ExpandRequest):
    """
    展开节点 - 使用真实LLM生成 + 语义相似度排序
    
    数据流:
    1. LLM生成相关概念 (generate_related_concepts)
    2. 计算每个概念与父节点的语义相似度 (compute_similarity)
    3. 按相似度排序，选择top-N个概念
    4. 为每个概念获取Wikipedia定义
    5. 计算动态可信度 (base * (0.7 + 0.3 * similarity))
    6. 返回排序后的节点和边
    """
    print(f"[INFO] 展开节点: {request.node_label} (使用真实LLM生成)")
    
    try:
        # 导入真实生成器
        from backend.api.real_node_generator import (
            generate_related_concepts,
            compute_similarity,
            compute_credibility
        )
    except ImportError as e:
        print(f"[WARNING] 无法导入real_node_generator: {e}，使用预定义概念")
        return await _expand_node_fallback(request)
    
    try:
        # 步骤1: LLM生成相关概念（生成比需要更多的候选）
        candidates = await generate_related_concepts(
            parent_concept=request.node_label,
            existing_concepts=request.existing_nodes,
            max_count=request.max_new_nodes * 2  # 生成2倍候选
        )
        
        if not candidates:
            print("[WARNING] LLM未生成任何概念，使用预定义")
            return await _expand_node_fallback(request)
        
        print(f"[INFO] LLM生成了{len(candidates)}个候选概念")
        
        # 步骤2: 批量计算语义相似度
        from backend.api.real_node_generator import compute_similarities_batch
        
        concept_names = [c["name"] for c in candidates]
        similarities = await compute_similarities_batch(concept_names, request.node_label)
        
        candidates_with_similarity = []
        for candidate, similarity in zip(candidates, similarities):
            candidates_with_similarity.append({
                **candidate,
                "similarity": similarity
            })
        
        # 步骤3: 按相似度排序，使用动态阈值筛选
        candidates_with_similarity.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 动态阈值筛选：保持3-9个节点
        SIMILARITY_THRESHOLD = 0.65  # 只选择真正相似度高的概念
        MIN_NODES = 3
        MAX_NODES = 9
        
        # 先筛选高于阈值的
        high_quality = [c for c in candidates_with_similarity if c["similarity"] >= SIMILARITY_THRESHOLD]
        
        # 确保数量在合理范围内
        if len(high_quality) < MIN_NODES:
            # 如果太少，补充到最小数量
            top_candidates = candidates_with_similarity[:MIN_NODES]
            print(f"[INFO] 阈值筛选结果不足{MIN_NODES}个，取相似度最高的{MIN_NODES}个")
        elif len(high_quality) > MAX_NODES:
            # 如果太多，限制到最大数量
            top_candidates = high_quality[:MAX_NODES]
            print(f"[INFO] 阈值筛选结果超过{MAX_NODES}个，取相似度最高的{MAX_NODES}个")
        else:
            # 数量合适
            top_candidates = high_quality
            print(f"[INFO] 阈值筛选结果: {len(high_quality)}个 (阈值={SIMILARITY_THRESHOLD})")
        
        print(f"[INFO] 选择了相似度最高的{len(top_candidates)}个概念:")
        for c in top_candidates:
            print(f"   - {c['name']} (相似度: {c['similarity']:.3f})")
        
        # 步骤4-6: 为每个概念获取定义并计算动态可信度
        new_nodes = []
        new_edges = []
        
        for i, candidate in enumerate(top_candidates):
            term = candidate["name"]
            node_id = f"{request.node_id}_expand_{i}"
            
            if node_id in request.existing_nodes:
                continue
            
            # 获取Wikipedia定义
            term_wiki = await get_wikipedia_definition(term, max_length=500)
            
            # 计算动态可信度（基于来源和相似度）
            credibility = await compute_credibility(
                concept=term,
                parent_concept=request.node_label,
                has_wikipedia=term_wiki["exists"]
            )
            
            # 生成简介
            brief_summary = await generate_brief_summary(term, term_wiki.get("definition", ""))
            
            new_nodes.append({
                "id": node_id,
                "label": term,
                "discipline": candidate["discipline"],
                "definition": term_wiki["definition"] if term_wiki["exists"] else f"{term}是{request.node_label}相关的学术概念",
                "brief_summary": brief_summary,
                "credibility": round(credibility, 3),
                "similarity": round(candidate["similarity"], 3),  # 保存相似度供前端显示
                "source": "Wikipedia" if term_wiki["exists"] else "LLM",
                "wiki_url": term_wiki.get("url", "")
            })
            
            # 创建边（权重基于相似度）
            new_edges.append({
                "source": request.node_id,
                "target": node_id,
                "relation": candidate["relation"],
                "weight": round(candidate["similarity"] * 0.9 + 0.1, 2),  # [0.1, 1.0]
                "reasoning": f"{term}与{request.node_label}具有{candidate['relation']}关系（相似度: {candidate['similarity']:.2f}）"
            })
        
        print(f"[SUCCESS] 成功展开{len(new_nodes)}个节点")
        
        return {
            "status": "success",
            "data": {
                "nodes": new_nodes,
                "edges": new_edges,
                "parent_id": request.node_id,
                "metadata": {
                    "total_candidates": len(candidates),
                    "selected_count": len(new_nodes),
                    "avg_similarity": round(sum(c["similarity"] for c in top_candidates) / len(top_candidates), 3) if top_candidates else 0,
                    "generation_method": "LLM + Similarity Ranking"
                }
            }
        }
    
    except Exception as e:
        print(f"[ERROR] 节点展开失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return await _expand_node_fallback(request)


async def _expand_node_fallback(request: ExpandRequest):
    """预定义概念回退方案"""
    print(f"[INFO] 使用预定义概念展开: {request.node_label}")
    
    domain_concepts = {
        "深度学习": [("神经网络", "计算机科学", "foundation"), ("反向传播", "算法", "methodology")],
        "机器学习": [("监督学习", "方法论", "sub_field"), ("深度学习", "计算机科学", "sub_field")],
    }
    
    related_concepts = domain_concepts.get(request.node_label, [
        (f"{request.node_label}理论", "理论基础", "theory"),
        (f"{request.node_label}应用", "应用领域", "application"),
    ])
    
    new_nodes = []
    new_edges = []
    
    for i, (term, discipline, relation_type) in enumerate(related_concepts):
        node_id = f"{request.node_id}_expand_{i}"
        if node_id not in request.existing_nodes:
            term_wiki = await get_wikipedia_definition(term, max_length=500)
            
            new_nodes.append({
                "id": node_id,
                "label": term,
                "discipline": discipline,
                "definition": term_wiki["definition"] if term_wiki["exists"] else f"{term}相关概念",
                "credibility": 0.90 if term_wiki["exists"] else 0.70,
                "source": "Wikipedia" if term_wiki["exists"] else "LLM",
                "wiki_url": term_wiki.get("url", "")
            })
            
            new_edges.append({
                "source": request.node_id,
                "target": node_id,
                "relation": relation_type,
                "weight": 0.80,
                "reasoning": f"{term}是{request.node_label}的{relation_type}"
            })
    
    return {"status": "success", "data": {"nodes": new_nodes, "edges": new_edges, "parent_id": request.node_id}}


@router.post("/ai/chat")
async def ai_chat(request: dict):
    """AI问答接口"""
    question = request.get("question", "")
    concept = request.get("concept", "")
    
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    client = get_llm_client()
    if not client:
        return {"status": "success", "data": {"answer": "AI服务暂时不可用", "sources": []}}
    
    try:
        system_prompt = f"""你是专业学术助手，擅长解答关于"{concept}"的问题。回答要准确简洁（150字以内）。"""
        
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.5,
                max_tokens=300
            ),
            timeout=20.0
        )
        
        if response and response.choices:
            answer = response.choices[0].message.content.strip()
            return {"status": "success", "data": {"answer": answer, "sources": ["LLM生成"]}}
    except Exception as e:
        print(f"[ERROR] AI问答失败: {str(e)}")
        return {"status": "error", "data": {"answer": "处理问题时出现错误", "sources": []}}


@router.delete("/cache/clear")
async def clear_cache(pattern: str = "*"):
    """
    清除Redis缓存
    
    参数:
    - pattern: 缓存key模式，默认"*"清除所有
      - "*": 清除所有缓存
      - "discover:v2:*": 清除功能1缓存
      - "discover:disciplined:v2:*": 清除功能2缓存
      - "discover:bridge:v2:*": 清除功能3缓存
    """
    try:
        if redis_client.mock_mode:
            # Mock模式：清除内存缓存
            if pattern == "*":
                count = len(redis_client._mock_cache)
                redis_client._mock_cache.clear()
                print(f"[INFO] Mock模式：已清除所有缓存 ({count}个key)")
            else:
                # 简单的模式匹配
                pattern_prefix = pattern.replace("*", "")
                keys_to_delete = [k for k in redis_client._mock_cache.keys() if k.startswith(pattern_prefix)]
                for key in keys_to_delete:
                    del redis_client._mock_cache[key]
                print(f"[INFO] Mock模式：已清除匹配 '{pattern}' 的缓存 ({len(keys_to_delete)}个key)")
                count = len(keys_to_delete)
        else:
            # 真实Redis模式
            if not redis_client.client:
                await redis_client.connect()
            
            if pattern == "*":
                # 清除所有key
                await redis_client.client.flushdb()
                count = "all"
                print(f"[INFO] Redis：已清除所有缓存")
            else:
                # 根据模式删除
                keys = []
                async for key in redis_client.client.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    await redis_client.client.delete(*keys)
                count = len(keys)
                print(f"[INFO] Redis：已清除匹配 '{pattern}' 的缓存 ({count}个key)")
        
        return {
            "status": "success",
            "message": f"已清除缓存",
            "pattern": pattern,
            "deleted_count": count
        }
    except Exception as e:
        print(f"[ERROR] 清除缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")

