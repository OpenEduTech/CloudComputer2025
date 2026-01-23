import chromadb
from config import settings
from tools.ecnu_embedding import ECNUEmbeddingFunction

def inspect_chroma(limit=5):
    print(f"Connecting to ChromaDB at {settings.CHROMA_SERVER_HOST}:{settings.CHROMA_SERVER_PORT}...")
    client = chromadb.HttpClient(
        host=settings.CHROMA_SERVER_HOST,
        port=settings.CHROMA_SERVER_PORT
    )
    
    # 获取所有 Collection
    collections = client.list_collections()
    print(f"Found {len(collections)} collections:")
    for col in collections:
        print(f" - {col.name} (Metadata: {col.metadata})")
    
    if not collections:
        return

    # 选择第一个或者指定的 Collection 查看
    target_col = collections[0]
    print(f"\nInspecting collection: {target_col.name}...")
    
    count = target_col.count()
    print(f"Total documents in collection: {count}")
    
    if count == 0:
        return

    # 获取前 N 条数据
    # peek() 方法在某些版本可用，或者使用 get()
    results = target_col.get(limit=limit, include=["metadatas", "documents"])
    
    print(f"\n--- First {limit} Documents ---")
    for i in range(len(results['ids'])):
        doc_id = results['ids'][i]
        meta = results['metadatas'][i]
        doc = results['documents'][i]
        
        print(f"\n[ID]: {doc_id}")
        print(f"[Metadata]: {meta}")
        print(f"[Content Snippet]: {doc[:100]}...") # 只显示前100个字符
        print("-" * 50)

if __name__ == "__main__":
    inspect_chroma()
