import chromadb
from chromadb.utils import embedding_functions
from config import settings
# 引入自定义的 Embedding Function
from tools.ecnu_embedding import ECNUEmbeddingFunction

class RagRetriever:
    def __init__(self, collection_name="psychology_knowledge"):
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_SERVER_HOST,
            port=settings.CHROMA_SERVER_PORT
        )
        
        # 切换为 ECNU Embedding
        if "ecnu" in settings.EMBEDDING_MODEL:
            self.embedding_fn = ECNUEmbeddingFunction()
        else:
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )
        
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn
        )

    def search(self, query: str, top_k: int = 3):
        """
        根据查询词进行语义搜索
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        # 格式化输出
        formatted_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                item = {
                    "id": results['ids'][0][i],
                    "keyword": results['metadatas'][0][i].get("keyword"),
                    "content": results['documents'][0][i],
                    "source": results['metadatas'][0][i].get("source"),
                    "distance": results['distances'][0][i] if results['distances'] else None
                }
                formatted_results.append(item)
                
        return formatted_results

if __name__ == "__main__":
    # 测试代码
    try:
        retriever = RagRetriever()
        print(f"Using Embedding Model: {settings.EMBEDDING_MODEL}")
        
        # 测试向量维度
        test_vec = retriever.embedding_fn(["测试文本"])[0]
        print(f"Embedding Vector Dimension: {len(test_vec)}")
        
        print("Searching for '熵'...")
        res = retriever.search("熵")
        for item in res:
            print(f"- {item['keyword']}: {item['content'][:50]}... (Source: {item['source']})")
    except Exception as e:
        print(f"Error: {e}")
