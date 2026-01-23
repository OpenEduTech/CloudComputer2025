"""PPT 扩展系统服务"""

from typing import List, Dict, Any
import json
import os

from langgraph.graph import StateGraph, END

from .ppt_parser_service import DocumentParserService
from ..agents.base import (
    LLMConfig,
    GlobalStructureAgent,
    KnowledgeClusteringAgent,
    StructureUnderstandingAgent,
    GapIdentificationAgent,
    KnowledgeExpansionAgent,
    RetrievalAgent,
    ConsistencyCheckAgent,
    StructuredOrganizationAgent,
)
from ..agents.models import GraphState


class PPTExpansionService:
    """PPT 扩展系统主服务"""
    
    def __init__(self, llm_config: LLMConfig):
        self.config = llm_config
        
        # 初始化所有 Agent
        self.global_structure_agent = GlobalStructureAgent(llm_config)
        self.clustering_agent = KnowledgeClusteringAgent(llm_config)
        self.structure_agent = StructureUnderstandingAgent(llm_config)
        self.gap_agent = GapIdentificationAgent(llm_config)
        self.expansion_agent = KnowledgeExpansionAgent(llm_config)
        self.retrieval_agent = RetrievalAgent(llm_config)
        self.check_agent = ConsistencyCheckAgent(llm_config)
        self.organization_agent = StructuredOrganizationAgent(llm_config)
        
        # 构建 Graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("global_structure", self.global_structure_agent.run)
        workflow.add_node("knowledge_clustering", self.clustering_agent.run)
        workflow.add_node("structure_understanding", self.structure_agent.run)
        workflow.add_node("gap_identification", self.gap_agent.run)
        workflow.add_node("knowledge_expansion", self.expansion_agent.run)
        workflow.add_node("retrieval", self.retrieval_agent.run)
        workflow.add_node("consistency_check", self.check_agent.run)
        workflow.add_node("structured_organization", self.organization_agent.run)
        
        # 定义边
        workflow.set_entry_point("global_structure")
        workflow.add_edge("global_structure", "knowledge_clustering")
        workflow.add_edge("knowledge_clustering", "structure_understanding")
        workflow.add_edge("structure_understanding", "gap_identification")
        workflow.add_edge("gap_identification", "knowledge_expansion")
        workflow.add_edge("gap_identification", "retrieval")  
        workflow.add_edge("knowledge_expansion", "consistency_check")
        workflow.add_edge("retrieval", "consistency_check")
        
        # 条件边
        workflow.add_conditional_edges(
            "consistency_check",
            self._should_revise,
            {
                "revise": "knowledge_expansion",
                "pass": "structured_organization"
            }
        )
        
        workflow.add_edge("structured_organization", END)
        
        return workflow.compile()
    
    def _should_revise(self, state: GraphState) -> str:
        """判断是否需要修订"""
        if state["check_result"].status == "revise":
            if state.get("revision_count", 0) < state.get("max_revisions", 2):
                state["revision_count"] = state.get("revision_count", 0) + 1
                return "revise"
        return "pass"
    
    def run(self, ppt_texts: List[str], max_revisions: int = 2) -> GraphState:
        """运行完整流程"""
        initial_state: GraphState = {
            "ppt_texts": ppt_texts,
            "global_outline": {},
            "knowledge_units": [],
            "current_unit_id": "",
            "current_page_id": 0,
            "raw_text": "",
            "page_structure": None,
            "knowledge_gaps": [],
            "expanded_content": [],
            "retrieved_docs": [],
            "check_result": None,
            "final_notes": "",
            "revision_count": 0,
            "max_revisions": max_revisions,
            "streaming_chunks": []
        }
        
        result = self.graph.invoke(initial_state)
        return result
    
    def run_per_page(self, ppt_texts: List[str], max_revisions: int = 2) -> List[Dict[str, Any]]:
        """逐页扩展 PPT"""
        results = []
        
        for i, text in enumerate(ppt_texts, 1):
            initial_state: GraphState = {
                "ppt_texts": [text],
                "global_outline": {},
                "knowledge_units": [],
                "current_unit_id": f"page_{i}",
                "current_page_id": i,
                "raw_text": text,
                "page_structure": None,
                "knowledge_gaps": [],
                "expanded_content": [],
                "retrieved_docs": [],
                "check_result": None,
                "final_notes": "",
                "revision_count": 0,
                "max_revisions": max_revisions,
                "streaming_chunks": []
            }
            
            result = self._run_from_structure(initial_state)
            
            results.append({
                "page_id": i,
                "raw_text": text,
                "page_structure": result["page_structure"].model_dump() if result.get("page_structure") else None,
                "knowledge_gaps": [gap.model_dump() for gap in result.get("knowledge_gaps", [])],
                "expanded_content": [ec.model_dump() for ec in result.get("expanded_content", [])],
                "final_notes": result.get("final_notes", "")
            })
        
        return results
    
    def _run_from_structure(self, initial_state: GraphState) -> GraphState:
        """从结构理解开始的部分流程"""
        state = initial_state
        state = self.structure_agent.run(state)
        state = self.gap_agent.run(state)
        state = self.expansion_agent.run(state)
        state = self.retrieval_agent.run(state)
        state = self.check_agent.run(state)
        
        if state["check_result"].status == "revise" and state.get("revision_count", 0) < state.get("max_revisions", 2):
            state["revision_count"] = state.get("revision_count", 0) + 1
            state = self.expansion_agent.run(state)
            state = self.check_agent.run(state)

        state = self.organization_agent.run(state)
        
        return state
