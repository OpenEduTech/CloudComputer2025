from redis import Redis
from rq import Queue
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

redis_conn = Redis.from_url(REDIS_URL)
queue = Queue("default", connection=redis_conn)

