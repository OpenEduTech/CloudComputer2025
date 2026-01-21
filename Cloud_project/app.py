import streamlit as st
from backend.database_service import DBManager
from backend.rag_service import RAGService
from backend.agents.quiz_generator import QuizGenerator
from backend.agents.quiz_grader import QuizGrader

# 导入前端组件
from frontend.sidebar import render_sidebar
from frontend.exam_view import render_exam_page
from frontend.dashboard_view import render_dashboard
from frontend.auth_view import render_auth_view

# 页面配置 - 必须是第一个Streamlit命令
st.set_page_config(page_title="智能学习闭环系统", layout="wide", initial_sidebar_state="expanded")

# 初始化 Session State
if 'db' not in st.session_state: 
    try:
        st.session_state.db = DBManager()
    except Exception as e:
        st.error(f"初始化数据库服务失败: {e}")
        st.stop()

# 初始化认证状态
if 'auth_state' not in st.session_state:
    st.session_state.auth_state = {
        'is_authenticated': False,
        'user': None,
        'auth_mode': 'login'
    }

# 检查用户认证状态
if not render_auth_view():
    # 用户未认证，停止渲染后续内容
    st.stop()

# 用户已认证，初始化其他服务
if 'kb' not in st.session_state: 
    try:
        st.session_state.kb = RAGService() # 注意：这里引用改名的服务
    except ValueError as e:
        st.error(f"配置错误: {e}")
        st.stop()
    except Exception as e:
        if "401" in str(e) or "无效的令牌" in str(e) or "AuthenticationError" in str(type(e).__name__):
            st.error("❌ API密钥认证失败")
            st.info("请联系管理员获取有效的API密钥并在.env文件中配置")
        else:
            st.error(f"初始化知识库服务失败: {e}")
        st.stop()

if 'generator' not in st.session_state: 
    try:
        st.session_state.generator = QuizGenerator()
    except ValueError as e:
        st.error(f"配置错误: {e}")
        st.stop()
    except Exception as e:
        if "401" in str(e) or "无效的令牌" in str(e) or "AuthenticationError" in str(type(e).__name__):
            st.error("❌ API密钥认证失败")
            st.info("请联系管理员获取有效的API密钥并在.env文件中配置")
        else:
            st.error(f"初始化试卷生成器失败: {e}")
        st.stop()

if 'grader' not in st.session_state: 
    try:
        st.session_state.grader = QuizGrader()
    except ValueError as e:
        st.error(f"配置错误: {e}")
        st.stop()
    except Exception as e:
        if "401" in str(e) or "无效的令牌" in str(e) or "AuthenticationError" in str(type(e).__name__):
            st.error("❌ API密钥认证失败")
            st.info("请联系管理员获取有效的API密钥并在.env文件中配置")
        else:
            st.error(f"初始化评分器失败: {e}")
        st.stop()

