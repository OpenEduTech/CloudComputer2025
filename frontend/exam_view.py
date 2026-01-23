import streamlit as st
import time
import pandas as pd

def render_exam_page(agent_generator, agent_grader, knowledge_base, db):
    st.header("2. 智能考核 (梯度试卷)")
    
    # ✅ 修复：直接使用 app.py 中统一设置的 user_id
    # 如果未登录，app.py 会拦截，所以这里理论上 user_id 一定存在
    if 'user_id' not in st.session_state:
        st.error("用户状态异常，请重新登录")
        return
    user_id = st.session_state.user_id
    
    # 自动保存到Redis的函数
    def auto_save_to_redis():
        if 'current_exam' in st.session_state and 'user_answers' in st.session_state:
            exam_data = {
                'user_id': user_id,
                'exam': st.session_state.current_exam,
                'user_answers': st.session_state.user_answers,
                'last_saved': time.time()
            }
            
            # 包含考试开始时间以便恢复计时器
            if 'exam_start_time' in st.session_state:
                exam_data['exam_start_time'] = st.session_state.exam_start_time
            
            # ✅ 这里的缓存已经是隔离的（user_id作为key的一部分）
            db.cache_user_exam(user_id, exam_data)
            st.session_state.last_saved = time.time()
    
    # 尝试从Redis加载之前的答题状态
    if 'current_exam' not in st.session_state:
        cached_exam = db.get_cached_user_exam(user_id)
        if cached_exam:
            st.session_state.current_exam = cached_exam['exam']
            st.session_state.user_answers = cached_exam['user_answers']
            st.session_state.last_saved = cached_exam['last_saved']
            st.session_state.exam_submitted = False
            # 恢复考试计时
            if 'exam_start_time' in cached_exam:
                st.session_state.exam_start_time = cached_exam['exam_start_time']
            else:
                # 如果没有考试开始时间，使用当前时间
                st.session_state.exam_start_time = time.time()
            st.info("已从上次答题状态恢复")
    
    # 生成试卷按钮
    col_preview, col_generate = st.columns(2)
    with col_preview:
        if st.button("预览本次考点清单"):
            with st.spinner("正在分析考点..."):
                context = knowledge_base.retrieve_relevant_content("核心考点 summarize")
                keypoints = agent_generator.extract_keypoints(context, max_points=20)
                st.session_state.exam_keypoints = keypoints
                st.session_state.exam_context = context
                st.success("考点清单生成完成")
    with col_generate:
        if st.button("基于考点生成梯度试卷"):
            with st.spinner("正在生成试卷..."):
                context = st.session_state.get("exam_context")
                if not context:
                    context = knowledge_base.retrieve_relevant_content("核心考点 summarize")
                    st.session_state.exam_context = context
                keypoints = st.session_state.get("exam_keypoints")
                if not keypoints:
                    keypoints = agent_generator.extract_keypoints(context, max_points=20)
                    st.session_state.exam_keypoints = keypoints
                quiz_list = agent_generator.generate_comprehensive_exam(context)
                if quiz_list:
                    st.session_state.current_exam = quiz_list
                    st.session_state.user_answers = {}
                    st.session_state.exam_submitted = False
                    st.session_state.last_saved = time.time()
                    st.session_state.exam_start_time = time.time()
                    auto_save_to_redis()
                    st.success("试卷生成成功！")
                else:
                    st.error("出题失败")

    keypoints = st.session_state.get("exam_keypoints")
    if keypoints:
        st.subheader("本次出题覆盖的关键考点清单")
        for idx, kp in enumerate(keypoints, 1):
            keyword = kp.get("keyword", "")
            importance = kp.get("importance", 0)
            ktype = kp.get("type", "concept")
            st.markdown(f"{idx}. {keyword} （类型: {ktype}，重要性: {importance:.2f}）")

    # 渲染试卷表单
    if 'current_exam' in st.session_state:
        exam = st.session_state.current_exam

        if 'user_answers' not in st.session_state or not isinstance(st.session_state.user_answers, dict):
            st.session_state.user_answers = {}

        # 显示考试信息
        col1, col2, col3 = st.columns(3)
        with col1:
            total_questions = len(exam)
            st.metric("题目总数", total_questions)
        with col2:
            answered_count = sum(1 for ans in st.session_state.user_answers.values() if ans)
            st.metric("已答题数", answered_count)
        with col3:
            progress = answered_count / total_questions if total_questions > 0 else 0
            st.metric("答题进度", f"{int(progress * 100)}%")
        
        # 显示答题进度条
        progress_container = st.container()
        with progress_container:
            st.progress(progress)
            st.caption(f"已答 {answered_count}/{total_questions} 题")
        
        # 初始化考试开始时间 (仅作记录)
        if 'exam_start_time' not in st.session_state:
            st.session_state.exam_start_time = time.time()
        
        # 渲染试卷表单
        with st.form("exam_form", clear_on_submit=False):
            # 题目导航
            nav_col1, nav_col2, nav_col3 = st.columns(3)
            with nav_col1:
                page_size = st.selectbox("每页显示题目数", [5, 10, 20], index=0)
            
            # 分页处理
            if 'current_page' not in st.session_state:
                st.session_state.current_page = 0
            
            total_pages = (total_questions + page_size - 1) // page_size
            
            with nav_col2:
                page = st.number_input("当前页码", min_value=1, max_value=total_pages, value=st.session_state.current_page + 1)
                st.session_state.current_page = page - 1
            
            start_idx = st.session_state.current_page * page_size
            end_idx = min(start_idx + page_size, total_questions)
            
            # 渲染当前页的题目
            for q in exam[start_idx:end_idx]:
                st.markdown(f"**[{q['difficulty']}] 第 {q['id']} 题 ({q['type']})**")
                st.write(q['question'])
                
                # 保存用户答案到session
                if q['type'] == 'choice':
                    answer = st.radio(
                        f"请选择 (Q{q['id']}):", q['options'], 
                        key=f"exam_q_{q['id']}",
                        index=q['options'].index(st.session_state.user_answers.get(q['id'], q['options'][0])) \
                            if q['id'] in st.session_state.user_answers and st.session_state.user_answers[q['id']] in q['options'] \
                            else 0
                    )
                else:
                    answer = st.text_area(
                        f"请输入答案 (Q{q['id']}):", 
                        value=st.session_state.user_answers.get(q['id'], ""),
                        key=f"exam_q_{q['id']}",
                        height=150
                    )
                
                # 比较答案是否变化，如果变化则自动保存
                if st.session_state.user_answers.get(q['id']) != answer:
                    st.session_state.user_answers[q['id']] = answer
                    auto_save_to_redis()
                    # 显示保存成功的临时提示
                    with st.empty():
                        st.success(f"第 {q['id']} 题答案已自动保存")
                        time.sleep(0.5)
                        st.empty()
                
                st.markdown("---")
            
            # End of question loop
            
            st.markdown("---")
            st.write("") # Spacer
            
            # 表单按钮区域 (Ensure this is OUTSIDE the for loop)
            # 使用 container 隔离
            button_container = st.container()
            with button_container:
                b_col1, b_col2, b_col3 = st.columns([1, 1, 1])
                
                with b_col1:
                    # 添加唯一 key 防止组件冲突
                    if st.form_submit_button("保存答案草稿", key="btn_save_draft_unique_v2"):
                        auto_save_to_redis()
                        st.success("答案已保存到Redis！")
                
                with b_col3:
                    # 添加唯一 key 防止组件冲突
                    if st.form_submit_button("提交试卷", key="btn_submit_exam_unique_v2", type="primary"):
                        # 检查是否所有题目都已答
                        if answered_count < total_questions:
                            st.warning("还有题目未答，确定要提交吗？")
                            st.stop()
                        # 最后保存一次到Redis
                        auto_save_to_redis()
                        _handle_submission(exam, agent_grader, knowledge_base, db)
                        # 提交后清除缓存
                        db.invalidate_cache('exam', user_id)

    # 结果展示
    if st.session_state.get('exam_submitted'):
        _render_results(agent_grader)

