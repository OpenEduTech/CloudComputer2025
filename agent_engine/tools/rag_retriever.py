import chromadb
import hashlib
from chromadb.utils import embedding_functions
from config import settings
# 引入自定义的 Embedding Function
from tools.ecnu_embedding import ECNUEmbeddingFunction

class RagRetriever:
    def __init__(self, collection_name=None):
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
        
        self.default_collection_name = collection_name or "psychology_knowledge"
        
        # 如果指定了 collection_name，预加载它
        if collection_name:
            self.default_collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn
            )
        else:
            self.default_collection = None

    def _get_collection_name(self, subject: str) -> str:
        """
        根据 Subject 计算 Collection Name (MD5 Hash)
        """
        if not subject:
            return self.default_collection_name
        
        # 与 ingest_books.py 保持一致的哈希逻辑
        hash_object = hashlib.md5(subject.encode())
        hash_hex = hash_object.hexdigest()
        return f"cat_{hash_hex}"

    def search(self, query: str, top_k: int = 3, subject: str = None):
        """
        根据查询词进行语义搜索
        """
        # 确定要搜索的 Collection
        target_name = self._get_collection_name(subject)
        
        try:
            # 动态获取/创建 Collection 对象
            # 注意：如果 subject 不存在，Chroma 也会创建一个空的 collection，这没问题
            collection = self.client.get_or_create_collection(
                name=target_name,
                embedding_function=self.embedding_fn
            )
            
            # 如果 collection 是空的，直接返回
            if collection.count() == 0:
                print(f"Collection '{target_name}' (Subject: {subject}) is empty.")
                return []

            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            # 格式化输出
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'][0])):
                    meta = results['metadatas'][0][i]
                    item = {
                        "id": results['ids'][0][i],
                        "keyword": meta.get("keyword"),
                        "content": results['documents'][0][i],
                        "source": meta.get("source"),
                        "sub_category": meta.get("sub_category"), # 新增
                        "category": meta.get("category"),         # 新增
                        "metadata": meta,                         # 为了保险，把原始 metadata 也带上
                        "distance": results['distances'][0][i] if results['distances'] else None
                    }
                    formatted_results.append(item)
                    
            return formatted_results
            
        except Exception as e:
            print(f"Error searching collection '{target_name}': {e}")
            return []

if __name__ == "__main__":
    # 测试代码
    try:
        retriever = RagRetriever()
        print(f"Using Embedding Model: {settings.EMBEDDING_MODEL}")
        
        # 测试：搜索 'Formal_Sciences_and_Computation' 下的 '熵'
        subject = "Formal_Sciences_and_Computation"
        print(f"Searching for '熵' in {subject}...")
        res = retriever.search("熵", subject=subject)
        for item in res:
            print(f"- {item['keyword']}: {item['content'][:50]}... (Source: {item['source']})")
            
    except Exception as e:
        print(f"Error: {e}")
