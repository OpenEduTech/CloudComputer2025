# view_mistakes.py
import redis
import json
import sys
import os
from dotenv import load_dotenv

# 加载环境变量（优先读取.env，Docker环境会被容器环境变量覆盖）
load_dotenv()

def view_user_mistakes(user_id: str):
    # ========== 核心修改：从环境变量读取Redis配置 ==========
    redis_host = os.getenv("REDIS_HOST", "127.0.0.1")  # Docker=redis，本地=127.0.0.1
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    
    try:
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_timeout=5,  # 超时保护
            connect_timeout=5
        )
        r.ping()  # 测试连接
    except redis.ConnectionError as e:
        print(f"❌ Redis连接失败：{e}")
        print(f"⚠️ 当前配置：REDIS_HOST={redis_host}, REDIS_PORT={redis_port}")
        print("   - 本地运行：确保Redis已启动，REDIS_HOST=127.0.0.1")
        print("   - Docker运行：使用命令：docker exec -it exam-system python view_mistakes.py <学号>")
        return

    key_pattern = f"mistake:{user_id}:*"
    mistake_keys = r.keys(key_pattern)
    
    if not mistake_keys:
        print(f"❌ 学号 {user_id} 没有错题记录。")
        return
    
    print(f"✅ 找到 {len(mistake_keys)} 道错题（学号: {user_id}）：\n")
    # 按题目编号排序
    mistake_keys_sorted = sorted(mistake_keys, key=lambda k: int(k.split(':')[-1]))
    for key in mistake_keys_sorted:
        data_str = r.get(key)
        try:
            data = json.loads(data_str)
            q_idx = data.get("question_index", "未知")
            score = data.get("score", 0)
            max_score = data.get("max_score", "?")
            topics = data.get("topics", [])
            feedback = data.get("feedback", "无评语")
            question = data.get("question", "")
            
            # 优化题目预览（避免截断关键内容）
            question_preview = question[:150] + "..." if len(question) > 150 else question
            
            print(f"--- 题目 {q_idx} ({score}/{max_score}) ---")
            print(f"考点: {', '.join(topics) if topics else '无'}")
            print(f"题目预览: {question_preview}")
            print(f"评语: {feedback}\n")
        except Exception as e:
            print(f"⚠️ 解析失败（key={key}）: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python view_mistakes.py <学号>")
        print("示例: python view_mistakes.py 10235501451")
    else:
        user_id = sys.argv[1]
        view_user_mistakes(user_id)