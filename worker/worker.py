import os

from redis import Redis
from rq import Queue, SimpleWorker, Worker

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

def hello_job(name: str):
    print(f"[worker] Hello, {name}!")

def main():
    redis_conn = Redis.from_url(REDIS_URL)
    queue = Queue("default", connection=redis_conn)
    # RQ's default Worker uses os.fork, which is unavailable on Windows.
    worker_cls = SimpleWorker if os.name == "nt" else Worker
    worker = worker_cls([queue], connection=redis_conn)
    worker.work(with_scheduler=True)

if __name__ == "__main__":
    main()
