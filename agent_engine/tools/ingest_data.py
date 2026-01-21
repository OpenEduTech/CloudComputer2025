import json
import os
import chromadb
from chromadb.utils import embedding_functions
from config import settings

def ingest_data(file_path: str, collection_name: str = "psychology_knowledge"):
    print(f"Connecting to ChromaDB at {settings.CHROMA_SERVER_HOST}:{settings.CHROMA_SERVER_PORT}...")
    client = chromadb.HttpClient(
        host=settings.CHROMA_SERVER_HOST,
        port=settings.CHROMA_SERVER_PORT
    )
    
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.EMBEDDING_MODEL
    )
    
    # 获取或创建集合 (如果存在先删除以确保数据最新，或者直接追加？这里为了测试简单，先重置)
    try:
        client.delete_collection(name=collection_name)
        print(f"Deleted existing collection: {collection_name}")
    except:
        pass
        
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn
    )
    
    print(f"Reading data from {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    ids = []
    documents = []
    metadatas = []
    
    for idx, item in enumerate(data):
        # ID 使用 keyword 或 索引
        doc_id = f"doc_{idx}_{item['keyword']}"
        ids.append(doc_id)
        documents.append(item['content'])
        metadatas.append({
            "keyword": item['keyword'],
            "source": item['source']
        })
        
    print(f"Ingesting {len(ids)} documents...")
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    print("Ingestion complete.")

if __name__ == "__main__":
    # 假设数据挂载在 /app/data (Docker内) 或本地 ./data
    data_path = "data/psychology_data.json" 
    # 如果在本地运行脚本，可能路径不同，检查是否存在
    if not os.path.exists(data_path):
        # 尝试使用绝对路径或相对路径调整
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "psychology_data.json")
    
    if os.path.exists(data_path):
        ingest_data(data_path)
    else:
        print(f"Data file not found at {data_path}")
