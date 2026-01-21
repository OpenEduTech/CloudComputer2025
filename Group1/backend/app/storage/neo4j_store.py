from __future__ import annotations

from dataclasses import dataclass

from neo4j import AsyncDriver

from app.models import Edge, Evidence, GraphResult, Node


@dataclass
class Neo4jStore:
    driver: AsyncDriver

    async def init_schema(self) -> None:
        cypher = """
        CREATE CONSTRAINT concept_id IF NOT EXISTS
        FOR (c:Concept) REQUIRE c.id IS UNIQUE
        """
        async with self.driver.session() as session:
            await session.run(cypher)

    async def upsert_graph(self, graph: GraphResult) -> None:
        async with self.driver.session() as session:
            # nodes
            for n in graph.nodes:
                is_root = n.domain == "Core" and n.name.strip().lower() == graph.concept.strip().lower()
                await session.run(
                    """
                    MERGE (c:Concept {id: $id})
                    SET c.name=$name, c.domain=$domain, c.definition=$definition,
                        c.confidence=$confidence, c.version=$version, c.concept=$concept,
                        c.root=$root
                    """,
                    id=n.id,
                    name=n.name,
                    domain=n.domain,
                    definition=n.definition,
                    confidence=n.confidence,
                    version=graph.meta.version,
                    concept=graph.concept,
                    root=is_root,
                )

            # edges
            for e in graph.edges:
                e.ensure_id()
                await session.run(
                    """
                    MATCH (a:Concept {id: $source})
                    MATCH (b:Concept {id: $target})
                    MERGE (a)-[r:REL {source: $source, target: $target, relation: $relation, version: $version, concept: $concept}]->(b)
                    SET r.explanation=$explanation,
                        r.edge_id=$edge_id,
                        r.flags=$flags,
                        r.check_reason=$check_reason,
                        r.evidence_title=$evidence_title,
                        r.evidence_url=$evidence_url,
                        r.evidence_snippet=$evidence_snippet,
                        r.evidence_domain=$evidence_domain,
                        r.confidence=$confidence,
                        r.checked=$checked
                    """,
                    source=e.source,
                    target=e.target,
                    relation=e.relation,
                    version=graph.meta.version,
                    concept=graph.concept,
                    explanation=e.explanation,
                    edge_id=e.id,
                    flags=e.flags,
                    check_reason=e.check_reason,
                    evidence_title=e.evidence.title,
                    evidence_url=e.evidence.url,
                    evidence_snippet=e.evidence.snippet,
                    evidence_domain=e.evidence.domain,
                    confidence=e.confidence,
                    checked=e.checked,
                )

    async def get_node(self, node_id: str) -> Node | None:
        cypher = "MATCH (c:Concept {id: $id}) RETURN c LIMIT 1"
        async with self.driver.session() as session:
            res = await session.run(cypher, id=node_id)
            row = await res.single()
            if not row:
                return None
            c = row["c"]
            return Node(
                id=c.get("id"),
                name=c.get("name"),
                domain=c.get("domain"),
                definition=c.get("definition"),
                confidence=float(c.get("confidence") or 0.7),
            )

    async def query_subgraph(self, *, concept: str, depth: int = 2, version: str = "v1") -> tuple[list[Node], list[Edge]]:
        # Query by concept field as a lightweight "root" filter (good enough for demo).
        # Depth is approximated by limiting path length.
        # Neo4j does not allow parameterized variable-length patterns (e.g. *0..$depth),
        # so we clamp and inline the integer.
        depth_i = max(0, min(int(depth), 3))
        cypher = f"""
        MATCH (root:Concept {{concept: $concept, version: $version, root: true}})
        CALL {{
          WITH root
          MATCH p=(root)-[r:REL*0..{depth_i}]->(n:Concept)
          WITH collect(p) as ps
          UNWIND ps as p
          UNWIND nodes(p) as nn
          RETURN collect(DISTINCT nn) as ns
        }}
        CALL {{
          WITH root
          MATCH p=(root)-[r:REL*0..{depth_i}]->(n:Concept)
          UNWIND relationships(p) as rr
          RETURN collect(DISTINCT rr) as rs
        }}
        RETURN ns, rs
        """
        async with self.driver.session() as session:
            res = await session.run(cypher, concept=concept, version=version)
            row = await res.single()
            if not row:
                return ([], [])

            ns = row["ns"] or []
            rs = row["rs"] or []

            nodes: list[Node] = []
            for n in ns:
                nodes.append(
                    Node(
                        id=n.get("id"),
                        name=n.get("name"),
                        domain=n.get("domain"),
                        definition=n.get("definition"),
                        confidence=float(n.get("confidence") or 0.7),
                    )
                )

            edges: list[Edge] = []
            for r in rs:
                rel = r.get("relation") or "related_to"
                if rel not in ("related_to", "used_in", "is_a", "explains", "bridges"):
                    rel = "related_to"
                edges.append(
                    Edge(
                        id=r.get("edge_id"),
                        source=r.get("source"),
                        target=r.get("target"),
                        relation=rel,  # type: ignore[arg-type]
                        explanation=r.get("explanation") or "",
                        evidence=Evidence(
                            title=r.get("evidence_title") or "",
                            snippet=r.get("evidence_snippet") or "",
                            url=r.get("evidence_url"),
                            domain=r.get("evidence_domain"),
                        ),
                        confidence=float(r.get("confidence") or 0.7),
                        checked=bool(r.get("checked")) if r.get("checked") is not None else False,
                        check_reason=r.get("check_reason"),
                        flags=list(r.get("flags") or []),
                    )
                )

            return nodes, edges

