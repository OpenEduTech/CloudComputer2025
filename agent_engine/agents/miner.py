import json
from agents.base_agent import BaseAgent
from tools.rag_retriever import RagRetriever

class MinerAgent(BaseAgent):
    def __init__(self):
        super().__init__("miner.txt", model_type="kimi")
        self.retriever = RagRetriever() # 使用默认的 ecnu-embedding

    def run(self, keyword, subject, depth=2):
        print(f"Miner Agent processing: {keyword} in {subject} (Depth: {depth})")
        
        # Calculate max chunks based on depth
        # Depth 1 -> 5 chunks
        # Depth 2 -> 10 chunks
        # ...
        # Depth 5 -> 25 chunks
        max_chunks = max(5, depth * 5)
        
        # 1. RAG Search
        # User requested to limit RAG search to match depth rule (max 25)
        search_k = max_chunks 
        chunks = self.retriever.search(f"{subject} {keyword}", top_k=search_k, subject=subject)
        
        if not chunks:
            print("No chunks found.")
            return []

        # 2. Group chunks by sub_category
        grouped_chunks = {}
        for c in chunks:
            sc = c.get('sub_category', 'Unknown')
            if sc not in grouped_chunks:
                grouped_chunks[sc] = []
            grouped_chunks[sc].append(c)
            
        print(f"DEBUG: Found sub-categories: {list(grouped_chunks.keys())}")

        extracted_nodes = []

        # 3. Process each significant sub-category
        # 策略：即使只有一个 chunk 也进行处理，因为可能是唯一的定义来源
        for sub_cat, sub_chunks in grouped_chunks.items():
            # 由于 RAG 检索时已经限制了总数 search_k = max_chunks
            # 这里不需要再做 [:max_chunks] 的切片了，直接全部使用
            filtered_chunks = []
            for c in sub_chunks:
                filtered_chunks.append({
                    "content": c['content'],
                    "source": c['source'],
                    "sub_category": sub_cat,
                    "score": c.get("score", 0)
                })

            print(f"DEBUG: Mining {sub_cat} with {len(filtered_chunks)} chunks")

            input_data = {
                "keyword": keyword,
                "chunk": filtered_chunks, 
                "subject_name": subject,
                "sub_category": sub_cat
            }
            
            prompt = self.prompt_template.replace("{subject_name}", subject)\
                                         .replace("{keyword}", keyword)\
                                         .replace("{sub_category}", sub_cat)
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(input_data, ensure_ascii=False)}
            ]
            
            try:
                response = self.llm.chat(messages)
                node_data = self.parse_json(response)
                
                if node_data:
                    # Ensure group is correctly formatted if LLM messed up
                    if "group" not in node_data or sub_cat not in node_data["group"]:
                        node_data["group"] = f"{subject}--{sub_cat}"
                    
                    extracted_nodes.append(node_data)
            except Exception as e:
                print(f"Error mining sub-category {sub_cat}: {e}")

        return extracted_nodes
