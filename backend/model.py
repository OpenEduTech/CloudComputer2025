import os
import json
from pathlib import Path
from typing import TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda
import re

from langgraph.graph import StateGraph,END

from prompt import first_get,next_get,checker,difinition_prompt,qa_prompt

load_dotenv()
base_url = os.getenv("base_url")
api_key = os.getenv("API_KEY")

#定义状态
class State(TypedDict):
    concept : str #概念
    content : dict #数据，包含返回的节点，边等
    check : str #检查者提出的建议
    score : float #评分，1~10
    times : int #循环次数，达到三次可以直接返回了
        
    
chat = ChatOpenAI(
    base_url=base_url,
    api_key=str(api_key),
    model="qwen-plus"
)


#定义节点
def getdata_node(state:State):
    concept = state["concept"]
    
    times = state["times"]
    
    #提示词
    if times == 0:#第一次生成
        prompt = ChatPromptTemplate.from_template(
            first_get          
        )
        
        chain = prompt | chat | JsonOutputParser()
        res = chain.invoke({"concept":concept})  #输出为字典类型
        
    else:
        check = state["check"] #获取意见
        hdata = json.dumps(state["content"])
        
        prompt = ChatPromptTemplate.from_template(
            next_get
        )
        
        chain = prompt | chat | JsonOutputParser()
        res = chain.invoke({"concept":concept,"history_graph_data":hdata,"suggestion":check})
        
    return {"content":res,"times":times+1}
    
    
def check_node(state:State):
    concept = state["concept"]
    data = json.dumps(state["content"])
    
    prompt = ChatPromptTemplate.from_template(
        checker
    )
    chain = prompt | chat | JsonOutputParser()
    res = chain.invoke({"concept":concept,"graph_data":data})
    
    return {"check":res['suggestion'],"score":res['total_score']}

#路由函数
def re_rooter(state:State):
    score = state["score"]
    if score >= 7:
        return "end"
    else:
        return "rewrite"

#构建图
builder = StateGraph(State)

builder.add_node("writer",getdata_node)
builder.add_node("rewriter",check_node)

builder.set_entry_point("writer")
builder.add_edge("writer","rewriter")

builder.add_conditional_edges(
    "rewriter",
    re_rooter,
    {
        "end":END,
        "rewrite":"writer"
    }
)

graph = builder.compile()

#修复返回格式
def fix_latex_escape(raw_str: str) -> str:
    # 正则匹配$...$（非贪婪匹配，避免跨多个公式）
    def replace_backslash(match):
        # 把匹配到的公式中的\换成\\
        latex_part = match.group(0)
        fixed_latex = latex_part.replace("\\", "\\\\")
        return fixed_latex
    
    # 执行替换
    fixed_str = re.sub(r'\$.*?\$', replace_backslash, raw_str)
    # 额外清理：移除首尾空白/换行（避免JSON解析开头错误）
    fixed_str = fixed_str.strip()
    return fixed_str

#具体概念查询智能体
prompt_difinition = ChatPromptTemplate.from_messages(
    difinition_prompt
)
chain_difinition = prompt_difinition | chat | RunnableLambda(lambda x: x.content)  | RunnableLambda(fix_latex_escape) | JsonOutputParser()

#提问助手
prompt_qa = ChatPromptTemplate.from_messages(
    qa_prompt
)
chain_qa = prompt_qa | chat | RunnableLambda(lambda x: x.content)  | RunnableLambda(fix_latex_escape) | JsonOutputParser()

'''
res = graph.invoke({"concept":"最小二乘法","times":0})
print(res)
'''

'''
prompt = ChatPromptTemplate.from_template(
            first_get          
        )

chain = prompt | chat | JsonOutputParser()

res = chain.invoke({"concept":"最小二乘法"})

print(type(res))
print(res)
'''

'''
res = chain_difinition.invoke({"concept":"梯度下降","domain":"深度学习"})
print(res)
'''
'''data = {"nodes": [{"id":"gd-001","label":"梯度下降","domain":"机器学习"},{"id":"gd-005","label":"动量法","domain":"深度学习"},{"id":"gd-009","label":"自适应矩估计(Adam)","domain":"深度学习"},{"id":"gd-010","label":"损失函数","domain":"机器学习"},{"id":"gd-007","label":"凸优化","domain":"数学"},{"id":"gd-008","label":"反向传播","domain":"深度学习"}],"edges": [{"source":"gd-005","target":"gd-001","relation":"优化改进"},{"source":"gd-009","target":"gd-001","relation":"进阶变体"},{"source":"gd-010","target":"gd-001","relation":"优化目标"}]}
res = chain_qa.invoke({'concept':"梯度下降","question":"在深度学习训练中，动量法和Adam优化器相比梯度下降原始版本有哪些优势？它们适合应用在哪些场景？","concept_relations":json.dumps(data,ensure_ascii=False)})
print(res)
'''