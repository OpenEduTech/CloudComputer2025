import uvicorn 
import os
import shutil
import time
import threading
from pymongo import MongoClient
import random 
from tinydb import TinyDB, Query
# from filelock import FileLock

# 清理__pycache__
def clean_pycache():
    for dirpath, dirnames, filenames in os.walk(os.getcwd()):
        if "__pycache__" in dirnames:
            pycache_path = os.path.join(dirpath, "__pycache__")
            shutil.rmtree(pycache_path)            

# 模拟其他用户在更新使用
# db_lock = FileLock(f"db.json.lock")
def simulation_other_users():
    while True:
        db = TinyDB("db.json")
        users_col = db.table("cloud_final")
        
        counts = random.randint(20, 40)
        # with db_lock:
        doc = next((d for d in users_col.all() if "total_tokens" in d and "total_counts" in d), None)
        if doc:
            doc["total_tokens"] += int(counts * random.randint(3000,8000)/1000)
            doc["total_counts"] += counts
            users_col.update(doc, doc_ids=[doc.doc_id])
        time.sleep(2)

if __name__ == "__main__":
    if os.path.exists("db.json"):
        os.remove("db.json")
    time.sleep(5)
    threading.Thread(target=simulation_other_users, daemon=True).start()
    uvicorn.run(
        "backend.routing.router:app",
        host="0.0.0.0",
        port=8000,
        workers=1
    )
    clean_pycache()