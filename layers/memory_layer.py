import redis
import json
import time
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
from openai import OpenAI  # 新增：调用LLM生成个性化建议

# 加载环境变量（适配 Docker 配置）
load_dotenv()

# 初始化 Qwen 客户端（复用决策层逻辑）
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"
client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)

# ========== 核心修改：适配Docker/本地的Redis连接 ==========
# Docker环境下REDIS_HOST=redis（容器服务名），本地=localhost/127.0.0.1
try:
    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "127.0.0.1"),  # Docker用redis，本地默认127.0.0.1
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True,
        socket_timeout=5,  # 超时时间，避免无限等待
        connect_timeout=5  # 新增连接超时，兼容高版本redis
    )
    r.ping()  # 测试连接
    print("[记忆层] Redis 连接成功 ✅")
except redis.ConnectionError as e:
    print(f"⚠️ Redis 连接失败：{e}")
    print("⚠️ 记忆层将不工作，请检查 Redis 服务是否启动")
    r = None
except TypeError as e:
    # 兼容低版本redis（无connect_timeout参数）
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True,
            socket_timeout=5
        )
        r.ping()
        print("[记忆层] Redis 连接成功 ✅（低版本兼容模式）")
    except:
        print(f"⚠️ Redis 低版本兼容模式也连接失败：{e}")
        r = None

def record_mistakes(
    user_id: str,
    grading_results: List[Dict],
    structured_questions: List[Dict]
) -> Dict[str, Any]:
    """
    将错题和考点错误次数写入 Redis
    返回记录结果（便于接口反馈）
    """
    if r is None:
        return {"status": "failed", "message": "Redis 未连接", "mistake_count": 0}

    mistake_count = 0
    recorded_ids = []  # 记录已存储的错题编号

    for result in grading_results:
        # 校验必要字段
        if not all(key in result for key in ["question_index", "score", "max_score", "feedback"]):
            print(f"[警告] 评分结果字段缺失，跳过：{result}")
            continue
        
        q_idx = result["question_index"] - 1
        if q_idx >= len(structured_questions):
            print(f"[警告] 题目索引超出范围，跳过：question_index={result['question_index']}")
            continue
            
        score = result["score"]
        max_score = result["max_score"]
        
        if score < max_score:  # 判定为错题
            mistake_count += 1
            q_info = structured_questions[q_idx]
            
            # 提取考点（默认未知考点）
            topics = q_info.get("topics", ["未知考点"])
            
            # 构建完整的错题数据
            mistake_data = {
                "question": q_info.get("question", ""),
                "question_index": result["question_index"],
                "user_answer": result.get("user_answer", "未作答"),
                "correct_answer": q_info.get("reference_answer", "无参考答案"),
                "feedback": result["feedback"],
                "score": score,
                "max_score": max_score,
                "topics": topics,
                "timestamp": int(time.time())
            }
            
            # 存储错题（key 包含用户ID和题目索引，避免重复）
            key = f"mistake:{user_id}:{result['question_index']}"
            r.set(key, json.dumps(mistake_data, ensure_ascii=False))
            recorded_ids.append(result["question_index"])
            
            # 更新每个考点的错误计数
            for topic in topics:
                topic_key = f"error_count:{user_id}:{topic}"
                r.incr(topic_key)
    
    # 更新总错题数
    if mistake_count > 0:
        total_key = f"mistake_count:{user_id}"
        r.incrby(total_key, mistake_count)
        print(f"[记忆层] 已记录 {mistake_count} 道错题（编号：{recorded_ids}）")
    
    return {
        "status": "success",
        "user_id": user_id,
        "mistake_count": mistake_count,
        "recorded_question_ids": recorded_ids
    }

# 新增：获取用户错题列表（可选，便于前端查询）
def get_user_mistakes(user_id: str) -> List[Dict]:
    if r is None:
        return []
    # 模糊匹配该用户的所有错题 key
    keys = r.keys(f"mistake:{user_id}:*")
    mistakes = []
    for key in keys:
        mistake_str = r.get(key)
        if mistake_str:
            try:
                mistakes.append(json.loads(mistake_str))
            except json.JSONDecodeError:
                print(f"[警告] 错题数据解析失败：{key}")
    # 按时间戳排序（最新错题在前）
    mistakes.sort(key=lambda x: x["timestamp"], reverse=True)
    return mistakes

# ========== 新增：动态个性化小灶函数 ==========
def generate_personalized_review(user_id: str) -> Dict[str, Any]:
    """
    基于用户高频错题考点，生成动态个性化复习建议（小灶）
    :param user_id: 用户ID
    :return: 包含复习建议的字典
    """
    if r is None:
        return {
            "status": "failed",
            "message": "Redis 未连接，无法生成个性化建议",
            "review_plan": ""
        }
    
    # 1. 获取用户高频错误考点（按错误次数排序）
    error_keys = r.keys(f"error_count:{user_id}:*")
    if not error_keys:
        return {
            "status": "success",
            "user_id": user_id,
            "review_plan": "暂无错题记录，建议巩固基础知识点！",
            "high_frequency_topics": []
        }
    
    # 统计每个考点的错误次数
    topic_error_count = {}
    for key in error_keys:
        topic = key.replace(f"error_count:{user_id}:", "")
        count = int(r.get(key) or 0)
        topic_error_count[topic] = count
    
    # 按错误次数降序排序，取前3个高频考点
    sorted_topics = sorted(topic_error_count.items(), key=lambda x: x[1], reverse=True)
    high_freq_topics = [topic for topic, _ in sorted_topics[:3]]
    high_freq_str = "\n".join([f"- {topic}（错误{count}次）" for topic, count in sorted_topics[:3]])
    
    # 2. 调用LLM生成个性化复习建议
    prompt = f"""
你是资深统计学辅导老师，请基于以下高频错题考点，为学生生成个性化复习建议：

【学生ID】{user_id}
【高频错误考点（按错误次数排序）】
{high_freq_str}

【生成规则】
1. 针对每个高频考点，给出：
   - 核心概念回顾（1-2句话）
   - 典型错误原因分析（结合统计学常见误区）
   - 针对性练习建议（具体题目方向）
2. 整体建议控制在300字以内，语言简洁、可落地；
3. 避免空话，聚焦“怎么补”，而非“要补”；
4. 仅输出复习建议文本，无其他格式、标题。
"""
    response = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": "你是个性化学习顾问，建议要具体、可落地、针对性强"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=500
    )
    review_plan = response.choices[0].message.content.strip()
    
    return {
        "status": "success",
        "user_id": user_id,
        "high_frequency_topics": high_freq_topics,
        "review_plan": review_plan,
        "error_count_summary": topic_error_count
    }