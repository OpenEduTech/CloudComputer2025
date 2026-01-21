import json
from agents.base_agent import BaseAgent
from tools.rag_retriever import RagRetriever

class MinerAgent(BaseAgent):
    def __init__(self):
        super().__init__("miner.txt", model_type="ecnu")
        self.retriever = RagRetriever() # 使用默认的 ecnu-embedding

    def run(self, keyword, subject):
        print(f"Miner Agent processing: {keyword} in {subject}")
        
        # 1. RAG Search
        chunks = self.retriever.search(f"{subject} {keyword}", top_k=3, subject=subject)
        
        if not chunks:
            print("No chunks found.")
            return None

        # Prepare context for LLM
        # 将 Chunk 的元数据也包含进去，以便 LLM 提取 sub_category 和 source
        chunk_data = []
        for c in chunks:
            chunk_data.append({
                "content": c['content'],
                "source": c['source'],
                "sub_category": c.get('sub_category', 'Unknown')
            })
        
        input_data = {
            "keyword": keyword,
            "chunk": chunk_data, # 现在这里是一个对象列表
            "subject_name": subject
        }
        prompt = self.prompt_template.replace("{subject_name}", subject).replace("{keyword}", keyword)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(input_data, ensure_ascii=False)}
        ]
        
        response = self.llm.chat(messages)
        # print(f"DEBUG: Miner LLM Response: {response}") # Uncomment for debug
        return self.parse_json(response)
