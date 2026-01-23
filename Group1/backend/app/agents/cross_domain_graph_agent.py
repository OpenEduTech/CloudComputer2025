from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypedDict

from langgraph.graph import StateGraph

from app.config import settings
from app.tools.seed_corpus import DEFAULT_DOMAINS
from app.tools.schema_validate import validate_graph, light_fix
from app.tools.multi_retriever import multi_retrieve, to_dicts
from app.agents.llm_client import chat_json


class AgentState(TypedDict, total=False):
    concept: str
    domains: list[str]
    depth: int
    strict_check: bool

    domain_queries: dict[str, list[str]]
    passages_by_domain: dict[str, list[dict[str, Any]]]
    graph_dict: dict[str, Any]
    schema_fixed: int


LogFn = Callable[[str], None]


def _default_domains(domains: list[str] | None) -> list[str]:
    return domains or DEFAULT_DOMAINS


def _plan_node(log: LogFn):
    def _node(state: AgentState) -> AgentState:
        concept = state["concept"]
        domains = state["domains"]
        log(f"[Planner/LLM] concept={concept} domains={domains}")

        system = "You are a cross-domain planner. Return ONLY a JSON object."
        payload = {
            "concept": concept,
            "domains": domains,
            "output_format": {"domains": {"Domain": ["query1", "query2", "query3"]}},
            "requirements": [
                "For EACH domain, output 3-6 related concepts/bridge concepts.",
                "Prefer textbook keywords; can include bilingual hint in parentheses.",
                "Do NOT repeat the same query across domains.",
                "Keep queries short (<= 8 words).",
            ],
        }
        obj = chat_json(system, payload, temperature=0.2)
        dom = obj.get("domains", {})
        if not isinstance(dom, dict):
            raise ValueError("Planner output missing 'domains' object")

        domain_queries: dict[str, list[str]] = {}
        for d in domains:
            xs = dom.get(d, [])
            if not isinstance(xs, list) or not xs:
                xs = [concept]
            domain_queries[d] = [str(x) for x in xs[:6]]
            log(f"[Planner/LLM] {d} queries={domain_queries[d]}")

        state["domain_queries"] = domain_queries
        return state

    return _node


def _retrieve_node(log: LogFn):
    def _node(state: AgentState) -> AgentState:
        concept = state["concept"]
        domains = state["domains"]
        domain_queries = state.get("domain_queries") or {d: [concept] for d in domains}

        if not settings.enable_wiki:
            log("[Retriever] WARNING: ENABLE_WIKI=0. Wikipedia evidence will be unavailable.")
        if not settings.enable_arxiv:
            log("[Retriever] INFO: ENABLE_ARXIV=0. arXiv evidence disabled.")

        out: dict[str, list[dict[str, Any]]] = {}
        for d in domains:
            queries = [str(x) for x in (domain_queries.get(d) or [concept])][:6]
            passages = multi_retrieve(domain=d, queries=queries, max_per_source=2)
            out[d] = to_dicts(passages)
            # log sources breakdown
            counts: dict[str, int] = {}
            for p in passages:
                counts[p.source] = counts.get(p.source, 0) + 1
            log(f"[Retriever] {d}: {len(passages)} passages sources={counts} (queries={len(queries)})")

        state["passages_by_domain"] = out
        return state

    return _node


def _extract_node(log: LogFn):
    def _node(state: AgentState) -> AgentState:
        concept = state["concept"]
        domains = state["domains"]
        passages_by_domain = state.get("passages_by_domain") or {}

        system = (
            "You are an information extraction agent that MUST output a JSON graph. "
            "Return ONLY a JSON object. Do not include markdown."
        )
        payload = {
            "concept": concept,
            "domains": domains,
            "passages_by_domain": passages_by_domain,
            "schema": {
                "concept": "string",
                "nodes": [
                    {"id": "string", "name": "string", "domain": "string", "definition": "string|null", "confidence": "0..1"}
                ],
                "edges": [
                    {
                        "id": "string|null",
                        "source": "node.id",
                        "target": "node.id",
                        "relation": "one of related_to/used_in/is_a/explains/bridges",
                        "explanation": "string",
                        "evidence": {"title": "string", "snippet": "string", "url": "string|null", "domain": "string|null"},
                        "confidence": "0..1",
                        "checked": "boolean",
                        "check_reason": "string|null",
                        "flags": "string[]",
                    }
                ],
                "meta": {"generated_at": "ISO string", "version": "v1", "checker_summary": "object"},
            },
            "requirements": [
                "Must include the central concept as a node in domain 'Core'.",
                "Must include at least 4 domains in nodes.",
                "Edges must include evidence.title and evidence.snippet; snippet should mention BOTH endpoint names.",
                "Use bridges edges to connect distant domains via 1-2 bridge concepts.",
                "Prefer concise, readable node ids. Example: 'mathematics:recurrence_relation'.",
            ],
        }
        graph = chat_json(system, payload, temperature=0.1)
        state["graph_dict"] = graph
        log(f"[Extractor/LLM] produced graph: nodes={len(graph.get('nodes', []))} edges={len(graph.get('edges', []))}")
        return state

    return _node


def _validate_node(log: LogFn):
    def _node(state: AgentState) -> AgentState:
        g = state.get("graph_dict") or {}
        ok, errors = validate_graph(g)
        fixed_total = 0
        if not ok:
            log(f"[Schema] invalid: {len(errors)} errors; applying light_fix")
            g, fixed = light_fix(g, errors)
            fixed_total += fixed
            ok2, errors2 = validate_graph(g)
            if not ok2:
                log(f"[Schema] still invalid after light_fix: {len(errors2)} errors")
        else:
            log("[Schema] ok")
        state["graph_dict"] = g
        state["schema_fixed"] = fixed_total
        return state

    return _node


@dataclass
class CrossDomainGraphAgent:
    log: LogFn

    def run(self, *, concept: str, domains: list[str] | None, depth: int, strict_check: bool) -> tuple[dict[str, Any], int]:
        if settings.llm_provider != "openai_compat":
            raise RuntimeError("LLM_PROVIDER must be 'openai_compat' for real agent mode")
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for real agent mode")

        sg: StateGraph[AgentState] = StateGraph(AgentState)
        sg.add_node("plan", _plan_node(self.log))
        sg.add_node("retrieve", _retrieve_node(self.log))
        sg.add_node("extract", _extract_node(self.log))
        sg.add_node("validate", _validate_node(self.log))

        sg.set_entry_point("plan")
        sg.add_edge("plan", "retrieve")
        sg.add_edge("retrieve", "extract")
        sg.add_edge("extract", "validate")
        sg.set_finish_point("validate")

        app = sg.compile()

        init: AgentState = {
            "concept": concept,
            "domains": _default_domains(domains),
            "depth": depth,
            "strict_check": strict_check,
        }
        out = app.invoke(init)
        graph_dict = out.get("graph_dict") or {}
        schema_fixed = int(out.get("schema_fixed") or 0)

        # Attach agent trace for frontend visualization
        try:
            meta = graph_dict.get("meta") if isinstance(graph_dict.get("meta"), dict) else {}
            if not isinstance(meta, dict):
                meta = {}
            meta["agent_trace"] = {
                "domains": out.get("domain_queries") or {},
                "passages_by_domain": out.get("passages_by_domain") or {},
            }
            graph_dict["meta"] = meta
        except Exception:
            pass

        return graph_dict, schema_fixed

