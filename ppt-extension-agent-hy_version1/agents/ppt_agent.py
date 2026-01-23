"""
PPT处理智能体（工作流编排层）

说明：
- 当前的系统“能力”主要分布在 `services/*` 与 `api/routes.py` 中；
- 本模块把这些能力“串起来”，形成可复用、可测试的工作流入口，供 API 复用；
- 本模块采用 LangGraph 进行工作流编排，体现“工具链 + Check Layer + 容错重试”的 Agent 设计。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TypedDict, Literal
import logging
import json
import re

from services.parser import PPTParser
from services.knowledge_expander import KnowledgeExpander
from services.search_service import SearchService
from services.reference_parser import ReferenceParser
from services.export_service import ExportService, export_service as default_export_service
from utils.llm_factory import create_llm
from utils.prompts import (
    get_search_decision_prompt,
    get_check_layer_prompt,
    get_repair_expansion_prompt,
)

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

ReferenceFilesStore = Dict[str, Dict[str, Any]]


class ExpandWorkflowState(TypedDict, total=False):
    # input
    title: str
    content: str
    context: Dict[str, Any] | None
    reference_file_ids: List[str] | None
    reference_files_store: ReferenceFilesStore | None
    validate: bool
    max_attempts: int

    # derived
    reference_contents: List[Dict[str, Any]]
    reference_files_used: List[str]
    reference_excerpt: str
    has_reference: bool

    use_search: bool
    search_reason: str

    attempt: int
    expanded_content: Dict[str, Any]

    check: Dict[str, Any]
    check_passed: bool

    next_action: Literal["done", "enable_search", "repair", "fail"]
    error_message: str


class PPTExtensionAgent:
    """
    PPT内容扩展智能体（工作流编排）

