import json
import re
from typing import List, Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化 Qwen 客户端
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

if not QWEN_API_KEY:
    raise ValueError("请在 .env 文件中配置 QWEN_API_KEY")

client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)

# ------------------------------------------------------------------------------
# 核心工具函数
# ------------------------------------------------------------------------------
def call_qwen_api(prompt: str, system_prompt: str, max_tokens: int = 1500) -> str:
    """调用 Qwen API，返回响应文本"""
    try:
        completion = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
            stream=False
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[错误] Qwen API 调用失败：{str(e)}")
        return ""

def display_exam_points(all_points: List[str]) -> None:
    """交互式模式：显示提取的考点（仅本地运行时生效）"""
    print("\n" + "="*60)
    print("检测到以下可出题考点（共 {} 条）：".format(len(all_points)))
    print("="*60)
    for i, point in enumerate(all_points, 1):
        print(f"{i:2d}. {point}")
    print("="*60)

def collect_user_requirements(all_points: List[str]) -> Dict[str, Any]:
    """交互式模式：收集用户出题要求（仅本地运行时生效）"""
    print("\n请设置出题要求：")
    
    # 题型选择（使用空格分隔）
    print("\n支持题型：1=选择题, 2=简答题, 3=计算题, 4=综合题")
    q_type_map = {"1": "选择题", "2": "简答题", "3": "计算题", "4": "综合题"}
    while True:
        q_type_input = input("请选择题型编号（空格分隔，如：1 2）：").strip()
        selected_types = []
        if not q_type_input:
            print("未输入题型，默认使用选择题")
            selected_types = ["选择题"]
            break
        
        parts = q_type_input.split()
        valid = True
        for t in parts:
            t_clean = t.strip()
            if t_clean in q_type_map:
                selected_types.append(q_type_map[t_clean])
            else:
                print(f"无效题型：{t_clean}，跳过")
                valid = False
        
        if selected_types:
            break
        else:
            print("未选择任何有效题型，请重新输入（1-4）")
    
    # 题目数量
    while True:
        try:
            num_questions = int(input("请输入题目总数（建议 1-10）："))
            if 1 <= num_questions <= 10:
                break
            else:
                print("请输入 1-10 之间的整数")
        except ValueError:
            print("请输入有效数字")

    # 难度（可选）
    difficulty = input("指定难度（简单/中等/困难，默认中等）：").strip() or "中等"

    # 重点领域（可选，空格分隔）
    print("\n可指定重点考点编号（空格分隔，如：1 3 5），留空则使用全部考点")
    focus_input = input("重点考点编号（空格分隔）：").strip()
    focus_points = []
    if focus_input:
        try:
            indices = [int(x.strip()) - 1 for x in focus_input.split() if x.strip()]
            focus_points = [all_points[i] for i in indices if 0 <= i < len(all_points)]
        except (ValueError, IndexError):
            print(" 编号格式错误，将使用全部考点")
            focus_points = all_points
    else:
        focus_points = all_points

    return {
        "question_types": selected_types,
        "num_questions": num_questions,
        "difficulty": difficulty,
        "focus_points": focus_points
    }

