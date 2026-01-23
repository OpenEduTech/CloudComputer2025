import fitz
import json
import re
import os
from openai import OpenAI

MODEL_NAME = "glm-4-flash"
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
)

def extract_text_from_pdf_bytes(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "".join([page.get_text() for page in doc])
    except: return ""

def extract_text_from_txt_bytes(file_bytes):
    try: return file_bytes.decode('utf-8')
    except: return file_bytes.decode('gbk', errors='ignore')

def safe_json_parse(ai_content):
    try: return json.loads(ai_content)
    except:
        match = re.search(r"(\{.*\})", ai_content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1).strip())
            except: return None
        return None

# --- 难度梯度实现核心 ---
def generate_one_mcq(text, difficulty=3):
    """实现 1-5 级难度梯度合理性"""
    diff_map = {
        1: "入门：考察单一事实，无干扰项。",
        2: "基础：考察基本定义，干扰项易辨析。",
        3: "进阶：考察原理应用，需逻辑推理。",
        4: "专业：多知识点关联，干扰项极具迷惑性。",
        5: "专家/地狱：案例背景复杂，考察底层逻辑与边界条件。"
    }
    level_hint = diff_map.get(difficulty, diff_map[3])
    
    prompt = f"""根据内容生成1道单选题，难度等级 {difficulty}/5 ({level_hint})。
    内容：{text[:1200]}
    必须返回JSON: {{"type":"mcq","question":"..","options":["A.","B.","C.","D."],"reference_answer":"A","analysis":".."}}
    """
    try:
        response = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.7)
        return safe_json_parse(response.choices[0].message.content)
    except: return {"question": "生成失败", "options": ["A.重试","B.重试","C.重试","D.重试"], "reference_answer": "A"}

def generate_one_short(text, difficulty=3):
    prompt = f"根据内容生成1道简答题，难度等级 {difficulty}/5。内容：{text[:1200]}。返回JSON含question, reference_answer, analysis。"
    try:
        response = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
        data = safe_json_parse(response.choices[0].message.content)
        if data: data['type'] = 'short'
        return data
    except: return {"type": "short", "question": "生成失败"}

# --- 个性化“小灶”建议实现核心 ---
def grade_short_answer(question, ref_ans, user_ans):
    """提供具有针对性的简答题评语 """
    prompt = f"题目：{question}\n标答：{ref_ans}\n学生回答：{user_ans}\n请扮演老师，指出学生回答中缺失的关键点并给出改进建议。返回JSON: {{'score': 整数, 'comment': '针对性建议'}}"
    try:
        response = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
        return safe_json_parse(response.choices[0].message.content)
    except: return {"score": 0, "comment": "判卷失败"}

def get_mistake_feedback(question, correct_ans, user_ans):
    """对比‘标答’与‘错选’，生成个性化纠偏分析 """
    prompt = f"题目：{question}\n正确答案：{correct_ans}\n学生错选：{user_ans}\n请分析学生为什么会选错，并给出50字内的纠偏建议。"
    try:
        response = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content.strip()
    except: return "请复习相关概念。"