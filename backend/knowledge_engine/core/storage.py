import os
import json
from typing import Dict, List

# 数据存储在 backend/data 目录下
DATA_DIR = "./data"
GRAPH_DIR = os.path.join(DATA_DIR, "graphs")

class JSONStorage:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(GRAPH_DIR, exist_ok=True)
        
        self.docs_file = os.path.join(DATA_DIR, "documents.json")
        self.chunk_map_file = os.path.join(DATA_DIR, "chunk_mapping.json")
        
        if not os.path.exists(self.docs_file):
            self._save_json(self.docs_file, {})
        if not os.path.exists(self.chunk_map_file):
            self._save_json(self.chunk_map_file, {})
    
    def _load_json(self, path: str) -> dict:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_json(self, path: str, data: dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def save_documents(self, docs: List[dict]):
        all_docs = self._load_json(self.docs_file)
        for doc in docs:
            all_docs[doc['doc_id']] = {
                'domain': doc['domain'],
                'content': doc['content']
            }
        self._save_json(self.docs_file, all_docs)
    
    def get_document(self, doc_id: str) -> dict:
        all_docs = self._load_json(self.docs_file)
        return all_docs.get(doc_id)
    
    def save_graph(self, concept: str, graph_data: dict):
        graph_file = os.path.join(GRAPH_DIR, f"{concept}.json")
        self._save_json(graph_file, graph_data)
    
    def get_graph(self, concept: str) -> dict:
        graph_file = os.path.join(GRAPH_DIR, f"{concept}.json")
        if not os.path.exists(graph_file):
            return None
        return self._load_json(graph_file)

storage = JSONStorage()