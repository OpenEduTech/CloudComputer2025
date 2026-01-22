"""
题目管理API
"""
from fastapi import APIRouter, HTTPException
import logging
from typing import List
import os

from app.models.schemas import (
    GenerateQuestionsRequest, GenerateQuestionsResponse,
    SubmitAnswerRequest, AnswerEvaluation, Question
)
from app.agents.question_agent import QuestionGenerationAgent, AnswerEvaluationAgent
from app.core.config import settings
from app.core.database import get_redis_client, get_chroma_client
import json
from app.parsers.ppt_parser import DocumentIndexer

logger = logging.getLogger(__name__)
router = APIRouter()

question_agent = QuestionGenerationAgent()
evaluation_agent = AnswerEvaluationAgent()


@router.post("/generate", response_model=GenerateQuestionsResponse)
async def generate_questions(request: GenerateQuestionsRequest):
    """
    生成题目
    """
    try:
        # 读取PPT内容
        file_path = None
        for ext in settings.allowed_extensions:
            temp_path = os.path.join(settings.UPLOAD_DIR, f"{request.file_id}{ext}")
            if os.path.exists(temp_path):
                file_path = temp_path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 简单提取内容（实际应用可以从已解析的数据中获取）
        from app.parsers.ppt_parser import PPTParser
        parser = PPTParser(file_path)
        parse_result = await parser.parse()

        # 确保向量索引存在
        chroma_client = get_chroma_client()
        indexer = DocumentIndexer(chroma_client)
        await indexer.index_document(request.file_id, parse_result["slides"])
        
        # 准备学习内容（向量检索优先）
        content_parts = []
        context_hint = request.focus_query

        if request.focus_query:
            # 基于向量检索定位知识点
            search_results = await indexer.search_similar(
                query=request.focus_query,
                file_id=request.file_id,
                top_k=request.top_k
            )

            if search_results and search_results.get("documents"):
                for i, doc in enumerate(search_results["documents"][0]):
                    metadata = search_results["metadatas"][0][i] if search_results.get("metadatas") else {}
                    slide_no = metadata.get("slide_number")
                    title = metadata.get("title", "")
                    content_parts.append(f"# Slide {slide_no}: {title}\n{doc}")
        
        # 如果检索无结果，回退到按页/全部内容
        if not content_parts:
            for slide in parse_result["slides"]:
                if request.slide_numbers and slide.slide_number not in request.slide_numbers:
                    continue

                slide_text = f"# {slide.title or 'Slide ' + str(slide.slide_number)}\n"
                slide_text += "\n".join(slide.content)
                if slide.ocr_texts:
                    slide_text += f"\nOCR: {' '.join(slide.ocr_texts)}"
                if slide.notes:
                    slide_text += f"\n备注: {slide.notes}"
                content_parts.append(slide_text)

        content = "\n\n".join(content_parts)
        
        # 生成题目
        gen_result = await question_agent.generate_questions(
            content=content,
            num_questions=request.num_questions,
            question_types=request.question_types,
            difficulty_levels=request.difficulty_levels,
            strict_context=request.strict_context,
            context_hint=context_hint
        )
        questions = gen_result.get("questions", [])
        llm_validation = gen_result.get("llm_validation")
        
        # 缓存题目到Redis
        redis_client = await get_redis_client()
        for q in questions:
            await redis_client.setex(
                f"question:{q.question_id}",
                3600 * 24,  # 24小时过期
                q.model_dump_json()
            )
        
        logger.info(f"生成题目成功: {len(questions)}道")
        
        return GenerateQuestionsResponse(
            file_id=request.file_id,
            questions=questions,
            llm_validation=llm_validation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成题目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate", response_model=AnswerEvaluation)
async def evaluate_answer(request: SubmitAnswerRequest):
    """
    评估答案
    """
    try:
        # 从Redis获取题目
        redis_client = await get_redis_client()
        question_json = await redis_client.get(f"question:{request.question_id}")
        
        if not question_json:
            raise HTTPException(status_code=404, detail="题目不存在或已过期")
        
        question = Question.model_validate_json(question_json)
        
        # 评估答案
        evaluation = await evaluation_agent.evaluate_answer(
            question=question,
            user_answer=request.user_answer
        )
        
        # 如果答错，记录到错题本
        if not evaluation.is_correct:
            await _record_mistake(request.question_id, evaluation, question, request.user_id or "default")
        
        logger.info(f"评估答案完成: {request.question_id}, 得分: {evaluation.score}")
        
        return evaluation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"评估答案失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _record_mistake(question_id: str, evaluation: AnswerEvaluation, question: Question, user_id: str):
    """记录错题"""
    try:
        redis_client = await get_redis_client()
        
        # 添加到错题集合（按用户）
        await redis_client.sadd(f"mistakes:{user_id}", question_id)
        await redis_client.sadd("mistakes:all", question_id)
        
        # 记录错题详情
        mistake_data = {
            "question_id": question_id,
            "user_id": user_id,
            "question": question.model_dump(),
            "evaluation": evaluation.model_dump(),
            "timestamp": str(datetime.now())
        }
        
        await redis_client.setex(
            f"mistake:{user_id}:{question_id}",
            3600 * 24 * 30,  # 30天过期
            json.dumps(mistake_data, ensure_ascii=False)
        )

        # 兼容旧键（保留一份）
        await redis_client.setex(
            f"mistake:{question_id}",
            3600 * 24 * 30,
            json.dumps(mistake_data, ensure_ascii=False)
        )

        # 更新用户画像（简单统计）
        profile_key = f"user:{user_id}:profile"
        profile_json = await redis_client.get(profile_key)
        profile = json.loads(profile_json) if profile_json else {
            "user_id": user_id,
            "mistake_count": 0,
            "error_types": {},
            "focus_topics": {},
            "last_focus_topic": None
        }

        profile["mistake_count"] = int(profile.get("mistake_count", 0)) + 1
        error_type = evaluation.error_type or "未知"
        profile["error_types"][error_type] = int(profile["error_types"].get(error_type, 0)) + 1

        # 优先使用题目标签作为知识点
        tags = question.tags or []
        if tags:
            for tag in tags:
                profile["focus_topics"][tag] = int(profile["focus_topics"].get(tag, 0)) + 1
        else:
            fallback_topic = (question.content or "").strip()[:30]
            if fallback_topic:
                profile["focus_topics"][fallback_topic] = int(profile["focus_topics"].get(fallback_topic, 0)) + 1

        # 更新最后关注点
        if profile["focus_topics"]:
            profile["last_focus_topic"] = max(profile["focus_topics"], key=profile["focus_topics"].get)

        await redis_client.set(profile_key, json.dumps(profile, ensure_ascii=False))
        
        logger.info(f"错题已记录: {question_id}")
        
    except Exception as e:
        logger.error(f"记录错题失败: {e}")


from datetime import datetime
