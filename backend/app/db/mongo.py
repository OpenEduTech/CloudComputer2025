import os

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "learning_agent")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]


def get_db():
    return db
