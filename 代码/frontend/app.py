import streamlit as st
import requests
import json
import base64
from typing import Dict, Any
import tempfile
import os

# 页面配置
st.set_page_config(
    page_title="PPT知识扩展智能体",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API配置
API_BASE_URL = "http://localhost:8000"  # 或从环境变量读取

def main():
    # 标题和介绍
    st.title("📚 PPT知识扩展智能体")
    st.markdown("""
    **上传您的PPT文件，AI将自动解析内容并扩展相关知识！**
    
    功能特点：
    - 📖 自动解析PPT结构
    - 🧠 AI知识扩展与补充
    - 🔍 关联外部权威资源
    - 📝 生成学习笔记和问题
    """)
    
    # 侧边栏
    with st.sidebar:
        st.header("设置")
        extension_depth = st.selectbox(
            "扩展深度",
            ["简单", "标准", "深度"],
            help="控制知识扩展的详细程度"
        )
        
        include_sources = st.multiselect(
            "包含的外部资源",
            ["Wikipedia", "Arxiv", "学术论文"],
            default=["Wikipedia", "Arxiv"],
            help="选择要搜索的外部知识源"
        )
        
        generate_questions = st.checkbox(
            "生成测试问题",
            value=True,
            help="基于内容生成测试题"
        )
        
        st.divider()
        
        # 示例PPT
        st.markdown("### 示例文件")
        example_files = {
            "机器学习简介": "example_ml.pptx",
            "Python基础": "example_python.pptx",
            "云计算架构": "example_cloud.pptx"
        }
        
        selected_example = st.selectbox("选择示例", list(example_files.keys()))
        
        if st.button("加载示例", type="secondary"):
            # 这里可以加载示例文件
            st.info(f"将加载示例：{selected_example}")
    
    # 主内容区
    tab1, tab2, tab3 = st.tabs(["📤 上传与处理", "📖 浏览结果", "🎯 测试与复习"])
    
    with tab1:
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择PPT文件",
            type=["pptx", "ppt", "pdf"],
            help="支持PPTX、PPT和PDF格式"
        )
        
        if uploaded_file is not None:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 显示文件信息
                st.info(f"""
                **文件信息**
                - 文件名：{uploaded_file.name}
                - 文件大小：{uploaded_file.size / 1024:.1f} KB
                - 文件类型：{uploaded_file.type}
                """)
            
            with col2:
                # 处理按钮
                if st.button("🚀 开始处理", type="primary", use_container_width=True):
                    with st.spinner("正在处理PPT文件..."):
                        result = process_ppt_file(uploaded_file)
                        
                        if result:
                            # 保存结果到session state
                            st.session_state['ppt_result'] = result
                            st.session_state['current_page'] = 0
                            
                            st.success("处理完成！")
                            st.rerun()
    
    with tab2:
        # 显示处理结果
        if 'ppt_result' in st.session_state:
            result = st.session_state['ppt_result']
            
            # 显示概览
            st.subheader(f"📄 {result.get('original_filename', 'PPT文件')}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总页数", result.get('total_pages', 0))
            with col2:
                st.metric("扩展条目", len(result.get('pages', [])))
            with col3:
                st.metric("外部引用", 
                         sum(len(page.get('external_references', {}).get('all_sources', [])) 
                            for page in result.get('pages', [])))
            
            # 目录导航
            st.divider()
            st.subheader("📑 目录导航")
            
            pages = result.get('pages', [])
            toc = result.get('structure', {}).get('toc', [])
            
            if toc:
                # 显示目录
                cols = st.columns(3)
                for i, item in enumerate(toc):
                    with cols[i % 3]:
                        if st.button(
                            f"📖 {item.get('title', f'Page {item.get("page")}')}",
                            key=f"toc_{i}",
                            use_container_width=True
                        ):
                            st.session_state['current_page'] = item.get('page', 1) - 1
            
            # 页面选择器
            current_page = st.session_state.get('current_page', 0)
            selected_page = st.selectbox(
                "选择页面",
                range(len(pages)),
                format_func=lambda x: f"第 {x+1} 页: {pages[x].get('title', '无标题')}",
                index=current_page
            )
            
            # 显示选中的页面
            if 0 <= selected_page < len(pages):
                page_data = pages[selected_page]
                display_page_content(page_data)
        
        else:
            st.info("👆 请先上传并处理PPT文件")
    
    with tab3:
        # 测试与复习功能
        if 'ppt_result' in st.session_state:
            st.subheader("🧠 知识测试")
            
            # 生成问题
            if st.button("生成测试题", type="primary"):
                with st.spinner("正在生成测试题..."):
                    questions = generate_test_questions(st.session_state['ppt_result'])
                    st.session_state['questions'] = questions
            
            # 显示问题
            if 'questions' in st.session_state:
                questions = st.session_state['questions']
                
                for i, q in enumerate(questions):
                    with st.expander(f"问题 {i+1}: {q.get('question', '')}"):
                        options = q.get('options', [])
                        
                        selected = st.radio(
                            "选择答案",
                            options,
                            key=f"q_{i}",
                            label_visibility="collapsed"
                        )
                        
                        if st.button("查看答案", key=f"answer_{i}"):
                            st.success(f"正确答案: {q.get('answer', '')}")
                            st.info(f"解析: {q.get('explanation', '')}")
            
            # 错题本
            st.divider()
            st.subheader("📝 错题本")
            
            if 'wrong_answers' in st.session_state and st.session_state['wrong_answers']:
                for wrong in st.session_state['wrong_answers'][:5]:
                    st.warning(f"❌ {wrong}")
            else:
                st.info("暂无错题记录")
        
        else:
            st.info("👆 请先上传并处理PPT文件")

