import json
from agents.base_agent import BaseAgent
from tools.search_arxiv import search_arxiv
from tools.search_wikipedia import search_wikipedia

class MinerOnlineAgent(BaseAgent):
    def __init__(self):
        super().__init__("miner_online.txt", model_type="kimi")

    def run(self, keyword, subject, depth=2):
        print(f"Miner Online Agent searching for: {keyword} in {subject} (Depth: {depth})")
        
        # 1. Search Arxiv
        arxiv_results = search_arxiv(f"{subject} {keyword}")
        
        # 2. Search Wikipedia
        wiki_result = search_wikipedia(f"{subject} {keyword}")
        
        # Prepare context
        search_content = {
            "arxiv": arxiv_results,
            "wikipedia": wiki_result
        }
        
        # Replace placeholders
        prompt = self.prompt_template.replace("{subject_name}", subject).replace("{keyword}", keyword)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(search_content, ensure_ascii=False)}
        ]
        
        response = self.llm.chat(messages)
        return self.parse_json(response)
