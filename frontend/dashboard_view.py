import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
from backend.agents.base_agent import BaseAgent
from backend.dashboard_service import DashboardService


def render_consolidation_quiz(dashboard_service, user_id):
    topic = st.session_state.get('consolidation_topic', 'Unknown')
    st.markdown(f"## 🏋️‍♂️ 巩固练习：{topic}")
    st.info("请完成以下针对性练习题，以检验复习效果。")

    if 'consolidation_quiz' not in st.session_state:
        st.error("未找到练习题")
        if st.button("返回仪表盘"):
            st.session_state.consolidation_mode = False
            st.rerun()
        return

    quiz = st.session_state.consolidation_quiz
    
    with st.form("consolidation_form"):
        user_answers = {}
        for i, q in enumerate(quiz):
            st.markdown(f"**{i+1}. {q['question']}**")
            options = q.get('options', [])
            # 确保选项是列表
            if isinstance(options, str):
                options = [options]
            
            # 尝试找到之前选择的答案作为默认值
            default_idx = None
            
            user_answers[i] = st.radio(f"请选择答案 (第{i+1}题)", options, key=f"consolidation_q_{i}", index=None, label_visibility="collapsed")
            st.markdown("---")
        
        submitted = st.form_submit_button("提交答案")
    
    if submitted:
        # 判分
        grader = st.session_state.get('grader')
        if not grader:
            st.error("判分服务未初始化")
            return

        # 调用服务处理提交
        result = dashboard_service.process_consolidation_quiz_submission(quiz, user_answers, topic, user_id)
        
        # 保存结果到 Session 用于展示
        st.session_state.consolidation_result = result
        st.rerun()

    if 'consolidation_result' in st.session_state:
        res = st.session_state.consolidation_result
        st.success(f"练习完成！得分: {res['score']} / {res['total_score']}")
        
        # 展示提升图表
        col1, col2 = st.columns([1, 1])
        with col1:
            acc_before_pct = res['accuracy_before'] * 100
            acc_after_pct = res['accuracy_after'] * 100
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=['小灶前', '小灶后'],
                y=[acc_before_pct, acc_after_pct],
                text=[f"{acc_before_pct:.1f}%", f"{acc_after_pct:.1f}%"],
                textposition='auto',
                marker_color=['#9E9E9E', '#4CAF50']
            ))
            fig.update_layout(title=f"'{topic}' 掌握度提升对比", yaxis_range=[0, 100], yaxis_title="正确率 (%)")
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            improvement = acc_after_pct - acc_before_pct
            if improvement > 0:
                st.markdown(f"### 🎉 显著进步！")
                st.markdown(f"在接受针对性小灶后，你在**“{topic}”**考点上的正确率从 **{acc_before_pct:.1f}%** 提升到 **{acc_after_pct:.1f}%**。")
                st.markdown(f"提升了 **{improvement:.1f}%**！继续保持！")
            elif improvement == 0:
                st.markdown(f"### 😐 保持平稳")
                st.markdown(f"你的正确率保持在 **{acc_after_pct:.1f}%**。")
            else:
                st.markdown(f"### 📉 状态起伏")
                st.markdown(f"本次练习正确率为 **{acc_after_pct:.1f}%**，低于之前的平均水平。建议再回顾一下相关知识点。")

        # 展示题目解析
        with st.expander("查看详细解析", expanded=True):
            for i, (q, r) in enumerate(zip(quiz, res['grading_results'])):
                color = "green" if r['correct'] else "red"
                st.markdown(f"**题目 {i+1}:** {q['question']}")
                st.markdown(f"<span style='color:{color}'>{r['comment']}</span>", unsafe_allow_html=True)
                st.markdown("---")

        if st.button("返回错题本"):
            st.session_state.consolidation_mode = False
            del st.session_state.consolidation_quiz
            del st.session_state.consolidation_result
            del st.session_state.consolidation_topic
            st.rerun()

