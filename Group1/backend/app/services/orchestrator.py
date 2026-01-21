from __future__ import annotations

from dataclasses import dataclass

from app.models import CheckerSummary, GraphResult, Meta, stable_version, utc_now_iso
from app.storage.neo4j_store import Neo4jStore
from app.storage.redis_store import RedisStore
from app.config import settings
from app.tools import checker, extract, merge, retrieval
from app.tools.planner import plan as plan_queries
from app.agents.cross_domain_graph_agent import CrossDomainGraphAgent
from app.tools.seed_corpus import Passage
from app.tools import schema_validate


@dataclass
class Orchestrator:
    redis_store: RedisStore
    neo4j_store: Neo4jStore

    async def generate_graph(self, *, job_id: str, concept: str, domains: list[str] | None, depth: int, strict_check: bool) -> GraphResult:
        await self.redis_store.set_status(job_id, status="running", progress=5, message="Planning")
        await self.redis_store.log(job_id, f"[Planner] concept={concept} depth={depth}")

        # Real agent mode (LangGraph + OpenAI-compatible)
        if settings.llm_provider == "openai_compat":
            await self.redis_store.set_status(job_id, status="running", progress=10, message="Agent planning/retrieval/extraction")

            logs: list[str] = []
            def _log(msg: str) -> None:
                logs.append(msg)

            agent = CrossDomainGraphAgent(log=_log)
            graph_dict, schema_fixed = agent.run(concept=concept, domains=domains, depth=depth, strict_check=strict_check)

            for m in logs:
                await self.redis_store.log(job_id, m)

            graph = GraphResult.model_validate(graph_dict)
            graph.meta.checker_summary.schema_fixed += int(schema_fixed)

            # merge/dedup + check layer + persist
            await self.redis_store.set_status(job_id, status="running", progress=65, message="Merge & de-dup")
            merged_nodes, merged_edges, mstats = merge.merge_synonyms(graph.nodes, graph.edges)
            graph.nodes = merged_nodes
            graph.edges = merged_edges
            graph.meta.checker_summary.dedup_nodes_merged += mstats.nodes_merged
            graph.meta.checker_summary.dedup_edges_removed += mstats.edges_removed
            graph.meta.checker_summary.conflicts_flagged += mstats.conflicts_flagged
            await self.redis_store.log(job_id, f"[Merge] nodes={len(graph.nodes)} edges={len(graph.edges)}")

            await self.redis_store.set_status(job_id, status="running", progress=75, message="Checking")
            graph = checker.run_check(graph, strict=strict_check)
            await self.redis_store.log(job_id, f"[Check] passed={graph.meta.checker_summary.passed} failed={graph.meta.checker_summary.failed}")

            await self.redis_store.set_status(job_id, status="running", progress=85, message="Persisting")
            await self.neo4j_store.upsert_graph(graph)
            await self.redis_store.log(job_id, "[Persist] upserted into Neo4j")

            await self.redis_store.log(
                job_id,
                "[Summary] "
                f"schema_fixed={graph.meta.checker_summary.schema_fixed} "
                f"dedup_nodes_merged={graph.meta.checker_summary.dedup_nodes_merged} "
                f"dedup_edges_removed={graph.meta.checker_summary.dedup_edges_removed} "
                f"conflicts_flagged={graph.meta.checker_summary.conflicts_flagged} "
                f"edges_checked={graph.meta.checker_summary.edges_checked} "
                f"edges_failed={graph.meta.checker_summary.edges_failed} "
                f"edges_downgraded={graph.meta.checker_summary.edges_downgraded}"
            )

            await self.redis_store.set_result(job_id, graph)
            await self.redis_store.set_status(job_id, status="succeeded", progress=100, message="Done")
            return graph

        selected_domains = retrieval.domains_or_default(domains)
        await self.redis_store.log(job_id, f"[Planner] domains={selected_domains}")
        domain_queries = plan_queries(concept, selected_domains)
        for d in selected_domains:
            await self.redis_store.log(job_id, f"[Planner] {d} queries={domain_queries.get(d, [])}")
        await self.redis_store.set_status(job_id, status="running", progress=10, message="Retrieving")

        passages_by_domain: dict[str, list[Passage]] = {}
        for i, d in enumerate(selected_domains):
            queries = domain_queries.get(d) or [concept]
            seen_titles: set[str] = set()
            ps_all: list[Passage] = []
            for q in queries:
                ps = await retrieval.search(d, q)
                for p in ps:
                    key = (p.title or "").strip().lower()
                    if key and key in seen_titles:
                        continue
                    if key:
                        seen_titles.add(key)
                    ps_all.append(p)
            passages_by_domain[d] = ps_all
            await self.redis_store.log(job_id, f"[Retrieve] {d}: {len(ps_all)} passages (queries={len(queries)})")
            await self.redis_store.set_status(job_id, status="running", progress=min(30, 10 + (i + 1) * 4), message="Retrieving")

        passages = retrieval.flatten(passages_by_domain)
        await self.redis_store.set_status(job_id, status="running", progress=35, message="Extracting")

        ex = extract.graph_from_passages(concept, passages)
        await self.redis_store.log(job_id, f"[Extract] nodes={len(ex.nodes)} edges={len(ex.edges)}")

        await self.redis_store.set_status(job_id, status="running", progress=50, message="Bridge discovery")
        ex2 = extract.bridge_discovery(ex)
        await self.redis_store.log(job_id, f"[Bridge] nodes={len(ex2.nodes)} edges={len(ex2.edges)}")

        await self.redis_store.set_status(job_id, status="running", progress=65, message="Merge & de-dup")
        merged_nodes, merged_edges, mstats = merge.merge_synonyms(ex2.nodes, ex2.edges)
        await self.redis_store.log(
            job_id,
            f"[Merge] nodes={len(merged_nodes)} edges={len(merged_edges)} "
            f"(nodes_merged={mstats.nodes_merged} edges_removed={mstats.edges_removed} conflicts={mstats.conflicts_flagged})",
        )

        # Build dict first, validate schema, fix, then re-validate and hydrate model
        graph_dict = {
            "concept": concept,
            "nodes": [n.model_dump(mode="json") for n in merged_nodes],
            "edges": [e.model_dump(mode="json") for e in merged_edges],
            "meta": {
                "generated_at": utc_now_iso(),
                "version": stable_version(),
                "checker_summary": CheckerSummary(
                    dedup_nodes_merged=mstats.nodes_merged,
                    dedup_edges_removed=mstats.edges_removed,
                    conflicts_flagged=mstats.conflicts_flagged,
                ).model_dump(mode="json"),
            },
        }

        await self.redis_store.set_status(job_id, status="running", progress=70, message="Schema validate")
        ok, errors = schema_validate.validate_graph(graph_dict)
        schema_fixed = 0
        if not ok:
            await self.redis_store.log(job_id, f"[Schema] invalid: {len(errors)} errors")
            for err in errors[:10]:
                await self.redis_store.log(job_id, f"[Schema][err] {err}")
            graph_dict, schema_fixed = schema_validate.light_fix(graph_dict, errors)
            await self.redis_store.log(job_id, f"[Schema] light_fix applied: schema_fixed={schema_fixed}")
            ok2, errors2 = schema_validate.validate_graph(graph_dict)
            if not ok2:
                await self.redis_store.log(job_id, f"[Schema] still invalid after light_fix: {len(errors2)} errors")
                # Optional: LLM fix hook (kept offline by default)
                graph_dict = await schema_validate.llm_fix(graph_dict, errors2)
                ok3, errors3 = schema_validate.validate_graph(graph_dict)
                if not ok3:
                    await self.redis_store.log(job_id, f"[Schema] still invalid after llm_fix: {len(errors3)} errors")
        else:
            await self.redis_store.log(job_id, "[Schema] ok")

        graph = GraphResult.model_validate(graph_dict)
        graph.meta.checker_summary.schema_fixed += schema_fixed

        await self.redis_store.set_status(job_id, status="running", progress=75, message="Checking")
        graph = checker.run_check(graph, strict=strict_check)
        await self.redis_store.log(
            job_id,
            f"[Check] passed={graph.meta.checker_summary.passed} failed={graph.meta.checker_summary.failed}",
        )

        await self.redis_store.set_status(job_id, status="running", progress=85, message="Persisting")
        await self.neo4j_store.upsert_graph(graph)
        await self.redis_store.log(job_id, "[Persist] upserted into Neo4j")

        await self.redis_store.log(
            job_id,
            "[Summary] "
            f"schema_fixed={graph.meta.checker_summary.schema_fixed} "
            f"dedup_nodes_merged={graph.meta.checker_summary.dedup_nodes_merged} "
            f"dedup_edges_removed={graph.meta.checker_summary.dedup_edges_removed} "
            f"conflicts_flagged={graph.meta.checker_summary.conflicts_flagged} "
            f"edges_checked={graph.meta.checker_summary.edges_checked} "
            f"edges_failed={graph.meta.checker_summary.edges_failed} "
            f"edges_downgraded={graph.meta.checker_summary.edges_downgraded}"
        )

        await self.redis_store.set_result(job_id, graph)
        await self.redis_store.set_status(job_id, status="succeeded", progress=100, message="Done")
        return graph

