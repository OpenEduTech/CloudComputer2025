from agents.base_agent import BaseAgent

class ValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("val.txt", model_type="ecnu")

    def run(self, node_data, subject):
        keyword = node_data.get("label")
        definition = node_data.get("info")
        
        prompt = self.prompt_template.replace("{subject_name}", subject).replace("{keyword}", keyword)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Definition: {definition}"}
        ]
        
        response = self.llm.chat(messages)
        try:
            score = float(response.strip())
            return score
        except:
            return 0.5