def _handle_submission(exam, grader, kb, db):
    # ✅ 获取 user_id
    if 'user_id' not in st.session_state:
        st.error("用户ID丢失，无法提交")
        return
    user_id = st.session_state.user_id

    st.session_state.exam_submitted = True
    # 记录考试结束时间，用于定格倒计时
    if 'exam_end_time' not in st.session_state:
        st.session_state.exam_end_time = time.time()
        
    st.session_state.grading_results = []
    total_score = 0
    
    with st.spinner("正在判卷中..."):
        for q in exam:
            u_ans = st.session_state.user_answers.get(q['id'], "")
            res = grader.grade_submission(
                q['type'], q['question'], q['answer'], u_ans, 
                kb.retrieve_relevant_content(q['question'])
            )
            res['id'] = q['id']
            res['user_ans'] = u_ans
            res['difficulty'] = q['difficulty']
            st.session_state.grading_results.append(res)
            total_score += res['score']
            
            if res['score'] < 6:
                # ✅ 关键：传入 user_id，确保错题归属正确
                db.add_mistake(q, u_ans, res, user_id=user_id)
                
    st.session_state.total_score = total_score
    # ✅ 关键：传入 user_id，确保试卷记录归属正确
    db.save_exam_record(
        exam, 
        st.session_state.user_answers, 
        total_score, 
        st.session_state.grading_results,
        user_id=user_id
    )

