# decision_layer.py（增强版：支持题号标记 + 错误敏感评分 + CoT判卷）
from openai import OpenAI
import os
from dotenv import load_dotenv
# from layers.perception_layer import parse_file_raw  # 复用感知层解析能力
import re

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)

def call_qwen_api(prompt: str, system_prompt: str, max_tokens: int = 10000) -> str:
    try:
        completion = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=max_tokens,
            stream=False
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[错误] Qwen API 调用失败：{e}")
        return ""

def extract_scoring_points(question: str, reference_answer: str, full_score: int) -> str:
    prompt = f"""
你是一名资深阅卷教师。请为以下题目制定清晰的评分细则。

【题目】
{question}

【参考答案】
{reference_answer}

【满分】
{full_score} 分

请按以下格式输出：
- 得分点1（X分）：...
- 得分点2（Y分）：...
（总分必须等于 {full_score}）

仅输出得分点列表，不要任何其他文字。
"""
    system_prompt = "你是严谨的评分标准制定者，输出必须结构化、可量化。"
    return call_qwen_api(prompt, system_prompt)

def primary_judge(question: str, reference_answer: str, user_answer: str, full_score: int) -> dict:
    if not user_answer or not user_answer.strip() or user_answer.strip() in ["（未作答）", "未作答", "无", "略", "-", "——"]:
        return {
            "score": 0,
            "reason": "用户未提供有效作答。",
            "need_review": False,
            "scoring_points": ""  # 或可设为 None
        }
    scoring_points = extract_scoring_points(question, reference_answer, full_score)
    
    # ========== 修改：新增CoT（Chain-of-Thought）判卷逻辑 ==========
    # 增强评分 prompt：强制先推理再打分，提升透明度
    prompt = f"""
你是一名**严格且细致**的统计、机器学习的阅卷老师。请遵循Chain-of-Thought（CoT）逻辑，先推理再打分。

【题目】
{question}

【参考答案与评分标准】
{scoring_points}

【用户答案】
{user_answer}

【CoT评分规则（必须严格遵守）】
1. **第一步：事实推理**
   - 逐条对比用户答案与评分标准，指出：
     a) 答对了哪些得分点（列出具体得分点+分值）；
     b) 答错/遗漏了哪些得分点（列出具体得分点+分值）；
     c) 是否存在事实性错误（概念/公式/逻辑错误）；
2. **第二步：扣分逻辑**
   - 若包含任何事实性错误，总分不得超过满分的50%；
   - 按答对的得分点累加分数，不超满分；
3. **第三步：最终打分**
   - 给出具体分数（整数）；
   - 给出至少20字的评语，包含推理过程；
4. **第四步：复核标记**
   - 若答案表述模糊/有争议，标记为“需复核”，否则“无需复核”；

【输出格式（必须严格按此格式，无其他内容）】
推理过程：[你的详细推理，至少50字]
得分：[X]分
理由：[至少20字的评语，包含推理结论]
需复核：[是/否]
"""
    system_prompt = "你是 LLM-as-a-Judge，遵循 Prometheus 评分协议 + CoT 逻辑，公平、透明、无偏见。"
    response = call_qwen_api(prompt, system_prompt)
    
    # 解析CoT评分结果
    lines = response.strip().split('\n')
    score = 0
    reason = ""
    need_review = False
    reasoning = ""  # 新增：记录推理过程
    
    for line in lines:
        if line.startswith("推理过程："):
            reasoning = line.replace("推理过程：", "").strip()
        elif line.startswith("得分："):
            try:
                score = int(line.replace("得分：", "").replace("分", "").strip())
            except:
                score = 0
        elif line.startswith("理由："):
            reason = line.replace("理由：", "").strip()
        elif line.startswith("需复核："):
            need_review = "是" in line
    
    # 确保理由长度符合要求
    if len(reason) < 20:
        reason = f"{reason} （补充：{reasoning[:50]}...）" if reasoning else "评分规则：事实错误扣50%，按得分点累加分数。"
    
    return {
        "score": score,
        "reason": reason,
        "need_review": need_review,
        "scoring_points": scoring_points,
        "cot_reasoning": reasoning  # 新增：返回CoT推理过程
    }

def secondary_judge(question: str, scoring_points: str, user_answer: str, full_score: int) -> dict:
    prompt = f"""
你是一名独立的复核专家。请重新评估以下答卷。

【题目】
{question}

【评分标准】
{scoring_points}

【用户答案】
{user_answer}

【任务】
1. 重新打分（0-{full_score}）；
2. 重点检查初评是否遗漏关键点或误判；
3. 特别注意是否存在事实性错误；
4. 输出格式：

最终得分：X 分
复核意见：...
"""
    system_prompt = "你是独立复核人，不受初评影响，只看事实与标准。"
    response = call_qwen_api(prompt, system_prompt)
    
    lines = response.strip().split('\n')
    final_score = 0
    review_comment = ""
    for line in lines:
        if line.startswith("最终得分："):
            try:
                final_score = int(line.replace("最终得分：", "").replace("分", "").strip())
            except:
                final_score = 0
        elif line.startswith("复核意见："):
            review_comment = line.replace("复核意见：", "").strip()
    
    return {
        "final_score": final_score,
        "review_comment": review_comment
    }

