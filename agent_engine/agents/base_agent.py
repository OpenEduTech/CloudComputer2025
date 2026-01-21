import os
import json
from tools.ecnu_llm import ECNULLM
from tools.kimi_llm import KimiLLM

class BaseAgent:
    def __init__(self, prompt_file, model_type="ecnu"):
        self.prompt_template = self._load_prompt(prompt_file)
        if model_type == "kimi":
            self.llm = KimiLLM()
        else:
            self.llm = ECNULLM(model="ecnu-plus") # Default to ecnu-plus

    def _load_prompt(self, filename):
        path = os.path.join(os.path.dirname(__file__), "..", "prompt", filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def parse_json(self, text):
        try:
            # 简单的 JSON 提取逻辑
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
                return json.loads(json_str)
            return json.loads(text)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return None
