
import pandas as pd
import re
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent

class DashboardService:
    def __init__(self, db_manager):
        self.db = db_manager

    def process_consolidation_quiz_submission(self, quiz, user_answers, topic, user_id):
        """
        处理巩固练习提交：判分、计算正确率、保存记录
        """
        # 构造判分所需的格式
        answers_payload = []
        for i, q in enumerate(quiz):
            ans = user_answers.get(i)
            # 提取选项字母 (A/B/C/D)
            user_choice = ans.split('.')[0].strip() if ans else ""
            answers_payload.append({
                "id": q.get('id', i),
                "question": q['question'],
                "user_answer": user_choice,
                "standard_answer": q.get('answer', ''),
                "type": "choice",
                "knowledge_point": topic,
                "difficulty": q.get('difficulty', 'Medium')
            })
        
        # 简单判分逻辑
        score = 0
        total_score = len(quiz) * 10
        correct_count = 0
        
        grading_results = []
        
        for ans in answers_payload:
            is_correct = ans['user_answer'].upper() == ans['standard_answer'].upper()
            if is_correct:
                score += 10
                correct_count += 1
            grading_results.append({
                "id": ans['id'],
                "correct": is_correct,
                "score": 10 if is_correct else 0,
                "comment": "回答正确" if is_correct else f"正确答案是 {ans['standard_answer']}"
            })

        # 计算精度
        accuracy_after = score / total_score if total_score > 0 else 0.0
        
        # 获取小灶前正确率
        accuracy_before = self.db.get_knowledge_point_accuracy(user_id, topic)
        
        # 保存记录
        self.db.add_consolidation_record(user_id, topic, accuracy_before, accuracy_after)
        
        return {
            "score": score,
            "total_score": total_score,
            "correct_count": correct_count,
            "total_count": len(quiz),
            "accuracy_before": accuracy_before,
            "accuracy_after": accuracy_after,
            "grading_results": grading_results
        }

    def get_consolidation_improvement_data(self, user_id, keyword):
        """
        获取巩固练习的提升数据
        """
        records = self.db.get_consolidation_records(user_id)
        # 筛选相关记录
        related_records = [r for r in records if r.get('knowledge_point') == keyword]
        if not related_records:
            return None

        # 取最新一次记录
        latest = related_records[-1]
        acc_before = latest.get('accuracy_before', 0)
        acc_after = latest.get('accuracy_after', 0)
        
        return {
            "acc_before": acc_before,
            "acc_after": acc_after,
            "improvement": acc_after - acc_before
        }

    def get_mistake_analytics(self, mistakes):
        """
        分析错题数据，返回难度分布和类型分布的DataFrame
        """
        # 难度分布
        difficulty_counts = {}
        for m in mistakes:
            diff = m.get('difficulty', 'Unknown')
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
            
        df_difficulty = pd.DataFrame()
        if difficulty_counts:
            df_difficulty = pd.DataFrame.from_dict(difficulty_counts, orient='index', columns=['数量']).reset_index()
            df_difficulty.columns = ['难度', '数量']
            
            difficulty_order = {'基础': 1, '进阶': 2, '挑战': 3, 'Unknown': 4}
            df_difficulty['排序'] = df_difficulty['难度'].map(difficulty_order)
            df_difficulty = df_difficulty.sort_values('排序').drop('排序', axis=1)
            
            difficulty_colors = {
                '基础': '#4CAF50',
                '进阶': '#FF9800',
                '挑战': '#F44336',
                'Unknown': '#9E9E9E'
            }
            df_difficulty['颜色'] = df_difficulty['难度'].map(difficulty_colors)

        # 类型分布
        type_counts = {}
        for m in mistakes:
            q_type = m.get('type', 'Unknown')
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
            
        df_type = pd.DataFrame()
        if type_counts:
            df_type = pd.DataFrame.from_dict(type_counts, orient='index', columns=['数量']).reset_index()
            df_type.columns = ['类型', '数量']
            
            type_colors = {
                'choice': '#667eea',
                'short_answer': '#764ba2',
                'Unknown': '#9E9E9E'
            }
            df_type['颜色'] = df_type['类型'].map(type_colors)
            
        return df_difficulty, df_type

    def clean_text_snippet(self, text):
        """清理文本片段"""
        if not text:
            return ""
        # 移除日期格式 (如 2025-9-23, 2025/09/23)
        text = re.sub(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', '', text)
        # 移除过短的行（可能是人名、页眉页脚）
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if len(line.strip()) > 10]
        return " ".join(cleaned_lines)[:150] + "..."

    def format_analysis(self, mistake):
        """格式化题目解析（针对开发模式优化）"""
        analysis = mistake.get("analysis") or ""
        if "该题考察的是[开发模式]" not in analysis:
            return analysis
            
        question = str(mistake.get("question", "")).strip()
        standard_answer = str(mistake.get("standard_answer", "")).strip()
        user_answer = str(mistake.get("user_answer", "")).strip()
        
        user_display = user_answer
        if user_answer:
            text = user_answer.strip().upper()
            if "." in text:
                parts = text.split(".", 1)
                potential = parts[0].strip()
                if len(potential) == 1 and potential.isalpha():
                    user_display = potential
            elif len(text) == 1 and text.isalpha():
                user_display = text
                
        parts = []
        if question:
            parts.append(f"[开发模式] 本题题干：{question}。")
        else:
            parts.append("[开发模式] 本题判分结果如下。")
            
        if standard_answer:
            parts.append(f"正确答案是 {standard_answer}。")
        if user_display:
            parts.append(f"你的答案是 {user_display}。")
            
        parts.append("当前运行在开发模式下，系统只做对错判断，无法基于教材内容生成更细致的知识点解析。")
        parts.append("请结合题干中的关键信息和各选项含义，思考为什么标准答案更符合题意，并复习相关内容。")
        
        return "".join(parts)

    def get_review_task_status(self, user_id, keyword, chapter, section, difficulty):
        """获取复习任务状态"""
        today = datetime.now().date()
        try:
            return self.db.get_review_task_status(user_id, keyword, chapter, section, difficulty, date=today)
        except Exception:
            return False

    def mark_review_task_completed(self, user_id, keyword, chapter, section, difficulty):
        """标记复习任务完成"""
        today = datetime.now().date()
        return self.db.mark_review_task_completed(user_id, keyword, chapter, section, difficulty, date=today)

    def generate_review_plan(self, weak_point_data, agent=None):
        """生成个性化复习方案"""
        # If agent is not provided, create a default one
        if agent is None:
            agent = BaseAgent(temperature=0.3)
            
        if agent.llm is None:
             return None

        prompt = ChatPromptTemplate.from_template("""
        你是一名云计算课程的学习教练，需要围绕下面的错题聚合生成复习方案。

        [考点信息]
        - 知识点: {keyword}
        - 难度: {difficulty}
        - 累计错误次数: {error_times}
        - 考点重要性权重: {importance}
        - 最近错误时间: {last_error_time}

        [代表错题]
        - 题干: {sample_question}
        - 标准答案: {sample_standard_answer}
        - 学生作答: {sample_user_answer}
        - 判卷解析: {sample_analysis}

        [相关资料片段]
        {relevant_content}

        [学习行为概览]
        {behavior_summary}

        请完成以下任务，并用自然中文输出一段综合说明，控制在260字以内：
        1. 判断该考点当前主要问题属于“记忆缺失”“逻辑混乱”或“应用不足”中的哪一类，并在开头给出标签。
        2. 给出分层复习建议：先基础再进阶，可引用上面的资料片段。
        3. 拆解为不超过3个、每个约5至10分钟即可完成的具体复习小目标，按顺序给出。
        4. 结合学习行为和艾宾浩斯遗忘规律，为未来3天设计复习节奏，例如“今天完成首次复习，明日复盘，3天后抽检”。

        直接输出一段连贯文字，不要列表符号，不要出现英文括号。
        """)
        chain = prompt | agent.llm | StrOutputParser()
        
        try:
            return chain.invoke(weak_point_data).strip()
        except Exception as e:
            print(f"生成复习建议失败: {e}")
            return None
