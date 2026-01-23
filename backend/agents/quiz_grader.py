import json
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent

class QuizGrader(BaseAgent):
    def grade_submission(self, problem_type, question, correct_answer, user_answer, context):
        """
        混合判卷逻辑 (Hybrid Grading Strategy)：
        1. 客观题 (Choice)：
           - 先进行 Python 字符串比对（硬逻辑）。
           - 如果正确 -> 直接给满分，不调用 LLM。
           - 如果错误 -> 仅对错题调用 LLM 生成辨析。
        2. 主观题 (Short Answer)：
           - 必须调用 LLM 进行 Prometheus 评分。
        """
        
        # --- 场景 A: 客观题 (选择题) ---
        if problem_type == "choice":
            return self._grade_objective_question(question, correct_answer, user_answer, context)

        # --- 场景 B: 主观题 (简答/填空) ---
        return self._grade_subjective_question(question, correct_answer, user_answer, context)

    def _grade_objective_question(self, question, correct_answer, user_answer, context):
        """
        处理客观题：硬逻辑比对 + 错题AI解析
        """
        # 1. 数据清洗与提取
        # 用户可能提交 "A. 选项内容"，我们需要提取 "A"
        # 标准答案通常是 "A"
        user_clean = self._extract_option_letter(user_answer)
        correct_clean = self._extract_option_letter(correct_answer)

        # 2. 硬逻辑判定 (Deterministic Check)
        is_correct = (user_clean == correct_clean)
        score = 10 if is_correct else 0
        
        # 3. 分支处理
        if is_correct:
            # ✅ 情况 1: 答对了
            # 此时不需要浪费 LLM 资源，直接返回静态鼓励
            return {
                "score": 10,
                "feedback": "回答正确",
                "analysis": f"🎉 恭喜！你的选择（{user_clean}）完全正确。该知识点掌握得很好。"
            }
        else:
            # ❌ 情况 2: 答错了
            # 此时调用 LLM，专门解释“为什么选错了”
            feedback_short = f"回答错误。你的选择是 {user_clean}，正确答案是 {correct_clean}。"
            
            # 开发模式下返回模拟的解析结果
            if self.llm is None:
                question_text = str(question).strip()
                analysis_parts = []
                if question_text:
                    analysis_parts.append(f"[开发模式] 本题题干：{question_text}。")
                else:
                    analysis_parts.append("[开发模式] 本题判分结果如下。")
                analysis_parts.append(f"正确答案是 {correct_clean}，你的选择是 {user_clean}。")
                analysis_parts.append("当前运行在开发模式下，系统只做对错判断，不调用大模型生成细致解析。")
                analysis_parts.append("请结合题干中的关键信息和各选项的含义，对比思考为什么标准答案更符合题意，并回顾相关知识点。")
                analysis_text = "".join(analysis_parts)
            else:
                analysis_prompt = ChatPromptTemplate.from_template("""
                你是一个专业的辅导老师。学生在做一道选择题时选错了。

                [题目信息]
                - 题目: {question}
                - 正确答案: {correct_answer}
                - 学生错误选项: {user_answer}
                - 相关知识点: {context}

                [任务]
                1. 明确指出学生的选项({user_answer})错在哪里（例如：概念混淆、计算错误、逻辑陷阱等）。
                2. 简要解释正确答案({correct_answer})的依据。
                3. 解析要一针见血，控制在100字以内。

                [输出]
                直接输出解析文本，不要包含任何格式标记。
                """)
                
                chain = analysis_prompt | self.llm | StrOutputParser()
                
                try:
                    # print(f"🔍 正在分析错题: 用户选 {user_clean} vs 正确 {correct_clean}")
                    analysis_text = chain.invoke({
                        "question": question,
                        "correct_answer": correct_answer,
                        "user_answer": user_answer,
                        "context": context[:800] 
                    })
                except Exception as e:
                    print(f"⚠️ 错题解析生成失败: {e}")
                    analysis_text = "（AI解析服务繁忙，请参考标准答案复习对应章节。）"

            return {
                "score": 0,
                "feedback": feedback_short,
                "analysis": analysis_text
            }

    def _grade_subjective_question(self, question, correct_answer, user_answer, context):
        """
        处理主观题：Prometheus 评分标准
        """
        # 开发模式下返回模拟的评分结果
        if self.llm is None:
            # 根据用户回答的长度和内容简单模拟评分
            score = 6 if len(user_answer.strip()) > 20 else 3
            return {
                "score": score,
                "feedback": f"[开发模式] 主观题评分完成",
                "analysis": f"[开发模式] 题目：{question}\n标准答案：{correct_answer}\n你的回答：{user_answer}\n基于Prometheus评分标准，你获得了{score}分。"
            }
        prometheus_prompt = ChatPromptTemplate.from_template("""
        ### Role
        你是一个公正的考官。请使用 Prometheus 评分标准评估学生的简答题。

        ### Input
        - 题目: {question}
        - 参考答案: {correct_answer}
        - 学生回答: {user_answer}
        - 知识背景: {context}

        ### Scoring Criteria (Total 10分)
        1. 知识点覆盖 (0-5分): 关键词命中情况
        2. 逻辑连贯性 (0-3分): 表达清晰度
        3. 准确性 (0-2分): 是否有事实错误

        ### Output Format (JSON Only)
        请严格返回合法的JSON格式，不要包含Markdown标记：
        {{
            "score": <0-10>,
            "feedback": "简短评语",
            "analysis": "详细解析：失分点在哪里..."
        }}
        """)
        
        chain = prometheus_prompt | self.llm | StrOutputParser()
        
        try:
            res = chain.invoke({
                "question": question, 
                "correct_answer": correct_answer, 
                "user_answer": user_answer,
                "context": context[:1000]
            })
            # 清洗可能的 Markdown 标记
            clean_res = res.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_res)
        except Exception as e:
            print(f"❌ 主观题评分失败: {e}")
            return {
                "score": 0, 
                "feedback": "评分服务响应超时", 
                "analysis": "无法完成智能评分，请人工核对。"
            }

    def _extract_option_letter(self, text):
        """
        辅助函数：从 "A. 选项内容" 或 " A " 中提取 "A"
        """
        if not text:
            return ""
        
        # 1. 尝试直接去除首尾空格并转大写
        text = str(text).strip().upper()
        
        # 2. 如果是 "A. xxx" 格式，取第一个点之前的部分
        if "." in text:
            parts = text.split(".")
            # 假设第一个部分是字母（如 A, B, C, D）
            potential_letter = parts[0].strip()
            if len(potential_letter) == 1 and potential_letter.isalpha():
                return potential_letter
        
        # 3. 如果只是单个字母，直接返回
        if len(text) == 1 and text.isalpha():
            return text
            
        # 4. 兜底：如果无法解析，返回原文本的前1个字符（假设它是选项）
        # 这一步是为了防止前端传回纯文本导致比对失败
        return text[0] if text else ""

    def analyze_difficulty_gradient(self, grading_results):
        """
        分析试卷的难度梯度合理性
        输入: grading_results (list of dict)
        输出: dict (包含各难度正确率、合理性判断、总结文案)
        """
        stats = {
            "Easy": {"score": 0, "max_score": 0},
            "Medium": {"score": 0, "max_score": 0},
            "Hard": {"score": 0, "max_score": 0}
        }
        
        for res in grading_results:
            diff = res.get('difficulty', 'Easy')
            if diff in stats:
                stats[diff]["score"] += res.get('score', 0)
                stats[diff]["max_score"] += 10  # 假设每题满分10分

        # 计算正确率 (score / max_score)
        accuracies = {}
        for diff in ["Easy", "Medium", "Hard"]:
            if stats[diff]["max_score"] > 0:
                accuracies[diff] = stats[diff]["score"] / stats[diff]["max_score"]
            else:
                accuracies[diff] = 0.0

        # 映射到前端展示名称
        # Easy -> 基础, Medium -> 进阶, Hard -> 挑战
        basic_acc = accuracies["Easy"]
        adv_acc = accuracies["Medium"]
        cha_acc = accuracies["Hard"]

        # 梯度合理性判定规则: 基础 >= 进阶 >= 挑战
        # 允许微小的波动(比如0.05?) 暂时严格判定
        is_reasonable = (basic_acc >= adv_acc) and (adv_acc >= cha_acc)

        # 生成总结文案
        summary = f"本次作答中，各难度正确率为：基础 {basic_acc:.0%}，进阶 {adv_acc:.0%}，挑战 {cha_acc:.0%}。"
        
        if is_reasonable:
            summary += " 正确率随难度递减，说明试卷难度梯度合理。"
        else:
            reasons = []
            if basic_acc < adv_acc:
                reasons.append("进阶题正确率高于基础题")
            if adv_acc < cha_acc:
                reasons.append("挑战题正确率高于进阶题")
            
            if reasons:
                summary += f" {'，'.join(reasons)}，系统标注难度可能存在偏差，或您在特定难度表现异常。"
            else:
                 summary += " 难度梯度分布不符合典型预期。"

        return {
            "chart_data": {
                "难度": ["基础", "进阶", "挑战"],
                "正确率": [basic_acc, adv_acc, cha_acc]
            },
            "summary": summary,
            "is_reasonable": is_reasonable
        }
