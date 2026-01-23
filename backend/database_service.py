import redis
from redis import ConnectionPool
from redis.cluster import RedisCluster
from pymongo import MongoClient
from pymongo import ReadPreference
from datetime import datetime, timedelta
import json
import bcrypt
from backend.config import AppConfig


class MemoryCollection:
    """内存集合类，用于在数据库连接失败时替代MongoDB集合"""
    def __init__(self):
        self.data = []
        self.indexes = set()
    
    def insert_one(self, document):
        self.data.append(document)
        return type('obj', (object,), {'inserted_id': len(self.data) - 1})
    
    def update_one(self, filter_dict, update_dict):
        for doc in self.data:
            if all(doc.get(k) == v for k, v in filter_dict.items()):
                # 处理 $inc 操作
                if '$inc' in update_dict:
                    for field, value in update_dict['$inc'].items():
                        doc[field] = doc.get(field, 0) + value
                # 处理 $set 操作
                if '$set' in update_dict:
                    for field, value in update_dict['$set'].items():
                        doc[field] = value
                return type('obj', (object,), {'modified_count': 1})
        return type('obj', (object,), {'modified_count': 0})
    
    def find_one(self, filter_dict, projection=None):
        for doc in self.data:
            if all(doc.get(k) == v for k, v in filter_dict.items()):
                if projection:
                    return {k: v for k, v in doc.items() if k in projection or k not in projection}
                return doc
        return None
    
    def find(self, filter_dict, projection=None):
        results = []
        for doc in self.data:
            if all(doc.get(k) == v for k, v in filter_dict.items()):
                if projection:
                    results.append({k: v for k, v in doc.items() if k in projection or k not in projection})
                else:
                    results.append(doc)
        return results
    
    def create_index(self, field, unique=False, descending=False):
        # 修复：如果field是列表，将其转换为元组以便哈希
        if isinstance(field, list):
            field = tuple(field)
        self.indexes.add(field)
        return True
    
    def count_documents(self, filter_dict):
        return len(self.find(filter_dict))
    
    def aggregate(self, pipeline):
        # 简单实现，仅支持 $match 和 $group 操作
        data = self.data
        
        # 1. 处理 $match
        if pipeline and '$match' in pipeline[0]:
            match_filter = pipeline[0]['$match']
            data = [doc for doc in data if all(doc.get(k) == v for k, v in match_filter.items())]
            # 移除已处理的 stage，继续处理后续
            pipeline = pipeline[1:]
            
        # 2. 处理 $group
        if pipeline and '$group' in pipeline[0]:
            group_stage = pipeline[0]['$group']
            if group_stage.get('_id') is None and 'avg_score' in group_stage:
                total = sum(doc.get('total_score', 0) for doc in data)
                count = len(data)
                avg = total / count if count > 0 else 0
                return [{'avg_score': avg}]
        return []

