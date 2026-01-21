from __future__ import annotations
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import AsyncGraphDatabase
from redis.asyncio import Redis
from ulid import ULID

from app.config import settings
from app.models import ExpandRequest, GenerateRequest, GenerateResponse, GraphResult, JobStatus
from app.services.orchestrator import Orchestrator
from app.storage.neo4j_store import Neo4jStore
from app.storage.redis_store import RedisStore


def create_app() -> FastAPI:
    app = FastAPI(title="Cross-Disciplinary Knowledge Graph Agent", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=False)
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        app.state.redis = redis
        app.state.neo4j_driver = driver
        app.state.redis_store = RedisStore(redis)
        app.state.neo4j_store = Neo4jStore(driver)
        app.state.orchestrator = Orchestrator(app.state.redis_store, app.state.neo4j_store)

        await app.state.neo4j_store.init_schema()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        redis: Redis = app.state.redis
        driver = app.state.neo4j_driver
        await redis.aclose()
        await driver.close()

    def _new_job_id() -> str:
        return str(ULID())

    async def _run_generate(job_id: str, req: GenerateRequest) -> None:
        orch: Orchestrator = app.state.orchestrator
        store: RedisStore = app.state.redis_store
        try:
            await orch.generate_graph(
                job_id=job_id,
                concept=req.concept,
                domains=req.domains,
                depth=req.depth,
                strict_check=req.strict_check,
            )
        except Exception as e:
            await store.log(job_id, f"[Error] {type(e).__name__}: {e}")
            await store.set_status(job_id, status="failed", progress=100, message="Failed")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "env": settings.app_env}

    @app.post("/api/graph/generate", response_model=GenerateResponse)
    async def generate(req: GenerateRequest, bg: BackgroundTasks) -> GenerateResponse:
        job_id = _new_job_id()
        store: RedisStore = app.state.redis_store
        await store.create_job(job_id, req.concept)
        bg.add_task(_run_generate, job_id, req)
        return GenerateResponse(job_id=job_id)

    @app.get("/api/job/{job_id}", response_model=JobStatus)
    async def get_job(job_id: str) -> JobStatus:
        store: RedisStore = app.state.redis_store
        job = await store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.get("/api/graph/{concept}", response_model=GraphResult)
    async def get_graph(concept: str, depth: int = 2, version: str = "v1") -> GraphResult:
        neo: Neo4jStore = app.state.neo4j_store
        nodes, edges = await neo.query_subgraph(concept=concept, depth=depth, version=version)
        if not nodes:
            raise HTTPException(status_code=404, detail="graph not found in Neo4j (generate first)")

        # Minimal meta for query results
        from app.models import CheckerSummary, Meta, utc_now_iso

        return GraphResult(
            concept=concept,
            nodes=nodes,
            edges=edges,
            meta=Meta(generated_at=utc_now_iso(), version=version, checker_summary=CheckerSummary()),
        )

    @app.post("/api/graph/expand", response_model=GraphResult)
    async def expand(req: ExpandRequest) -> GraphResult:
        """
        Demo expand:
        - Fetch the node from Neo4j (if exists), and run a small generate for that node's name as a "new concept"
        - Persist and return the expanded subgraph of that new concept
        """
        neo: Neo4jStore = app.state.neo4j_store

        node = await neo.get_node(req.node_id)
        if not node:
            raise HTTPException(status_code=404, detail="node not found")

        # Synchronous expand to simplify UI: run pipeline directly (small)
        job_id = _new_job_id()
        store: RedisStore = app.state.redis_store
        await store.create_job(job_id, node.name)
        orch: Orchestrator = app.state.orchestrator
        await orch.generate_graph(job_id=job_id, concept=node.name, domains=None, depth=1 + req.depth_increment, strict_check=True)

        # Return subgraph for expanded concept
        nodes, edges = await neo.query_subgraph(concept=node.name, depth=2, version="v1")
        from app.models import CheckerSummary, Meta, utc_now_iso

        return GraphResult(
            concept=node.name,
            nodes=nodes,
            edges=edges,
            meta=Meta(generated_at=utc_now_iso(), version="v1", checker_summary=CheckerSummary()),
        )

    @app.get("/api/history")
    async def history() -> list[dict[str, Any]]:
        store: RedisStore = app.state.redis_store
        return await store.get_history()

    return app


app = create_app()