def render_review_checkin(dashboard_service, user_id, keyword, chapter, section, difficulty, idx):
    completed = dashboard_service.get_review_task_status(user_id, keyword, chapter, section, difficulty)
    
    if completed:
        st.success("今日复习任务已完成")
    else:
        if st.button("今日任务打卡", key=f"review_checkin_{idx}"):
            try:
                dashboard_service.mark_review_task_completed(user_id, keyword, chapter, section, difficulty)
            except Exception:
                st.error("打卡失败，请稍后重试")
                return
            st.success("今日任务已打卡")
            st.rerun()


def render_consolidation_history(dashboard_service, user_id, keyword):
    data = dashboard_service.get_consolidation_improvement_data(user_id, keyword)
    if not data:
        return

    acc_before = data['acc_before'] * 100
    acc_after = data['acc_after'] * 100
    improvement = data['improvement'] * 100
    
    st.markdown("#### 📊 巩固效果追踪")
    col1, col2 = st.columns([2, 3])
    with col1:
        st.metric("小灶前正确率", f"{acc_before:.1f}%")
        st.metric("小灶后正确率", f"{acc_after:.1f}%", delta=f"{improvement:.1f}%")
    
    with col2:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=['前', '后'],
            y=[acc_before, acc_after],
            text=[f"{acc_before:.1f}%", f"{acc_after:.1f}%"],
            textposition='auto',
            marker_color=['#9E9E9E', '#4CAF50']
        ))
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=150,
            yaxis_range=[0, 100]
        )
        st.plotly_chart(fig, use_container_width=True)
    
    if improvement > 30:
        st.success(f"太棒了！在接受针对性小灶后，你在“{keyword}”考点上的正确率从 {acc_before:.0f}% 提升到 {acc_after:.0f}%，掌握度显著提升。")
    elif improvement > 0:
        st.info(f"有进步！在接受针对性小灶后，你在“{keyword}”考点上的正确率从 {acc_before:.0f}% 提升到 {acc_after:.0f}%。")
    elif improvement == 0:
        st.warning(f"注意！你在“{keyword}”考点上的正确率保持在 {acc_before:.0f}%，未见明显提升，建议加强复习。")
    else:
        st.error(f"警惕！你在“{keyword}”考点上的正确率从 {acc_before:.0f}% 下降到 {acc_after:.0f}%，请务必重新学习相关知识点。")