class DBManager:
    def __init__(self):
        # 数据库连接状态
        self.mongo_connected = False
        self.redis_connected = False
        
        # 连接 MongoDB - 优化配置
        try:
            self.mongo_client = MongoClient(
                AppConfig.MONGO_URI,
                maxPoolSize=200,  # 增大连接池大小以支持高并发
                minPoolSize=20,    # 增大最小连接数
                maxIdleTimeMS=30000,  # 连接最大空闲时间
                serverSelectionTimeoutMS=5000,  # 服务器选择超时
                socketTimeoutMS=5000  # 套接字超时
            )
            self.db = self.mongo_client["study_agent_db"]
            self.exam_col = self.db["exam_records"]
            self.mistake_col = self.db["error_questions"]
            self.user_col = self.db["users"]
            self.review_col = self.db["review_tasks"]
            
            # 验证 MongoDB 连接
            self.mongo_client.admin.command('ping')
            print("✅ MongoDB 连接成功")
            self.mongo_connected = True
            
            # 创建索引以提高查询性能
            self._create_indexes()
        except Exception as e:
            print(f"❌ MongoDB 连接失败: {e}")
            if AppConfig.DEV_MODE:
                print("⚠️ 开发模式下，将使用内存存储替代 MongoDB")
                self.exam_col = MemoryCollection()
                self.mistake_col = MemoryCollection()
                self.user_col = MemoryCollection()
                self.review_col = MemoryCollection()
                self.consolidation_col = MemoryCollection()
                self._create_indexes()
            else:
                # 非开发模式下直接抛出错误
                raise Exception(f"MongoDB 连接失败，无法继续运行: {e}") from e
        
        # 连接 Redis
        try:
            if AppConfig.REDIS_CLUSTER_NODES:
                print(f"尝试连接Redis集群: {AppConfig.REDIS_CLUSTER_NODES}")
                startup_nodes = []
                for node in AppConfig.REDIS_CLUSTER_NODES.split(','):
                    if ':' in node:
                        host, port = node.split(':')
                        startup_nodes.append({"host": host, "port": int(port)})
                
                self.redis_client = RedisCluster(
                    startup_nodes=startup_nodes,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    password=AppConfig.REDIS_PASSWORD if AppConfig.REDIS_PASSWORD else None
                )
            else:
                print("尝试连接Redis单节点...")
                redis_config = {
                    'host': AppConfig.REDIS_HOST,
                    'port': AppConfig.REDIS_PORT,
                    'decode_responses': True,
                    'max_connections': 200,
                    'socket_timeout': 3,
                    'socket_connect_timeout': 3,
                    'retry_on_timeout': True,
                    'health_check_interval': 30
                }
                
                password = AppConfig.REDIS_PASSWORD
                if password and password.strip():
                    redis_config['password'] = password
                
                redis_config['socket_keepalive'] = True
                redis_config['retry_on_error'] = [redis.exceptions.ConnectionError, redis.exceptions.TimeoutError]
                
                redis_pool = ConnectionPool(**redis_config)
                self.redis_client = redis.Redis(connection_pool=redis_pool)
            
            # 验证 Redis 连接
            try:
                self.redis_client.ping()
                print("✅ Redis 连接成功")
                self.redis_connected = True
                
                # 修复Redis RDB快照错误：禁用stop-writes-on-bgsave-error
                try:
                    self.redis_client.config_set('stop-writes-on-bgsave-error', 'no')
                except Exception as e:
                    pass
            except Exception as e:
                print(f"❌ Redis 连接失败: {e}")
                if "MISCONF" in str(e) or "stop-writes-on-bgsave-error" in str(e):
                    print("⚠️ Redis RDB快照错误：正在尝试修复...")
                self.redis_cache = {}
                self.redis_connected = False
        except Exception as e:
            print(f"❌ Redis 连接失败: {e}")
            self.redis_cache = {}
            self.redis_connected = False
        
        # 缓存键前缀
        self.CACHE_PREFIX = "learning_agent:"
        
        self.CACHE_EXPIRE = {
            'exam': 3600,
            'user_answers': 7200,
            'mistakes': 1800,
            'stats': 300,
            'review_task': 86400
        }
    
    def _create_indexes(self):
        """创建数据库索引以提高查询性能"""
        self.user_col.create_index("username", unique=True)
        self.user_col.create_index("email", unique=True)
        
        # ✅ 为错题集合创建索引 - 增加 user_id
        self.mistake_col.create_index("user_id")
        self.mistake_col.create_index([("user_id", 1), ("question", 1)], unique=True)  # 每个用户的题目唯一
        self.mistake_col.create_index([("error_times", -1)])
        self.mistake_col.create_index("difficulty")
        self.mistake_col.create_index([("last_error_time", -1)])
        self.mistake_col.create_index("knowledge_point")
        self.mistake_col.create_index("keyword")
        
        # ✅ 为试卷集合创建索引 - 增加 user_id
        self.exam_col.create_index("user_id")
        self.exam_col.create_index([("timestamp", -1)])
        self.exam_col.create_index("total_score")
        
        if hasattr(self, "review_col"):
            self.review_col.create_index("user_id")
            self.review_col.create_index("keyword")
            self.review_col.create_index("date")
    
    def _get_cache_key(self, key_type, identifier):
        """生成缓存键"""
        return f"{self.CACHE_PREFIX}{key_type}:{identifier}"
    
    def _build_review_identifier(self, user_id, keyword, chapter, section, difficulty, date_str):
        chapter_part = chapter if chapter is not None else ""
        section_part = section if section is not None else ""
        difficulty_part = difficulty if difficulty is not None else ""
        return f"{user_id}|{keyword}|{chapter_part}|{section_part}|{difficulty_part}|{date_str}"
    
    def cache_data(self, key_type, identifier, data, expire=None):
        """缓存数据到Redis或内存"""
        try:
            cache_key = self._get_cache_key(key_type, identifier)
            expire_time = expire or self.CACHE_EXPIRE.get(key_type, 3600)
            
            if self.redis_connected:
                # 序列化数据
                if isinstance(data, (dict, list)):
                    data_str = json.dumps(data, default=str)
                else:
                    data_str = str(data)
                
                try:
                    self.redis_client.set(cache_key, data_str, ex=expire_time)
                    return True
                except Exception as redis_error:
                    self.redis_connected = False
            
            # 使用内存缓存
            if not hasattr(self, 'redis_cache'):
                self.redis_cache = {}
            self.redis_cache[cache_key] = {
                'data': data,
                'expire_at': datetime.now() + timedelta(seconds=expire_time)
            }
            return True
        except Exception as e:
            print(f"缓存数据失败: {e}")
            return False
    
    def get_cached_data(self, key_type, identifier):
        """从Redis或内存获取缓存数据"""
        try:
            cache_key = self._get_cache_key(key_type, identifier)
            
            if self.redis_connected:
                try:
                    data_str = self.redis_client.get(cache_key)
                    if data_str:
                        try:
                            return json.loads(data_str)
                        except json.JSONDecodeError:
                            return data_str
                    return None
                except Exception as redis_error:
                    self.redis_connected = False
            
            if not hasattr(self, 'redis_cache') or cache_key not in self.redis_cache:
                return None
            
            cached_item = self.redis_cache[cache_key]
            if datetime.now() > cached_item['expire_at']:
                del self.redis_cache[cache_key]
                return None
            
            return cached_item['data']
        except Exception as e:
            print(f"获取缓存数据失败: {e}")
            return None
    
    def invalidate_cache(self, key_type, identifier=None):
        """失效Redis或内存缓存"""
        try:
            if identifier:
                cache_key = self._get_cache_key(key_type, identifier)
                if self.redis_connected:
                    try:
                        self.redis_client.delete(cache_key)
                    except Exception:
                        self.redis_connected = False
                
                if hasattr(self, 'redis_cache') and cache_key in self.redis_cache:
                    del self.redis_cache[cache_key]
            else:
                pattern = f"{self.CACHE_PREFIX}{key_type}:*"
                if self.redis_connected:
                    try:
                        keys = self.redis_client.keys(pattern)
                        if keys:
                            self.redis_client.delete(*keys)
                    except Exception:
                        self.redis_connected = False
                
                if hasattr(self, 'redis_cache'):
                    keys_to_delete = [key for key in self.redis_cache if key.startswith(pattern)]
                    for key in keys_to_delete:
                        del self.redis_cache[key]
            return True
        except Exception as e:
            print(f"失效缓存失败: {e}")
            return False
    
    def save_exam_record(self, questions, user_answers, total_score, details, user_id="default"):
        """保存考试记录 - 增加 user_id 隔离"""
        # 将 user_answers 的 Key 转换为字符串 (MongoDB 不允许整数作为 Key)
        user_answers_str = {str(k): v for k, v in user_answers.items()}

        record = {
            "user_id": user_id,  # ✅ 关键：记录归属用户
            "timestamp": datetime.now(),
            "total_score": total_score,
            "questions": questions,
            "user_answers": user_answers_str, 
            "grading_details": details
        }
        
        # 保存到数据库
        self.exam_col.insert_one(record)
        
        # 失效相关缓存（带 user_id）
        self.invalidate_cache('exam', user_id)
        self.invalidate_cache('stats', user_id)

    def mark_review_task_completed(self, user_id, keyword, chapter=None, section=None, difficulty=None, date=None, tasks=None):
        if date is None:
            date = datetime.now().date()
        date_str = date.isoformat()
        identifier = self._build_review_identifier(user_id, keyword, chapter, section, difficulty, date_str)
        data = {
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }
        if tasks is not None:
            data["tasks"] = tasks
        self.cache_data("review_task", identifier, data)
        filter_doc = {
            "user_id": user_id,
            "keyword": keyword,
            "chapter": chapter,
            "section": section,
            "difficulty": difficulty,
            "date": date_str,
        }
        existing = self.review_col.find_one(filter_doc)
        if existing:
            self.review_col.update_one(filter_doc, {"$set": data})
        else:
            doc = filter_doc.copy()
            doc.update(data)
            self.review_col.insert_one(doc)
        return True

    def get_review_task_status(self, user_id, keyword, chapter=None, section=None, difficulty=None, date=None):
        if date is None:
            date = datetime.now().date()
        date_str = date.isoformat()
        identifier = self._build_review_identifier(user_id, keyword, chapter, section, difficulty, date_str)
        cached = self.get_cached_data("review_task", identifier)
        if isinstance(cached, dict):
            return cached.get("status") == "completed"
        filter_doc = {
            "user_id": user_id,
            "keyword": keyword,
            "chapter": chapter,
            "section": section,
            "difficulty": difficulty,
            "date": date_str,
        }
        record = self.review_col.find_one(filter_doc)
        if record:
            data = {
                "status": record.get("status", ""),
                "completed_at": record.get("completed_at"),
                "tasks": record.get("tasks"),
            }
            self.cache_data("review_task", identifier, data)
            return data.get("status") == "completed"
        return False

    def add_mistake(self, question_data, user_ans, grading_result, user_id="default"):
        """添加错题 - 增加 user_id 隔离"""
        try:
            # 查找该用户是否已存在该错题
            existing_query = {
                "question": question_data['question'],
                "user_id": user_id  # ✅ 关键：只查当前用户的
            }
            existing = self.mistake_col.find_one(existing_query)
            
            if existing:
                self.mistake_col.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$inc": {"error_times": 1},
                        "$set": {
                            "last_error_time": datetime.now(),
                            "latest_feedback": grading_result.get('feedback', '')
                        }
                    }
                )
            else:
                knowledge_point = question_data.get('knowledge_point')
                raw_standard_answer = question_data.get('answer')
                options = question_data.get('options') or []
                standard_answer_display = raw_standard_answer
                
                # 尝试从选项中匹配完整答案文本
                if isinstance(raw_standard_answer, str) and options:
                    raw_letter = raw_standard_answer.strip().upper()
                    for opt in options:
                        if not isinstance(opt, str):
                            continue
                        text = opt.strip()
                        if not text:
                            continue
                        if "." in text:
                            letter_part = text.split(".", 1)[0].strip().upper()
                            if len(letter_part) == 1 and letter_part.isalpha() and letter_part == raw_letter:
                                standard_answer_display = text
                                break
                                
                record = {
                    "user_id": user_id,  # ✅ 关键：记录归属
                    "question": question_data['question'],
                    "type": question_data.get('type', 'choice'),
                    "difficulty": question_data.get('difficulty', 'Unknown'),
                    "standard_answer": standard_answer_display,
                    "user_answer": user_ans,
                    "analysis": grading_result.get('analysis', ''),
                    "error_times": 1,
                    "create_time": datetime.now(),
                    "last_error_time": datetime.now(),
                    "knowledge_point": knowledge_point,
                    "keyword": knowledge_point,
                    "chapter": question_data.get('chapter'),
                    "section": question_data.get('section'),
                    "importance": float(question_data.get('importance', 1.0)),
                }
                self.mistake_col.insert_one(record)
            
            # 失效相关缓存
            self.invalidate_cache('mistakes', user_id)
            self.invalidate_cache('stats', user_id)
            return True
        except Exception as e:
            print(f"添加错题失败: {e}")
            return False

    def get_mistakes(self, user_id="default", difficulty=None):
        """获取错题列表，支持用户隔离"""
        # 缓存键带上 user_id
        cached_mistakes = self.get_cached_data('mistakes', user_id)
        if cached_mistakes:
            if difficulty:
                return [m for m in cached_mistakes if m.get("difficulty") == difficulty]
            return cached_mistakes
        
        # ✅ 关键：增加 user_id 过滤
        query = {"user_id": user_id}
        mistakes = sorted(self.mistake_col.find(query, {"_id": 0}), key=lambda x: x.get("error_times", 0), reverse=True)
        
        self.cache_data('mistakes', user_id, mistakes)
        
        if difficulty:
            return [m for m in mistakes if m.get("difficulty") == difficulty]
        return mistakes
    
    def get_weak_points(self, user_id="default", limit=5):
        """获取薄弱知识点，支持用户隔离"""
        # 这里的 get_mistakes 已经被修改为带隔离的了
        mistakes = self.get_mistakes(user_id)
        grouped = {}
        
        for m in mistakes:
            keyword = m.get("keyword") or m.get("knowledge_point") or "未知考点"
            chapter = m.get("chapter")
            section = m.get("section")
            difficulty = m.get("difficulty", "Unknown")
            error_times = m.get("error_times", 0)
            importance = float(m.get("importance", 1.0))
            last_error_time = m.get("last_error_time")

            
            # 使用 (keyword, difficulty) 作为唯一标识
            key = (keyword, difficulty)
            if key not in grouped:
                grouped[key] = {
                    "keyword": keyword,
                    "chapter": chapter,
                    "section": section,
                    "difficulty": difficulty,
                    "error_times": error_times,
                    "importance": importance,
                    "last_error_time": last_error_time,
                }
            else:
                grouped[key]["error_times"] += error_times
                grouped[key]["importance"] = max(grouped[key]["importance"], importance)
                if last_error_time and grouped[key]["last_error_time"]:
                    try:
                        grouped[key]["last_error_time"] = max(grouped[key]["last_error_time"], last_error_time)
                    except:
                        pass
                elif last_error_time:
                    grouped[key]["last_error_time"] = last_error_time
        
        weak_points = []
        for item in grouped.values():
            score = item["error_times"] * item["importance"]
            item["score"] = score
            weak_points.append(item)
        
        weak_points.sort(key=lambda x: x.get("score", 0), reverse=True)
        return weak_points[:limit]
    
    def get_exam_stats(self, user_id="default"):
        """获取考试统计信息 - 增加 user_id 隔离"""
        cached_stats = self.get_cached_data('stats', user_id)
        if cached_stats:
            return cached_stats
        
        # ✅ 关键：所有查询增加 user_id 过滤
        filter_query = {"user_id": user_id}
        
        stats = {
            "total_exams": self.exam_col.count_documents(filter_query),
            "total_mistakes": self.mistake_col.count_documents(filter_query),
            "avg_score": 0,
            "recent_exams": []
        }
        
        # 计算平均分数 (使用 aggregate)
        pipeline = [
            {"$match": filter_query},
            {"$group": {"_id": None, "avg_score": {"$avg": "$total_score"}}}
        ]
        avg_result = list(self.exam_col.aggregate(pipeline))
        if avg_result:
            stats["avg_score"] = round(avg_result[0]["avg_score"], 2)
        
        # 获取最近的考试记录
        recent_exams = self.exam_col.find(filter_query, {"_id": 0, "timestamp": 1, "total_score": 1})
        stats["recent_exams"] = sorted(recent_exams, key=lambda x: x.get("timestamp", 0), reverse=True)[:10]
        
        # 缓存统计结果
        self.cache_data('stats', user_id, stats)
        
        return stats
    
    def cache_user_exam(self, user_id, exam_data):
        """缓存用户的试卷数据"""
        return self.cache_data('exam', user_id, exam_data)
    
    def get_cached_user_exam(self, user_id):
        """获取用户缓存的试卷数据"""
        return self.get_cached_data('exam', user_id)
    
    def cache_user_answers(self, user_id, answers):
        """缓存用户的答案"""
        return self.cache_data('user_answers', user_id, answers)
    
    def get_cached_user_answers(self, user_id):
        """获取用户缓存的答案"""
        return self.get_cached_data('user_answers', user_id)
    
    # 用户管理相关方法 (保持原样)
    def create_user(self, username, password, email, name=None):
        if self.user_col.find_one({'username': username}):
            return None, '用户名已存在'
        if self.user_col.find_one({'email': email}):
            return None, '邮箱已存在'
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = {
            'username': username,
            'password': hashed_password,
            'email': email,
            'name': name or username,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'role': 'user'
        }
        result = self.user_col.insert_one(user)
        return str(result.inserted_id), '用户创建成功'
    
    def verify_user(self, username, password):
        user = self.user_col.find_one({'username': username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            user_copy = user.copy()
            user_copy.pop('password', None)
            return user_copy
        return None
    
    def get_user(self, user_id):
        from bson import ObjectId
        try:
            user = self.user_col.find_one({'_id': ObjectId(user_id)})
            if user:
                user_copy = user.copy()
                user_copy.pop('password', None)
                return user_copy
        except Exception:
            user = self.user_col.find_one({'username': user_id})
            if user:
                user_copy = user.copy()
                user_copy.pop('password', None)
                return user_copy
        return None
    
    def update_user(self, user_id, update_data):
        from bson import ObjectId
        update_data.pop('password', None)
        update_data.pop('username', None)
        update_data.pop('email', None)
        update_data['updated_at'] = datetime.now()
        try:
            result = self.user_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception:
            result = self.user_col.update_one(
                {'username': user_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
    
    def update_password(self, user_id, old_password, new_password):
        from bson import ObjectId
        user = self.user_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            user = self.user_col.find_one({'username': user_id})
        if not user:
            return False, '用户不存在'
        if not bcrypt.checkpw(old_password.encode('utf-8'), user['password']):
            return False, '旧密码错误'
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        try:
            result = self.user_col.update_one(
                {'_id': user['_id']},
                {'$set': {'password': hashed_password, 'updated_at': datetime.now()}}
            )
            return result.modified_count > 0, '密码更新成功'
        except Exception:
            return False, '更新密码失败'
    
    def delete_user(self, user_id):
        from bson import ObjectId
        try:
            result = self.user_col.delete_one({'_id': ObjectId(user_id)})
            if result.deleted_count > 0:
                return True
        except Exception:
            result = self.user_col.delete_one({'username': user_id})
            if result.deleted_count > 0:
                return True
        return False

    def get_knowledge_point_accuracy(self, user_id, knowledge_point):
        """
        计算特定知识点的历史正确率
        """
        try:
            records = self.exam_col.find({"user_id": user_id})
            total_possible_score = 0
            total_earned_score = 0
            
            for record in records:
                questions = record.get("questions", [])
                grading_details = record.get("grading_details", []) # list of dicts
                
                # 创建 id 到 score 的映射
                # grading_details 是 list, 每个 item 有 id 和 score
                id_to_score = {}
                if isinstance(grading_details, list):
                    for res in grading_details:
                        if isinstance(res, dict) and 'id' in res:
                            id_to_score[res['id']] = res.get('score', 0)
                
                for q in questions:
                    if q.get('knowledge_point') == knowledge_point:
                        q_id = q.get('id')
                        if q_id in id_to_score:
                            total_possible_score += 10 # 假设每题10分
                            total_earned_score += id_to_score[q_id]
                            
            if total_possible_score == 0:
                return 0.0
                
            return total_earned_score / total_possible_score
        except Exception as e:
            print(f"计算知识点正确率失败: {e}")
            return 0.0

    def remove_mistake(self, user_id, question_text):
        """从错题本中移除已掌握的题目"""
        try:
            result = self.mistake_col.delete_one({
                "user_id": user_id,
                "question": question_text
            })
            if result.deleted_count > 0:
                # 移除成功后清除缓存
                self.invalidate_cache('mistakes', user_id)
                self.invalidate_cache('stats', user_id)
                return True
            return False
        except Exception as e:
            print(f"移除错题失败: {e}")
            return False

    def add_consolidation_record(self, user_id, knowledge_point, acc_before, acc_after):
        """添加巩固练习记录"""
        try:
            record = {
                "user_id": user_id,
                "knowledge_point": knowledge_point,
                "accuracy_before": acc_before,
                "accuracy_after": acc_after,
                "improvement": acc_after - acc_before,
                "timestamp": datetime.now()
            }
            self.consolidation_col.insert_one(record)
            return True
        except Exception as e:
            print(f"添加巩固记录失败: {e}")
            return False

    def get_consolidation_records(self, user_id, limit=10):
        """获取巩固练习记录"""
        try:
            return sorted(
                self.consolidation_col.find({"user_id": user_id}), 
                key=lambda x: x.get("timestamp", datetime.min), 
                reverse=True
            )[:limit]
        except Exception as e:
            print(f"获取巩固记录失败: {e}")
            return []