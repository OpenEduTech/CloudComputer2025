from agents.base_agent import BaseAgent

class QueryAgent(BaseAgent):
    def __init__(self):
        super().__init__("query.txt", model_type="ecnu")

    def run(self, miner_result):
        # 简单逻辑：如果 Miner 返回空，直接返回 yes
        if not miner_result:
            return "yes"
            
        # 让 LLM 判断结果质量
        messages = [
            {"role": "system", "content": self.prompt_template},
            {"role": "user", "content": f"Current Result: {miner_result}"}
        ]
        response = self.llm.chat(messages)
        return response.strip().lower()
