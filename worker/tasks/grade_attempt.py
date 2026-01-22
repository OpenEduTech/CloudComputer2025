import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId
from openai import OpenAI
from pymongo import MongoClient

from tasks.rag import retrieve_context

from checkers.gate import run_with_checker
from checkers.grade_check import GradeCheck
from checkers.base import CheckStatus

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "learning_agent")
KIMI_API_KEY = os.getenv("MOONSHOT_API_KEY")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")
PASS_SCORE_THRESHOLD = float(os.getenv("PASS_SCORE_THRESHOLD", "0.7"))
PARTIAL_SCORE_THRESHOLD = float(os.getenv("PARTIAL_SCORE_THRESHOLD", "0.4"))
CRITERIA_WEIGHTS = {
    "correctness": 0.4,
    "completeness": 0.3,
    "reasoning": 0.2,
    "clarity": 0.1,
}


def _get_db():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB_NAME]


def _attempts_col(db):
    return db["attempts"]


def _quizzes_col(db):
    return db["quizzes"]


def _questions_col(db):
    return db["questions"]


def _mistakes_col(db):
    return db["mistakes"]


def _mastery_col(db):
    return db["mastery"]


def _call_kimi(prompt: str) -> str:
    if not KIMI_API_KEY:
        raise RuntimeError("MOONSHOT_API_KEY is required for grading")
    client = OpenAI(api_key=KIMI_API_KEY, base_url="https://api.moonshot.cn/v1")
    resp = client.chat.completions.create(
        model=KIMI_MODEL,
        messages=[
            {"role": "system", "content": "You are a fair grader. Output JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _parse_grade(raw: str) -> Dict[str, Any]:
    cleaned = _strip_code_fence(raw)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("grading result must be an object")
    return data


def _clamp_score(value: Any) -> float:
    try:
        score = float(value or 0.0)
    except Exception:
        score = 0.0
    return max(0.0, min(1.0, score))


def _derive_verdict(score: float) -> str:
    if score >= PASS_SCORE_THRESHOLD:
        return "correct"
    if score >= PARTIAL_SCORE_THRESHOLD:
        return "partial"
    return "wrong"


def _strip_choice_label(text: str) -> str:
    return re.sub(r"^[A-Da-d]\s*[\.\)、\):：\-\]]\s*", "", text).strip()


def _normalize_choice(text: str) -> str:
    return re.sub(r"\s+", "", _strip_choice_label(text)).lower()


def _extract_choice_letter(text: str) -> str:
    s = str(text or "").strip()
    if re.fullmatch(r"[A-Da-d]", s):
        return s.upper()
    m = re.match(r"^\s*([A-Da-d])\s*[\.\)、\):：\-\]]", s)
    return m.group(1).upper() if m else ""


def _resolve_choice_text(options: List[str], raw: Any) -> str:
    raw_str = str(raw or "").strip()
    if not raw_str:
        return ""
    letter = _extract_choice_letter(raw_str)
    if letter:
        idx = ord(letter) - ord("A")
        if 0 <= idx < len(options):
            opt_display = _strip_choice_label(str(options[idx])).strip()
            return f"{letter}. {opt_display}" if opt_display else letter
        return raw_str
    normalized = _normalize_choice(raw_str)
    for idx, opt in enumerate(options):
        if _normalize_choice(str(opt)) == normalized:
            letter = chr(ord("A") + idx)
            opt_display = _strip_choice_label(str(opt)).strip()
            return f"{letter}. {opt_display}" if opt_display else letter
    return raw_str


def _display_answer(question: Dict[str, Any], raw: Any) -> str:
    if question.get("type") == "mcq":
        options = [str(o) for o in (question.get("options") or [])]
        return _resolve_choice_text(options, raw)
    return str(raw or "").strip()


def _normalize_criteria_scores(criteria: Any, fallback_score: float) -> Dict[str, float]:
    base = {k: _clamp_score(fallback_score) for k in CRITERIA_WEIGHTS}
    if not isinstance(criteria, dict):
        return base
    for key in base:
        if key in criteria:
            base[key] = _clamp_score(criteria.get(key))
    return base


def _score_from_criteria(criteria: Dict[str, float]) -> float:
    return sum(criteria.get(k, 0.0) * CRITERIA_WEIGHTS[k] for k in CRITERIA_WEIGHTS)


def _round_score(score: float) -> float:
    rounded = round(float(score or 0.0), 4)
    if rounded > 0.9999:
        return 1.0
    if rounded < 0.0001:
        return 0.0
    return rounded


def _build_analysis_text(
    explanation: str,
    error_analysis: str,
    knowledge_points: List[str],
    is_correct: bool,
) -> str:
    parts: List[str] = []
    if explanation:
        parts.append(str(explanation).strip())
    if not is_correct and error_analysis:
        parts.append(f"错因：{error_analysis}")
    if knowledge_points:
        parts.append(f"知识点：{' / '.join([str(k) for k in knowledge_points])}")
    return "\n".join([p for p in parts if p]).strip()


def _normalize_grade_result(
    result: Dict[str, Any],
    question: Dict[str, Any],
    answer: Any,
    knowledge_points: List[str],
    question_analysis: str,
) -> Dict[str, Any]:
    normalized = dict(result or {})
    score = _clamp_score(normalized.get("score"))
    criteria = _normalize_criteria_scores(normalized.get("criteria_scores"), score)
    score = _round_score(_score_from_criteria(criteria))

    if question.get("type") == "mcq":
        is_correct = bool(normalized.get("is_correct", False))
        score = 1.0 if is_correct else 0.0
        criteria = {
            "correctness": score,
            "completeness": score,
            "reasoning": score,
            "clarity": score,
        }

    normalized["criteria_scores"] = criteria
    normalized["score"] = score
    normalized["verdict"] = _derive_verdict(score)
    normalized["is_correct"] = normalized["verdict"] == "correct"

    missing_points = normalized.get("missing_points")
    if not isinstance(missing_points, list):
        missing_points = []
    normalized["missing_points"] = [str(x).strip() for x in missing_points if str(x).strip()]

    error_tags = normalized.get("error_tags")
    if not isinstance(error_tags, list):
        error_tags = []
    normalized["error_tags"] = [str(x).strip() for x in error_tags if str(x).strip()]

    error_analysis = normalized.get("error_analysis")
    normalized["error_analysis"] = str(error_analysis or "").strip()

    feedback = normalized.get("feedback")
    normalized["feedback"] = str(feedback or "").strip()

    if not normalized["is_correct"]:
        normalized = _ensure_knowledge_focus(normalized, knowledge_points)

    student_answer = _display_answer(question, answer)
    if not student_answer:
        student_answer = "未作答"
    correct_answer = _display_answer(question, question.get("answer_key"))
    normalized["student_answer"] = student_answer
    normalized["correct_answer"] = correct_answer

    explanation = question_analysis or normalized.get("feedback") or ""
    normalized["analysis"] = _build_analysis_text(
        explanation=explanation,
        error_analysis=normalized.get("error_analysis", ""),
        knowledge_points=knowledge_points,
        is_correct=normalized["is_correct"],
    )
    return normalized


def _build_rag_query(question: Dict[str, Any], answer: Any, knowledge_points: List[str]) -> str:
    parts = [
        str(question.get("stem") or "").strip(),
        str(question.get("answer_key") or "").strip(),
        str(answer or "").strip(),
        " ".join([str(k) for k in knowledge_points if str(k).strip()]).strip(),
    ]
    return " ".join([p for p in parts if p]).strip()


def _grade_short_answer(
    question: Dict[str, Any],
    answer: Any,
    rag_context: str,
) -> Dict[str, Any]:
    rubric = question.get("rubric", "")
    reference = question.get("answer_key", "")
    knowledge_points = question.get("knowledge_points", [])
    prompt = (
        "Grade the student's short answer based on the rubric and reference answer.\n"
        "Use criteria_scores with keys: correctness, completeness, reasoning, clarity (0-1).\n"
        f"Final score = 0.4*correctness + 0.3*completeness + 0.2*reasoning + 0.1*clarity.\n"
        f"verdict: correct if score >= {PASS_SCORE_THRESHOLD}, partial if score >= {PARTIAL_SCORE_THRESHOLD}, otherwise wrong.\n"
        "Return JSON with fields: criteria_scores, score (0-1), verdict, is_correct (true/false), "
        "missing_points (array of strings), error_tags (array of strings), "
        "error_analysis (string), feedback (string).\n"
        "missing_points and error_tags MUST be knowledge-point oriented. "
        "Prefer selecting from the provided knowledge_points list.\n"
        "Use the provided context as authoritative; if context is insufficient, be conservative.\n"
        "If you include formulas, wrap them with $...$.\n"
        f"Context:\n{rag_context}\n"
        f"Question: {question['stem']}\n"
        f"Rubric: {rubric}\n"
        f"Reference answer: {reference}\n"
        f"Knowledge points: {knowledge_points}\n"
        f"Student answer: {answer}\n"
    )
    result, check_result = run_with_checker(
        prompt=prompt,
        call_llm=_call_kimi,
        checker=GradeCheck(),
        context={},
        max_retries=2,
    )
    if check_result.status == CheckStatus.ESCALATE or not isinstance(result, dict):
        raise ValueError(f"grade check failed: {check_result.reason}")
    return result


def _grade_mcq(question: Dict[str, Any], answer: Any, rag_context: str) -> Dict[str, Any]:
    options = question.get("options") or []
    correct = str(question.get("answer_key", "")).strip()
    given = str(answer or "").strip()

    # Map A/B/C/D -> option text
    letter_to_option = {}
    for idx, opt in enumerate(options):
        letter = chr(ord("A") + idx)
        letter_to_option[letter] = str(opt)

    # Resolve correct option text
    correct_letter = _extract_choice_letter(correct)
    correct_option = letter_to_option.get(correct_letter, "")
    if not correct_option and options:
        correct_norm = _normalize_choice(correct)
        for opt in options:
            if _normalize_choice(str(opt)) == correct_norm:
                correct_option = str(opt)
                break
        if not correct_option:
            for opt in options:
                if correct_norm and correct_norm in _normalize_choice(str(opt)):
                    correct_option = str(opt)
                    break

    # Resolve student's chosen option text (allow letter input)
    given_letter = _extract_choice_letter(given)
    given_option = letter_to_option.get(given_letter, given) if given_letter else given

    is_correct = False
    if correct_option:
        is_correct = _normalize_choice(given_option) == _normalize_choice(correct_option)
    else:
        # Fallback: compare raw answer_key vs given when no options are available
        is_correct = _normalize_choice(given) == _normalize_choice(correct)

    if is_correct:
        return {
            "score": 1.0,
            "is_correct": True,
            "verdict": "correct",
            "criteria_scores": {
                "correctness": 1.0,
                "completeness": 1.0,
                "reasoning": 1.0,
                "clarity": 1.0,
            },
            "missing_points": [],
            "error_tags": [],
            "error_analysis": "",
            "feedback": "答案正确。",
        }

    # Wrong: ask LLM for knowledge-point-based error analysis (score stays 0).
    if KIMI_API_KEY and options:
        try:
            return _analyze_mcq_error(question, given_option, correct, rag_context)
        except Exception:
            pass

    # Default: treat as incorrect with empty analysis (will be filled by knowledge focus).
    return {
        "score": 0.0,
        "is_correct": False,
        "verdict": "wrong",
        "criteria_scores": {
            "correctness": 0.0,
            "completeness": 0.0,
            "reasoning": 0.0,
            "clarity": 0.0,
        },
        "missing_points": [],
        "error_tags": [],
        "error_analysis": "",
        "feedback": f"答案错误。正确答案为 {correct}。",
    }


def _grade_mcq_with_llm(question: Dict[str, Any], answer: Any, correct_key: str) -> Dict[str, Any]:
    options = question.get("options") or []
    knowledge_points = question.get("knowledge_points", [])
    prompt = (
        "You are grading a multiple-choice question.\n"
        "Decide whether the student's selected option should be accepted as correct.\n"
        "Accept semantically equivalent answers (e.g., likelihood vs log-likelihood) if they are truly equivalent.\n"
        "Use criteria_scores with keys: correctness, completeness, reasoning, clarity (0-1).\n"
        f"Final score = 0.4*correctness + 0.3*completeness + 0.2*reasoning + 0.1*clarity.\n"
        f"verdict: correct if score >= {PASS_SCORE_THRESHOLD}, partial if score >= {PARTIAL_SCORE_THRESHOLD}, otherwise wrong.\n"
        "Return JSON with fields: criteria_scores, score (0-1), verdict, is_correct (true/false), "
        "missing_points (array of strings), error_tags (array of strings), "
        "error_analysis (string), feedback (string).\n"
        "missing_points and error_tags MUST be knowledge-point oriented. "
        "Prefer selecting from the provided knowledge_points list.\n"
        "If you include formulas, wrap them with $...$.\n"
        f"Question: {question.get('stem')}\n"
        f"Options: {options}\n"
        f"Correct answer key: {correct_key}\n"
        f"Student selected option: {answer}\n"
        f"Knowledge points: {knowledge_points}\n"
    )
    result, check_result = run_with_checker(
        prompt=prompt,
        call_llm=_call_kimi,
        checker=GradeCheck(),
        context={},
        max_retries=2,
    )
    if check_result.status == CheckStatus.ESCALATE or not isinstance(result, dict):
        raise ValueError(f"grade check failed: {check_result.reason}")
    return result


def _analyze_mcq_error(
    question: Dict[str, Any],
    answer: Any,
    correct_key: str,
    rag_context: str,
) -> Dict[str, Any]:
    options = question.get("options") or []
    knowledge_points = question.get("knowledge_points", [])
    labeled_options = [f"{chr(ord('A') + idx)}. {opt}" for idx, opt in enumerate(options)]
    correct_display = _resolve_choice_text(options, correct_key)
    student_display = _resolve_choice_text(options, answer)
    prompt = (
        "You are analyzing why a student's multiple-choice answer is wrong.\n"
        "The answer is incorrect; do NOT change correctness.\n"
        "Return JSON with fields: score(0), is_correct(false), missing_points(array), error_tags(array), "
        "error_analysis(string), feedback(string).\n"
        "missing_points and error_tags MUST be knowledge-point oriented, preferably from knowledge_points.\n"
        "Use the provided context as authoritative; if context is insufficient, be conservative.\n"
        "If you include formulas, wrap them with $...$.\n"
        f"Context:\n{rag_context}\n"
        f"Question: {question.get('stem')}\n"
        f"Options: {labeled_options}\n"
        f"Correct answer: {correct_display}\n"
        f"Student answer: {student_display}\n"
        f"Knowledge points: {knowledge_points}\n"
    )
    result, check_result = run_with_checker(
        prompt=prompt,
        call_llm=_call_kimi,
        checker=GradeCheck(),
        context={},
        max_retries=2,
    )
    if check_result.status == CheckStatus.ESCALATE or not isinstance(result, dict):
        raise ValueError(f"grade check failed: {check_result.reason}")
    # force MCQ scoring invariants
    result["score"] = 0.0
    result["is_correct"] = False
    result["verdict"] = "wrong"
    return result


def _grade_blank(question: Dict[str, Any], answer: Any, rag_context: str) -> Dict[str, Any]:
    correct = str(question.get("answer_key", "")).strip()
    given = str(answer or "").strip()
    if correct and given and given.lower() == correct.lower():
        return {
            "score": 1.0,
            "is_correct": True,
            "missing_points": [],
            "error_tags": [],
            "error_analysis": "",
            "feedback": "答案正确。",
        }
    result = _grade_short_answer(question, answer, rag_context)
    return result


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def _ensure_knowledge_focus(result: Dict[str, Any], knowledge_points: List[str]) -> Dict[str, Any]:
    kp = [str(k).strip() for k in (knowledge_points or []) if str(k).strip()]
    if not kp:
        return result

    def _has_overlap(items: List[str]) -> bool:
        for item in items:
            if not item:
                continue
            for k in kp:
                if _normalize_text(k) in _normalize_text(item):
                    return True
        return False

    missing_points = result.get("missing_points")
    if not isinstance(missing_points, list):
        missing_points = []
    missing_points = [str(x).strip() for x in missing_points if str(x).strip()]
    if not missing_points or not _has_overlap(missing_points):
        missing_points = kp
    result["missing_points"] = missing_points

    error_tags = result.get("error_tags")
    if not isinstance(error_tags, list):
        error_tags = []
    error_tags = [str(x).strip() for x in error_tags if str(x).strip()]
    if not error_tags or not _has_overlap(error_tags):
        error_tags = kp
    result["error_tags"] = error_tags

    if not result.get("error_analysis"):
        result["error_analysis"] = "知识点未掌握： " + " / ".join(kp)
    return result


def _update_mistakes(
    db,
    student_id: str,
    notebook_id: str,
    question_id: str,
    missing_points: List[str],
    error_tags: List[str],
    error_analysis: str,
    knowledge_points: List[str],
    question: Dict[str, Any],
    result: Dict[str, Any],
):
    last_question = str(question.get("stem") or "").strip()
    last_type = str(question.get("type") or "").strip()
    last_options = [str(o) for o in (question.get("options") or [])]
    last_student_answer = str(result.get("student_answer") or "").strip()
    last_correct_answer = str(result.get("correct_answer") or "").strip()
    last_explanation = str(question.get("analysis") or result.get("analysis") or "").strip()
    _mistakes_col(db).update_one(
        {"student_id": student_id, "notebook_id": notebook_id, "question_id": question_id},
        {
            "$setOnInsert": {"notebook_id": notebook_id},
            "$set": {
                "last_wrong_at": datetime.utcnow(),
                "last_error_analysis": error_analysis,
                "last_question": last_question,
                "last_question_type": last_type,
                "last_options": last_options,
                "last_student_answer": last_student_answer,
                "last_correct_answer": last_correct_answer,
                "last_explanation": last_explanation,
            },
            "$inc": {"wrong_count": 1},
            "$addToSet": {
                "missing_points": {"$each": missing_points},
                "error_tags": {"$each": error_tags},
                "knowledge_points": {"$each": knowledge_points},
            },
        },
        upsert=True,
    )


def _update_mastery(db, student_id: str, notebook_id: str, node_ids: List[str], is_correct: bool):
    # IMPORTANT (M2): update only the nodes this question is tagged with.
    # Children mastery must be independent; parent mastery is computed as an aggregate
    # over children in the knowledge-tree endpoint.
    if not node_ids:
        return
    now = datetime.utcnow()
    for node_id in node_ids:
        q = {"student_id": student_id, "node_id": node_id, "notebook_id": notebook_id}
        inc = {"seen": 1, "correct": 1 if is_correct else 0, "wrong": 0 if is_correct else 1}
        _mastery_col(db).update_one(
            q,
            {"$inc": inc, "$set": {"updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        doc = _mastery_col(db).find_one(q, {"seen": 1, "correct": 1})
        seen = int((doc or {}).get("seen", 0) or 0)
        correct = int((doc or {}).get("correct", 0) or 0)
        score = (correct / seen) if seen > 0 else 0.0
        _mastery_col(db).update_one(q, {"$set": {"mastery_score": float(score)}})


def grade_attempt(attempt_id: str):
    db = _get_db()
    attempt = _attempts_col(db).find_one({"_id": ObjectId(attempt_id)})
    if not attempt:
        print(f"[grade_attempt] attempt not found: {attempt_id}")
        return

    _attempts_col(db).update_one({"_id": ObjectId(attempt_id)}, {"$set": {"status": "processing"}})

    quiz = _quizzes_col(db).find_one({"_id": ObjectId(attempt["quiz_id"])})
    if not quiz:
        _attempts_col(db).update_one(
            {"_id": ObjectId(attempt_id)},
            {"$set": {"status": "failed", "error_message": "quiz not found"}},
        )
        return

    questions = list(_questions_col(db).find({"quiz_id": attempt["quiz_id"]}))
    answers = attempt.get("answers", {})

    grading_details = []
    total_score = 0.0
    try:
        for q in questions:
            qid = str(q["_id"])
            answer = answers.get(qid)

            knowledge_points = q.get("knowledge_points", [])
            node_ids = q.get("node_ids", [])  # M2：绑定的章节/知识点

            question_analysis = q.get("analysis") or ""
            material_ids = q.get("material_ids") or quiz.get("material_ids") or []
            rag_query = _build_rag_query(q, answer, knowledge_points)
            rag_context = ""
            if material_ids and rag_query:
                try:
                    rag_context = retrieve_context(
                        db,
                        material_ids,
                        rag_query,
                        student_id=attempt.get("student_id", "demo_user"),
                        notebook_id=quiz.get("notebook_id"),
                    )
                except Exception:
                    rag_context = ""

            if q.get("type") == "short":
                result = _grade_short_answer(q, answer, rag_context)
            elif q.get("type") == "blank":
                result = _grade_blank(q, answer, rag_context)
            else:
                result = _grade_mcq(q, answer, rag_context)

            result = _normalize_grade_result(
                result=result,
                question=q,
                answer=answer,
                knowledge_points=knowledge_points,
                question_analysis=question_analysis,
            )
            score_value = float(result.get("score", 0.0) or 0.0)
            is_correct = bool(result.get("is_correct", False))
            mistake_added = not is_correct
            total_score += score_value

            grading_details.append(
                {
                    "question_id": qid,
                    "result": result,
                    "score": score_value,
                    "is_correct": is_correct,
                    "mistake_added": mistake_added,
                    "knowledge_points": knowledge_points,
                    "node_ids": node_ids,
                    "analysis": question_analysis,
                }
            )

            if mistake_added:
                _update_mistakes(
                    db,
                    attempt.get("student_id", "demo_user"),
                    quiz.get("notebook_id"),
                    qid,
                    result.get("missing_points", []),
                    result.get("error_tags", []),
                    result.get("error_analysis", ""),
                    knowledge_points,
                    question=q,
                    result=result,
                )

            # ---------------- M2 新增：回写 mastery ----------------
            _update_mastery(
                db,
                student_id=attempt.get("student_id", "demo_user"),
                notebook_id=quiz.get("notebook_id"),
                node_ids=node_ids,
                is_correct=is_correct,
            )

        _attempts_col(db).update_one(
            {"_id": ObjectId(attempt_id)},
            {"$set": {"status": "done", "score": total_score, "grading": grading_details}},
        )
    except Exception as exc:
        _attempts_col(db).update_one(
            {"_id": ObjectId(attempt_id)},
            {"$set": {"status": "failed", "error_message": str(exc)}},
        )
        print(f"[grade_attempt] failed: {exc}")
