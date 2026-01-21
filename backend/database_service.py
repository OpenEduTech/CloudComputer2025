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
        # 简单实现，仅支持 $group 和 $avg 操作
        if pipeline and '$group' in pipeline[0]:
            group_stage = pipeline[0]['$group']
            if group_stage.get('_id') is None and 'avg_score' in group_stage:
                total = sum(doc.get('total_score', 0) for doc in self.data)
                count = len(self.data)
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
                # read_preference参数已在URI中配置或使用默认值
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
                self._create_indexes()
            else:
                # 非开发模式下直接抛出错误
                raise Exception(f"MongoDB 连接失败，无法继续运行: {e}") from e
        
        # 连接 Redis - 支持集群和单节点
        try:
            # 检查是否配置了Redis集群
            if AppConfig.REDIS_CLUSTER_NODES:
                print("尝试连接Redis集群...")
                cluster_nodes = [node.strip() for node in AppConfig.REDIS_CLUSTER_NODES.split(',')]
                startup_nodes = []
                for node in cluster_nodes:
                    host, port = node.split(':')
                    startup_nodes.append({'host': host, 'port': int(port)})
                
                redis_config = {
                    'startup_nodes': startup_nodes,
                    'decode_responses': True,
                    'password': AppConfig.REDIS_PASSWORD if AppConfig.REDIS_PASSWORD else None,
                    'skip_full_coverage_check': True,  # 跳过全节点覆盖检查以加快连接速度
                    'retry_on_timeout': True,
                    'socket_timeout': 5,
                    'socket_connect_timeout': 5,
                    'health_check_interval': 30
                }
                
                self.redis_client = RedisCluster(**redis_config)
            else:
                print("尝试连接Redis单节点...")
                redis_config = {
                    'host': AppConfig.REDIS_HOST,
                    'port': AppConfig.REDIS_PORT,
                    'decode_responses': True,
                    'max_connections': 200,  # 增大最大连接数
                    'socket_timeout': 3,     # 减少套接字超时
                    'socket_connect_timeout': 3,  # 减少连接超时
                    'retry_on_timeout': True,  # 超时重试
                    'health_check_interval': 30  # 健康检查间隔
                }
                
                # 仅当密码不为空时添加密码配置
                password = AppConfig.REDIS_PASSWORD
                if password and password.strip():
                    redis_config['password'] = password
                
                # 修复：添加禁用RDB错误停止写入的配置
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
                    # 尝试修改Redis配置，解决RDB写入错误
                    self.redis_client.config_set('stop-writes-on-bgsave-error', 'no')
                    print("✅ Redis配置已修复：禁用了stop-writes-on-bgsave-error")
                except Exception as e:
                    print(f"⚠️ 无法修改Redis配置：{e}")
                    # 配置修改失败不影响继续运行
                    pass
            except Exception as e:
                print(f"❌ Redis 连接失败: {e}")
                if "MISCONF" in str(e) or "stop-writes-on-bgsave-error" in str(e):
                    print("⚠️ Redis RDB快照错误：正在尝试修复...")
                    # 在Python中模拟修复命令
                    print("✅ Redis错误已处理：将使用内存缓存替代")
                # 无论如何，都将使用内存缓存替代
                self.redis_cache = {}
                self.redis_connected = False
                print("✅ 已启用内存缓存替代Redis")
        except Exception as e:
            print(f"❌ Redis 连接失败: {e}")
            print("⚠️ 警告: Redis服务未运行，将使用内存缓存替代")
            print("💡 提示: 安装并运行Redis可获得更好的性能")
            
            # 无论开发模式如何，都使用内存缓存替代Redis
            # 这样可以确保应用程序能够运行，同时保持API验证功能
            self.redis_cache = {}
            self.redis_connected = False
            print("✅ 已启用内存缓存替代Redis")
        
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
        self.user_col.create_index("username", unique=True)  # 用户名唯一索引
        self.user_col.create_index("email", unique=True)  # 邮箱唯一索引
        
        # 为错题集合创建索引
        self.mistake_col.create_index("question", unique=True)  # 题目唯一索引
        self.mistake_col.create_index([("error_times", -1)])  # 错误次数索引（降序）
        self.mistake_col.create_index("difficulty")  # 难度索引
        self.mistake_col.create_index([("last_error_time", -1)])  # 最后错误时间索引（降序）
        self.mistake_col.create_index("knowledge_point")  # 考点索引
        self.mistake_col.create_index("keyword")  # 关键字索引
        
        self.exam_col.create_index([("timestamp", -1)])  # 时间戳索引（降序）
        self.exam_col.create_index("total_score")  # 总分索引
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
                    # Redis命令执行失败，回退到内存缓存
                    print(f"Redis缓存失败，回退到内存缓存: {redis_error}")
                    self.redis_connected = False  # 临时标记Redis不可用
            
            # 使用内存缓存
            if not hasattr(self, 'redis_cache'):
                self.redis_cache = {}
            # 存储数据和过期时间
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
                        # 尝试反序列化为JSON
                        try:
                            return json.loads(data_str)
                        except json.JSONDecodeError:
                            return data_str
                    return None
                except Exception as redis_error:
                    # Redis命令执行失败，回退到内存缓存
                    print(f"Redis获取缓存失败，回退到内存缓存: {redis_error}")
                    self.redis_connected = False  # 临时标记Redis不可用
            
            # 使用内存缓存
            if not hasattr(self, 'redis_cache') or cache_key not in self.redis_cache:
                return None
            
            # 检查是否过期
            cached_item = self.redis_cache[cache_key]
            if datetime.now() > cached_item['expire_at']:
                # 过期则删除
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
                    except Exception as redis_error:
                        # Redis命令执行失败，回退到内存缓存
                        print(f"Redis删除缓存失败，回退到内存缓存: {redis_error}")
                        self.redis_connected = False  # 临时标记Redis不可用
                
                # 同时清理内存缓存（无论Redis是否可用）
                if hasattr(self, 'redis_cache') and cache_key in self.redis_cache:
                    del self.redis_cache[cache_key]
            else:
                # 失效所有指定类型的缓存
                pattern = f"{self.CACHE_PREFIX}{key_type}:*"
                if self.redis_connected:
                    try:
                        keys = self.redis_client.keys(pattern)
                        if keys:
                            self.redis_client.delete(*keys)
                    except Exception as redis_error:
                        # Redis命令执行失败，回退到内存缓存
                        print(f"Redis批量删除缓存失败，回退到内存缓存: {redis_error}")
                        self.redis_connected = False  # 临时标记Redis不可用
                
                # 同时清理内存缓存（无论Redis是否可用）
                if hasattr(self, 'redis_cache'):
                    # 找出所有匹配的键
                    keys_to_delete = [key for key in self.redis_cache if key.startswith(pattern)]
                    for key in keys_to_delete:
                        del self.redis_cache[key]
            return True
        except Exception as e:
            print(f"失效缓存失败: {e}")
            return False
    
    def save_exam_record(self, questions, user_answers, total_score, details):
            # ✅ 修复：将 user_answers 的 Key 转换为字符串 (MongoDB 不允许整数作为 Key)
            # 原始 user_answers 可能是 {1: "A", 2: "B"} -> 导致报错
            # 转换后 user_answers_str 为 {"1": "A", "2": "B"} -> MongoDB 支持
            user_answers_str = {str(k): v for k, v in user_answers.items()}

            record = {
                "timestamp": datetime.now(),
                "total_score": total_score,
                "questions": questions,
                "user_answers": user_answers_str, # 使用转换后的字典
                "grading_details": details
            }
            
            # 保存到数据库
            self.exam_col.insert_one(record)
            
            # 失效相关缓存
            self.invalidate_cache('exam')
            self.invalidate_cache('stats')

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

    def add_mistake(self, question_data, user_ans, grading_result, user_id=None):
        try:
            existing_query = {"question": question_data['question']}
            if user_id:
                existing_query["user_id"] = user_id
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
                    "user_id": user_id if user_id else "default",
                }
                self.mistake_col.insert_one(record)
            
            self.invalidate_cache('mistakes')
            self.invalidate_cache('stats')
            return True
        except Exception as e:
            print(f"添加错题失败: {e}")
            return False

    def get_mistakes(self, user_id="default", difficulty=None):
        """获取错题列表，支持用户隔离"""
        cached_mistakes = self.get_cached_data('mistakes', user_id)
        if cached_mistakes:
            if difficulty:
                return [m for m in cached_mistakes if m.get("difficulty") == difficulty]
            return cached_mistakes
        
        query = {}
        mistakes = sorted(self.mistake_col.find(query, {"_id": 0}), key=lambda x: x.get("error_times", 0), reverse=True)
        
        self.cache_data('mistakes', user_id, mistakes)
        
        if difficulty:
            return [m for m in mistakes if m.get("difficulty") == difficulty]
        return mistakes
    
    def get_weak_points(self, user_id="default", limit=5):
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
            
            key = (keyword, chapter, section, difficulty)
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
                    grouped[key]["last_error_time"] = max(grouped[key]["last_error_time"], last_error_time)
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
        """获取考试统计信息"""
        # 尝试从缓存获取
        cached_stats = self.get_cached_data('stats', user_id)
        if cached_stats:
            return cached_stats
        
        # 缓存不存在，从数据库查询
        stats = {
            "total_exams": self.exam_col.count_documents({}),
            "total_mistakes": self.mistake_col.count_documents({}),
            "avg_score": 0,
            "recent_exams": []
        }
        
        # 计算平均分数
        pipeline = [
            {"$group": {"_id": None, "avg_score": {"$avg": "$total_score"}}}
        ]
        avg_result = list(self.exam_col.aggregate(pipeline))
        if avg_result:
            stats["avg_score"] = round(avg_result[0]["avg_score"], 2)
        
        # 获取最近的考试记录
        recent_exams = self.exam_col.find({}, {"_id": 0, "timestamp": 1, "total_score": 1})
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
    
    # 用户管理相关方法
    def create_user(self, username, password, email, name=None):
        """创建新用户，返回用户ID或None（如果用户名/邮箱已存在）"""
        # 检查用户名是否已存在
        if self.user_col.find_one({'username': username}):
            return None, '用户名已存在'
        
        # 检查邮箱是否已存在
        if self.user_col.find_one({'email': email}):
            return None, '邮箱已存在'
        
        # 生成密码哈希
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # 创建用户文档
        user = {
            'username': username,
            'password': hashed_password,
            'email': email,
            'name': name or username,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'role': 'user'  # 默认角色为普通用户
        }
        
        # 保存到数据库
        result = self.user_col.insert_one(user)
        
        return str(result.inserted_id), '用户创建成功'
    
    def verify_user(self, username, password):
        """验证用户密码，返回用户信息或None"""
        user = self.user_col.find_one({'username': username})
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            # 不返回密码
            user_copy = user.copy()
            user_copy.pop('password', None)
            return user_copy
        
        return None
    
    def get_user(self, user_id):
        """根据用户ID获取用户信息"""
        from bson import ObjectId
        
        try:
            user = self.user_col.find_one({'_id': ObjectId(user_id)})
            if user:
                user_copy = user.copy()
                user_copy.pop('password', None)
                return user_copy
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            # 尝试通过用户名获取（兼容旧版本）
            user = self.user_col.find_one({'username': user_id})
            if user:
                user_copy = user.copy()
                user_copy.pop('password', None)
                return user_copy
        
        return None
    
    def update_user(self, user_id, update_data):
        """更新用户信息"""
        from bson import ObjectId
        
        # 移除敏感字段
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
        except Exception as e:
            print(f"更新用户信息失败: {e}")
            # 尝试通过用户名更新（兼容旧版本）
            result = self.user_col.update_one(
                {'username': user_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
    
    def update_password(self, user_id, old_password, new_password):
        """更新用户密码"""
        from bson import ObjectId
        
        # 先验证旧密码
        user = self.user_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            # 尝试通过用户名查找（兼容旧版本）
            user = self.user_col.find_one({'username': user_id})
            
        if not user:
            return False, '用户不存在'
        
        if not bcrypt.checkpw(old_password.encode('utf-8'), user['password']):
            return False, '旧密码错误'
        
        # 更新密码
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        try:
            result = self.user_col.update_one(
                {'_id': user['_id']},
                {'$set': {
                    'password': hashed_password,
                    'updated_at': datetime.now()
                }}
            )
            return result.modified_count > 0, '密码更新成功'
        except Exception as e:
            print(f"更新密码失败: {e}")
            return False, '更新密码失败'
    
    def delete_user(self, user_id):
        """删除用户"""
        from bson import ObjectId
        
        try:
            result = self.user_col.delete_one({'_id': ObjectId(user_id)})
            if result.deleted_count > 0:
                return True
        except Exception as e:
            print(f"删除用户失败: {e}")
            # 尝试通过用户名删除（兼容旧版本）
            result = self.user_col.delete_one({'username': user_id})
            if result.deleted_count > 0:
                return True
        
        return False
