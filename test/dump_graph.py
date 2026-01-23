import json
import sys
import os
sys.path.append(os.getcwd())
from backend.models.llm_graph_builder import build_knowledge_graph
import time

start = time.time()
print("start")
g = build_knowledge_graph("熵")  # 可以换成别的概念
end = time.time()
print(f"耗时 {end - start} 秒")
print(g)
with open("sample_data.json", "w", encoding="utf-8") as f:
    json.dump(g, f, ensure_ascii=False, indent=2)
print("saved to sample_data.json")
