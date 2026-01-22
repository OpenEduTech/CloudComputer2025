import streamlit as st
import requests
import os
import json

# --- 配置 ---
# 从环境变量获取后端地址，在 Docker 内部自动指向 http://backend:8000
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# --- 页面设置 ---
st.set_page_config(
    page_title="智能学习评估助手",
    page_icon="🎓",
    layout="wide"
)

# --- 侧边栏导航 ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/student-center.png", width=80)
    st.title("学习助手导航")
    mode = st.radio(
        "选择功能模块:",
        ["📝 上传资料出题", "📚 查看错题本/历史", "⚙️ 系统状态"]
    )
    st.markdown("---")
    st.caption("云计算期末大作业 Demo")
    st.caption("命题二：学习效果评估智能体")

# --- 主标题 ---
st.title("🎓 智能学习评估与巩固助手")

# ========================================================
# 功能模块 1: 上传资料出题
# ========================================================
if mode == "📝 上传资料出题":
    st.header("1. 资料上传与题目生成")
    st.markdown("请将你的 **笔记、教材文本或复习资料** 粘贴在下方，AI 将自动为你生成考核试题。")
    
    # 文本输入框
    user_text = st.text_area("在此粘贴学习内容 (建议 500 字以上):", height=250, placeholder="例如：云计算是一种基于互联网的计算方式...")
    
    # 生成按钮
    if st.button("🚀 开始智能出题", type="primary"):
        if not user_text:
            st.warning("⚠️ 请先输入学习资料！")
        else:
            with st.spinner("🧠 AI 正在分析知识点、构建题目并存入数据库..."):
                try:
                    # 调用后端生成接口
                    payload = {"text": user_text}
                    response = requests.post(f"{BACKEND_URL}/generate_quiz", json=payload)
                    
                    if response.status_code == 200:
                        quiz_data = response.json()
                        st.success("✅ 出题成功！已自动存入错题本数据库。")
                        
                        # 展示生成结果
                        st.subheader(f"📑 试卷主题: {quiz_data.get('topic', '未命名')}")
                        
                        for q in quiz_data.get("questions", []):
                            with st.container():
                                st.markdown(f"**第 {q['id']} 题: {q['question']}**")
                                # 展示选项
                                for opt in q['options']:
                                    st.text(opt)
                                # 答案与解析（默认折叠，防止剧透）
                                with st.expander("查看答案与解析"):
                                    st.markdown(f"**正确答案:** `{q['correct_answer']}`")
                                    st.info(f"💡 **解析:** {q['explanation']}")
                                st.divider()
                    else:
                        st.error(f"后端报错 ({response.status_code}): {response.text}")
                
                except Exception as e:
                    st.error(f"❌ 无法连接后端服务: {e}")
                    st.caption("提示: 请检查 Docker 容器是否正在运行。")

# ========================================================
# 功能模块 2: 查看错题本 (MongoDB 数据)
# ========================================================
elif mode == "📚 查看错题本/历史":
    st.header("2. 学习历史与错题回顾")
    st.markdown("这里展示了所有 **持久化存储在 MongoDB** 中的历史生成记录。")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        refresh_btn = st.button("🔄 刷新列表")
    
    # 获取历史记录
    try:
        with st.spinner("正在从 MongoDB 读取数据..."):
            res = requests.get(f"{BACKEND_URL}/get_history")
            
            if res.status_code == 200:
                history_data = res.json()
                
                if not history_data:
                    st.info("📭 数据库暂时为空，请先去生成一些题目吧！")
                else:
                    st.write(f"共找到 {len(history_data)} 套历史试卷")
                    
                    # 遍历显示每一套试卷
                    for i, item in enumerate(history_data):
                        # 使用 expander 收纳每一套题
                        with st.expander(f"📅 记录 {i+1}: {item.get('topic', '未命名主题')}", expanded=(i==0)):
                            st.caption(f"数据库 ID: {item.get('_id')}")
                            
                            for q in item.get("questions", []):
                                st.markdown(f"**Q{q['id']}: {q['question']}**")
                                st.code("\n".join(q['options']), language="text")
                                
                                # 这里的答案直接显示，因为是复习模式
                                col_a, col_b = st.columns([1, 3])
                                with col_a:
                                    st.markdown(f"✅ **答案:** `{q['correct_answer']}`")
                                with col_b:
                                    st.markdown(f"📖 **解析:** {q['explanation']}")
                                st.divider()
            else:
                st.error(f"获取数据失败: {res.status_code}")
                
    except Exception as e:
        st.error(f"无法连接数据库接口: {e}")

# ========================================================
# 功能模块 3: 系统状态
# ========================================================
elif mode == "⚙️ 系统状态":
    st.header("系统运行监控")
    
    st.markdown("### 微服务状态")
    
    # 检查后端连接
    col1, col2 = st.columns(2)
    with col1:
        st.metric("前端服务 (Streamlit)", "运行中", delta="Normal")
    
    with col2:
        try:
            res = requests.get(f"{BACKEND_URL}/", timeout=2)
            if res.status_code == 200:
                data = res.json()
                st.metric("后端服务 (FastAPI)", "在线", delta=f"{res.elapsed.total_seconds()*1000:.0f}ms")
                st.json(data)
            else:
                st.metric("后端服务", "异常", delta_color="inverse")
        except:
            st.metric("后端服务", "离线", delta_color="inverse")
            st.error("无法连接到后端容器，请检查 Docker 日志。")

    st.markdown("### 架构说明")
    st.markdown("""
    * **Frontend**: Streamlit (Python)
    * **Backend**: FastAPI (Python)
    * **LLM Provider**: DeepSeek / OpenAI / Mock
    * **Database**: MongoDB (Persistence)
    """)