核心目标：
- 把“解析 / 参考文件选择 / 扩充 / 多源搜索 / 导出”等步骤组合成一条一致的工作流；
- 让 `api/routes.py` 仅负责入参校验与响应，不再承载复杂业务逻辑。
    """

    def __init__(
        self,
        parser: Optional[PPTParser] = None,
        expander: Optional[KnowledgeExpander] = None,
        search_service: Optional[SearchService] = None,
        reference_parser: Optional[ReferenceParser] = None,
        export_service: Optional[ExportService] = None,
    ):
        self.parser = parser or PPTParser()
        self.expander = expander or KnowledgeExpander()
        self.search_service = search_service or SearchService()
        self.reference_parser = reference_parser or ReferenceParser()
        self.export_service = export_service or default_export_service

        # LLM用于“决策/校验/修复”节点（Check Layer 低温更稳）
        self.llm = create_llm(temperature=0.1)

        # 预编译 LangGraph 工作流（可复用）
        self._expand_graph = self._build_expand_graph()

    # -----------------------------
    # LangGraph: 构建扩充工作流图
    # -----------------------------
    def _build_expand_graph(self):
        g: StateGraph = StateGraph(ExpandWorkflowState)

        g.add_node("collect_references", self._node_collect_references)
        g.add_node("decide_search", self._node_decide_search)
        g.add_node("expand", self._node_expand)
        g.add_node("check", self._node_check)
        g.add_node("enable_search", self._node_enable_search)
        g.add_node("repair", self._node_repair)
        g.add_node("finalize_failure", self._node_finalize_failure)

        g.set_entry_point("collect_references")
        g.add_edge("collect_references", "decide_search")
        g.add_edge("decide_search", "expand")
        g.add_edge("expand", "check")

        def _route_after_check(state: ExpandWorkflowState) -> str:
            if state.get("check_passed"):
                return END
            if state.get("attempt", 0) >= state.get("max_attempts", 3):
                return "finalize_failure"
            return state.get("next_action", "repair")

        g.add_conditional_edges(
            "check",
            _route_after_check,
            {
                END: END,
                "enable_search": "enable_search",
                "repair": "repair",
                "finalize_failure": "finalize_failure",
                "fail": "finalize_failure",
            },
        )

        g.add_edge("enable_search", "expand")
        g.add_edge("repair", "check")
        g.add_edge("finalize_failure", END)

        return g.compile()

    # -----------------------------
    # LangGraph Nodes
    # -----------------------------
    def _node_collect_references(self, state: ExpandWorkflowState) -> ExpandWorkflowState:
        reference_contents, used_files = self._collect_reference_contents(
            reference_file_ids=state.get("reference_file_ids"),
            ppt_content=state.get("content", ""),
            reference_files_store=state.get("reference_files_store"),
        )

        # 生成摘录（供决策/校验/修复使用）
        excerpt_parts: List[str] = []
        for ref in reference_contents[:2]:
            filename = ref.get("filename", "未知文件")
            text = (ref.get("content") or "").strip()
            if len(text) > 1200:
                text = text[:1200] + "...（截断）"
            excerpt_parts.append(f"[{filename}]\n{text}")
        reference_excerpt = "\n\n---\n\n".join(excerpt_parts) if excerpt_parts else "无"

        return {
            **state,
            "reference_contents": reference_contents,
            "reference_files_used": used_files,
            "reference_excerpt": reference_excerpt,
            "has_reference": len(reference_contents) > 0,
            "attempt": state.get("attempt", 0),
        }

    def _node_decide_search(self, state: ExpandWorkflowState) -> ExpandWorkflowState:
        # 默认：无参考文件 -> 必搜；有参考文件 -> 由 LLM 决策
        if not state.get("has_reference"):
            return {
                **state,
                "use_search": True,
                "search_reason": "无参考文件，默认检索",
            }

        prompt = get_search_decision_prompt(
            title=state.get("title", ""),
            content=state.get("content", ""),
            context=json.dumps(state.get("context") or {}, ensure_ascii=False),
            reference_excerpt=state.get("reference_excerpt", "无"),
        )

        try:
            resp = self.llm.invoke(prompt)
            parsed = self._safe_parse_json_object(resp.content)
            use_search = bool(parsed.get("use_search", True))
            reason = str(parsed.get("reason", "")).strip()[:50] or "LLM决策"
        except Exception as e:
            logger.warning(f"决策节点失败，回退为 use_search=True: {str(e)}")
            use_search, reason = True, "决策失败回退检索"

        return {**state, "use_search": use_search, "search_reason": reason}

    def _node_expand(self, state: ExpandWorkflowState) -> ExpandWorkflowState:
        attempt = int(state.get("attempt", 0)) + 1
        logger.info(
            f"LANGGRAPH: expand attempt={attempt}/{state.get('max_attempts', 3)} use_search={state.get('use_search')}"
        )

        try:
            expanded = self.expander.expand_knowledge_point(
                title=state.get("title", ""),
                content=state.get("content", ""),
                context=state.get("context"),
                use_search=bool(state.get("use_search", True)),
                reference_contents=state.get("reference_contents") or None,
            )
        except Exception as e:
            # 容错：不要让异常中断工作流，交给 Check/重试策略兜底
            logger.error(f"expand 节点异常: {str(e)}")
            expanded = {
                "background": "",
                "principles": "",
                "formulas": "",
                "examples": "",
                "summary": f"扩展阶段出错：{str(e)}",
                "references": [],
            }

        return {**state, "attempt": attempt, "expanded_content": expanded}

    def _node_check(self, state: ExpandWorkflowState) -> ExpandWorkflowState:
        expansion_json = json.dumps(state.get("expanded_content") or {}, ensure_ascii=False)
        prompt = get_check_layer_prompt(
            original=state.get("content", ""),
            expansion_json=expansion_json,
            reference_excerpt=state.get("reference_excerpt", "无"),
            used_search=bool(state.get("use_search", False)),
        )

        try:
            resp = self.llm.invoke(prompt)
            check = self._safe_parse_json_object(resp.content)
        except Exception as e:
            logger.warning(f"Check Layer 调用失败: {str(e)}")
            check = {
                "is_relevant": False,
                "is_accurate": False,
                "is_consistent": False,
                "confidence": 0.0,
                "issues": [f"Check Layer 失败: {str(e)}"],
            }

        confidence = float(check.get("confidence", 0.0) or 0.0)
        passed = bool(check.get("is_relevant")) and bool(check.get("is_accurate")) and bool(
            check.get("is_consistent")
        ) and confidence >= 0.7

        # 失败时的下一步策略：
        # - 若用户提供参考文件且本次未检索，则先启用检索再试（一次）
        # - 否则走 repair 节点
        if passed:
            next_action: Literal["done", "enable_search", "repair", "fail"] = "done"
        else:
            if state.get("has_reference") and not state.get("use_search"):
                next_action = "enable_search"
            else:
                next_action = "repair"

        return {
            **state,
            "check": check,
            "check_passed": passed,
            "next_action": next_action,
        }

    def _node_enable_search(self, state: ExpandWorkflowState) -> ExpandWorkflowState:
        # 启用外部检索后重新 expand（attempt 会在 expand 节点自增）
        return {**state, "use_search": True, "search_reason": "Check 未通过，启用外部检索重试"}

    def _node_repair(self, state: ExpandWorkflowState) -> ExpandWorkflowState:
        """
        repair 节点：直接用“修复Prompt”产出新的 expanded_content，然后再次进入 check。
        attempt 在此也计入一次尝试（避免无限重试）。
        """
        attempt = int(state.get("attempt", 0)) + 1
        issues = state.get("check", {}).get("issues") or []
        if not isinstance(issues, list):
            issues = [str(issues)]

        prompt = get_repair_expansion_prompt(
            original=state.get("content", ""),
            previous_expansion_json=json.dumps(state.get("expanded_content") or {}, ensure_ascii=False),
            issues=[str(i) for i in issues][:8],
            reference_excerpt=state.get("reference_excerpt", "无"),
        )

        try:
            resp = self.llm.invoke(prompt)
            repaired = self._safe_parse_json_object(resp.content)
            repaired = self._normalize_expansion(repaired)
        except Exception as e:
            logger.warning(f"repair 节点失败，保留原输出: {str(e)}")
            repaired = state.get("expanded_content") or {}

        return {**state, "attempt": attempt, "expanded_content": repaired}

    def _node_finalize_failure(self, state: ExpandWorkflowState) -> ExpandWorkflowState:
        # 兜底：保证前端可展示，不至于 expanded_content 为空导致页面异常
        msg = "出错啦，请重新上传或更换更清晰的参考文件后再试。"
        fallback = {
            "background": "",
            "principles": "",
            "formulas": "",
            "examples": "",
            "summary": msg,
            "references": [],
        }
        return {
            **state,
            "error_message": msg,
            "expanded_content": fallback,
            "check_passed": False,
        }

    # -----------------------------
    # Helpers
    # -----------------------------
    def _safe_parse_json_object(self, text: str) -> Dict[str, Any]:
        """
        尝试从 LLM 输出中提取 JSON 对象并解析。
        """
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            pass
        # 去除可能的 ```json 包裹
        cleaned = re.sub(r"^```json\s*", "", text.strip())
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # 正则提取第一个对象
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return {}
        return json.loads(m.group(0))

    def _normalize_expansion(self, obj: Any) -> Dict[str, Any]:
        if not isinstance(obj, dict):
            return {
                "background": "",
                "principles": "",
                "formulas": "",
                "examples": "",
                "summary": str(obj),
                "references": [],
            }
        for k in ["background", "principles", "formulas", "examples", "summary"]:
            obj.setdefault(k, "")
        refs = obj.get("references", [])
        if not isinstance(refs, list):
            refs = []
        obj["references"] = refs
        return obj

    # -----------------------------
    # Workflow: PPT解析（上传/URL）
    # -----------------------------
    def parse_ppt_file(self, file_path: str) -> Dict[str, Any]:
        """解析本地 PPT 文件。"""
        return self.parser.parse_from_file(file_path)

    def parse_ppt_url(self, url: str, download_path: str = "./uploads") -> Dict[str, Any]:
        """下载并解析 PPT URL。"""
        return self.parser.parse_from_url(url, download_path=download_path)

    def try_vectorize_ppt(self, ppt_data: Dict[str, Any]) -> bool:
        """
        尝试向量化 PPT（Milvus 未启动/依赖缺失时自动降级）。
        """
        try:
            from utils.vector_db import VectorDB

            chunks = self.parser.extract_text_chunks(ppt_data)
            VectorDB().insert_chunks(chunks)
            logger.info(f"已向量化 {len(chunks)} 个文本切片")
            return True
        except Exception as e:
            logger.warning(f"向量化失败（可能 Milvus 未启动或依赖缺失）: {str(e)}")
            return False

    # ---------------------------------
    # Workflow: 参考文件 → 相关性筛选
    # ---------------------------------
    def _collect_reference_contents(
        self,
        reference_file_ids: Optional[List[str]],
        ppt_content: str,
        reference_files_store: Optional[ReferenceFilesStore],
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        从参考文件 store 中取回解析文本，并做相关性筛选。

        返回：
        - reference_contents: 传给 KnowledgeExpander 的结构
        - reference_files_used: 实际被采用的文件名列表
        """
        if not reference_file_ids or not reference_files_store:
            return [], []

        reference_contents: List[Dict[str, Any]] = []
        used_filenames: List[str] = []

        for ref_id in reference_file_ids:
            stored = reference_files_store.get(ref_id)
            if not stored:
                continue

            parsed = stored.get("parsed_data") or {}
            ref_content = parsed.get("content", "")

            try:
                is_relevant = self.reference_parser.is_relevant(ref_content, ppt_content)
            except Exception as e:
                logger.warning(f"参考文件相关性判断失败，默认视为相关: {str(e)}")
                is_relevant = True

            if not is_relevant:
                logger.info(f"参考文件 {parsed.get('filename', '')} 与PPT内容不相关，跳过")
                continue

            filename = parsed.get("filename") or stored.get("filename") or "unknown"
            reference_contents.append(
                {
                    "filename": filename,
                    "content": ref_content,
                    "chunks": parsed.get("chunks", []),
                }
            )
            used_filenames.append(filename)

        return reference_contents, used_filenames

    # -----------------------------
    # Workflow: 单点扩充（含可选验证）
    # -----------------------------
    def run_expand_workflow(
        self,
        *,
        title: str,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        reference_file_ids: Optional[List[str]] = None,
        reference_files_store: Optional[ReferenceFilesStore] = None,
        validate: bool = False,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        执行“扩充知识点”工作流（LangGraph 编排 + Check Layer + 容错重试）。
        """
        logger.info(f"WORKFLOW(langgraph): expand start title={title!r} validate={validate}")

        init_state: ExpandWorkflowState = {
            "title": title,
            "content": content,
            "context": context,
            "reference_file_ids": reference_file_ids,
            "reference_files_store": reference_files_store,
            "validate": validate,
            "max_attempts": max_attempts,
            "attempt": 0,
        }

        try:
            final_state: ExpandWorkflowState = self._expand_graph.invoke(init_state)
        except Exception as e:
            # 极端容错：LangGraph 执行本身异常（例如依赖/运行时问题）
            logger.error(f"LangGraph 执行失败: {str(e)}")
            final_state = {
                **init_state,
                "attempt": init_state.get("attempt", 0),
                "check_passed": False,
                "expanded_content": {
                    "background": "",
                    "principles": "",
                    "formulas": "",
                    "examples": "",
                    "summary": "出错啦，请重新上传或稍后重试。",
                    "references": [],
                },
                "reference_files_used": [],
                "check": {"issues": [f"LangGraph 执行失败: {str(e)}"], "confidence": 0.0},
            }
        expanded_content = self._normalize_expansion(final_state.get("expanded_content") or {})
        passed = bool(final_state.get("check_passed"))

        # 统一返回结构，保证前端稳定
        base: Dict[str, Any] = {
            "title": title,
            "original_content": content,
            "expanded_content": expanded_content,
            "reference_files_used": final_state.get("reference_files_used", []),
            "status": "success" if passed else "failed",
            "attempts": final_state.get("attempt", 0),
        }

        # /expand-with-validation 需要额外返回校验信息
        if validate:
            base["validation"] = final_state.get("check", {})
        return base

    # -----------------------------
    # Workflow: 批量扩充
    # -----------------------------
    def run_batch_expand_workflow(self, knowledge_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行“批量扩充”工作流（与 `POST /api/v1/batch-expand` 对齐）。

        说明：当前批量接口入参里不携带参考文件ID，因此这里保持与原实现一致，直接调用 expander.batch_expand。
        若要支持“每个知识点绑定参考文件”，建议扩展接口模型后再增强本工作流。
        """
        results = self.expander.batch_expand(knowledge_points)
        success_count = sum(1 for r in results if r.get("status") == "success")
        return {
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
            "results": results,
        }

    # -----------------------------
    # Workflow: 导出
    # -----------------------------
    def run_export_workflow(
        self,
        *,
        ppt_data: Dict[str, Any],
        expanded_data: Dict[str, Any],
        export_format: str = "markdown",
        page_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        执行导出工作流（底层调用 ExportService）。
        """
        markdown_content = self.export_service.export_to_markdown(
            ppt_data=ppt_data, expanded_data=expanded_data, page_number=page_number
        )

        if export_format.lower() == "markdown":
            return {"format": "markdown", "content": markdown_content}

        if export_format.lower() == "pdf":
            # 这里只负责生成 markdown，PDF 文件写入/命名由 API 路由层统一处理更合适
            return {"format": "pdf", "content": markdown_content}

        raise ValueError(f"不支持的导出格式: {export_format}")
