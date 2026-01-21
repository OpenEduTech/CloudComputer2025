from agents.base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("planner.txt", model_type="ecnu")

    def run(self, user_query):
        print(f"Planner Agent processing: {user_query}")
        messages = [
            {"role": "system", "content": self.prompt_template},
            {"role": "user", "content": user_query}
        ]
        response = self.llm.chat(messages)
        return self.parse_json(response)
