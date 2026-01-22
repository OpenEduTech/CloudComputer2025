"""
错题本API
"""
from fastapi import APIRouter, HTTPException
import logging
import json
from typing import List

from app.models.schemas import MistakeRecord, MistakeStats, Question, AnswerEvaluation, RemediationRequest, RemediationResponse
from app.core.database import get_redis_client
from app.agents.remediation_agent import RemediationAgent

logger = logging.getLogger(__name__)
router = APIRouter()
remediation_agent = RemediationAgent()


@router.get("/list")
async def list_mistakes(limit: int = 20, user_id: str = "default"):
    """
    获取错题列表
    """
    try:
        redis_client = await get_redis_client()
        
        # 获取用户错题ID
        mistake_ids = await redis_client.smembers(f"mistakes:{user_id}")
        
        if not mistake_ids:
            legacy_ids = await redis_client.smembers("mistakes:all")
            mistake_ids = legacy_ids
        if not mistake_ids:
            return {
                "success": True,
                "mistakes": [],
                "total": 0
            }
        
        # 获取错题详情
        mistakes = []
        for mistake_id in list(mistake_ids)[:limit]:
            mistake_json = await redis_client.get(f"mistake:{user_id}:{mistake_id}")
            if not mistake_json:
                mistake_json = await redis_client.get(f"mistake:{mistake_id}")
            if mistake_json:
                mistake_data = json.loads(mistake_json)
                # 补齐题目信息
                if not mistake_data.get("question"):
                    question_json = await redis_client.get(f"question:{mistake_id}")
                    if question_json:
                        try:
                            question = Question.model_validate_json(question_json)
                            mistake_data["question"] = question.model_dump()
                        except Exception:
                            pass
                mistakes.append(mistake_data)
        
        return {
            "success": True,
            "mistakes": mistakes,
            "total": len(mistakes)
        }
        
    except Exception as e:
        logger.error(f"获取错题列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MistakeStats)
async def get_mistake_stats(user_id: str = "default"):
    """
    获取错题统计
    """
    try:
        redis_client = await get_redis_client()
        
        # 获取用户错题
        mistake_ids = await redis_client.smembers(f"mistakes:{user_id}")
        if not mistake_ids:
            mistake_ids = await redis_client.smembers("mistakes:all")
        
        # 统计数据
        total_mistakes = len(mistake_ids)
        by_difficulty = {"easy": 0, "medium": 0, "hard": 0}
        by_type = {"choice": 0, "short_answer": 0, "true_false": 0}
        weak_topics = []
        
        for mistake_id in mistake_ids:
            mistake_json = await redis_client.get(f"mistake:{user_id}:{mistake_id}")
            if not mistake_json:
                mistake_json = await redis_client.get(f"mistake:{mistake_id}")
            if mistake_json:
                mistake_data = json.loads(mistake_json)
                evaluation = mistake_data.get("evaluation", {})
                error_type = evaluation.get("error_type")
                if error_type and error_type not in weak_topics:
                    weak_topics.append(error_type)
        
        improvement_rate = 0.0
        if total_mistakes > 0:
            # 简单计算：这里可以根据复习次数等计算
            improvement_rate = 0.0
        
        return MistakeStats(
            user_id=user_id,
            total_mistakes=total_mistakes,
            by_difficulty=by_difficulty,
            by_type=by_type,
            weak_topics=weak_topics,
            improvement_rate=improvement_rate
        )
        
    except Exception as e:
        logger.error(f"获取错题统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{question_id}")
async def remove_mistake(question_id: str, user_id: str = "default"):
    """
    从错题本中移除
    """
    try:
        redis_client = await get_redis_client()
        
        # 从集合中移除
        await redis_client.srem(f"mistakes:{user_id}", question_id)
        await redis_client.srem("mistakes:all", question_id)
        
        # 删除详情
        await redis_client.delete(f"mistake:{user_id}:{question_id}")
        await redis_client.delete(f"mistake:{question_id}")
        
        return {
            "success": True,
            "message": "已从错题本中移除"
        }
        
    except Exception as e:
        logger.error(f"移除错题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{question_id}/review")
async def mark_as_reviewed(question_id: str, user_id: str = "default"):
    """
    标记为已复习
    """
    try:
        redis_client = await get_redis_client()
        
        mistake_json = await redis_client.get(f"mistake:{user_id}:{question_id}")
        if not mistake_json:
            mistake_json = await redis_client.get(f"mistake:{question_id}")
        if not mistake_json:
            raise HTTPException(status_code=404, detail="错题不存在")
        
        mistake_data = json.loads(mistake_json)
        mistake_data["reviewed"] = True
        mistake_data["review_count"] = mistake_data.get("review_count", 0) + 1
        
        await redis_client.setex(
            f"mistake:{user_id}:{question_id}",
            3600 * 24 * 30,
            json.dumps(mistake_data, ensure_ascii=False)
        )
        await redis_client.setex(
            f"mistake:{question_id}",
            3600 * 24 * 30,
            json.dumps(mistake_data, ensure_ascii=False)
        )
        
        return {
            "success": True,
            "message": "已标记为复习",
            "review_count": mistake_data["review_count"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记复习失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remediate", response_model=RemediationResponse)
async def remediate_mistake(request: RemediationRequest):
    """生成个性化纠偏内容"""
    try:
        redis_client = await get_redis_client()

        # 获取题目
        question_json = await redis_client.get(f"question:{request.question_id}")
        if not question_json:
            raise HTTPException(status_code=404, detail="题目不存在或已过期")
        question = Question.model_validate_json(question_json)

        # 获取错题记录（含评估）
        mistake_json = await redis_client.get(f"mistake:{request.user_id}:{request.question_id}")
        if not mistake_json:
            mistake_json = await redis_client.get(f"mistake:{request.question_id}")
        if not mistake_json:
            raise HTTPException(status_code=404, detail="错题记录不存在")
        mistake_data = json.loads(mistake_json)
        evaluation = mistake_data.get("evaluation", {})

        # 获取用户画像/关注知识点（来自系统记录）
        profile_json = await redis_client.get(f"user:{request.user_id}:profile")
        profile = json.loads(profile_json) if profile_json else {}
        user_profile = json.dumps(profile, ensure_ascii=False)
        focus_topic = profile.get("last_focus_topic")
        if not focus_topic:
            tags = (question.tags or [])
            focus_topic = tags[0] if tags else (question.content or "")[:30]

        result = await remediation_agent.generate_remediation(
            question=question.content,
            correct_answer=question.correct_answer,
            user_answer=evaluation.get("user_answer", ""),
            error_type=evaluation.get("error_type"),
            user_profile=user_profile,
            focus_topic=focus_topic
        )

        return RemediationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成纠偏内容失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
