import os
import fitz  # PyMuPDF 库，用于解析 PDF
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

# 1. 定义数据结构模型
class Question(BaseModel):
    index: int = Field(description="题目序号")
    type: str = Field(description="题目类型：选择题 或 简答题")
    question: str = Field(description="题目内容")
    options: List[str] = Field(default=[], description="选择题选项，简答题留空")
    answer: str = Field(description="选择题的标准字母答案，或简答题的参考答案要点")
    analysis: str = Field(description="知识点深度解析")

# 2. 核心智能体类
class StudyAgent:
    def __init__(self):
        # 初始化 DeepSeek 客户端
        self.model = ChatOpenAI(
            api_key="sk-2e6471af496247b88ea3793eaceca94f", 
            base_url="https://api.deepseek.com", 
            model="deepseek-chat",
            temperature=0.5 # 调低温度提高格式稳定性
        )
        
    def parse_pdf(self, file_path):
        """解析本地 PDF 文件提取文本"""
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text[:3000] # 限制字符防止超限

    def generate_comprehensive_questions(self, text):
        """智能出题：生成选择题+简答题"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个教育专家。请根据提供的资料出 2 道单选题和 1 道简答题。
            注意：必须严格返回 JSON 列表格式，每个对象必须包含 'index'(1,2,3)、'type'、'question'、'options'、'answer'、'analysis' 字段。"""),
            ("human", "学习资料内容：{context}")
        ])
        chain = prompt | self.model | JsonOutputParser()
        try:
            return chain.invoke({"context": text})
        except Exception as e:
            print(f"出题失败: {e}")
            return None

    def grade_answer(self, question_text, standard_answer, user_answer):
        """智能阅卷：对比用户输入与标准答案，给出评分和建议"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个严谨的阅卷老师。请根据标准答案评判用户答案。
            返回 JSON 格式，包含：'is_correct'(布尔值)、'score'(0-100分)、'feedback'(详细的改进建议)。"""),
            ("human", "题目：{q}\n标准答案：{sa}\n用户答案：{ua}")
        ])
        chain = prompt | self.model | JsonOutputParser()
        try:
            return chain.invoke({"q": question_text, "sa": standard_answer, "ua": user_answer})
        except Exception as e:
            print(f"判卷失败: {e}")
            return {"is_correct": False, "score": 0, "feedback": "判卷逻辑发生错误"}