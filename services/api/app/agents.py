import json
import logging
import os
import random
import re
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional

import httpx

from . import prompt_templates
from .models import (
    AppealRequest,
    AppealResult,
    GradeFeedback,
    GradeRequest,
    GradeResponse,
    MaterialCreate,
    Quiz,
    QuizQuestion,
    QuizRequest,
)


def _offline_generate(material_text: str, req: QuizRequest) -> Quiz:
    cleaned = (material_text or "").strip()
    if not cleaned:
        cleaned = "学习资料暂缺，建议先上传内容以生成高质量题目。"
    fragments = re.split(r"(?<=[。！？.!?])\s+", cleaned)
    fragments = [frag.strip() for frag in fragments if len(frag.strip()) >= 6]
    if not fragments:
        fragments = [cleaned[:120]]
    gradients = req.difficulty_span or ["easy", "medium", "hard"]
    questions: List[QuizQuestion] = []
    for i in range(req.num_questions):
        difficulty = gradients[i % len(gradients)]
        key_point = fragments[i % len(fragments)]
        snippet = key_point[:160]
        if i % 2 == 0:
            stem = f"根据学习资料，概括以下要点的核心含义：\"{snippet}\"。"
            rationale = "考察对材料中关键句的理解与复述能力。"
            summary = _condense_text(snippet)
            questions.append(
                QuizQuestion(
                    id=str(uuid.uuid4()),
                    type="short",
                    stem=stem,
                    answer_key=summary,
                    rationale=rationale,
                    difficulty=difficulty,
                )
            )
        else:
            distractors = [frag for frag in fragments if frag != key_point]
            random.shuffle(distractors)
            options = [key_point] + distractors[:3]
            random.shuffle(options)
            stem = "材料中哪一项最能对应下列描述？"
            rationale = "考察对多个材料片段的辨识度。"
            questions.append(
                QuizQuestion(
                    id=str(uuid.uuid4()),
                    type="mcq",
                    stem=f"{stem}\n描述：{snippet}",
                    options=options,
                    answer_key=key_point,
                    rationale=rationale,
                    difficulty=difficulty,
                )
            )
    return Quiz(
        quiz_id=str(uuid.uuid4()),
        user_id=req.user_id,
        topic=req.topic,
        questions=questions,
    )


def _condense_text(text: str) -> str:
    cleaned = text.strip()
    if len(cleaned) <= 80:
        return cleaned
    sentences = re.split(r"(?<=[。！？.!?])", cleaned)
    if sentences:
        for s in sentences:
            snippet = s.strip()
            if 12 <= len(snippet) <= 80:
                return snippet
    keywords = cleaned[:120]
    return f"概括要点：{keywords[:60]}..."


logger = logging.getLogger(__name__)


