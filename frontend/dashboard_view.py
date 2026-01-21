import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render_dashboard(db):
    st.header("3. 学习进度与错题本")
    
    # 获取考试统计数据
    exam_stats = db.get_exam_stats()
    
    # 学习进度可视化
    st.subheader("📈 学习进度概览")
    
    # 显示学习统计信息
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
    
    # 考试历史趋势
    st.subheader("📊 考试历史趋势")
    
    if exam_stats.get("recent_exams") and len(exam_stats["recent_exams"]) > 1:
        # 准备数据
        df_exams = pd.DataFrame(exam_stats["recent_exams"])
        
        # 转换时间戳
        df_exams['date'] = df_exams['timestamp'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M") if hasattr(x, 'strftime') else x)
        df_exams['timestamp'] = df_exams['timestamp'].apply(lambda x: x.timestamp() if hasattr(x, 'timestamp') else x)
        
        # 绘制分数趋势图
        fig = px.line(df_exams, x='date', y='total_score', 
                     title='考试分数趋势',
                     markers=True,
                     labels={'date': '时间', 'total_score': '分数'})
        
        # 自定义图表样式
        fig.update_layout(
            xaxis_tickangle=-45,
            yaxis_title='分数',
            xaxis_title='考试时间',
            template='plotly_white',
            showlegend=False
        )
        
        # 显示图表
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("还没有足够的考试数据来显示趋势")
    
    # 分割线
    st.markdown("---")
    
    # 刷新错题数据
    if st.button("刷新数据"):
        st.session_state.mistakes = db.get_mistakes()
        st.experimental_rerun()
    
    # 初始化错题数据
    if 'mistakes' not in st.session_state:
        st.session_state.mistakes = db.get_mistakes()
    
    mistakes = st.session_state.mistakes
    
    if not mistakes:
        st.info("暂无错题记录")
    else:
        # 显示错题统计信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("错题总数", len(mistakes))
        with col2:
            total_errors = sum(m['error_times'] for m in mistakes)
            st.metric("累计错误次数", total_errors)
        with col3:
            avg_errors = total_errors / len(mistakes) if mistakes else 0
            st.metric("平均错误次数", round(avg_errors, 1))
        
        # 错题类型分析
        st.subheader("📊 错题分析")
        
        # 1. 错题难度分布
        difficulty_counts = {}
        for m in mistakes:
            diff = m.get('difficulty', 'Unknown')
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
        
        if difficulty_counts:
            st.markdown("### 1. 错题难度分布")
            # 将字典转换为DataFrame以兼容旧版本Streamlit
            df_difficulty = pd.DataFrame.from_dict(difficulty_counts, orient='index', columns=['数量'])
            st.bar_chart(df_difficulty)
        
        # 2. 错题类型分布
        type_counts = {}
        for m in mistakes:
            q_type = m.get('type', 'Unknown')
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
        
        if type_counts:
            st.markdown("### 2. 错题类型分布")
            # 将字典转换为DataFrame以兼容旧版本Streamlit
            df_type = pd.DataFrame.from_dict(type_counts, orient='index', columns=['数量'])
            
            # 使用饼图显示
            fig = px.pie(df_type, values='数量', names=df_type.index, 
                       title='错题类型分布',
                       template='plotly_white')
            
            st.plotly_chart(fig, use_container_width=True)
        
        # 3. 学习效果评估
        st.subheader("🎯 学习效果评估")
        
        if exam_stats.get('total_exams', 0) > 0:
            # 计算学习效率指标
            accuracy_rate = 1 - (exam_stats.get('total_mistakes', 0) / (exam_stats.get('total_exams', 1) * 10))
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("整体正确率", f"{int(accuracy_rate * 100)}%")
            
            with col2:
                # 学习进步情况
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
        
        # 错题列表
        st.subheader("错题详情")
        
        # 难度筛选
        difficulty_options = list(difficulty_counts.keys()) + ['全部']
        selected_difficulty = st.selectbox("按难度筛选", difficulty_options, index=len(difficulty_options)-1)
        
        # 过滤错题
        filtered_mistakes = mistakes
        if selected_difficulty != '全部':
            filtered_mistakes = [m for m in mistakes if m.get('difficulty') == selected_difficulty]
        
        # 按错误次数排序
        filtered_mistakes.sort(key=lambda x: x.get('error_times', 0), reverse=True)
        
        # 渲染错题卡片
        for i, m in enumerate(filtered_mistakes, 1):
            # 使用markdown分割线替代border参数
            st.markdown(f"### 第 {i} 题 ({m.get('type', 'choice')})")
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(m['question'])
                st.markdown(f"**正确答案**: {m['standard_answer']}")
                st.markdown(f"**你的答案**: {m['user_answer']}")
                with st.expander("查看详细解析"):
                    st.write(m['analysis'])
                if m.get('latest_feedback'):
                    st.info(f"最新反馈: {m['latest_feedback']}")
            with col_b:
                st.metric("错误次数", m['error_times'])
                st.caption(f"难度: {m.get('difficulty', 'Unknown')}")
                last_error_time = m.get('last_error_time', '')
                if last_error_time:
                    try:
                        # 检查是否已经是datetime对象
                        if hasattr(last_error_time, 'strftime'):
                            formatted_time = last_error_time.strftime('%Y-%m-%d %H:%M')
                        else:
                            # 如果是字符串，尝试转换为datetime对象
                            from datetime import datetime
                            if isinstance(last_error_time, str):
                                # 尝试解析常见的datetime字符串格式
                                if 'T' in last_error_time:  # ISO格式: 2023-01-01T12:00:00
                                    formatted_time = datetime.fromisoformat(last_error_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                                else:  # 其他格式
                                    try:
                                        formatted_time = datetime.strptime(last_error_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
                                    except:
                                        formatted_time = last_error_time  # 如果解析失败，直接使用原始字符串
                            else:
                                formatted_time = str(last_error_time)  # 其他类型转换为字符串
                        
                        st.caption(f"最后错误时间: {formatted_time}")
                    except Exception as e:
                        # 任何错误都直接显示原始值
                        st.caption(f"最后错误时间: {last_error_time}")
                # 标记为已掌握按钮
                if st.button(f"标记为已掌握", key=f"mastered_{i}"):
                    st.success(f"已将第 {i} 题标记为已掌握")
            st.markdown("---")
        
        # 导出功能
        if filtered_mistakes:
            if st.button("导出错题本"):
                # 转换为DataFrame
                df = pd.DataFrame(filtered_mistakes)
                # 选择需要导出的列
                export_cols = ['question', 'type', 'difficulty', 'standard_answer', 'user_answer', 'error_times', 'analysis']
                df_export = df[export_cols]
                # 转换为CSV
                csv = df_export.to_csv(index=False, encoding='utf-8-sig')
                # 提供下载
                st.download_button(
                    label="下载错题本 (CSV)",
                    data=csv,
                    file_name="错题本.csv",
                    mime="text/csv"
                )