# ==================== 新增：智能答案分割函数 ====================
def split_answers_by_question_marker(full_text: str, num_questions: int) -> list:
    """
    根据题号标记（如 '题目1'、'第2题'、'Q3'）智能分割学生答案。
    支持多种格式：
      - 题目1：...
      - 第2题：...
      - Q3 ...
      - Question 4: ...
    若未找到有效标记，则回退到按段落分割，并打印警告。
    
    返回：长度为 num_questions 的列表，answers[i] 对应题目 i+1 的答案
    """
    answers = [""] * num_questions
    
    # 定义多种题号匹配模式（不区分大小写）
    patterns = [
        r'(?:题目|第)(\d+)[题:\s：]',      # 题目1： 或 第1题：
        r'Q(\d+)[\s：:\.]',               # Q1: 或 Q1.
        r'Question\s*(\d+)[\s：:\.]',     # Question 1:
        r'第(\d+)题[\s：:]'                # 第1题：
    ]
    
    # 尝试每种模式
    for pattern in patterns:
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE))
        if matches:
            segments = []
            for match in matches:
                try:
                    q_num = int(match.group(1))
                    start_pos = match.end()
                    segments.append((q_num, start_pos, match.start()))
                except (ValueError, IndexError):
                    continue
            
            if not segments:
                continue
                
            segments.sort(key=lambda x: x[2])  # 按文本位置排序
            
            for i, (q_num, start, _) in enumerate(segments):
                if q_num < 1 or q_num > num_questions:
                    continue
                    
                end_pos = segments[i + 1][2] if i + 1 < len(segments) else len(full_text)
                answer_text = full_text[start:end_pos].strip()
                
                # 清除后续题号污染
                for p in patterns:
                    next_match = re.search(p, answer_text, re.IGNORECASE)
                    if next_match:
                        answer_text = answer_text[:next_match.start()].strip()
                        break
                
                answers[q_num - 1] = answer_text
            
            if any(ans.strip() for ans in answers):
                return answers
    
    # ========== 回退方案：按段落/换行分割 ==========
    print("⚠️  未检测到明确题号标记！尝试按段落/换行分割答案（可能不准确）")
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    
    # 合并短行（避免选项字母被单独分割）
    merged_lines = []
    current = ""
    for line in lines:
        if len(line) < 10 and not current:
            if current:
                merged_lines.append(current)
                current = ""
            current = line
        elif len(line) < 10 and current:
            current += " " + line
        else:
            if current:
                merged_lines.append(current)
                current = ""
            merged_lines.append(line)
    if current:
        merged_lines.append(current)
    
    for i in range(min(num_questions, len(merged_lines))):
        answers[i] = merged_lines[i]
    
    return answers

# ==================== 主函数：批改所有题目 ====================
def batch_grade_all_questions(structured_questions: list, full_answer_text: str) -> dict:
    """
    批量批改所有题目
    :param structured_questions: 规划层生成的结构化题目列表，每个元素包含：
        - "question": 题目文本
        - "reference_answer": 参考答案
        - "full_score": 满分
    :param full_answer_text: 用户作答的完整文本（可能来自多个文件合并）
    :return: 包含每题得分和总分的字典
    """
    if not full_answer_text or not full_answer_text.strip():
        return {"error": "作答内容为空"}
    
    print(f"[调试] 作答全文长度：{len(full_answer_text)} 字符")
    
    # 使用智能分割提取每题答案
    student_answers = split_answers_by_question_marker(full_answer_text, len(structured_questions))
    
    # 调试输出
    for i, ans in enumerate(student_answers):
        preview = ans.replace('\n', ' ')[:60] + ("..." if len(ans) > 60 else "")
        print(f"[调试] 题目{i+1} 答案预览：{preview}")
    
    results = []
    total_score = 0
    max_total = 0
    
    for i, q_info in enumerate(structured_questions):
        print(f"\n[决策层] 正在批改题目 {i+1}...")
        user_ans = student_answers[i] if i < len(student_answers) else "（未作答）"
        
        # 初评（已加入CoT逻辑）
        result1 = primary_judge(
            question=q_info["question"],
            reference_answer=q_info["reference_answer"],
            user_answer=user_ans,
            full_score=q_info["full_score"]
        )
        
        if result1["need_review"]:
            print("  ⚠️ 触发二次判卷...")
            result2 = secondary_judge(
                question=q_info["question"],
                scoring_points=result1["scoring_points"],
                user_answer=user_ans,
                full_score=q_info["full_score"]
            )
            final_score = result2["final_score"]
            feedback = f"{result1['reason']} | 复核：{result2['review_comment']}"
        else:
            final_score = result1["score"]
            feedback = result1["reason"]
        
        results.append({
            "question_index": i + 1,
            "question": q_info["question"],
            "user_answer": user_ans, 
            "score": final_score,
            "max_score": q_info["full_score"],
            "feedback": feedback,
            "triggered_review": result1["need_review"],
            "cot_reasoning": result1.get("cot_reasoning", "")  # 新增：返回CoT推理过程
        })
        
        total_score += final_score
        max_total += q_info["full_score"]
    
    return {
        "results": results,
        "total_score": total_score,
        "max_total": max_total,
        "success": True
    }