def process_ppt_file(uploaded_file) -> Dict[str, Any]:
    """
    处理上传的PPT文件
    """
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # 调用API
        files = {'file': (uploaded_file.name, open(tmp_path, 'rb'), uploaded_file.type)}
        
        response = requests.post(
            f"{API_BASE_URL}/api/ppt/upload",
            files=files
        )
        
        # 清理临时文件
        os.unlink(tmp_path)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"处理失败: {response.text}")
            return None
            
    except Exception as e:
        st.error(f"处理过程中出错: {str(e)}")
        return None

def display_page_content(page_data: Dict):
    """
    显示页面内容
    """
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # 原始内容
        st.subheader("📄 原始内容")
        
        if page_data.get('title'):
            st.markdown(f"### {page_data['title']}")
        
        if page_data.get('text'):
            st.markdown(page_data['text'])
        
        # 显示图片
        if page_data.get('images'):
            st.subheader("🖼️ 图片")
            for img in page_data['images'][:3]:  # 最多显示3张
                if img.get('data'):
                    try:
                        st.image(
                            base64.b64decode(img['data']),
                            caption=f"图片",
                            use_column_width=True
                        )
                    except:
                        pass
    
    with col2:
        # 扩展内容
        st.subheader("🧠 AI知识扩展")
        
        extensions = page_data.get('extensions', {})
        
        if extensions.get('error'):
            st.warning("扩展内容生成失败")
        elif extensions:
            # 显示扩展内容
            content = extensions.get('extended_content', '')
            if content:
                st.markdown(content)
            
            # 显示章节
            sections = extensions.get('sections', [])
            if sections:
                with st.expander("📚 扩展章节"):
                    for section in sections:
                        st.markdown(f"- {section}")
        else:
            st.info("点击'开始处理'生成扩展内容")
        
        # 外部引用
        st.subheader("🔍 外部参考")
        
        refs = page_data.get('external_references', {}).get('all_sources', [])
        
        if refs:
            for ref in refs[:3]:  # 最多显示3个
                with st.expander(f"{ref.get('source', '来源')}: {ref.get('title', '')}"):
                    st.markdown(ref.get('summary', ''))
                    if ref.get('url'):
                        st.markdown(f"[查看原文]({ref['url']})")
        else:
            st.info("暂无外部参考")

def generate_test_questions(ppt_result: Dict) -> List[Dict]:
    """
    生成测试问题
    """
    # 这里应该调用API生成问题
    # 简化实现：返回示例问题
    return [
        {
            "question": "什么是机器学习？",
            "options": [
                "A. 让计算机从数据中学习",
                "B. 手动编写规则的程序",
                "C. 数据库管理系统",
                "D. 网络协议"
            ],
            "answer": "A. 让计算机从数据中学习",
            "explanation": "机器学习是人工智能的一个分支，它使计算机能够从数据中学习而无需明确编程。"
        },
        {
            "question": "监督学习和无监督学习的主要区别是什么？",
            "options": [
                "A. 是否需要标签数据",
                "B. 计算复杂度",
                "C. 应用领域",
                "D. 算法类型"
            ],
            "answer": "A. 是否需要标签数据",
            "explanation": "监督学习使用有标签的数据进行训练，而无监督学习使用无标签的数据。"
        }
    ]

if __name__ == "__main__":
    # 初始化session state
    if 'ppt_result' not in st.session_state:
        st.session_state['ppt_result'] = None
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 0
    if 'questions' not in st.session_state:
        st.session_state['questions'] = []
    if 'wrong_answers' not in st.session_state:
        st.session_state['wrong_answers'] = []
    
    main()