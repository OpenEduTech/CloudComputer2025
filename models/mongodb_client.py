from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from datetime import datetime
from typing import Dict, Any, List
import json
from models import Question, EvaluationResult


class MongoDBClient:
    """MongoDB客户端，处理数据持久化"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """连接MongoDB"""
        try:
            self.client = MongoClient(
                self.config.MONGO_URI,
                serverSelectionTimeoutMS=5000
            )
            # 测试连接
            self.client.server_info()
            self.db = self.client[self.config.MONGO_DB]
            
            # 创建索引
            self._create_indexes()
            print("MongoDB connected successfully")
        except ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")
            # 可以在这里实现降级方案
            raise
    
    def _create_indexes(self):
        """创建必要的索引"""
        # 用户表现集合索引
        self.db.user_performance.create_index([
            ("user_id", ASCENDING),
            ("timestamp", DESCENDING)
        ])
        
        self.db.user_performance.create_index([
            ("user_id", ASCENDING),
            ("tags", ASCENDING)
        ])
        
        # 错题本集合索引
        self.db.wrong_questions.create_index([
            ("user_id", ASCENDING),
            ("question_id", ASCENDING)
        ], unique=True)
        
        self.db.wrong_questions.create_index([
            ("user_id", ASCENDING),
            ("review_count", ASCENDING)
        ])
        
        # 学习进度集合索引
        self.db.learning_progress.create_index([
            ("user_id", ASCENDING),
            ("subject", ASCENDING)
        ], unique=True)
    
    def save_user_performance(
        self, 
        user_id: str, 
        question: Question,
        evaluation: EvaluationResult,
        user_answer: str
    ) -> str:
        """保存用户答题表现"""
        
        record = {
            "user_id": user_id,
            "question_id": question.question_id,
            "question": question.content,
            "question_type": question.question_type,
            "user_answer": user_answer,
            "correct_answer": question.correct_answer,
            "is_correct": evaluation.is_correct,
            "score": evaluation.score,
            "tags": question.tags,
            "difficulty": question.difficulty,
            "feedback": evaluation.feedback,
            "mistakes": evaluation.mistakes,
            "timestamp": datetime.now(),
            "metadata": {
                "explanation": question.explanation,
                "source_chunks": question.source_chunks[:3]
            }
        }
        
        # 保存到user_performance集合
        result = self.db.user_performance.insert_one(record)
        
        # 如果是错题，添加到错题本
        if not evaluation.is_correct:
            self._add_to_wrong_questions(user_id, question, evaluation, user_answer)
        
        # 更新学习进度
        self._update_learning_progress(user_id, question.tags, evaluation.is_correct)
        
        return str(result.inserted_id)
    
    def _add_to_wrong_questions(
        self, 
        user_id: str, 
        question: Question,
        evaluation: EvaluationResult,
        user_answer: str
    ):
        """添加错题到错题本"""
        
        wrong_question = {
            "user_id": user_id,
            "question_id": question.question_id,
            "question": question.content,
            "question_type": question.question_type,
            "user_answer": user_answer,
            "correct_answer": question.correct_answer,
            "mistakes": evaluation.mistakes,
            "difficulty": question.difficulty,
            "tags": question.tags,
            "first_wrong_time": datetime.now(),
            "review_count": 0,
            "mastered": False,
            "detailed_explanation": evaluation.detailed_explanation,
            "suggested_improvement": evaluation.suggested_improvement
        }
        
        # 使用upsert避免重复
        # 注意：last_wrong_time 和 wrong_count 通过单独的操作符更新，不在 $setOnInsert 中
        self.db.wrong_questions.update_one(
            {
                "user_id": user_id,
                "question_id": question.question_id
            },
            {
                "$setOnInsert": wrong_question,
                "$set": {"last_wrong_time": datetime.now()},
                "$inc": {"wrong_count": 1}
            },
            upsert=True
        )
    
    def _update_learning_progress(
        self, 
        user_id: str, 
        tags: List[str],
        is_correct: bool
    ):
        """更新学习进度
        
        参数:
            user_id: 用户ID
            tags: 题目标签列表
            is_correct: 是否答对
        """
        # 如果没有标签，使用默认标签
        if not tags:
            tags = ["general"]
        
        # 只更新前3个标签
        for tag in tags[:3]:
            # 跳过空标签
            if not tag or tag.strip() == "":
                continue
            
            update_query = {
                "user_id": user_id,
                "subject": tag  # 使用 subject 字段名匹配索引定义
            }
            
            update_data = {
                "$inc": {
                    "total_attempts": 1,
                    "correct_attempts": 1 if is_correct else 0
                },
                "$set": {
                    "last_attempt": datetime.now(),
                    "accuracy": None  # 将在应用层计算
                },
                "$setOnInsert": {
                    "first_attempt": datetime.now()
                }
            }
            
            self.db.learning_progress.update_one(
                update_query,
                update_data,
                upsert=True
            )
    
    def get_wrong_questions(
        self, 
        user_id: str, 
        limit: int = 20,
        tags: List[str] = None
    ) -> List[Dict]:
        """获取用户的错题"""
        
        query = {"user_id": user_id, "mastered": False}
        if tags:
            query["tags"] = {"$in": tags}
        
        return list(self.db.wrong_questions.find(
            query,
            sort=[("last_wrong_time", DESCENDING)],
            limit=limit
        ))
    
    def get_user_statistics(self, user_id: str) -> Dict:
        """获取用户统计信息"""
        
        # 总体统计
        total_attempts = self.db.user_performance.count_documents({"user_id": user_id})
        correct_attempts = self.db.user_performance.count_documents({
            "user_id": user_id,
            "is_correct": True
        })
        
        overall_accuracy = correct_attempts / total_attempts if total_attempts > 0 else 0
        
        # 按难度统计
        difficulty_stats = {}
        for difficulty in ["easy", "medium", "hard"]:
            total = self.db.user_performance.count_documents({
                "user_id": user_id,
                "difficulty": difficulty
            })
            correct = self.db.user_performance.count_documents({
                "user_id": user_id,
                "difficulty": difficulty,
                "is_correct": True
            })
            
            if total > 0:
                difficulty_stats[difficulty] = {
                    "total": total,
                    "correct": correct,
                    "accuracy": correct / total
                }
        
        # 按标签统计（前10个）
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$unwind": "$tags"},
            {"$group": {
                "_id": "$tags",
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}}
            }},
            {"$project": {
                "tag": "$_id",
                "total": 1,
                "correct": 1,
                "accuracy": {"$divide": ["$correct", "$total"]}
            }},
            {"$sort": {"total": DESCENDING}},
            {"$limit": 10}
        ]
        
        tag_stats = list(self.db.user_performance.aggregate(pipeline))
        
        return {
            "user_id": user_id,
            "total_attempts": total_attempts,
            "correct_attempts": correct_attempts,
            "overall_accuracy": overall_accuracy,
            "difficulty_stats": difficulty_stats,
            "tag_stats": tag_stats,
            "wrong_questions_count": self.db.wrong_questions.count_documents({
                "user_id": user_id,
                "mastered": False
            })
        }
    
    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()