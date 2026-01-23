from app.services.llm_factory import LLMFactory
from app.models.quiz import QuizResult
from typing import List, Dict, Tuple
from datetime import datetime
import json

class TutorAgent:
    def __init__(self):
        self.llm = LLMFactory.get_deepseek_llm()

    async def _verify_recommendations(self, mistakes_summary: str, recommendations: List[str]) -> Tuple[bool, str]:
        """
        验证学习建议是否针对性强、可行，避免泛泛而谈
        返回: (是否通过验证, 问题描述)
        """
        verification_prompt = f"""你是一位教育质量审核员，负责检查学习建议是否有针对性和可行性。

学生错题摘要：
{mistakes_summary}

生成的学习建议：
{json.dumps(recommendations, ensure_ascii=False, indent=2)}

请严格判断：
1. 建议是否针对学生的具体错误类型和薄弱知识点？
2. 建议是否具体可行，而不是"多练习"、"认真学习"这类空话？
3. 建议是否有实际指导意义，能帮助学生改进？
4. 建议数量是否合理（3-5条）？
5. 是否存在与错题无关的建议（幻觉）？

返回JSON格式：
{{
  "is_valid": true/false,
  "reason": "简要说明建议质量好 或 指出具体问题"
}}

只返回JSON，不要其他文字。"""

        try:
            response = await self.llm.ainvoke(verification_prompt)
            content = response.content.strip()
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            return result.get("is_valid", True), result.get("reason", "未知原因")
        except Exception as e:
            print(f"⚠️  验证建议时出错: {e}")
            # 如果验证失败，默认通过
            return True, "验证系统异常，默认通过"

    async def update_analysis_cache(self, user_id: str) -> Dict:
        """
        更新用户的错题分析缓存
        在提交测验后自动调用
        """
        from app.core.database import db
        from bson import ObjectId
        
        print(f"🔄 更新用户 {user_id} 的错题分析缓存...")
        
        # 获取用户最近的测验结果
        cursor = db.db.quiz_results.find({"user_id": user_id}).sort("created_at", -1)
        history_data = await cursor.to_list(length=20)
        history = [QuizResult(**r) for r in history_data]
        
        # 执行分析
        analysis = await self.analyze_mistakes(history)
        
        # 保存到缓存
        cache_data = {
            "user_id": user_id,
            "weak_points": analysis["weak_points"],
            "recommendations": analysis["recommendations"],
            "total_mistakes": len(analysis["recent_mistakes"]),
            "last_updated": datetime.utcnow()
        }
        
        # 更新或插入缓存
        await db.db.mistake_analysis_cache.update_one(
            {"user_id": user_id},
            {"$set": cache_data},
            upsert=True
        )
        
        print(f"✅ 错题分析缓存已更新")
        return analysis

    async def get_cached_analysis(self, user_id: str) -> Dict:
        """
        获取缓存的错题分析
        如果缓存不存在或过期，则重新分析
        """
        from app.core.database import db
        from datetime import datetime, timedelta
        
        # 尝试从缓存获取
        cache = await db.db.mistake_analysis_cache.find_one({"user_id": user_id})
        
        if cache:
            # 检查缓存是否过期（超过1小时）
            last_updated = cache.get("last_updated")
            if last_updated and datetime.utcnow() - last_updated < timedelta(hours=1):
                print(f"✅ 使用缓存的错题分析（更新于 {last_updated}）")
                
                # 获取最近错题详情
                cursor = db.db.quiz_results.find({"user_id": user_id}).sort("created_at", -1)
                history_data = await cursor.to_list(length=20)
                history = [QuizResult(**r) for r in history_data]
                
                recent_mistakes = []
                for result in history:
                    from bson import ObjectId
                    try:
                        quiz = await db.db.quiz.find_one({"_id": ObjectId(result.quiz_id)})
                        if not quiz:
                            continue
                            
                        questions_map = {q["id"]: q for q in quiz["questions"]}
                        
                        for grading in result.results:
                            if not grading.is_correct:
                                question_data = questions_map.get(grading.question_id)
                                if not question_data:
                                    continue
                                    
                                user_answer = ""
                                for ans in result.submission.answers:
                                    if ans.question_id == grading.question_id:
                                        user_answer = ans.user_answer
                                        break
                                
                                recent_mistakes.append({
                                    "question": question_data,
                                    "user_answer": user_answer,
                                    "result": {
                                        "question_id": grading.question_id,
                                        "is_correct": grading.is_correct,
                                        "score": grading.score,
                                        "feedback": grading.feedback,
                                        "error_type": grading.error_type,
                                        "explanation": grading.analysis
                                    }
                                })
                    except Exception as e:
                        print(f"Error processing result: {e}")
                        continue
                
                return {
                    "recent_mistakes": recent_mistakes,
                    "weak_points": cache.get("weak_points", []),
                    "recommendations": cache.get("recommendations", [])
                }
        
        # 缓存不存在或过期，重新分析
        print(f"⚠️  缓存不存在或已过期，重新分析...")
        return await self.update_analysis_cache(user_id)

    async def analyze_mistakes(self, history: List[QuizResult]) -> Dict:
        # Collect all mistakes with full context
        recent_mistakes = []
        weak_points_map = {}
        
        for result in history:
            # Get quiz to access questions
            from app.core.database import db
            from bson import ObjectId
            try:
                quiz = await db.db.quiz.find_one({"_id": ObjectId(result.quiz_id)})
                if not quiz:
                    continue
                    
                questions_map = {q["id"]: q for q in quiz["questions"]}
                
                for i, grading in enumerate(result.results):
                    if not grading.is_correct:
                        question_data = questions_map.get(grading.question_id)
                        if not question_data:
                            continue
                            
                        # Get user answer from submission
                        user_answer = ""
                        for ans in result.submission.answers:
                            if ans.question_id == grading.question_id:
                                user_answer = ans.user_answer
                                break
                        
                        # Add to recent mistakes
                        recent_mistakes.append({
                            "question": question_data,
                            "user_answer": user_answer,
                            "result": {
                                "question_id": grading.question_id,
                                "is_correct": grading.is_correct,
                                "score": grading.score,
                                "feedback": grading.feedback,
                                "error_type": grading.error_type,
                                "explanation": grading.analysis
                            }
                        })
                        
                        # Track weak points
                        kp = question_data.get("knowledge_point", "General")
                        if kp not in weak_points_map:
                            weak_points_map[kp] = {
                                "knowledge_point": kp,
                                "error_count": 0,
                                "error_types": set()
                            }
                        weak_points_map[kp]["error_count"] += 1
                        if grading.error_type:
                            weak_points_map[kp]["error_types"].add(grading.error_type)
            except Exception as e:
                print(f"Error processing result: {e}")
                continue
        
        # Convert weak points to list
        weak_points = []
        for wp in weak_points_map.values():
            weak_points.append({
                "knowledge_point": wp["knowledge_point"],
                "error_count": wp["error_count"],
                "error_types": list(wp["error_types"])
            })
        
        # Sort by error count
        weak_points.sort(key=lambda x: x["error_count"], reverse=True)
        
        # Generate recommendations using LLM
        recommendations = []
        if len(recent_mistakes) > 0:
            mistakes_summary = ""
            for mistake in recent_mistakes[:10]:  # Limit to 10 most recent
                mistakes_summary += f"- 知识点: {mistake['question']['knowledge_point']}, 错误类型: {mistake['result']['error_type']}\n"
            
            prompt = f"""你是一位个性化导师。根据学生的错题历史，提供3-5条具体的学习建议。

错题摘要:
{mistakes_summary}

要求：
1. 建议必须针对学生的具体错误类型和薄弱知识点
2. 建议必须具体可行，给出明确的学习方法或练习方向
3. 避免"多练习"、"认真学习"这类空泛建议
4. 每条建议要有实际指导意义

请以JSON格式输出，包含一个recommendations数组，每条建议都是具体可行的学习行动。
只返回JSON，不要其他文字。

示例格式:
{{"recommendations": ["针对电磁感应概念理解不足，建议重点复习法拉第定律的推导过程", "建议2", "建议3"]}}
"""
            
            try:
                response = await self.llm.ainvoke(prompt)
                content = response.content
                json_str = content.strip()
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                
                result = json.loads(json_str)
                recommendations = result.get("recommendations", [])
                
                # Check layer: 验证建议质量
                print("🔍 验证学习建议质量...")
                is_valid, reason = await self._verify_recommendations(mistakes_summary, recommendations)
                
                if is_valid:
                    print(f"  ✓ 建议验证通过: {reason[:50]}...")
                else:
                    print(f"  ⚠️  建议验证失败: {reason}")
                    print(f"  🔄 使用默认建议")
                    recommendations = [
                        f"重点复习薄弱知识点：{', '.join([wp['knowledge_point'] for wp in weak_points[:3]])}",
                        "针对错误类型进行专项练习，特别注意概念理解和逻辑推理",
                        "建议做题时先仔细审题，理解题目要求后再作答",
                        "对于错题，建议整理到错题本并定期复习"
                    ]
                    
            except Exception as e:
                print(f"Error generating recommendations: {e}")
                recommendations = ["继续练习薄弱知识点", "仔细阅读题目要求", "多做类似题目巩固理解"]
        
        return {
            "recent_mistakes": recent_mistakes,
            "weak_points": weak_points,
            "recommendations": recommendations
        }

tutor_agent = TutorAgent()
