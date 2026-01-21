import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import uuid
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent


def format_dev_mode_analysis(mistake):
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


def render_review_checkin(db, user_id, keyword, chapter, section, difficulty, idx):
    today = datetime.now().date()
    try:
        completed = db.get_review_task_status(user_id, keyword, chapter, section, difficulty, date=today)
    except Exception:
        completed = False
    if completed:
        st.success("今日复习任务已完成")
    else:
        if st.button("今日任务打卡", key=f"review_checkin_{idx}"):
            try:
                db.mark_review_task_completed(user_id, keyword, chapter, section, difficulty, date=today)
            except Exception:
                st.error("打卡失败，请稍后重试")
                return
            st.success("今日任务已打卡")
            st.rerun()


def render_dashboard(db):
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    user_id = st.session_state.user_id
    st.header("3. 学习进度与错题本")
    exam_stats = db.get_exam_stats()
    st.subheader("📈 学习进度概览")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总考试次数", exam_stats.get("total_exams", 0))
    with col2:
        st.metric("错题总数", exam_stats.get("total_mistakes", 0))
    with col3:
        st.metric("平均分数", exam_stats.get("avg_score", 0))
    with col4:
        if exam_stats.get("recent_exams"):
            latest_score = exam_stats["recent_exams"][0].get("total_score", 0)
            st.metric("最近一次得分", latest_score)
    st.subheader("📊 考试历史趋势")
    if exam_stats.get("recent_exams") and len(exam_stats["recent_exams"]) > 1:
        df_exams = pd.DataFrame(exam_stats["recent_exams"])
        df_exams['date'] = df_exams['timestamp'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M") if hasattr(x, 'strftime') else x)
        df_exams['timestamp'] = df_exams['timestamp'].apply(lambda x: x.timestamp() if hasattr(x, 'timestamp') else x)
        fig = px.line(df_exams, x='date', y='total_score', 
                     title='考试分数趋势',
                     markers=True,
                     labels={'date': '时间', 'total_score': '分数'})
        fig.update_layout(
            xaxis_tickangle=-45,
            yaxis_title='分数',
            xaxis_title='考试时间',
            template='plotly_white',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("还没有足够的考试数据来显示趋势")
    st.markdown("---")
    if st.button("刷新数据"):
        st.session_state.mistakes = db.get_mistakes(user_id)
        st.rerun()
    if 'mistakes' not in st.session_state:
        st.session_state.mistakes = db.get_mistakes(user_id)
    mistakes = st.session_state.mistakes
    if not mistakes:
        st.info("暂无错题记录")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("错题总数", len(mistakes))
        with col2:
            total_errors = sum(m['error_times'] for m in mistakes)
            st.metric("累计错误次数", total_errors)
        with col3:
            avg_errors = total_errors / len(mistakes) if mistakes else 0
            st.metric("平均错误次数", round(avg_errors, 1))
        st.subheader("📊 错题分析")
        difficulty_counts = {}
        for m in mistakes:
            diff = m.get('difficulty', 'Unknown')
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
        if difficulty_counts:
            st.markdown("### 1. 错题难度分布")
            df_difficulty = pd.DataFrame.from_dict(difficulty_counts, orient='index', columns=['数量'])
            st.bar_chart(df_difficulty)
        type_counts = {}
        for m in mistakes:
            q_type = m.get('type', 'Unknown')
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
        if type_counts:
            st.markdown("### 2. 错题类型分布")
            df_type = pd.DataFrame.from_dict(type_counts, orient='index', columns=['数量'])
            fig = px.pie(df_type, values='数量', names=df_type.index, 
                       title='错题类型分布',
                       template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("🎯 学习效果评估")
        if exam_stats.get('total_exams', 0) > 0:
            accuracy_rate = 1 - (exam_stats.get('total_mistakes', 0) / (exam_stats.get('total_exams', 1) * 10))
            col1, col2 = st.columns(2)
            with col1:
                st.metric("整体正确率", f"{int(accuracy_rate * 100)}%")
            with col2:
                if exam_stats.get('recent_exams') and len(exam_stats['recent_exams']) > 1:
                    first_score = exam_stats['recent_exams'][-1].get('total_score', 0)
                    latest_score = exam_stats['recent_exams'][0].get('total_score', 0)
                    progress = latest_score - first_score
                    if progress > 0:
                        st.metric("学习进步", f"+{progress}分", "✓ 进步明显")
                    elif progress < 0:
                        st.metric("学习进步", f"{progress}分", "⚠️ 需要加强")
                    else:
                        st.metric("学习进步", "0分", "→ 保持稳定")
        else:
            st.info("还没有足够的数据来评估学习效果")
        st.subheader("错题详情")
        difficulty_options = list(difficulty_counts.keys()) + ['全部']
        selected_difficulty = st.selectbox("按难度筛选", difficulty_options, index=len(difficulty_options)-1)
        filtered_mistakes = mistakes
        if selected_difficulty != '全部':
            filtered_mistakes = [m for m in mistakes if m.get('difficulty') == selected_difficulty]
        filtered_mistakes.sort(key=lambda x: x.get('error_times', 0), reverse=True)
        for i, m in enumerate(filtered_mistakes, 1):
            st.markdown(f"### 第 {i} 题 ({m.get('type', 'choice')})")
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(m['question'])
                st.markdown(f"**正确答案**: {m['standard_answer']}")
                st.markdown(f"**你的答案**: {m['user_answer']}")
                with st.expander("查看详细解析"):
                    analysis_text = format_dev_mode_analysis(m)
                    st.write(analysis_text)
                if m.get('latest_feedback'):
                    st.info(f"最新反馈: {m['latest_feedback']}")
            with col_b:
                st.metric("错误次数", m['error_times'])
                st.caption(f"难度: {m.get('difficulty', 'Unknown')}")
                last_error_time = m.get('last_error_time', '')
                if last_error_time:
                    try:
                        if hasattr(last_error_time, 'strftime'):
                            formatted_time = last_error_time.strftime('%Y-%m-%d %H:%M')
                        else:
                            from datetime import datetime
                            if isinstance(last_error_time, str):
                                if 'T' in last_error_time:
                                    formatted_time = datetime.fromisoformat(last_error_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                                else:
                                    try:
                                        formatted_time = datetime.strptime(last_error_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
                                    except:
                                        formatted_time = last_error_time
                            else:
                                formatted_time = str(last_error_time)
                        st.caption(f"最后错误时间: {formatted_time}")
                    except Exception as e:
                        st.caption(f"最后错误时间: {last_error_time}")
                if st.button(f"标记为已掌握", key=f"mastered_{i}"):
                    st.success(f"已将第 {i} 题标记为已掌握")
            st.markdown("---")
        if filtered_mistakes:
            if st.button("导出错题本"):
                df = pd.DataFrame(filtered_mistakes)
                export_cols = ['question', 'type', 'difficulty', 'standard_answer', 'user_answer', 'error_times', 'analysis']
                df_export = df[export_cols]
                csv = df_export.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载错题本 (CSV)",
                    data=csv,
                    file_name="错题本.csv",
                    mime="text/csv"
                )
        st.subheader("📚 个性化复习建议")
        kb = st.session_state.get('kb')
        if not kb:
            st.info("知识库未初始化，暂无法生成复习建议")
        else:
            weak_points = db.get_weak_points(user_id, limit=5)
            if not weak_points:
                st.info("暂无可生成的复习建议")
            else:
                agent = BaseAgent(temperature=0.3)
                recent_exams = exam_stats.get("recent_exams") or []
                behavior_summary = ""
                if exam_stats:
                    total_exams = exam_stats.get("total_exams", 0)
                    avg_score = exam_stats.get("avg_score", 0)
                    latest_score = 0
                    last_time_str = ""
                    if recent_exams:
                        latest_score = recent_exams[0].get("total_score", 0)
                        latest_time = recent_exams[0].get("timestamp")
                        if hasattr(latest_time, "strftime"):
                            last_time_str = latest_time.strftime("%Y-%m-%d %H:%M")
                        else:
                            last_time_str = str(latest_time)
                    volatility_desc = ""
                    if len(recent_exams) >= 3:
                        scores = [x.get("total_score", 0) for x in recent_exams[:5]]
                        diff_score = max(scores) - min(scores)
                        if diff_score >= 20:
                            volatility_desc = "最近得分波动较大，状态不够稳定。"
                        elif diff_score <= 5:
                            volatility_desc = "最近得分较为稳定。"
                    behavior_summary = f"共完成{total_exams}次考试，平均分约为{avg_score}分。最近一次得分为{latest_score}分，时间为{last_time_str}。{volatility_desc}"
                if agent.llm is None:
                    for idx, point in enumerate(weak_points, 1):
                        keyword = point.get('keyword', '')
                        difficulty = point.get('difficulty', '')
                        error_times = point.get('error_times', 0)
                        importance = point.get('importance', 1.0)
                        chapter = point.get('chapter')
                        section = point.get('section')
                        point_mistakes = []
                        for m in mistakes:
                            mk = m.get("keyword") or m.get("knowledge_point") or "未知考点"
                            if mk != keyword:
                                continue
                            if chapter and m.get("chapter") != chapter:
                                continue
                            if section and m.get("section") != section:
                                continue
                            if m.get("difficulty", "Unknown") != difficulty:
                                continue
                            point_mistakes.append(m)
                        sample = point_mistakes[0] if point_mistakes else None
                        sample_question = sample.get("question", "") if sample else ""
                        relevant_content = kb.retrieve_relevant_content(keyword, k=3)
                        snippet = ""
                        if isinstance(relevant_content, str):
                            snippet = relevant_content[:200]
                        suggestion_text = f"[开发模式] 建议围绕“{keyword}”整理一套短时复习计划，先重看资料中的关键段落，再完成两三道同类题，最后总结自己的易错点。"
                        with st.expander(f"{idx}. {keyword} ({difficulty})"):
                            st.markdown(f"错题聚合：该考点下累计错误次数约为 {error_times}，重要性权重 {importance:.2f}。")
                            if sample_question:
                                st.markdown(f"代表错题：{sample_question}")
                            if snippet:
                                st.markdown(f"原资料片段预览：{snippet}")
                            st.markdown("个性化复习方案（开发模式示例）：")
                            st.write(suggestion_text)
                            render_review_checkin(db, user_id, keyword, chapter, section, difficulty, idx)
                else:
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
                    for idx, point in enumerate(weak_points, 1):
                        keyword = point.get('keyword', '')
                        difficulty = point.get('difficulty', '')
                        error_times = point.get('error_times', 0)
                        importance = point.get('importance', 1.0)
                        last_error_time = point.get('last_error_time', '')
                        chapter = point.get('chapter')
                        section = point.get('section')
                        point_mistakes = []
                        for m in mistakes:
                            mk = m.get("keyword") or m.get("knowledge_point") or "未知考点"
                            if mk != keyword:
                                continue
                            if chapter and m.get("chapter") != chapter:
                                continue
                            if section and m.get("section") != section:
                                continue
                            if m.get("difficulty", "Unknown") != difficulty:
                                continue
                            point_mistakes.append(m)
                        sample = point_mistakes[0] if point_mistakes else None
                        sample_question = sample.get("question", "") if sample else ""
                        sample_standard_answer = sample.get("standard_answer", "") if sample else ""
                        sample_user_answer = sample.get("user_answer", "") if sample else ""
                        sample_analysis = format_dev_mode_analysis(sample) if sample else ""
                        relevant_content = kb.retrieve_relevant_content(keyword, k=3)
                        snippet = ""
                        if isinstance(relevant_content, str):
                            snippet = relevant_content[:400]
                        try:
                            suggestion_text = chain.invoke({
                                "keyword": keyword,
                                "difficulty": difficulty,
                                "error_times": error_times,
                                "importance": importance,
                                "last_error_time": str(last_error_time),
                                "sample_question": sample_question,
                                "sample_standard_answer": sample_standard_answer,
                                "sample_user_answer": sample_user_answer,
                                "sample_analysis": sample_analysis,
                                "relevant_content": snippet,
                                "behavior_summary": behavior_summary,
                            }).strip()
                        except Exception as e:
                            print(f"生成复习建议失败: {e}")
                            suggestion_text = f"建议重温与“{keyword}”相关的课程内容，先回顾教材中的关键段落，再完成2至3道同类题，并在24小时内进行一次复盘。"
                        with st.expander(f"{idx}. {keyword} ({difficulty})"):
                            st.markdown(f"错题聚合：该考点下累计错误次数约为 {error_times}，重要性权重 {importance:.2f}。")
                            if sample_question:
                                st.markdown(f"代表错题：{sample_question}")
                            if snippet:
                                st.markdown(f"原资料片段预览：{snippet}")
                            st.markdown("个性化复习方案：")
                            st.write(suggestion_text)
                            render_review_checkin(db, user_id, keyword, chapter, section, difficulty, idx)
