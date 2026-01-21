from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from app.models import GraphResult, JobStatus, utc_now_iso


@dataclass
class RedisStore:
    redis: Redis

    async def create_job(self, job_id: str, concept: str) -> None:
        now = utc_now_iso()
        key = f"job:{job_id}"
        await self.redis.hset(
            key,
            mapping={
                "status": "queued",
                "progress": 0,
                "concept": concept,
                "message": "",
                "created_at": now,
                "updated_at": now,
            },
        )
        await self.redis.delete(f"{key}:logs", f"{key}:result")
        await self.redis.lpush("history", json.dumps({"job_id": job_id, "concept": concept, "ts": now}))
        await self.redis.ltrim("history", 0, 49)

    async def log(self, job_id: str, msg: str) -> None:
        key = f"job:{job_id}"
        await self.redis.rpush(f"{key}:logs", msg)
        await self.redis.hset(key, mapping={"updated_at": utc_now_iso()})

    async def set_status(self, job_id: str, *, status: str, progress: int | None = None, message: str | None = None) -> None:
        key = f"job:{job_id}"
        mapping: dict[str, Any] = {"status": status, "updated_at": utc_now_iso()}
        if progress is not None:
            mapping["progress"] = int(progress)
        if message is not None:
            mapping["message"] = message
        await self.redis.hset(key, mapping=mapping)

    async def set_result(self, job_id: str, result: GraphResult) -> None:
        key = f"job:{job_id}"
        await self.redis.set(f"{key}:result", result.model_dump_json())
        await self.redis.hset(key, mapping={"updated_at": utc_now_iso()})

    async def get_job(self, job_id: str) -> JobStatus | None:
        key = f"job:{job_id}"
        data = await self.redis.hgetall(key)
        if not data:
            return None

        logs_raw = await self.redis.lrange(f"{key}:logs", 0, -1)
        logs = [x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else str(x) for x in logs_raw]

        result_raw = await self.redis.get(f"{key}:result")
        result: GraphResult | None = None
        if result_raw:
            s = result_raw.decode("utf-8") if isinstance(result_raw, (bytes, bytearray)) else str(result_raw)
            result = GraphResult.model_validate_json(s)

        def _get(field: str, default: str = "") -> str:
            v = data.get(field.encode("utf-8"))
            if v is None:
                return default
            return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)

        def _get_int(field: str, default: int = 0) -> int:
            try:
                return int(_get(field, str(default)) or default)
            except ValueError:
                return default

        return JobStatus(
            job_id=job_id,
            status=_get("status", "queued"),  # type: ignore[arg-type]
            progress=_get_int("progress", 0),
            concept=_get("concept", ""),
            message=_get("message", "") or None,
            logs=logs,
            result=result,
            created_at=_get("created_at", utc_now_iso()),
            updated_at=_get("updated_at", utc_now_iso()),
        )

    async def get_history(self) -> list[dict[str, Any]]:
        raw = await self.redis.lrange("history", 0, 49)
        out: list[dict[str, Any]] = []
        for x in raw:
            s = x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else str(x)
            try:
                out.append(json.loads(s))
            except Exception:
                continue
        return out

