import os

class Settings:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "/app/chroma_data")

settings = Settings()
