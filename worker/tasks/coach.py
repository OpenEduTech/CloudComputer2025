import json
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from openai import OpenAI
from pymongo import MongoClient

from checkers.base import CheckStatus
from checkers.coach_check import CoachCheck
from checkers.gate import run_with_checker


MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "learning_agent")
KIMI_API_KEY = os.getenv("MOONSHOT_API_KEY")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")


def _get_db():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB_NAME]


def _mistakes_col(db):
    return db["mistakes"]


def _questions_col(db):
    return db["questions"]


def _coach_plans_col(db):
    return db["coach_plans"]


def _call_kimi(prompt: str) -> str:
    if not KIMI_API_KEY:
        raise RuntimeError("MOONSHOT_API_KEY is required for coach generation")
    client = OpenAI(api_key=KIMI_API_KEY, base_url="https://api.moonshot.cn/v1")
    resp = client.chat.completions.create(
        model=KIMI_MODEL,
        messages=[
            {"role": "system", "content": "You are a learning coach. Output JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _safe_object_id(s: str) -> Optional[ObjectId]:
    try:
        return ObjectId(s)
    except Exception:
        return None


def _fetch_question(db, question_id: str) -> Optional[Dict[str, Any]]:
    oid = _safe_object_id(question_id)
    if not oid:
        return None
    return _questions_col(db).find_one({"_id": oid})


def _aggregate_mistakes(
    db,
    student_id: str,
    notebook_id: Optional[str],
    material_id: Optional[str],
    days: int,
    top_k: int,
) -> Dict[str, Any]:
    """Aggregate mistakes into a coach-ready structured context."""

    query: Dict[str, Any] = {"student_id": student_id}
    if notebook_id:
        query["notebook_id"] = notebook_id

    since = datetime.utcnow() - timedelta(days=days)
    # last_wrong_at might be missing for old records; keep them as fallback
    query_with_time = dict(query)
    query_with_time["last_wrong_at"] = {"$gte": since}

    docs = list(
        _mistakes_col(db)
        .find(query_with_time)
        .sort([("wrong_count", -1), ("last_wrong_at", -1)])
        .limit(top_k * 3)
    )
    if not docs:
        # fallback: no time filter
        docs = list(
            _mistakes_col(db)
            .find(query)
            .sort([("wrong_count", -1), ("last_wrong_at", -1)])
            .limit(top_k * 3)
        )

    picked: List[Dict[str, Any]] = []
    examples: List[Dict[str, Any]] = []
    node_counter: Counter[str] = Counter()
    tag_counter: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()
    material_ids: List[str] = []

    for d in docs:
        qid = str(d.get("question_id"))
        q = _fetch_question(db, qid)
        if not q:
            continue

        # material scope filter
        if material_id:
            mids = [str(x) for x in (q.get("material_ids") or [])]
            if material_id not in mids:
                continue

        picked.append(d)
        # accumulate materials for one-click retrain
        for mid in (q.get("material_ids") or []):
            smid = str(mid)
            if smid and smid not in material_ids:
                material_ids.append(smid)
        # counters
        for nid in (q.get("node_ids") or []):
            snid = str(nid)
            if snid:
                node_counter[snid] += 1
        for t in (d.get("error_tags") or []):
            st = str(t)
            if st:
                tag_counter[st] += 1
        for mp in (d.get("missing_points") or []):
            smp = str(mp)
            if smp:
                missing_counter[smp] += 1

        if len(examples) < 5:
            examples.append(
                {
                    "question_id": qid,
                    "stem": q.get("stem"),
                    "wrong_count": int(d.get("wrong_count", 0) or 0),
                    "last_wrong_at": (d.get("last_wrong_at").isoformat() if d.get("last_wrong_at") else None),
                    "missing_points": d.get("missing_points") or [],
                    "error_tags": d.get("error_tags") or [],
                    "weak_node_ids": q.get("node_ids") or [],
                    "error_analysis": d.get("last_error_analysis") or "",
                }
            )

        if len(picked) >= top_k:
            break

    weak_node_ids = [nid for nid, _ in node_counter.most_common(3)]
    error_tags = [t for t, _ in tag_counter.most_common(8)]
    missing_points = [m for m, _ in missing_counter.most_common(10)]

    if material_id:
        material_ids = [material_id]
    else:
        material_ids = material_ids[:3]

    return {
        "weak_node_ids": weak_node_ids,
        "error_tags": error_tags,
        "missing_points": missing_points,
        "recent_mistakes_examples": examples,
        "material_ids": material_ids,
    }


def _build_prompt(ctx: Dict[str, Any]) -> str:
    """Prompt that forces grounded, structured coaching output."""

    schema_hint = {
        "diagnosis": {
            "summary": "string",
            "key_weak_node_ids": ["node_id"],
            "top_error_tags": ["tag"],
            "top_missing_points": ["point"],
        },
        "corrective_actions": [
            {
                "issue": "string",
                "how_to_fix": "string",
                "evidence": {
                    "missing_points": ["..."] ,
                    "error_tags": ["..."] ,
                    "weak_node_ids": ["..."] ,
                },
            }
        ],
        "practice_plan": [
            {
                "level": "L1|L2",
                "focus_node_ids": ["node_id"],
                "num_questions": 3,
                "notes": "string",
            }
        ],
        "one_click_practice": {
            "node_id": "node_id",
            "num_questions": 5,
            "difficulty_mix": {"L1": 0.6, "L2": 0.4},
            "type_mix": {"mcq": 0.6, "short": 0.4},
            "material_ids": ["material_id"],
        },
    }

    return (
        "你是学习小教练(Coach)。请基于给定的错题聚合信息，为学生生成‘小灶建议’。\n"
        "要求：\n"
        "1) 只输出 JSON 对象，不要任何解释或 markdown。\n"
        "2) 建议必须‘有证据’，在 corrective_actions[*].evidence 里必须引用：missing_points / error_tags / weak_node_ids 中至少一种，且引用的值必须来自输入。\n"
        "3) 给出可执行的再练计划：先 L1 夯实，再 L2 提升。\n"
        "4) one_click_practice 用于后端直接复用 /quizzes/generate。\n\n"
        f"输出 JSON 结构示例(字段名必须一致，内容可自行填充)：\n{json.dumps(schema_hint, ensure_ascii=False)}\n\n"
        f"=== 错题聚合输入 ===\n{json.dumps(ctx, ensure_ascii=False)}\n"
    )


def generate_coach(
    student_id: str,
    notebook_id: Optional[str] = None,
    material_id: Optional[str] = None,
    days: int = 14,
    top_k: int = 5,
):
    """RQ job: generate and persist a coaching plan.

    Stores to MongoDB collection: coach_plans.
    """

    db = _get_db()

    ctx = _aggregate_mistakes(
        db=db,
        student_id=student_id,
        notebook_id=notebook_id,
        material_id=material_id,
        days=int(days or 14),
        top_k=int(top_k or 5),
    )

    # If no examples, persist an empty plan to avoid UI polling confusion.
    now = datetime.utcnow()
    if not ctx.get("recent_mistakes_examples"):
        _coach_plans_col(db).insert_one(
            {
                "student_id": student_id,
                "notebook_id": notebook_id,
                "material_id": material_id,
                "status": "done",
                "created_at": now,
                "context": ctx,
                "plan": {
                    "diagnosis": {
                        "summary": "暂无可用错题数据，请先完成一次测验并批改后再生成小灶建议。",
                        "key_weak_node_ids": [],
                        "top_error_tags": [],
                        "top_missing_points": [],
                    },
                    "corrective_actions": [],
                    "practice_plan": [],
                    "one_click_practice": {
                        "node_id": None,
                        "num_questions": 5,
                        "difficulty_mix": {"L1": 0.6, "L2": 0.4},
                        "type_mix": {"mcq": 0.6, "short": 0.4},
                        "material_ids": ctx.get("material_ids") or [],
                    },
                },
            }
        )
        return

    prompt = _build_prompt(ctx)
    plan, check_result = run_with_checker(
        prompt=prompt,
        call_llm=_call_kimi,
        checker=CoachCheck(),
        context={
            "missing_points": ctx.get("missing_points") or [],
            "error_tags": ctx.get("error_tags") or [],
            "weak_node_ids": ctx.get("weak_node_ids") or [],
        },
        max_retries=2,
    )

    status = "done"
    if check_result.status == CheckStatus.ESCALATE or not isinstance(plan, dict):
        status = "failed"
        plan = {
            "error": "coach generation failed",
            "reason": check_result.reason,
        }
    else:
        # Patch one_click_practice with safe defaults if missing
        oc = plan.get("one_click_practice") if isinstance(plan.get("one_click_practice"), dict) else {}
        if not oc.get("node_id"):
            oc["node_id"] = (ctx.get("weak_node_ids") or [None])[0]
        oc.setdefault("num_questions", 5)
        oc.setdefault("difficulty_mix", {"L1": 0.6, "L2": 0.4})
        oc.setdefault("type_mix", {"mcq": 0.6, "short": 0.4})
        oc.setdefault("material_ids", ctx.get("material_ids") or [])
        plan["one_click_practice"] = oc

    _coach_plans_col(db).insert_one(
        {
            "student_id": student_id,
            "notebook_id": notebook_id,
            "material_id": material_id,
            "status": status,
            "created_at": now,
            "updated_at": datetime.utcnow(),
            "context": ctx,
            "plan": plan,
        }
    )