def _render_results(grader=None):
    st.markdown("---")
    
    # 显示总分
    total_score = st.session_state.total_score
    max_score = len(st.session_state.grading_results) * 10  # 每题10分
    percentage = (total_score / max_score) * 100 if max_score > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总分", f"{total_score}/{max_score}")
    with col2:
        st.metric("正确率", f"{int(percentage)}%")
    with col3:
        passed = percentage >= 60
        st.metric("考试结果", "通过" if passed else "未通过", 
                  "🎉 恭喜！" if passed else "继续加油！")
    
    # 新增：难度-正确率分析模块
    if grader and hasattr(grader, 'analyze_difficulty_gradient'):
        st.subheader("📊 难度-正确率分析")
        analysis = grader.analyze_difficulty_gradient(st.session_state.grading_results)
        
        col_chart, col_summary = st.columns([2, 1])
        with col_chart:
            # 使用 pandas 渲染折线图 (或条形图)
            df = pd.DataFrame(analysis['chart_data'])
            # 设置 '难度' 为索引，以便 x 轴正确显示
            df = df.set_index('难度')
            # 也可以用 st.line_chart，但只有三个点，bar_chart可能更直观
            st.bar_chart(df)
            
        with col_summary:
            st.info(analysis['summary'])
            if analysis['is_reasonable']:
                st.caption("✅ 难度梯度合理")
            else:
                st.caption("⚠️ 难度梯度需关注")
    
    # 按难度统计得分
    st.subheader("按难度得分统计")
    difficulty_scores = {}
    difficulty_counts = {}
    
    for res in st.session_state.grading_results:
        diff = res.get('difficulty', 'Unknown')
        difficulty_scores[diff] = difficulty_scores.get(diff, 0) + res['score']
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 10  # 每题10分
    
    if difficulty_scores:
        for diff, score in difficulty_scores.items():
            max_diff_score = difficulty_counts[diff]
            # st.progress()需要的值范围是[0.0, 1.0]，所以不乘以100
            diff_percentage = (score / max_diff_score) if max_diff_score > 0 else 0
            progress_container = st.container()
            with progress_container:
                st.progress(diff_percentage)
                # 显示的时候再转换为百分比
                percentage_display = int(diff_percentage * 100)
                st.caption(f"{diff}: {score}/{max_diff_score} ({percentage_display}%)")
    
    # 题目详细结果
    st.subheader("题目详细结果")
    
    # 按得分高低排序
    results_sorted = sorted(st.session_state.grading_results, key=lambda x: x['score'])
    
    for res in results_sorted:
        color = "green" if res['score'] >= 8 else "yellow" if res['score'] >= 6 else "red"
        with st.expander(f"第 {res['id']} 题得分: :{color}[{res['score']}] - {res['feedback']}"):
            st.write(f"**你的回答**: {res['user_ans']}")
            st.write(f"**深度解析**: {res['analysis']}")
    
    # 提供重新考试选项
    if st.button("重新考试"):
        for key in ['current_exam', 'user_answers', 'exam_submitted', 'grading_results', 'total_score', 'exam_start_time', 'exam_end_time']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
