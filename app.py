import streamlit as st
import os
from backend.database_service import DBManager
from backend.rag_service import RAGService
from backend.agents.quiz_generator import QuizGenerator
from backend.agents.quiz_grader import QuizGrader

# 导入前端组件
from frontend.sidebar import render_sidebar
from frontend.exam_view import render_exam_page
from frontend.dashboard_view import render_dashboard
from frontend.auth_view import render_auth_view

# 页面配置
st.set_page_config(page_title="智能学习闭环系统", layout="wide", initial_sidebar_state="expanded")

# ✅ 修复：指定 encoding='utf-8' 防止 Windows 下报 GBK 解码错误
def load_css(file_name):
    with open(file_name, encoding="utf-8") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

css_path = os.path.join("frontend", "style.css")
if os.path.exists(css_path):
    load_css(css_path)

# 初始化 Session State
if 'db' not in st.session_state: 
    try:
        st.session_state.db = DBManager()
    except Exception as e:
        st.error(f"初始化数据库服务失败: {e}")
        st.stop()
# 热修复：如果 db 实例缺少新方法，强制重新初始化
elif not hasattr(st.session_state.db, 'remove_mistake'):
    try:
        from backend.database_service import DBManager
        import importlib
        import backend.database_service
        importlib.reload(backend.database_service)
        st.session_state.db = DBManager()
        st.toast("系统后台已更新，正在重新加载...", icon="🔄")
        st.rerun()
    except Exception as e:
        st.error(f"更新数据库服务失败: {e}")

# 初始化认证状态
if 'auth_state' not in st.session_state:
    st.session_state.auth_state = {
        'is_authenticated': False,
        'user': None,
        'auth_mode': 'login'
    }

# 检查用户认证状态
if not render_auth_view():
    st.stop()

# ✅ 关键：确保 user_id 在 Session 中是正确的
if st.session_state.auth_state['is_authenticated'] and st.session_state.auth_state['user']:
    user_info = st.session_state.auth_state['user']
    # 优先使用 _id (转字符串)，如果没有则用 username
    st.session_state.user_id = str(user_info.get('_id', user_info.get('username')))
else:
    st.session_state.user_id = "default" 

# 初始化其他服务
if 'kb' not in st.session_state: 
    try:
        st.session_state.kb = RAGService()
    except Exception as e:
        st.error(f"初始化知识库服务失败: {e}")

if 'generator' not in st.session_state: 
    st.session_state.generator = QuizGenerator()

if 'grader' not in st.session_state: 
    st.session_state.grader = QuizGrader()
# 强制更新 grader 实例以确保包含最新方法 (热修复)
elif not hasattr(st.session_state.grader, 'analyze_difficulty_gradient'):
    st.session_state.grader = QuizGrader()

st.title("📚 学习效果评估与巩固智能体 (Enterprise Edition)")

# 渲染侧边栏
render_sidebar(st.session_state.kb)

# 渲染主界面
tab1, tab2 = st.tabs(["📝 智能考核", "📊 错题仪表盘"])

with tab1:
    if st.session_state.get('file_ready'):
        render_exam_page(
            st.session_state.generator, 
            st.session_state.grader, 
            st.session_state.kb, 
            st.session_state.db
        )
    else:
        st.info("👈 请先在左侧上传学习资料")

with tab2:
    render_dashboard(st.session_state.db)