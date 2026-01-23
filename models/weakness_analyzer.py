from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime, timedelta
import numpy as np
from models import Question

class WeaknessAnalyzer:
    """分析用户弱点，生成错题本和个性化建议"""
    
    def __init__(self, mongo_client):
        self.mongo_client = mongo_client
        self.collection = mongo_client.db["user_performance"]
    
    def analyze_user_weaknesses(self, user_id: str, time_range_days: int = 30) -> Dict:
        """分析用户弱点"""
        
        # 查询用户历史表现
        start_date = datetime.now() - timedelta(days=time_range_days)
        
        performances = list(self.collection.find({
            "user_id": user_id,
            "timestamp": {"$gte": start_date}
        }))
        
        if not performances:
            return {"status": "no_data", "message": "暂无历史数据"}
        
        # 按标签分析
        tag_stats = defaultdict(lambda: {"total": 0, "correct": 0, "questions": []})
        
        for perf in performances:
            for tag in perf.get("tags", []):
                tag_stats[tag]["total"] += 1
                tag_stats[tag]["correct"] += 1 if perf["is_correct"] else 0
                if not perf["is_correct"]:
                    tag_stats[tag]["questions"].append({
                        "question_id": perf["question_id"],
                        "question": perf["question"],
                        "user_answer": perf["user_answer"],
                        "correct_answer": perf["correct_answer"]
                    })
        
        # 计算准确率并识别弱点
        weaknesses = []
        for tag, stats in tag_stats.items():
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            if accuracy < 0.7:  # 准确率低于70%视为弱点
                weaknesses.append({
                    "tag": tag,
                    "accuracy": round(accuracy * 100, 1),
                    "total_attempts": stats["total"],
                    "error_questions": stats["questions"][:5]  # 取最近的5个错题
                })
        
        # 按准确率排序
        weaknesses.sort(key=lambda x: x["accuracy"])
        
        return {
            "user_id": user_id,
            "analysis_period": f"最近{time_range_days}天",
            "total_attempts": len(performances),
            "overall_accuracy": self._calculate_overall_accuracy(performances),
            "weaknesses": weaknesses,
            "recommendations": self._generate_recommendations(weaknesses),
            "trend": self._analyze_trend(performances)
        }
    
    def generate_targeted_questions(
        self, 
        weaknesses: List[Dict], 
        question_bank: List[Question]
    ) -> List[Question]:
        """针对弱点生成专项练习题"""
        
        targeted_questions = []
        weak_tags = [weakness["tag"] for weakness in weaknesses[:3]]  # 针对前3个弱点
        
        for question in question_bank:
            # 检查问题是否包含弱点标签
            if any(tag in question.tags for tag in weak_tags):
                targeted_questions.append(question)
                
                if len(targeted_questions) >= 5:  # 生成5道针对性题目
                    break
        
        return targeted_questions
    
    def create_study_plan(self, weaknesses: List[Dict]) -> Dict:
        """创建个性化学习计划"""
        
        plan = {
            "priority_areas": [],
            "daily_goals": [],
            "recommended_resources": [],
            "timeline": "2周提升计划"
        }
        
        for i, weakness in enumerate(weaknesses[:3]):  # 重点关注前3个弱点
            plan["priority_areas"].append({
                "area": weakness["tag"],
                "current_level": f"{weakness['accuracy']}%",
                "target_level": "85%",
                "suggested_actions": [
                    f"复习{weakness['tag']}相关概念",
                    f"完成专项练习题（{len(weakness['error_questions'])}道）",
                    "整理错题笔记"
                ]
            })
        
        # 生成每日学习目标
        for day in range(1, 8):
            plan["daily_goals"].append({
                "day": day,
                "focus": weaknesses[day % len(weaknesses)]["tag"] if weaknesses else "综合复习",
                "tasks": [
                    "完成10道练习题",
                    "复习错题本",
                    "总结知识点"
                ]
            })
        
        return plan
    
    def _calculate_overall_accuracy(self, performances: List[Dict]) -> float:
        """计算总体准确率"""
        if not performances:
            return 0.0
        
        correct = sum(1 for p in performances if p["is_correct"])
        return round(correct / len(performances) * 100, 1)
    
    def _generate_recommendations(self, weaknesses: List[Dict]) -> List[str]:
        """生成学习建议"""
        recommendations = []
        
        if not weaknesses:
            recommendations.append("表现良好，可以挑战更高难度题目")
            return recommendations
        
        # 根据弱点生成建议
        for weakness in weaknesses[:3]:
            if weakness["accuracy"] < 50:
                rec = f"【紧急】{weakness['tag']}概念薄弱（准确率{weakness['accuracy']}%），建议系统复习"
            elif weakness["accuracy"] < 70:
                rec = f"【重点】{weakness['tag']}需要加强（准确率{weakness['accuracy']}%）"
            else:
                rec = f"【巩固】{weakness['tag']}基本掌握，可以适当练习"
            
            recommendations.append(rec)
        
        # 添加通用建议
        recommendations.extend([
            "建议每天花30分钟复习错题",
            "建立知识点之间的联系，形成知识网络",
            "尝试向他人讲解概念，加深理解"
        ])
        
        return recommendations
    
    def _analyze_trend(self, performances: List[Dict]) -> Dict:
        """分析学习趋势"""
        if len(performances) < 5:
            return {"trend": "insufficient_data", "message": "数据不足分析趋势"}
        
        # 按时间分组计算准确率
        performances.sort(key=lambda x: x["timestamp"])
        
        # 简单趋势分析
        recent = performances[-5:]
        older = performances[-10:-5] if len(performances) >= 10 else performances[:5]
        
        recent_acc = self._calculate_overall_accuracy(recent)
        older_acc = self._calculate_overall_accuracy(older)
        
        trend = "improving" if recent_acc > older_acc else "declining" if recent_acc < older_acc else "stable"
        
        return {
            "trend": trend,
            "recent_accuracy": recent_acc,
            "previous_accuracy": older_acc,
            "change": round(recent_acc - older_acc, 1)
        }