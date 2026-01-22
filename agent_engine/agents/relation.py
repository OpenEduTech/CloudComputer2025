import json
from agents.base_agent import BaseAgent

class RelationAgent(BaseAgent):
    def __init__(self):
        super().__init__("relation.txt", model_type="kimi")

    def run(self, node1, node2):
        subject1 = node1.get("group")
        subject2 = node2.get("group")
        
        input_data = {
            "keyword": node1.get("label"), 
            "subject_name1": node1.get("info"),
            "subject_name2": node2.get("info")
        }
        
        prompt = self.prompt_template.replace("{subject_name1}", subject1).replace("{subject_name2}", subject2)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(input_data, ensure_ascii=False)}
        ]
        
        response = self.llm.chat(messages)
        return self.parse_json(response)