class LlmAgent:
    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY", "sk-iihmzbfvqnmrateznntugliogwzfyfsgbtgyozowwbshjiev")
        raw_base = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1/chat/completions")
        self.base_url = self._normalize_base_url(raw_base)
        self.model = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3.2-Exp")
        timeout_raw = os.getenv("LLM_TIMEOUT_SECONDS", "60")
        try:
            self.timeout_seconds = max(10.0, float(timeout_raw))
        except ValueError:
            self.timeout_seconds = 60.0

    @staticmethod
    def _normalize_base_url(url: str) -> str:
        if not url:
            return "https://api.siliconflow.cn/v1/chat/completions"
        clean = url.strip()
        if clean.endswith("/chat/completions"):
            return clean
        return clean.rstrip("/") + "/chat/completions"

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            return ""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            client_timeout = httpx.Timeout(self.timeout_seconds, connect=20.0)
            async with httpx.AsyncClient(timeout=client_timeout) as client:
                resp = await client.post(self.base_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as err:
            logger.error("LLM 调用失败", exc_info=err)
            if hasattr(err, "response") and err.response is not None:
                try:
                    logger.error("LLM 响应: %s", err.response.text)
                except Exception:  # pragma: no cover
                    pass
            return ""

    async def generate_quiz(self, materials: List[Dict[str, Any]], req: QuizRequest) -> Quiz:
        combined = "\n".join(m.get("content", "") for m in materials)
        content = combined[:8000]
        user_prompt = f"Materials:\n{content}\nRequested difficulties: {req.difficulty_span}\nQuestions: {req.num_questions}"
        raw = await self._call_llm(prompt_templates.GEN_QUIZ, user_prompt)
        data = self._safe_json(raw)
        if not data:
            return _offline_generate(content, req)
        questions = [QuizQuestion(**q) for q in data.get("questions", [])][: req.num_questions]
        return Quiz(
            quiz_id=data.get("quiz_id", str(uuid.uuid4())),
            user_id=req.user_id,
            topic=req.topic,
            questions=questions,
        )

    async def grade(self, quiz: Quiz, payload: GradeRequest) -> GradeResponse:
        quiz_map = {q.id: q for q in quiz.questions}
        base_feedback: List[GradeFeedback] = []
        score_units: List[float] = []

        def normalize_answer(text: Optional[str]) -> str:
            if not text:
                return ""
            return re.sub(r"\s+", "", text).lower()

        def resolve_mcq_expected(question: QuizQuestion) -> tuple[Optional[str], dict[str, str]]:
            letters: dict[str, str] = {}
            options = question.options or []
            for idx, opt in enumerate(options):
                letter = chr(65 + idx)
                letters[letter] = normalize_answer(opt)
            raw = (question.answer_key or "").strip()
            if not raw:
                return None, letters
            upper = raw.upper()
            if upper in letters:
                return letters[upper], letters
            normalized_raw = normalize_answer(raw)
            if normalized_raw in letters.values():
                return normalized_raw, letters
            return normalized_raw or None, letters

        def compute_overlap_ratio(expected: str, answer: str) -> float:
            if not expected or not answer:
                return 0.0
            exp_counter = Counter(expected)
            ans_counter = Counter(answer)
            matches = sum(min(count, ans_counter.get(ch, 0)) for ch, count in exp_counter.items())
            return matches / max(len(expected), 1)

        for item in payload.answers:
            q = quiz_map.get(item.question_id)
            if not q:
                base_feedback.append(
                    GradeFeedback(question_id=item.question_id, correct=False, rationale="Unknown question ID")
                )
                score_units.append(0.0)
                continue
            is_correct = False
            expected_norm = normalize_answer(q.answer_key)
            user_norm = normalize_answer(item.answer)
            contribution = 0.0
            overlap_ratio = 0.0
            if q.type == "mcq":
                expected_norm, letter_map = resolve_mcq_expected(q)
                user_letter = (item.answer or "").strip().upper()
                if expected_norm and user_norm == expected_norm:
                    is_correct = True
                    contribution = 1.0
                elif expected_norm and user_letter in letter_map and letter_map[user_letter] == expected_norm:
                    is_correct = True
                    contribution = 1.0
            else:
                overlap_ratio = compute_overlap_ratio(expected_norm, user_norm)
                if overlap_ratio >= 0.5:
                    is_correct = True
                    contribution = 1.0
                else:
                    contribution = overlap_ratio / 0.5 if expected_norm else 0.0
            rationale = q.rationale or "Checks alignment with the key point."
            base_feedback.append(
                GradeFeedback(
                    question_id=q.id,
                    correct=is_correct,
                    rationale=rationale,
                    suggested_review=None,
                )
            )
            if q.type == "short" and not is_correct and contribution > 0:
                base_feedback[-1].rationale = (
                    f"答案与标准要点重合度约 {overlap_ratio:.0%}，未达到 50% 满分阈值，按比例扣分。"
                )
            score_units.append(min(contribution, 1.0))
        base_feedback = await self._enrich_feedback_with_ai(quiz, payload, base_feedback)
        total_questions = max(len(quiz.questions), 1)
        score_value = round(100 * sum(score_units) / total_questions, 2)
        initial = GradeResponse(
            user_id=payload.user_id,
            quiz_id=quiz.quiz_id,
            score=score_value,
            feedback=base_feedback,
        )
        checked = await self._apply_check_layer(quiz, initial)
        return checked

    async def generate_memory(self, material: MaterialCreate) -> Optional[Dict[str, Any]]:
        snippet = (material.content or "")[:4000]
        if not snippet.strip():
            return None
        topic = material.topic or "General"
        user_prompt = f"Topic: {topic}\nMaterial:\n{snippet}"
        raw = await self._call_llm(prompt_templates.MEMORY_FROM_MATERIAL, user_prompt)
        data = self._safe_json(raw)
        if not data:
            return self._offline_memory(topic, snippet)
        title = (data.get("title") or topic or "记忆点").strip()
        content = (data.get("content") or "").strip()
        if not content:
            return self._offline_memory(topic, snippet)
        tags = data.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        elif isinstance(tags, list):
            tags = [str(t).strip() for t in tags if str(t).strip()]
        else:
            tags = []
        if topic and topic not in tags:
            tags.append(topic)
        return {"title": title, "content": content, "tags": tags}

    def _offline_memory(self, topic: str, snippet: str) -> Optional[Dict[str, Any]]:
        clean = snippet.strip()
        if not clean:
            return None
        sentences = re.split(r"(?<=[。！？.!?])\s+", clean)
        summary = " ".join(sentences[:2]).strip()
        if not summary:
            summary = clean[:200]
        title = f"{topic} 记忆卡" if topic else "记忆卡"
        tags = [topic] if topic else []
        return {"title": title, "content": summary, "tags": tags}

    async def _enrich_feedback_with_ai(
        self,
        quiz: Quiz,
        payload: GradeRequest,
        feedback: List[GradeFeedback],
    ) -> List[GradeFeedback]:
        quiz_map = {q.id: q for q in quiz.questions}
        answer_map = {item.question_id: item.answer for item in payload.answers}
        pending: List[Dict[str, Any]] = []
        for fb in feedback:
            if fb.correct or fb.suggested_review:
                continue
            question = quiz_map.get(fb.question_id)
            if not question:
                continue
            pending.append(
                {
                    "question_id": question.id,
                    "stem": question.stem,
                    "type": question.type,
                    "options": question.options,
                    "answer_key": question.answer_key,
                    "difficulty": question.difficulty,
                    "user_answer": answer_map.get(question.id, ""),
                    "rationale": fb.rationale,
                }
            )
        if not pending:
            return feedback
        user_prompt = json.dumps({"items": pending}, ensure_ascii=False)
        raw = await self._call_llm(prompt_templates.REMEDIATION_HINTS, user_prompt)
        data = self._safe_json(raw)
        suggestions: Dict[str, str] = {}
        if data:
            entries = data.get("suggestions") or data.get("items") or []
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    qid = entry.get("question_id")
                    text = entry.get("suggested_review") or entry.get("tip")
                    if qid and isinstance(text, str) and text.strip():
                        suggestions[qid] = text.strip()
        for fb in feedback:
            if fb.correct or fb.suggested_review:
                continue
            question = quiz_map.get(fb.question_id)
            if not question:
                continue
            fb.suggested_review = suggestions.get(fb.question_id) or self._default_review_tip(
                question,
                answer_map.get(fb.question_id, ""),
            )
        return feedback

    @staticmethod
    def _default_review_tip(question: QuizQuestion, user_answer: Optional[str]) -> str:
        rationale_hint = (question.rationale or question.stem).strip()
        rationale_hint = rationale_hint[:60]
        answer_hint = (question.answer_key or "").strip()
        if question.type == "mcq":
            focus = rationale_hint or question.stem[:60]
            return f"回看题干，锁定“{focus}”，逐项排除选项后再作答。"
        if answer_hint:
            return f"对照标准要点“{answer_hint[:40]}”，找差距并重新表述。"
        if user_answer:
            return "把自己的答案拆成要点，与材料关键句逐条校对。"
        return "重读材料相关段落，列出2个关键要点后复述。"

    async def _apply_check_layer(self, quiz: Quiz, response: GradeResponse) -> GradeResponse:
        quiz_json = quiz.dict()
        resp_json = response.dict()
        user_prompt = f"Quiz: {quiz_json}\nGrader output: {resp_json}"
        raw = await self._call_llm(prompt_templates.CHECK_LAYER, user_prompt)
        if not raw:
            return response
        try:
            data = json.loads(raw)
            feedback = [GradeFeedback(**f) for f in data.get("feedback", response.feedback)]
            score = data.get("score", response.score)
            return GradeResponse(user_id=response.user_id, quiz_id=response.quiz_id, score=score, feedback=feedback)
        except Exception:
            return response

    async def appeal(self, quiz: Quiz, req: AppealRequest, user_answer: str, original_feedback: GradeFeedback) -> AppealResult:
        question = next((q for q in quiz.questions if q.id == req.question_id), None)
        if not question:
            return AppealResult(quiz_id=req.quiz_id, question_id=req.question_id, correct=False, rationale="Question not found")
        payload = {
            "question": question.dict(),
            "user_answer": user_answer,
            "answer_key": question.answer_key,
            "original_feedback": original_feedback.dict(),
        }
        user_prompt = f"Review this appeal: {payload}"
        raw = await self._call_llm(prompt_templates.APPEAL, user_prompt)
        if not raw:
            return AppealResult(quiz_id=req.quiz_id, question_id=req.question_id, correct=original_feedback.correct, rationale=original_feedback.rationale)
        try:
            data = json.loads(raw)
            return AppealResult(
                quiz_id=req.quiz_id,
                question_id=req.question_id,
                correct=bool(data.get("correct", original_feedback.correct)),
                rationale=data.get("rationale", original_feedback.rationale),
            )
        except Exception:
            return AppealResult(quiz_id=req.quiz_id, question_id=req.question_id, correct=original_feedback.correct, rationale=original_feedback.rationale)

    @staticmethod
    def _safe_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        text = raw.strip()
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()
        try:
            return json.loads(text)
        except Exception:
            return None
