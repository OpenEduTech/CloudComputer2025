from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    try:
        db.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db.db = db.client[settings.MONGODB_DB_NAME]
        # Verify connection
        await db.client.admin.command('ping')
        
        # 创建索引以优化查询性能
        await db.db.users.create_index("email", unique=True)
        await db.db.users.create_index("username", unique=True)
        await db.db.quiz_results.create_index([("user_id", 1), ("created_at", -1)])
        await db.db.mistake_analysis_cache.create_index("user_id", unique=True)
        await db.db.mistake_analysis_cache.create_index("last_updated")
        
        print("✅ Connected to MongoDB and created indexes")
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")

async def close_mongo_connection():
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")
