from tinydb import TinyDB, Query
db = TinyDB("db.json")
users_col = db.table("cloud_final")
doc = next((d for d in users_col.all() if "total_tokens" in d and "total_counts" in d), None)
if doc:
    doc["total_tokens"] += 100
    doc["total_counts"] += 100
    users_col.update(doc, doc_ids=[doc.doc_id])
result = users_col.all()
print(result)
