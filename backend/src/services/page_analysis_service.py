"""页面级别的深度分析服务 - 基于优化的 Agent 流程"""

from typing import List, Dict, Any, Optional
import json

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .mcp_tools import MCPRouter
from ..agents.base import (
    GlobalStructureAgent,
    StructureUnderstandingAgent,
    GapIdentificationAgent,
    KnowledgeExpansionAgent,
    RetrievalAgent,
    ConsistencyCheckAgent,
    StructuredOrganizationAgent,
    GraphState,
    LLMConfig,
)
from ..agents.models import CheckResult


class PageKnowledgeClusterer:
    """单页面知识聚类"""
    
    def __init__(self, llm_config: LLMConfig):
        self.llm = llm_config.create_llm(temperature=0.3)
    
    def run(self, raw_text: str, global_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """分析单页面中学生可能有难度的概念
        
        Args:
            raw_text: 当前页面的文本内容
            global_context: 全局分析结果，包含主题、知识点框架等
        """
        if global_context:
            template = """作为学习专家,基于整个文档的全局分析结果,分析当前页面中学生可能有理解难度的概念。

文档全局信息:
- 主题: {main_topic}
- 知识逻辑流程: {knowledge_flow}
- 全局知识点单元: {knowledge_units}

当前页面内容:
{content}

任务: 结合全局知识框架,识别当前页面中难以理解的概念
要求:
1. 参考全局知识点单元,识别当前页面涉及的核心概念
2. 考虑概念在整个文档知识体系中的位置
3. 识别学生可能不理解的原因

识别难以理解的概念(JSON格式,最多10个):
[
  {{
    "concept": "概念名称",
    "difficulty_level": 难度1-5,
    "why_difficult": "为什么难理解(50字内)",
    "related_concepts": ["相关概念1", "相关概念2"],
    "global_context": "在全局知识框架中的位置(可选)"
  }}
]

只返回JSON数组。
"""
            # 格式化
            knowledge_units_str = ""
            if global_context.get("knowledge_units"):
                for unit in global_context["knowledge_units"][:10]:  
                    pages_str = ",".join(map(str, unit.get("pages", [])))
                    concepts_str = ",".join(unit.get("core_concepts", []))
                    knowledge_units_str += f"- {unit.get('title', '')} (页码: {pages_str}, 核心概念: {concepts_str})\n"
            
            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | self.llm
            
            response = chain.invoke({
                "main_topic": global_context.get("main_topic", "未知"),
                "knowledge_flow": global_context.get("knowledge_flow", ""),
                "knowledge_units": knowledge_units_str or "无",
                "content": raw_text[:1500]
            })
        else:
            template = """作为学习专家,分析以下内容中学生可能有理解难度的概念。

内容:
{content}

识别难以理解的概念(JSON格式,最多10个):
[
  {{
    "concept": "概念名称",
    "difficulty_level": 难度1-5,
    "why_difficult": "为什么难理解(50字内)",
    "related_concepts": ["相关概念1", "相关概念2"]
  }}
]

只返回JSON数组。
"""
            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | self.llm
            
            response = chain.invoke({"content": raw_text[:1500]})
        
        try:
            clusters_data = json.loads(response.content)
            return clusters_data if isinstance(clusters_data, list) else []
        except:
            return []


class DeepAnalysisResult(BaseModel):
    """页面深度分析结果"""
    page_id: int = Field(description="页面 ID")
    title: str = Field(description="页面标题")
    
    raw_content: str = Field(description="原始文本内容")
    
    page_structure: Dict[str, Any] = Field(description="页面结构化分析结果")
    knowledge_clusters: List[Dict[str, Any]] = Field(description="知识聚类分析")
    
    understanding_notes: str = Field(description="结构化学习笔记 (Markdown)")
    knowledge_gaps: List[Dict[str, Any]] = Field(description="识别的知识缺口")
    expanded_content: List[Dict[str, str]] = Field(description="补充说明内容")
    
    references: List[Dict[str, str]] = Field(default_factory=list, description="参考文献列表")
    
    raw_points: List[Dict[str, Any]] = Field(default_factory=list, description="原始要点")


class PageDeepAnalysisService:
    """单页深度分析服务"""
    
    def __init__(self, llm_config):
        self.llm_config = llm_config
        self.mcp_router = MCPRouter()
        
        # 初始化
        self.structure_agent = GlobalStructureAgent(llm_config)
        self.clustering_agent = PageKnowledgeClusterer(llm_config)
        self.understanding_agent = StructureUnderstandingAgent(llm_config)
        self.gap_agent = GapIdentificationAgent(llm_config)
        self.expansion_agent = KnowledgeExpansionAgent(llm_config)
        self.retrieval_agent = RetrievalAgent(llm_config)
        self.consistency_agent = ConsistencyCheckAgent(llm_config)
        self.organization_agent = StructuredOrganizationAgent(llm_config)
    
    
    def analyze_page(
        self,
        page_id: int,
        title: str,
        content: str,
        raw_points: List[Dict[str, Any]] = None
    ) -> DeepAnalysisResult:
        """分析单个页面 - 使用优化的 Agent 流程
        
        Args:
            page_id: 页面 ID
            title: 页面标题
            content: 页面内容
            raw_points: 原始要点结构
        
        Returns:
            DeepAnalysisResult: 深度分析结果
        """
        # 初始化状态
        state: GraphState = {
            "ppt_texts": [content],
            "global_outline": {},
            "knowledge_units": [],
            "current_unit_id": f"page_{page_id}",
            "current_page_id": page_id,
            "raw_text": content,
            "page_structure": {},
            "knowledge_clusters": [],
            "understanding_notes": "",
            "knowledge_gaps": [],
            "expanded_content": [],
            "retrieved_docs": [],
            "check_result": CheckResult(status="pass", issues=[], suggestions=[]),
            "final_notes": "",
            "revision_count": 0,
            "max_revisions": 1,
            "streaming_chunks": []
        }
        
        # 步骤1: 知识聚类和难度分析
        try:
            knowledge_clusters = self.clustering_agent.run(content)
            state["knowledge_clusters"] = knowledge_clusters
        except Exception as e:
            print(f"知识聚类失败: {e}")
            state["knowledge_clusters"] = []
        
        # 步骤2: 学生理解笔记
        try:
            state = self.understanding_agent.run(state)
        except Exception as e:
            print(f"理解笔记生成失败: {e}")
        
        # 步骤3: 识别知识缺口
        try:
            state = self.gap_agent.run(state)
        except Exception as e:
            print(f"知识缺口识别失败: {e}")
        
        # 步骤4: 定向知识扩展
        try:
            state = self.expansion_agent.run(state)
        except Exception as e:
            print(f"知识扩展失败: {e}")
        
        # 步骤5: 外部检索增强
        try:
            state = self.retrieval_agent.run(state)
        except Exception as e:
            print(f"外部检索失败: {e}")
        
        # 步骤6: 一致性校验
        try:
            state = self.consistency_agent.run(state)
        except Exception as e:
            print(f"一致性校验失败: {e}")
        
        # 步骤7: 最终内容组织
        try:
            state = self.organization_agent.run(state)
        except Exception as e:
            print(f"内容组织失败: {e}")
        
        references = []
        for doc in state.get("retrieved_docs", [])[:5]:
            references.append({
                "title": doc.metadata.get("title", ""),
                "url": doc.metadata.get("url", ""),
                "source": doc.metadata.get("source", "Unknown"),
                "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            })
        
        expanded_content_list = []
        if state.get("expanded_content"):
            for ec in state["expanded_content"]:
                if hasattr(ec, 'concept'):  
                    expanded_content_list.append({
                        "concept": ec.concept,
                        "gap_type": ec.gap_type,
                        "content": ec.content,
                        "sources": ec.sources
                    })
                else:  
                    expanded_content_list.append(ec)
        
        return DeepAnalysisResult(
            page_id=page_id,
            title=title,
            raw_content=content,
            page_structure=state.get("page_structure", {}),
            knowledge_clusters=state.get("knowledge_clusters", []),
            understanding_notes=state.get("understanding_notes", ""),
            knowledge_gaps=[
                {
                    "concept": gap.concept if hasattr(gap, 'concept') else gap.get("concept", ""),
                    "gap_types": gap.gap_types if hasattr(gap, 'gap_types') else gap.get("gap_types", []),
                    "priority": gap.priority if hasattr(gap, 'priority') else gap.get("priority", 3)
                } for gap in state.get("knowledge_gaps", [])
            ],
            expanded_content=expanded_content_list,
            references=references,
            raw_points=raw_points or []
        )
    
