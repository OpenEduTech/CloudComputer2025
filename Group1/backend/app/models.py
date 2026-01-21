from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
import hashlib

from pydantic import BaseModel, Field


RelationType = Literal["related_to", "used_in", "is_a", "explains", "bridges"]


class Evidence(BaseModel):
    title: str
    snippet: str
    url: str | None = None
    domain: str | None = None


class Node(BaseModel):
    id: str
    name: str
    domain: str
    definition: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.75)


class Edge(BaseModel):
    id: str | None = None
    source: str
    target: str
    relation: RelationType
    explanation: str
    evidence: Evidence
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    checked: bool = True
    check_reason: str | None = None
    flags: list[str] = Field(default_factory=list)

    def ensure_id(self) -> None:
        if self.id:
            return
        s = f"{self.source}|{self.relation}|{self.target}".encode("utf-8", "ignore")
        self.id = hashlib.sha1(s).hexdigest()[:12]


class CheckerSummary(BaseModel):
    # schema
    schema_fixed: int = 0
    # evidence check stats
    edges_checked: int = 0
    edges_failed: int = 0
    edges_downgraded: int = 0
    # dedup/merge stats
    dedup_nodes_merged: int = 0
    dedup_edges_removed: int = 0
    conflicts_flagged: int = 0
    # keep compatibility
    passed: int = 0
    failed: int = 0


class Meta(BaseModel):
    generated_at: str
    version: str
    checker_summary: CheckerSummary
    agent_trace: dict[str, Any] | None = None


class GraphResult(BaseModel):
    concept: str
    nodes: list[Node]
    edges: list[Edge]
    meta: Meta


class GenerateRequest(BaseModel):
    concept: str = Field(min_length=1, max_length=80)
    domains: list[str] | None = None
    depth: int = Field(default=2, ge=1, le=3)
    strict_check: bool = True


class GenerateResponse(BaseModel):
    job_id: str


class ExpandRequest(BaseModel):
    node_id: str
    depth_increment: int = Field(default=1, ge=1, le=2)


class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    progress: int = Field(ge=0, le=100, default=0)
    concept: str
    message: str | None = None
    logs: list[str] = Field(default_factory=list)
    result: GraphResult | None = None
    created_at: str
    updated_at: str


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def stable_version() -> str:
    # simple versioning; can be replaced by timestamp/semantic later
    return "v1"