# 添加自定义CSS样式
st.markdown("""
<style>
    /* 页面主题 */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    .css-1d391kg {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        margin: 1rem;
        padding: 2rem;
    }
    
    /* 标题样式 */
    h1 {
        color: #2c3e50;
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 2.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
    }
    
    h2 {
        color: #34495e;
        font-size: 2rem;
        font-weight: 700;
        margin-top: 2.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }
    
    h2::before {
        content: "";
        display: block;
        width: 4px;
        height: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 2px;
    }
    
    h3 {
        color: #34495e;
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* 卡片样式 */
    .stMetric {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(102, 126, 234, 0.1);
        transition: all 0.3s ease;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
        border-color: rgba(102, 126, 234, 0.3);
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before {
        content: "";
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s;
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* 表单样式 */
    .stForm {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    /* 进度条样式 */
    .stProgress > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    .stProgress {
        border-radius: 10px;
        background-color: rgba(102, 126, 234, 0.1);
        height: 12px;
        overflow: hidden;
    }
    
    /* 选择框样式 */
    .stSelectbox > div {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 10px;
        border: 2px solid rgba(102, 126, 234, 0.2);
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div:hover {
        border-color: rgba(102, 126, 234, 0.4);
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
    }
    
    /* 文本区域样式 */
    .stTextArea > div {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 10px;
        border: 2px solid rgba(102, 126, 234, 0.2);
        transition: all 0.3s ease;
    }
    
    .stTextArea > div:focus-within {
        border-color: rgba(102, 126, 234, 0.6);
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* 单选框样式 */
    .stRadio > div {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 0.8rem;
        border-radius: 10px;
        border: 2px solid rgba(102, 126, 234, 0.2);
        transition: all 0.3s ease;
    }
    
    /* 分隔线样式 */
    hr {
        border: 0;
        height: 3px;
        background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.3), transparent);
        margin: 2rem 0;
    }
    
    /* 侧边栏样式 */
    .sidebar {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    /* 提示框样式 */
    .stAlert {
        border-radius: 10px;
        border: 2px solid;
        padding: 1rem;
        transition: all 0.3s ease;
    }
    
    .stAlert:hover {
        transform: translateX(4px);
    }
    
    /* 标签页样式 */
    .stTabs {
        margin-bottom: 2rem;
    }
    
    .stTabs > div:first-child {
        background: rgba(255, 255, 255, 0.8);
        border-radius: 12px 12px 0 0;
        padding: 0.5rem;
        backdrop-filter: blur(10px);
    }
    
    .stTabs > div:first-child > button {
        background: transparent;
        border: none;
        padding: 0.8rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        color: #666;
    }
    
    .stTabs > div:first-child > button:hover {
        background: rgba(102, 126, 234, 0.1);
        color: #667eea;
    }
    
    .stTabs > div:first-child > button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    /* 输入框样式 */
    .stTextInput > div {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 10px;
        border: 2px solid rgba(102, 126, 234, 0.2);
        transition: all 0.3s ease;
    }
    
    .stTextInput > div:focus-within {
        border-color: rgba(102, 126, 234, 0.6);
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* 文件上传样式 */
    .stFileUploader > div {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 10px;
        border: 2px dashed rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
        padding: 2rem;
    }
    
    .stFileUploader > div:hover {
        border-color: rgba(102, 126, 234, 0.6);
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
    }
    
    /* 复选框样式 */
    .stCheckbox > div {
        padding: 0.5rem;
    }
    
    .stCheckbox label {
        font-weight: 500;
        transition: color 0.3s ease;
    }
    
    .stCheckbox label:hover {
        color: #667eea;
    }
    
    /* 响应式设计 - 移动端适配 */
    @media (max-width: 768px) {
        /* 调整标题字体大小 */
        h1 {
            font-size: 1.8rem;
            margin-bottom: 1.2rem;
            text-align: center;
        }
        
        h2 {
            font-size: 1.4rem;
            margin-top: 1.2rem;
            margin-bottom: 0.8rem;
        }
        
        h3 {
            font-size: 1.1rem;
        }
        
        /* 调整按钮大小和间距 */
        .stButton > button {
            padding: 0.6rem 1rem;
            font-size: 0.95rem;
            width: 100%;
            margin-bottom: 0.8rem;
            border-radius: 8px;
        }
        
        /* 调整表单样式 */
        .stForm {
            padding: 1.2rem;
            margin: 0 -0.5rem;
        }
        
        /* 调整卡片样式 */
        .stMetric {
            padding: 1rem;
            margin-bottom: 1.2rem;
            border-radius: 10px;
        }
        
        /* 调整进度条样式 */
        .stProgress {
            margin: 1.2rem 0;
        }
        
        /* 调整侧边栏样式 */
        .sidebar {
            padding: 1rem;
        }
        
        /* 调整文本区域高度 */
        .stTextArea > div {
            height: 140px;
            font-size: 0.95rem;
        }
        
        /* 调整单选框样式 */
        .stRadio > div {
            padding: 0.5rem;
            font-size: 0.95rem;
        }
        
        /* 调整选择框样式 */
        .stSelectbox > div {
            padding: 0.5rem;
            font-size: 0.95rem;
        }
        
        /* 调整分割线样式 */
        hr {
            margin: 1.5rem 0;
        }
        
        /* 调整表格样式 */
        .stDataFrame {
            font-size: 0.9rem;
        }
        
        /* 调整标签页样式 */
        .stTabs {
            margin-bottom: 1.2rem;
        }
        
        /* 调整输入框样式 */
        .stTextInput > div {
            padding: 0.5rem;
            font-size: 0.95rem;
        }
        
        /* 调整文件上传样式 */
        .stFileUploader > div {
            padding: 0.8rem;
            margin: 0 -0.5rem;
        }
        
        /* 调整复选框样式 */
        .stCheckbox > div {
            padding: 0.5rem;
            font-size: 0.95rem;
        }
        
        /* 调整时间选择器样式 */
        .stTimeInput > div {
            padding: 0.5rem;
            font-size: 0.95rem;
        }
        
        /* 调整日期选择器样式 */
        .stDateInput > div {
            padding: 0.5rem;
            font-size: 0.95rem;
        }
        
        /* 调整滑块样式 */
        .stSlider > div {
            padding: 0.5rem;
        }
        
        /* 调整容器边距 */
        .main > div {
            padding: 0 0.5rem;
        }
        
        /* 调整标签页样式 */
        .stTabs > div:first-child {
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .stTabs > div:first-child > button {
            width: 100%;
            text-align: center;
            padding: 0.6rem;
            border-radius: 8px;
        }
        
        /* 优化移动端列布局 */
        .css-1lcbmhc {
            flex-direction: column !important;
            gap: 1rem !important;
        }
        
        /* 调整 expander 样式 */
        .stExpander {
            margin: 0.8rem 0;
        }
        
        .stExpander > button {
            font-size: 0.95rem;
            padding: 0.8rem;
        }
        
        /* 调整错误提示样式 */
        .stError {
            font-size: 0.9rem;
            padding: 0.8rem;
            margin: 0.8rem -0.5rem;
        }
        
        /* 调整成功提示样式 */
        .stSuccess {
            font-size: 0.9rem;
            padding: 0.8rem;
            margin: 0.8rem -0.5rem;
        }
        
        /* 调整信息提示样式 */
        .stInfo {
            font-size: 0.9rem;
            padding: 0.8rem;
            margin: 0.8rem -0.5rem;
        }
        
        /* 调整警告提示样式 */
        .stWarning {
            font-size: 0.9rem;
            padding: 0.8rem;
            margin: 0.8rem -0.5rem;
        }
    }
    
    /* 响应式设计 - 平板适配 */
    @media (min-width: 769px) and (max-width: 1024px) {
        /* 调整标题字体大小 */
        h1 {
            font-size: 2.2rem;
            margin-bottom: 1.8rem;
        }
        
        h2 {
            font-size: 1.6rem;
            margin-top: 1.8rem;
            margin-bottom: 0.9rem;
        }
        
        h3 {
            font-size: 1.3rem;
        }
        
        /* 调整按钮大小和间距 */
        .stButton > button {
            padding: 0.5rem 0.9rem;
            font-size: 0.95rem;
        }
        
        /* 调整表单样式 */
        .stForm {
            padding: 1.2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📚 学习效果评估与巩固智能体 (Enterprise Edition)")

# 1. 渲染侧边栏
render_sidebar(st.session_state.kb)

# 2. 渲染主界面
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