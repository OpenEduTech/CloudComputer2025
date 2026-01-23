import json
from collections import Counter
from typing import List, Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv
import redis

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)

# ========== 核心修改：适配Docker/本地的Redis连接 ==========
try:
    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "127.0.0.1"),  # Docker用redis，本地默认127.0.0.1
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True,
        socket_timeout=5,
        connect_timeout=5  # 新增连接超时，兼容高版本redis
    )
    r.ping()  # 测试连接
    print("[反思层] Redis 连接成功 ✅")
except redis.ConnectionError as e:
    print(f"⚠️ Redis 连接失败：{e}")
    print("⚠️ 反思层将不工作，请检查 Redis 服务是否启动")
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
        print("[反思层] Redis 连接成功 ✅（低版本兼容模式）")
    except:
        print(f"⚠️ Redis 低版本兼容模式也连接失败：{e}")
        r = None

def call_qwen_api(prompt: str, system_prompt: str, max_tokens: int = 2000) -> str:
    try:
        completion = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=max_tokens,
            stream=False
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[错误] Qwen API 调用失败：{e}")
        return ""

def get_user_mistakes(user_id: str) -> List[Dict]:
    """从 Redis 获取用户所有错题（现在是 JSON 字符串）"""
    if r is None:
        return []
    key_pattern = f"mistake:{user_id}:*"
    mistake_keys = r.keys(key_pattern)
    mistakes = []
    for key in mistake_keys:
        data_str = r.get(key)  # ← 现在是 JSON 字符串，不是哈希
        if data_str:
            try:
                data = json.loads(data_str)
                # 确保 topics 字段存在（应为列表）
                if "topics" in data and isinstance(data["topics"], list):
                    mistakes.append(data)
            except (json.JSONDecodeError, TypeError):
                continue  # 跳过解析失败的数据
    return mistakes

def analyze_frequent_topics(mistakes: List[Dict], min_count: int = 2) -> List[str]:
    """分析高频错误考点"""
    all_topics = []
    for m in mistakes:
        all_topics.extend(m.get("topics", []))
    topic_counts = Counter(all_topics)
    frequent = [topic for topic, count in topic_counts.items() if count >= min_count]
    return frequent

def generate_remedial_content(user_id: str, mistakes: List[Dict]) -> str:
    """生成个性化小灶内容"""
    frequent_topics = analyze_frequent_topics(mistakes)
    
    if not frequent_topics:
        return "✅ 暂无高频错题，继续保持！"
    
    # 统计每个 topic 的错误次数
    topic_counts = Counter()
    for m in mistakes:
        topic_counts.update(m.get("topics", []))
    
    # 构建错误详情
    error_summary = "\n".join([
        f"- “{topic}” 错误 {count} 次"
        for topic, count in topic_counts.most_common(5)
    ])
    
    # 判断是否需要"深度升级"
    deep_topics = [topic for topic, count in topic_counts.items() if count >= 3]
    depth_instruction = ""
    if deep_topics:
        depth_instruction = f"\n\n【深度强化】对于以下反复出错的概念，请提供：\n- 数学推导或代码示例\n- 常见误区辨析\n- 至少 2 道新练习题\n涉及主题：{', '.join(deep_topics)}"
    
    prompt = f"""
你是一名 AI 学习教练，正在为学生生成个性化复习建议。

【学生错题统计】
{error_summary}

【任务】
1. 针对上述高频错误考点，生成一段简洁的"小灶内容"；
2. 内容应包括：
   - 核心概念澄清（1-2 句）
   - 常见错误原因分析
   - 1-2 道针对性新练习题（带参考答案）
{depth_instruction}

【输出格式】
直接输出 Markdown 格式的复习建议，不要任何前缀。
"""
    system_prompt = "你是教育专家，擅长诊断学习漏洞并提供精准补救方案。"
    return call_qwen_api(prompt, system_prompt)

def reflection_layer(user_id: str) -> Dict[str, Any]:
    """主入口：生成反思报告"""
    print("\n[反思层] 正在分析您的错题模式...")
    mistakes = get_user_mistakes(user_id)
    
    if not mistakes:
        report = "✅ 暂无错题记录，无需生成复习建议。"
    else:
        report = generate_remedial_content(user_id, mistakes)
    
    # 保存报告到 Redis（24小时过期）
    if r:
        report_key = f"reflection:{user_id}"
        r.setex(report_key, 3600 * 24, report)
    
    return {
        "user_id": user_id,
        "mistake_count": len(mistakes),
        "frequent_topics": analyze_frequent_topics(mistakes),
        "remedial_report": report
    }