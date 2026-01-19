import time
import redis
import sys
from config import settings

def main():
    print("AutoKGS Worker starting...")
    
    # 尝试连接 Redis
    r = None
    retry_count = 0
    while retry_count < 5:
        try:
            r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
            r.ping()
            print("Successfully connected to Redis.")
            break
        except Exception as e:
            print(f"Failed to connect to Redis (Attempt {retry_count+1}/5): {e}")
            retry_count += 1
            time.sleep(2)
            
    if not r:
        print("Could not connect to Redis. Exiting.")
        return

    print("Worker is ready and waiting for tasks...")
    
    # 模拟 Worker 循环
    while True:
        try:
            # 这里的逻辑后续会替换为真实的 Redis POP 操作
            # task = r.blpop("task_queue", timeout=5)
            # if task:
            #     process_task(task)
            time.sleep(5) # 仅仅为了保活，不空转 CPU
            print("Worker heartbeat: Waiting for tasks...", flush=True)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in worker loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