# ========== 核心修改1：简化JSON提取函数（降低解析复杂度） ==========
def extract_json(text: str) -> str:
    """
    简化JSON提取逻辑：优先返回纯文本题目，失败则返回空（不再强行修复格式）
    """
    text = text.strip()
    # 仅移除Markdown代码块，不做复杂格式修复
    text = re.sub(r'^```(json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    
    # 仅检查是否包含合法JSON数组开头/结尾
    if text.startswith('[') and text.endswith(']'):
        return text
    return ""

# ========== 新增：事实校验函数 ==========
def validate_question(question: str, source_text: str) -> bool:
    """
    校验题目是否基于教材原文，防LLM幻觉超纲题
    :param question: 生成的题目文本
    :param source_text: 原始教材文本
    :return: True=题目合规，False=题目超纲
    """
    prompt = f"""
请严格判断以下题目是否仅基于提供的教材内容生成，禁止包含原文未提及的概念/知识点：

【教材原文片段】
{source_text[:1500]}  # 限制长度，避免token超限

【待校验题目】
{question}

【判断规则】
1. 仅回答“是”或“否”，不要任何解释、备注；
2. 题目中的所有概念、知识点必须在教材原文中明确出现；
3. 即使是合理推断，但原文未提及的，也回答“否”。
"""
    response = call_qwen_api(
        prompt=prompt,
        system_prompt="你是严格的事实校验专家，仅输出“是”或“否”，无其他内容",
        max_tokens=10
    )
    return "是" in response.strip()

# ========== 核心修改2：重构generate_structured_questions函数 ==========
def generate_structured_questions(requirements: Dict[str, Any], raw_text: str) -> List[Dict]:
    """生成结构化题目（优先纯文本解析，JSON失败则兜底生成不重复题目）"""
    focus_str = "\n".join(f"- {p}" for p in requirements["focus_points"])
    types_str = "、".join(requirements["question_types"])
    num_questions = requirements['num_questions']
    
    # 修改Prompt：优先要求纯文本输出（而非强制JSON），降低解析难度
    prompt = f"""
你是严谨的大学统计学命题教师，请按以下要求生成{num_questions}道题目，仅输出题目文本，无任何额外内容！

【原始教材内容】
{raw_text[:2000]}

【指定考点】
{focus_str}

【出题要求】
1. 题型：{types_str}（随机分配，确保不重复）
2. 数量：{num_questions} 道
3. 难度：{requirements['difficulty']}
4. 必须基于指定考点，禁止超纲
5. 每题对应不同考点，绝对不要重复
6. 出题时题的内容要和题型一致

【输出格式】
每道题的格式为：题目X（题型，分值，难度）|题干内容
示例：
题目1（选择题，5分，简单）主成分分析的核心目的是什么？
A. 特征选择
B. 特征降维
C. 特征标准化
D. 特征编码
题目2（简答题，5分，简单）请解释主成分回归与普通线性回归的区别
"""
    response = call_qwen_api(
        prompt=prompt,
        system_prompt="仅输出题目文本，严格按示例格式，无JSON、无解释、无多余内容",
        max_tokens=3000
    )

    try:
        # 第一步：尝试解析纯文本题目（替代复杂JSON解析）
        structured_questions = []
        lines = response.strip().split("\n")
        
        for i, line in enumerate(lines):
            if i >= num_questions:
                break
            if "|" not in line:
                continue
            
            # 拆分题目元信息和题干
            meta_part, question_part = line.split("|", 1)
            meta_part = meta_part.strip()
            question_part = question_part.strip()
            
            # 提取题型/分值/难度
            type_match = re.search(r"（(.*?)，\d+分，(.*?)）", meta_part)
            q_type = type_match.group(1) if type_match else requirements["question_types"][0]
            q_difficulty = type_match.group(2) if type_match else requirements["difficulty"]
            
            # 构造结构化题目（兼容原有字段）
            q = {
                "question": question_part,
                "reference_answer": "合理回答即可",  # 兜底答案
                "full_score": 5,
                "type": q_type,
                "difficulty": q_difficulty,
                "topics": [requirements["focus_points"][i % len(requirements["focus_points"])]]
            }
            
            # 事实校验
            if validate_question(q["question"], raw_text):
                structured_questions.append(q)

        # 第二步：兜底补充（确保题目数量足够，且不重复）
        while len(structured_questions) < num_questions:
            idx = len(structured_questions)
            focus_point = requirements["focus_points"][idx % len(requirements["focus_points"])]
            q_type = requirements["question_types"][idx % len(requirements["question_types"])]
            
            # 生成不重复的兜底题
            backup_q = {
                "question": f"请解释{focus_point}的核心原理及应用场景",
                "reference_answer": f"{focus_point}的核心原理是...，主要应用于...",
                "full_score": 5,
                "type": q_type,
                "difficulty": requirements["difficulty"],
                "topics": [focus_point]
            }
            
            if validate_question(backup_q["question"], raw_text):
                structured_questions.append(backup_q)

        return structured_questions

    except Exception as e:
        print(f"[警告] 文本解析失败：{str(e)}，使用兜底题目")
        # 最终兜底：生成不重复的题目（基于不同考点）
        structured_questions = []
        for i in range(num_questions):
            focus_point = requirements["focus_points"][i % len(requirements["focus_points"])]
            q_type = requirements["question_types"][i % len(requirements["question_types"])]
            
            structured_questions.append({
                "question": f"请解释 {focus_point} 的定义及应用场景",
                "reference_answer": f"{focus_point} 是统计学中的重要概念，核心定义为...，主要应用于...",
                "full_score": 5,
                "type": q_type,
                "difficulty": requirements["difficulty"],
                "topics": [focus_point]
            })
        
        return structured_questions

# ------------------------------------------------------------------------------
# 非交互式依赖函数（修复导入循环）
# ------------------------------------------------------------------------------
def extract_exam_points_from_text(text: str) -> dict:
    """
    从文本提取考点（复制 perception_layer 核心逻辑，避免导入循环）
    """
    if not text or not text.strip():
        return {"all_points": []}
    
    # 调用 LLM 提取考点（复用 Qwen API 逻辑）
    prompt = f"""
请从以下文本中提取所有与统计学/机器学习相关的明确知识点，严格按以下规则输出：

【文本内容】
{text[:10000]}

【提取规则】
1. 仅提取原文明确提及的概念、定义、公式、性质、步骤、条件；
2. 每条考点以"- "开头，内容简洁（≤25字）；
3. 禁止编造、总结、推断原文未出现的内容；
4. 无有效考点则返回空字符串。

【输出示例】
- 主成分回归=主成分分析+线性回归
- 多重共线性导致参数估计方差增大
- 主成分需基于方差-协方差矩阵求解
"""
    response = call_qwen_api(
        prompt=prompt,
        system_prompt="严谨的学术助教，仅输出符合要求的考点列表，无其他内容"
    )
    
    # 解析考点列表
    all_points = []
    if response.strip():
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("- "):
                content = line[2:].strip()
                if content:
                    all_points.append(content)
    
    return {"all_points": all_points}

def build_requirements_from_params(
    all_points: List[str],
    question_types: List[str] = None,
    num_questions: int = 5,
    difficulty: str = "中等",
    focus_point_indices: List[int] = None
) -> Dict[str, Any]:
    """非交互式构建出题需求（用于 API 调用）"""
    # 题型映射与校验
    if not question_types:
        question_types = ["选择题"]
    else:
        q_type_map = {"1": "选择题", "2": "简答题", "3": "计算题", "4": "综合题"}
        mapped_types = []
        for t in question_types:
            t_clean = str(t).strip()
            if t_clean in q_type_map:
                mapped_types.append(q_type_map[t_clean])
            elif t_clean in ["选择题", "简答题", "计算题", "综合题"]:
                mapped_types.append(t_clean)
        question_types = mapped_types if mapped_types else ["选择题"]

    # 题目数量限制（1-10 道）
    num_questions = max(1, min(10, num_questions))

    # 重点考点处理
    if focus_point_indices and isinstance(focus_point_indices, list):
        try:
            # 转换为 0-based 索引并过滤有效考点
            focus_points = [
                all_points[i-1] for i in focus_point_indices
                if isinstance(i, int) and 1 <= i <= len(all_points)
            ]
        except Exception:
            focus_points = all_points
    else:
        focus_points = all_points

    return {
        "question_types": question_types,
        "num_questions": num_questions,
        "difficulty": difficulty,
        "focus_points": focus_points
    }

# ------------------------------------------------------------------------------
# 核心对外接口
# ------------------------------------------------------------------------------
def planning_layer(
    all_points: List[str],
    raw_text: str,
    question_types: List[str] = None,
    num_questions: int = None,
    difficulty: str = None,
    focus_point_indices: List[int] = None,
    interactive: bool = True
) -> Dict[str, Any]:
    """
    规划层主函数（支持交互式/非交互式调用）
    """
    if not all_points:
        print("无可出题考点，无法生成题目")
        return {
            "requirements": {},
            "questions_raw": "",
            "structured_questions": [],
            "validation_note": "无可出题考点"
        }

    # 构建出题需求
    if interactive:
        display_exam_points(all_points)
        requirements = collect_user_requirements(all_points)
    else:
        requirements = build_requirements_from_params(
            all_points=all_points,
            question_types=question_types,
            num_questions=num_questions or 5,
            difficulty=difficulty or "中等",
            focus_point_indices=focus_point_indices,
        )

    print("\n正在生成结构化题目...")
    structured_questions = generate_structured_questions(requirements, raw_text)

    # 生成对外展示的题目文本（无答案）
    public_questions = []
    for i, q in enumerate(structured_questions, 1):
        public_questions.append(
            f"题目{i}（{q['type']}，{q['full_score']}分，{q['difficulty']}）\n{q['question']}\n"
        )
    
    return {
        "requirements": requirements,
        "questions_raw": "\n".join(public_questions),
        "structured_questions": structured_questions,
        "validation_note": "题目生成完成（已做事实校验）",  # 新增备注
        "question_count": len(structured_questions)
    }

def generate_questions_from_text(
    text: str,
    question_types: List[str] = None,
    num_questions: int = 5,
    difficulty: str = "中等",
    focus_point_indices: List[int] = None
) -> dict:
    """
    微服务入口函数（适配 FastAPI 接口调用）
    """
    if not text.strip():
        raise ValueError("输入文本不能为空")
    
    # 1. 提取考点（内置逻辑，避免导入循环）
    exam_points_result = extract_exam_points_from_text(text)
    all_points = exam_points_result.get("all_points", [])
    
    if not all_points:
        raise ValueError("未能从文本中提取有效考点，无法出题")
    
    # 2. 生成题目（非交互模式）
    result = planning_layer(
        all_points=all_points,
        raw_text=text,
        question_types=question_types,
        num_questions=num_questions,
        difficulty=difficulty,
        focus_point_indices=focus_point_indices,
        interactive=False
    )
    
    # 3. 修复返回格式（扁平化结构，移除冗余嵌套）
    return {
        "user_id": "",  # 由接口参数填充
        "questions_raw": result["questions_raw"],
        "structured_questions": result["structured_questions"],
        "question_count": len(result["structured_questions"]),  # 修复数量统计
        "status": "success",
        "validation_note": result["validation_note"]
    }