def render_dashboard(db):
    # 初始化服务
    dashboard_service = DashboardService(db)

    # 处理巩固练习模式
    if st.session_state.get('consolidation_mode', False):
        if 'user_id' not in st.session_state:
            st.error("用户状态异常，请重新登录")
            return
        user_id = st.session_state.user_id
        render_consolidation_quiz(dashboard_service, user_id)
        return

    # ✅ 修复：强制从 Session 获取 user_id，不再随机生成
    if 'user_id' not in st.session_state:
        st.error("用户状态异常，请重新登录")
        return
    user_id = st.session_state.user_id

    st.header("3. 学习进度与错题本")
    
    # ✅ 修复：传入 user_id 获取特定用户的统计
    exam_stats = db.get_exam_stats(user_id)
    
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
            
    # --- 巩固练习效果追踪 ---
    consolidation_records = db.get_consolidation_records(user_id, limit=50)
    if consolidation_records:
        st.subheader("🏋️‍♂️ 重点突破追踪")
        # 获取唯一的知识点（保留最新记录）
        unique_points = []
        seen = set()
        for r in consolidation_records:
            kp = r.get('knowledge_point')
            if kp and kp not in seen:
                seen.add(kp)
                unique_points.append(kp)
        
        if unique_points:
             # 展示最近3个练习过的知识点
            for kp in unique_points[:3]:
                with st.container():
                    render_consolidation_history(dashboard_service, user_id, kp)
                    st.markdown("---")
    # -----------------------

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
        # ✅ 修复：清除缓存并重新获取数据
        db.invalidate_cache('mistakes', user_id)
        db.invalidate_cache('stats', user_id)
        st.session_state.mistakes = db.get_mistakes(user_id)
        st.rerun()
        
    if 'mistakes' not in st.session_state:
        # ✅ 修复：传入 user_id
        st.session_state.mistakes = db.get_mistakes(user_id)
        
    mistakes = st.session_state.mistakes

    # ✅ 新增：统计各难度数量，避免 difficulty_counts 未定义
    difficulty_counts = {}
    for m in mistakes:
        d = m.get("difficulty") or "Unknown"
        difficulty_counts[d] = difficulty_counts.get(d, 0) + 1
    
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
        
        col_chart1, col_chart2 = st.columns(2)
        
        df_difficulty, df_type = dashboard_service.get_mistake_analytics(mistakes)

        with col_chart1:
            st.markdown("### 📈 错题难度分布")
            if not df_difficulty.empty:
                difficulty_colors = {
                    '基础': '#4CAF50',
                    '进阶': '#FF9800',
                    '挑战': '#F44336',
                    'Unknown': '#9E9E9E'
                }
                
                fig_difficulty = px.bar(
                    df_difficulty,
                    x='难度',
                    y='数量',
                    color='难度',
                    color_discrete_map=difficulty_colors,
                    title='错题难度分布',
                    text='数量',
                    template='plotly_white'
                )
                fig_difficulty.update_traces(
                    textposition='outside',
                    texttemplate='%{y}',
                    marker_line_color='white',
                    marker_line_width=2
                )
                fig_difficulty.update_layout(
                    showlegend=False,
                    xaxis_title='难度级别',
                    yaxis_title='题目数量',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=14, color='#2c3e50'),
                    margin=dict(l=20, r=20, t=60, b=20),
                    height=400
                )
                fig_difficulty.update_xaxes(
                    tickfont=dict(size=12),
                    gridcolor='rgba(0,0,0,0.05)'
                )
                fig_difficulty.update_yaxes(
                    tickfont=dict(size=12),
                    gridcolor='rgba(0,0,0,0.05)'
                )
                st.plotly_chart(fig_difficulty, use_container_width=True)
            
        with col_chart2:
            st.markdown("### 🎯 错题类型分布")
            if not df_type.empty:
                type_colors = {
                    'choice': '#667eea',
                    'short_answer': '#764ba2',
                    'Unknown': '#9E9E9E'
                }
                
                fig_type = px.pie(
                    df_type,
                    values='数量',
                    names='类型',
                    title='错题类型分布',
                    color='类型',
                    color_discrete_map=type_colors,
                    hole=0.4,
                    template='plotly_white'
                )
                fig_type.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    textfont_size=14,
                    marker=dict(
                        line=dict(color='white', width=2)
                    ),
                    pull=[0.02] * len(df_type),
                    hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>'
                )
                fig_type.update_layout(
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.1,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=12)
                    ),
                    font=dict(size=14, color='#2c3e50'),
                    margin=dict(l=20, r=20, t=60, b=80),
                    height=400,
                    annotations=[dict(
                        text=f'{len(mistakes)}题',
                        x=0.5, y=0.5,
                        font_size=20,
                        showarrow=False,
                        font=dict(color='#2c3e50', family='Arial Black')
                    )]
                )
                st.plotly_chart(fig_type, use_container_width=True)
            
        st.markdown("---")
        
        st.subheader("🎯 学习效果评估")
        if exam_stats.get('total_exams', 0) > 0:
            accuracy_rate = 1 - (exam_stats.get('total_mistakes', 0) / (exam_stats.get('total_exams', 1) * 10))
            accuracy_percent = int(accuracy_rate * 100)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("整体正确率", f"{accuracy_percent}%")
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
            with col3:
                st.metric("考试次数", exam_stats.get('total_exams', 0))
            
            st.markdown("### 📊 正确率进度")
            progress_color = "#4CAF50" if accuracy_percent >= 80 else "#FF9800" if accuracy_percent >= 60 else "#F44336"
            st.markdown(
                f"""
                <div style="background: rgba(0,0,0,0.05); border-radius: 10px; padding: 20px; margin: 10px 0;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="font-weight: 600; color: #2c3e50;">当前正确率</span>
                        <span style="font-weight: bold; color: {progress_color}; font-size: 1.2em;">{accuracy_percent}%</span>
                    </div>
                    <div style="background: rgba(0,0,0,0.1); border-radius: 8px; height: 24px; overflow: hidden;">
                        <div style="background: {progress_color}; height: 100%; width: {accuracy_percent}%; transition: width 0.5s ease; border-radius: 8px;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.9em; color: #666;">
                        <span>0%</span>
                        <span>目标: 80%</span>
                        <span>100%</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info("还没有足够的数据来评估学习效果")
            
        st.markdown("---")
        
        st.subheader("📝 错题详情")
        
        col_filter, col_search = st.columns([2, 1])
        with col_filter:
            difficulty_options = ['全部'] + list(difficulty_counts.keys())
            selected_difficulty = st.selectbox(
                "按难度筛选",
                difficulty_options,
                index=0,
                label_visibility="collapsed"
            )
        with col_search:
            search_query = st.text_input("🔍 搜索题目", placeholder="输入关键词搜索...", label_visibility="collapsed")
        
        filtered_mistakes = mistakes
        if selected_difficulty != '全部':
            filtered_mistakes = [m for m in mistakes if m.get('difficulty') == selected_difficulty]
        if search_query:
            filtered_mistakes = [m for m in filtered_mistakes if search_query.lower() in str(m.get('question', '')).lower()]
        filtered_mistakes.sort(key=lambda x: x.get('error_times', 0), reverse=True)
        
        if not filtered_mistakes:
            st.info("没有找到符合条件的错题")
        else:
            for i, m in enumerate(filtered_mistakes, 1):
                difficulty = m.get('difficulty', 'Unknown')
                difficulty_color = {
                    '基础': '#4CAF50',
                    '进阶': '#FF9800',
                    '挑战': '#F44336',
                    'Unknown': '#9E9E9E'
                }.get(difficulty, '#9E9E9E')
                
                error_times = m.get('error_times', 0)
                error_level = '高' if error_times >= 3 else '中' if error_times == 2 else '低'
                error_color = '#F44336' if error_times >= 3 else '#FF9800' if error_times == 2 else '#4CAF50'
                
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); 
                                border-left: 4px solid {difficulty_color}; 
                                border-radius: 12px; 
                                padding: 20px; 
                                margin: 15px 0; 
                                box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <div>
                                <span style="background: {difficulty_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">
                                    {difficulty}
                                </span>
                                <span style="background: rgba(102, 126, 234, 0.1); color: #667eea; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600; margin-left: 8px;">
                                    {m.get('type', 'choice')}
                                </span>
                            </div>
                            <div style="text-align: right;">
                                <div style="color: {error_color}; font-weight: bold; font-size: 1.1em;">
                                    错误 {error_times} 次
                                </div>
                                <div style="color: #999; font-size: 0.85em;">
                                    {error_level}频错题
                                </div>
                            </div>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <div style="font-weight: 600; color: #2c3e50; margin-bottom: 8px; font-size: 1.05em;">
                                题目 {i}:
                            </div>
                            <div style="color: #555; line-height: 1.6;">
                                {m.get('question', '')}
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                            <div style="background: rgba(76, 175, 80, 0.1); padding: 12px; border-radius: 8px;">
                                <div style="color: #4CAF50; font-weight: 600; font-size: 0.9em; margin-bottom: 5px;">
                                    ✓ 正确答案
                                </div>
                                <div style="color: #2c3e50;">
                                    {m.get('standard_answer', '')}
                                </div>
                            </div>
                            <div style="background: rgba(244, 67, 54, 0.1); padding: 12px; border-radius: 8px;">
                                <div style="color: #F44336; font-weight: 600; font-size: 0.9em; margin-bottom: 5px;">
                                    ✗ 你的答案
                                </div>
                                <div style="color: #2c3e50;">
                                    {m.get('user_answer', '')}
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                with st.expander("📖 查看详细解析", expanded=False):
                    analysis_text = dashboard_service.format_analysis(m)
                    st.markdown(
                        f"""
                        <div style="background: rgba(102, 126, 234, 0.05); 
                                    padding: 15px; 
                                    border-radius: 8px; 
                                    border-left: 3px solid #667eea;
                                    line-height: 1.8;">
                            {analysis_text}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                if m.get('latest_feedback'):
                    st.info(f"💡 最新反馈: {m['latest_feedback']}")
                
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button(f"✅ 标记为已掌握", key=f"mastered_{i}"):
                        # 调用数据库删除错题
                        if db.remove_mistake(user_id, m['question']):
                            st.success(f"已将第 {i} 题标记为已掌握，从错题本中移除！")
                            # 重新加载页面以刷新数据
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("操作失败，请重试")
                with col_btn2:
                    last_error_time = m.get('last_error_time', '')
                    if last_error_time:
                        try:
                            if hasattr(last_error_time, 'strftime'):
                                formatted_time = last_error_time.strftime('%Y-%m-%d %H:%M')
                            else:
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
                            st.caption(f"🕐 最后错误: {formatted_time}")
                        except Exception as e:
                            st.caption(f"🕐 最后错误: {last_error_time}")
                
                st.markdown("---")
            
        if filtered_mistakes:
            col_export, col_count = st.columns([3, 1])
            with col_export:
                df = pd.DataFrame(filtered_mistakes)
                export_cols = ['question', 'type', 'difficulty', 'standard_answer', 'user_answer', 'error_times', 'analysis']
                df_export = df[export_cols]
                csv = df_export.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 导出错题本 (CSV)",
                    data=csv,
                    file_name=f"错题本_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv; charset=utf-8-sig",
                    use_container_width=True,
                    help="下载后请使用Excel打开，选择UTF-8编码"
                )
            with col_count:
                st.metric("可导出题目", len(filtered_mistakes))
                
        st.subheader("📚 个性化复习建议")
        kb = st.session_state.get('kb')
        if not kb:
            st.info("知识库未初始化，暂无法生成复习建议")
        else:
            # ✅ 修复：传入 user_id 获取特定用户的薄弱点
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
                
                # 统一处理逻辑，移除大量重复代码，调用 DashboardService 生成复习建议
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
                    sample_analysis = dashboard_service.format_analysis(sample) if sample else ""
                    
                    relevant_content = kb.retrieve_relevant_content(keyword, k=3)
                    snippet = ""
                    if isinstance(relevant_content, str):
                        snippet = dashboard_service.clean_text_snippet(relevant_content)
                        
                    suggestion_text = ""
                    if agent.llm is None:
                        suggestion_text = f"[开发模式] 建议围绕“{keyword}”整理一套短时复习计划，先重看资料中的关键段落，再完成两三道同类题，最后总结自己的易错点。"
                    else:
                        data = {
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
                        }
                        suggestion_text = dashboard_service.generate_review_plan(data, agent)
                        
                        if not suggestion_text:
                            suggestion_text = f"建议重温与“{keyword}”相关的课程内容，先回顾教材中的关键段落，再完成2至3道同类题，并在24小时内进行一次复盘。"

                    with st.expander(f"{idx}. {keyword} ({difficulty})", expanded=True):
                        st.markdown(f"错题聚合：该考点下累计错误次数约为 {error_times}，重要性权重 {importance:.2f}。")
                        if sample_question:
                            st.markdown(f"**代表错题**：{sample_question}")
                            st.markdown(f"**参考答案**：{sample_standard_answer}")
                            st.markdown(f"**相关知识点**：{keyword}")
                        if snippet:
                            st.caption(f"原资料片段预览：{snippet}")
                        
                        st.markdown("个性化复习方案：")
                        st.write(suggestion_text)
                        
                        render_consolidation_history(dashboard_service, user_id, keyword)
                        
                        # 按钮Key需要唯一，结合idx
                        if st.button(f"🏋️‍♂️ 开始巩固练习 ({keyword})", key=f"start_consolidation_{idx}"):
                            st.session_state.consolidation_topic = keyword
                            generator = st.session_state.get('generator')
                            if generator:
                                with st.spinner(f"正在为考点“{keyword}”生成练习题..."):
                                    quiz = generator.generate_practice_quiz(keyword, count=3)
                                    st.session_state.consolidation_quiz = quiz
                                    st.session_state.consolidation_mode = True
                                    st.rerun()
                            else:
                                st.error("题目生成器未初始化")
                        
                        render_review_checkin(dashboard_service, user_id, keyword, chapter, section, difficulty, idx)