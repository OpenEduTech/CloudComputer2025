from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
# 加载环境变量
load_dotenv()

def get_llm():
    return ChatOpenAI(
    api_key="sk-eeguuqrgdxpamorwpxmypfmmmkycsycchvrfitekxtatioqr",# 直接硬编码
    base_url="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-V3.2-Exp",
    temperature=0.3,
    max_retries=3
)