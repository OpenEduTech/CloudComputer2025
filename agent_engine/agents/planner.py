from agents.base_agent import BaseAgent
from config import settings

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("planner.txt", model_type="ecnu")

    def run(self, user_query):
        print(f"Planner Agent processing: {user_query}")
        
        # 动态获取学科列表
        subjects = settings.AVAILABLE_SUBJECTS
        subject_list_str = str(subjects)
        
        # 注入动态列表到 Prompt
        prompt = self.prompt_template.replace("{subject_list}", subject_list_str)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_query}
        ]
        response = self.llm.chat(messages)
        plan = self.parse_json(response)
        
        # 处理全学科查找逻辑
        if plan and (not plan.get("subjects") or len(plan["subjects"]) == 0):
            print(f"No specific subjects found in plan, defaulting to ALL subjects: {subjects}")
            plan["subjects"] = subjects
            
        return plan
