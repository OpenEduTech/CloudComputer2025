from tinydb import TinyDB, Query
db = TinyDB("db.json")
users_col = db.table("cloud_final")
result = users_col.all()
print(result)
