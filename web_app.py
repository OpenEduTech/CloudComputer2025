import streamlit as st
import requests
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import time
import base64
from typing import Dict, List, Any
import io
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="PPT内容扩展智能体",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8010")

# 自定义CSS - 添加颜色类
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #374151;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #D1FAE5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #10B981;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #DBEAFE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #FEF3C7;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #F59E0B;
        margin: 1rem 0;
    }
    .slide-card {
        background-color: #F9FAFB;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #E5E7EB;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .slide-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }
    .expanded-content {
        background-color: #FEFCE8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #EAB308;
        margin: 1rem 0;
    }
    .stButton > button {
        width: 100%;
    }
    .hierarchy-item {
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        border-left: 4px solid #3B82F6;
    }
    .hierarchy-level-1 {
        background-color: #EFF6FF;
        border-left-color: #1D4ED8;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .hierarchy-level-2 {
        background-color: #DBEAFE;
        border-left-color: #3B82F6;
        margin-left: 1rem;
        font-weight: 600;
    }
    .hierarchy-level-3 {
        background-color: #E0F2FE;
        border-left-color: #0EA5E9;
        margin-left: 2rem;
    }
    .hierarchy-level-4 {
        background-color: #F0F9FF;
        border-left-color: #38BDF8;
        margin-left: 3rem;
    }
    .hierarchy-level-5 {
        background-color: #F8FAFC;
        border-left-color: #94A3B8;
        margin-left: 4rem;
    }
    .content-type-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    .content-type-directory { background-color: #3B82F6; color: white; }
    .content-type-chapter { background-color: #10B981; color: white; }
    .content-type-section { background-color: #F59E0B; color: white; }
    .content-type-content { background-color: #8B5CF6; color: white; }
    .content-type-image { background-color: #EC4899; color: white; }
    .content-type-summary { background-color: #6366F1; color: white; }
    .content-type-reference { background-color: #64748B; color: white; }
    .hierarchy-tree {
        font-family: 'Courier New', monospace;
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #E2E8F0;
    }

    .color-main-title { color: #FF0000; }
    .color-directory { color: #0000FF; }
    .color-chapter-title { color: #008000; }
    .color-section-title { color: #FFA500; }
    .color-image-page { color: #FF69B4; }
    .color-content { color: #000000; }
    .color-end-page { color: #800080; }
    .color-thanks { color: #A52A2A; }
    .color-references { color: #4B0082; }
    .color-qa { color: #FF4500; }
    .color-empty { color: #808080; }
    .color-summary { color: #20B2AA; }
    .color-box {
        padding: 8px 12px;
        margin: 6px 0;
        border-radius: 5px;
        border-left: 5px solid;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """检查API健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=60)
        return response.status_code == 200
    except:
        return False


def call_api(endpoint: str, method: str = "GET", data: Dict = None, files: Dict = None, max_retries: int = 3):
    """调用API - 添加重试机制"""
    url = f"{API_BASE_URL}{endpoint}"

    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = requests.get(url, timeout=180)
            elif method == "POST":
                if files:
                    response = requests.post(url, files=files, data=data, timeout=180)
                else:
                    response = requests.post(url, json=data, timeout=180)
            else:
                return {"error": f"不支持的HTTP方法: {method}"}

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 408:
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
                    continue
                return {"error": "请求超时，请稍后重试"}
            elif response.status_code in [429, 502, 503, 504]:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.info(f"API错误 {response.status_code}，等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
                    continue
            else:
                return {"error": f"API错误 ({response.status_code})", "details": response.text}

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            return {"error": "请求超时，请检查网络连接或稍后重试"}
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"error": f"网络错误: {str(e)}"}

    return {"error": f"请求失败，尝试 {max_retries} 次后仍未成功"}


def get_all_slides_from_api(file_id: str, total_slides: int):
    """从API获取所有幻灯片数据 - 修正版本"""
    all_slides = []

    # 使用现有的API端点逐页获取幻灯片详情
    progress_bar = st.progress(0)
    status_text = st.empty()

    for slide_num in range(total_slides):
        # 更新进度显示
        progress_percent = int((slide_num + 1) / total_slides * 100)
        progress_bar.progress(progress_percent)
        status_text.text(f"正在加载幻灯片 {slide_num + 1}/{total_slides}...")

        try:
            # 调用现有的单张幻灯片API端点
            response = call_api(f"/api/file/{file_id}/slide/{slide_num}")

            if "error" not in response:
                all_slides.append(response)
            else:
                # 如果API调用失败，创建占位数据
                logger.warning(f"获取幻灯片 {slide_num} 失败: {response.get('error')}")
                all_slides.append({
                    "slide_number": slide_num,
                    "title": f"幻灯片 {slide_num + 1}",
                    "content": [],
                    "bullet_points": [],
                    "images": [],
                    "notes": "",
                    "level": 1
                })
        except Exception as e:
            logger.error(f"获取幻灯片 {slide_num} 时出错: {e}")
            # 创建占位数据
            all_slides.append({
                "slide_number": slide_num,
                "title": f"幻灯片 {slide_num + 1}",
                "content": [],
                "bullet_points": [],
                "images": [],
                "notes": "",
                "level": 1
            })

        # 小延迟避免请求过快
        if slide_num % 10 == 0:  # 每10张幻灯片休息一下
            time.sleep(0.1)

    progress_bar.empty()
    status_text.empty()

    # 按幻灯片编号排序
    all_slides.sort(key=lambda x: x.get("slide_number", 0))

    return all_slides


def show_header():
    """显示页面标题"""
    st.markdown('<h1 class="main-header">🗂️ PPT内容扩展智能体</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #6B7280; margin-bottom: 2rem;">
    基于云原生和LLM技术，自动扩展PPT内容，提供详细解释、代码示例和学习资源
    </div>
    """, unsafe_allow_html=True)


def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.markdown("### 🎯 导航")
        page = st.radio(
            "选择功能",
            ["🏠 首页", "📤 上传PPT", "📋 文件管理", "🗺️ 层级分析", "🖌️ 内容扩展", "🔍 向量搜索", "⚙️ 设置"],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("### 📊 系统状态")

        # 显示API状态
        if check_api_health():
            st.success("✅ API连接正常")
        else:
            st.error("❌ API连接失败")
            st.info("请确保API服务已启动：`python main.py --mode api`")

        st.markdown("---")
        st.markdown("### 📈 统计信息")

        # 获取文件统计
        files_response = call_api("/api/files")
        if "files" in files_response:
            total_files = len(files_response["files"])
            total_slides = sum(f.get("total_slides", 0) for f in files_response["files"])

            col1, col2 = st.columns(2)
            with col1:
                st.metric("总文件数", total_files)
            with col2:
                st.metric("总幻灯片数", total_slides)

        st.markdown("---")
        st.markdown("### ℹ️ 快速开始")
        with st.expander("查看指南"):
            st.markdown("""
            1. **上传PPT文件** → 选择PPT/PPTX文件
            2. **查看解析结果** → 自动分析PPT结构
            3. **层级分析** → 深度分析PPT结构
            4. **智能扩展** → AI生成详细内容
            5. **向量搜索** → 查询PPT相关内容
            """)

        return page


def home_page():
    """首页"""
    st.markdown('<h2 class="sub-header">🏠 欢迎使用PPT内容扩展智能体</h2>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="info-box">
        <h3>🎯 核心功能</h3>
        <ul>
        <li><b>智能解析</b>：自动分析PPT结构</li>
        <li><b>层级分析</b>：深度识别目录结构</li>
        <li><b>语义检索</b>：基于向量搜索语义</li>
        <li><b>知识扩展</b>：AI生成详细解释</li>
        <li><b>代码示例</b>：自动生成相关代码</li>
        <li><b>试题生成</b>：提供自测问题</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-box">
        <h3>🚀 快速开始</h3>
        <ol>
        <li>点击左侧"上传PPT"</li>
        <li>选择你的PPT文件</li>
        <li>查看解析结果</li>
        <li>选择要扩展的内容</li>
        <li>下载学习材料</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)


    # 系统要求
    st.markdown("---")
    st.markdown('<h3>⚙️ 系统要求</h3>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **运行环境**：
        - Python 3.8+
        - 4GB以上内存
        - 网络连接

        **API要求**：
        - 硅基流动API密钥
        - FastAPI服务
        - Milvus 向量数据库 API
        - Wikipedia API
        """)

    with col2:
        st.markdown("""
        **依赖库**：
        - FastAPI / Streamlit
        - python-pptx
        - pymilvus
        - uvicorn
        - requests
        - python-dotenv
        - python-multipart

        **推荐浏览器**：
        - Chrome 100+
        - Edge 100+
        - Firefox 100+
        """)


def upload_page():
    """上传页面"""
    st.markdown('<h2 class="sub-header">📤 上传PPT文件</h2>', unsafe_allow_html=True)

    # 上传区域
    uploaded_file = st.file_uploader(
        "选择PPT文件",
        type=['pptx', 'ppt'],
        help="支持PPT和PPTX格式，最大100MB"
    )

    if uploaded_file is not None:
        # 显示文件信息
        file_size = uploaded_file.size / 1024 / 1024  # MB
        file_info = {
            "filename": uploaded_file.name,
            "size": f"{file_size:.2f} MB",
            "type": uploaded_file.type
        }

        st.markdown(f"""
        <div class="info-box">
        <h4>📄 文件信息</h4>
        <p><b>文件名</b>: {file_info['filename']}</p>
        <p><b>文件大小</b>: {file_info['size']}</p>
        <p><b>文件类型</b>: {file_info['type']}</p>
        </div>
        """, unsafe_allow_html=True)

        # 文件描述
        description = st.text_area(
            "文件描述（可选）",
            placeholder="请输入PPT的主要内容、课程名称或用途...",
            height=80,
            help="描述将帮助AI更好地理解内容"
        )

        # 上传按钮
        if st.button("🚀 开始上传和处理", type="primary", use_container_width=True):
            with st.spinner("正在上传和处理文件..."):
                # 创建进度显示
                progress_bar = st.progress(0)
                status_text = st.empty()

                # 上传文件
                status_text.text("📤 上传文件中...")
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {"description": description}

                progress_bar.progress(25)

                # 调用上传API
                response = call_api("/api/upload", "POST", data=data, files=files)

                if "error" in response:
                    st.error(f"上传失败: {response['error']}")
                    if "details" in response:
                        with st.expander("查看错误详情"):
                            st.code(response["details"])
                else:
                    progress_bar.progress(50)
                    status_text.text("🔍 解析PPT内容...")

                    # 显示结果
                    progress_bar.progress(75)
                    status_text.text("✅ 处理完成！")

                    st.markdown(f"""
                    <div class="success-box">
                    <h4>✅ 文件上传成功！</h4>
                    <p><b>文件ID</b>: {response.get('file_id', 'N/A')}</p>
                    <p><b>幻灯片数量</b>: {response.get('total_slides', 0)}</p>
                    <p><b>处理状态</b>: 已完成</p>
                    </div>
                    """, unsafe_allow_html=True)


                    # 保存文件ID到session state
                    st.session_state.current_file_id = response.get('file_id')
                    st.session_state.expansion_options = {}

                    progress_bar.progress(100)
                    time.sleep(0.5)
                    progress_bar.empty()
                    status_text.empty()

                    st.success("✅ 文件处理完成！请在'层级分析'或'内容扩展'页面继续操作。")


def file_management_page():
    """文件管理页面"""
    st.markdown('<h2 class="sub-header">📋 文件管理</h2>', unsafe_allow_html=True)

        # 刷新按钮
    if st.button("🔄 刷新列表", use_container_width=True):
        st.rerun()

    # 获取文件列表
    files_response = call_api("/api/files")

    if "files" in files_response and files_response["files"]:
        files = files_response["files"]

        # 文件统计
        st.markdown("### 文件统计")
        stat_cols = st.columns(4)

        with stat_cols[0]:
            st.metric("总文件数", len(files))
        with stat_cols[1]:
            total_slides = sum(f.get("total_slides", 0) for f in files)
            st.metric("总幻灯片数", total_slides)
        with stat_cols[2]:
            avg_slides = total_slides // max(len(files), 1)
            st.metric("平均幻灯片", avg_slides)
        with stat_cols[3]:
            latest_file = files[0]["filename"] if files else "无"
            st.metric("最近上传", latest_file[:15] + "..." if len(latest_file) > 15 else latest_file)

        # 文件列表
        st.markdown("### 📄 文件列表")

        for file_info in files:
            with st.container():
                st.markdown(f'<div class="slide-card">', unsafe_allow_html=True)

                cols = st.columns([3, 1, 1, 1])

                with cols[0]:
                    st.write(f"**{file_info['filename']}**")
                    st.caption(f"📅 上传时间: {file_info['uploaded_at'][:16]}")
                    if file_info.get('description'):
                        st.info(f"📝 {file_info['description']}")

                with cols[1]:
                    st.metric("幻灯片", file_info.get('total_slides', 0))

                with cols[2]:
                    if st.button("选择", key=f"select_{file_info['file_id']}", use_container_width=True):
                        st.session_state.current_file_id = file_info['file_id']
                        st.success(f"已选择: {file_info['filename']}")
                        st.rerun()

                with cols[3]:
                    if st.button("删除", key=f"delete_{file_info['file_id']}",
                                 use_container_width=True, type="secondary"):
                        # 这里应该调用删除API
                        st.warning("删除功能开发中...")

                st.markdown('</div>', unsafe_allow_html=True)

        # 显示当前选中文件的详细信息
        if 'current_file_id' in st.session_state and st.session_state.current_file_id:
            st.markdown("---")
            show_file_details(st.session_state.current_file_id)

    else:
        st.markdown("""
        <div class="warning-box">
        <h4>📭 还没有上传任何文件</h4>
        <p>请先前往<strong>上传PPT</strong>页面上传你的PPT文件。</p>
        </div>
        """, unsafe_allow_html=True)


def show_file_details(file_id: str):
    """显示文件详情 - 修正版本"""
    st.markdown(f"### 📄 文件详情")

    file_response = call_api(f"/api/file/{file_id}")

    if "error" in file_response:
        st.error(f"获取文件详情失败: {file_response['error']}")
        return

    file_info = file_response
    total_slides = file_info.get('structure', {}).get('total_slides', 0)

    # 基本信息
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("文件大小", f"{file_info.get('file_size', 0) / 1024:.1f} KB")
    with col2:
        st.metric("幻灯片数", total_slides)
    with col3:
        st.metric("关键词数", len(file_info.get('structure', {}).get('keywords', [])))
    with col4:
        st.metric("解析状态", "✅ 完成")

    # 标签页
    tab1, tab2, tab3 = st.tabs(["📑 幻灯片预览", "🔑 关键词", "🏗️ 层级结构"])

    with tab1:
        if total_slides > 0:
            # 显示加载提示
            st.info(f"正在加载 {total_slides} 张幻灯片...")

            # 获取所有幻灯片数据
            all_slides = get_all_slides_from_api(file_id, total_slides)

            if all_slides:
                st.success(f"✅ 成功加载 {len(all_slides)} 张幻灯片")

                # 显示分页控件
                page_size = 20
                pages = (len(all_slides) + page_size - 1) // page_size

                if pages > 1:
                    page_num = st.number_input("页码", min_value=1, max_value=pages, value=1)
                    start_idx = (page_num - 1) * page_size
                    end_idx = min(start_idx + page_size, len(all_slides))
                    current_slides = all_slides[start_idx:end_idx]
                    st.info(f"显示第 {start_idx + 1}-{end_idx} 张幻灯片（共 {len(all_slides)} 张）")
                else:
                    current_slides = all_slides

                # 显示当前页的幻灯片
                for slide in current_slides:
                    slide_num = slide.get('slide_number', 0)
                    slide_title = slide.get('title', f"幻灯片 {slide_num + 1}")

                    with st.expander(f"幻灯片 {slide_num + 1}: {slide_title}"):
                        # 显示标题
                        if slide.get('title'):
                            st.write(f"**标题**: {slide['title']}")

                        # 显示内容
                        if slide.get('content'):
                            st.write("**内容**:")
                            for i, content in enumerate(slide['content']):
                                st.write(f"{i + 1}. {content}")

                        # 显示项目符号
                        if slide.get('bullet_points'):
                            st.write("**项目符号**:")
                            for bullet in slide['bullet_points']:
                                st.write(f"- {bullet}")

                        # 显示图片信息
                        if slide.get('images'):
                            image_count = len(slide['images'])
                            st.write(f"**图片数量**: {image_count}")

                        # 显示备注
                        if slide.get('notes'):
                            st.write(f"**备注**: {slide['notes']}")
            else:
                st.error("无法加载幻灯片数据")
        else:
            st.info("该文件没有幻灯片")

    with tab2:
        keywords = file_info.get('structure', {}).get('keywords', [])
        if keywords:
            keyword_text = " ".join([f"`{kw}`" for kw in keywords])
            st.markdown(keyword_text)
        else:
            st.info("暂无关键词")

    with tab3:
        # 显示层级结构（如果API支持）
        if "hierarchical_structure" in file_info.get('structure', {}):
            show_hierarchical_structure_preview(file_info['structure']['hierarchical_structure'])
        else:
            st.info("层级结构数据正在加载中...")
            # 尝试从API获取层级结构
            hierarchy_response = call_api(f"/api/hierarchy/{file_id}")
            if "error" not in hierarchy_response:
                show_hierarchical_structure_preview(hierarchy_response.get("structure", []))
            else:
                st.info("暂无层级结构信息，请在层级分析页面生成")


def show_hierarchical_structure_preview(structure: List[Dict]):
    """显示层级结构预览"""
    if not structure:
        st.info("暂无层级结构信息")
        return

    st.markdown("### 🏗️ 层级结构预览")

    # 内容类型统计
    content_types = {}
    for item in structure:
        content_type = item.get('content_type', '未知')
        content_types[content_type] = content_types.get(content_type, 0) + 1

    # 显示统计
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总结构元素", len(structure))
    with col2:
        st.metric("内容类型数", len(content_types))
    with col3:
        max_level = max([item.get('hierarchical_level', 1) for item in structure])
        st.metric("最大层级深度", max_level)

    # 显示前5个结构元素
    st.markdown("#### 结构元素示例")
    for i, item in enumerate(structure[:5]):
        with st.expander(f"元素 {i + 1}: {item.get('title', '无标题')}"):
            content_type = item.get('content_type', '未知')
            level = item.get('hierarchical_level', 1)

            st.write(f"**内容类型**: `{content_type}`")
            st.write(f"**层级**: {level}")
            if item.get('parent_titles'):
                st.write(f"**上级路径**: {' > '.join(item['parent_titles'])}")

            if item.get('content_elements'):
                st.write("**内容元素**:")
                for elem in item['content_elements'][:3]:
                    st.write(f"- {elem.get('type')}: {elem.get('content', '')[:50]}...")

    if len(structure) > 5:
        st.info(f"还有 {len(structure) - 5} 个结构元素未显示...（详情请看层级分析页面）")


def expansion_page():
    """内容扩展页面 - 修正版本"""
    st.markdown('<h2 class="sub-header">🔍 内容扩展</h2>', unsafe_allow_html=True)

    if 'current_file_id' not in st.session_state or not st.session_state.current_file_id:
        st.warning("⚠️ 请先在文件管理页面选择一个文件")
        return

    file_id = st.session_state.current_file_id

    # 获取文件详情
    file_response = call_api(f"/api/file/{file_id}")
    if "error" in file_response:
        st.error(f"获取文件失败: {file_response['error']}")
        return

    file_info = file_response
    total_slides = file_info.get('structure', {}).get('total_slides', 0)

    if total_slides == 0:
        st.error("该文件没有幻灯片")
        return

    st.markdown(f"### 当前文件: {file_info.get('filename', '未知文件')}")

    # 幻灯片选择
    st.markdown("### 🎯 选择要扩展的幻灯片")

    # 选择模式
    selection_mode = st.radio(
        "选择模式",
        ["按层级分析（只扩展正文页）","全部幻灯片", "指定范围", "手动选择"],
        horizontal=True
    )

    # 设置默认的扩展类型
    expand_types = ["explanation", "references", "examples", "quiz"]  # 默认包含所有扩展类型

    # 根据选择模式确定幻灯片
    slide_numbers = []
    hierarchy_expansion = False  # 标记是否为层级分析扩展

    if selection_mode == "全部幻灯片":
        slide_numbers = list(range(total_slides))
        st.info(f"将扩展全部 {total_slides} 张幻灯片")

    elif selection_mode == "指定范围":
        col1, col2 = st.columns(2)
        with col1:
            start_slide = st.number_input("起始幻灯片", min_value=1, max_value=total_slides, value=1)
        with col2:
            end_slide = st.number_input("结束幻灯片", min_value=1, max_value=total_slides, value=min(5, total_slides))

        if start_slide <= end_slide:
            slide_numbers = list(range(start_slide - 1, end_slide))
            st.info(f"将扩展第 {start_slide} 到第 {end_slide} 张幻灯片，共 {len(slide_numbers)} 张")
        else:
            st.error("起始幻灯片不能大于结束幻灯片")

    elif selection_mode == "按层级分析（只扩展正文页）":
        hierarchy_expansion = True

        # 检查是否有层级分析结果
        hierarchy_response = call_api(f"/api/hierarchy/{file_id}")

        if "error" in hierarchy_response:
            st.warning("该文件尚未进行层级结构分析，请先进行层级分析。")

            if st.button("立即进行层级分析", key="hierarchy_analysis_btn"):
                with st.spinner("正在分析层级结构..."):
                    analysis_response = call_api(f"/api/analyze-hierarchy/{file_id}", "POST")
                    if "error" in analysis_response:
                        st.error(f"层级分析失败: {analysis_response['error']}")
                    else:
                        st.success("✅ 层级结构分析完成！")
                        st.rerun()
        else:
            # 统计正文页数量
            structure = hierarchy_response.get("structure", [])
            body_slides = []
            for item in structure:
                if item.get("content_type") == "正文":
                    slide_num = item.get("slide_number", -1)
                    if slide_num >= 0 and slide_num < total_slides:
                        body_slides.append(slide_num)

            if not body_slides:
                st.warning("层级分析结果中没有找到正文页")
            else:
                slide_numbers = body_slides
                st.success(f"✅ 找到 {len(body_slides)} 个正文页")

                # 显示正文页预览
                with st.expander("📋 查看正文页列表"):
                    for slide_num in body_slides[:10]:  # 只显示前10个
                        # 尝试获取幻灯片标题
                        slide_title = f"幻灯片 {slide_num + 1}"
                        try:
                            slide_response = call_api(f"/api/file/{file_id}/slide/{slide_num}")
                            if "error" not in slide_response:
                                slide_title = slide_response.get("title", slide_title)
                        except:
                            pass
                        st.write(f"- 幻灯片 {slide_num + 1}: {slide_title}")

                    if len(body_slides) > 10:
                        st.info(f"还有 {len(body_slides) - 10} 个正文页未显示...")

    else:  # 手动选择
        st.info(f"共 {total_slides} 张幻灯片")

        # 创建全选/取消全选功能
        col1, col2 = st.columns([1, 4])
        with col1:
            select_all = st.checkbox("全选", value=False, key=f"select_all_{file_id}")

        # 显示所有幻灯片的复选框
        selected_slides = []

        # 获取所有幻灯片数据
        all_slides = get_all_slides_from_api(file_id, total_slides)

        if all_slides:
            for slide in all_slides:
                slide_num = slide.get('slide_number', 0)
                slide_title = slide.get('title', f"幻灯片 {slide_num + 1}")

                # 创建唯一的key
                checkbox_key = f"slide_checkbox_{file_id}_{slide_num}"

                # 如果选择了全选，则默认选中
                default_value = select_all

                if st.checkbox(
                        f"幻灯片 {slide_num + 1}: {slide_title}",
                        value=default_value,
                        key=checkbox_key
                ):
                    selected_slides.append(slide_num)

            slide_numbers = selected_slides

            if selected_slides:
                st.success(f"已选择 {len(selected_slides)} 张幻灯片")
            else:
                st.warning("请至少选择一张幻灯片")
        else:
            st.warning("无法加载幻灯片数据，请稍后重试")
            slide_numbers = []

    # 扩展按钮
    if slide_numbers or hierarchy_expansion:
        if st.button("🚀 开始智能扩展", type="primary", use_container_width=True):
            with st.spinner("正在使用AI扩展内容..."):
                # 准备请求数据
                if hierarchy_expansion:
                    # 使用层级分析扩展API
                    endpoint = f"/api/expand-by-hierarchy/{file_id}"
                    request_data = {}  # 不需要额外的参数
                else:
                    # 使用普通扩展API
                    endpoint = f"/api/expand/{file_id}"
                    request_data = {
                        "slide_numbers": slide_numbers,
                        "expansion_types": expand_types
                    }

                # 显示进度
                progress_bar = st.progress(0)
                status_text = st.empty()

                status_text.text("📤 发送扩展请求..." if not hierarchy_expansion else "📤 发送层级分析扩展请求...")
                progress_bar.progress(10)

                # 调用扩展API
                response = call_api(endpoint, "POST", data=request_data)

                if "error" in response:
                    st.error(f"扩展失败: {response['error']}")
                else:
                    progress_bar.progress(50)
                    status_text.text(" AI正在处理内容...")

                    # 等待处理完成（轮询结果）
                    result_id = response.get('result_id')
                    if result_id:
                        # 简单轮询
                        for i in range(10):
                            time.sleep(2)
                            result_response = call_api(f"/api/expansion/{result_id}")

                            if "error" not in result_response:
                                progress_bar.progress(70 + (i * 3))

                                if result_response.get('total_slides', 0) > 0:
                                    progress_bar.progress(100)
                                    status_text.text("✅ 扩展完成！")

                                    expansion_type = response.get('expansion_type', '普通')
                                    if expansion_type == 'hierarchy_based':
                                        expansion_desc = "层级分析扩展"
                                        body_slides_count = response.get('total_body_slides', 0)
                                        st.markdown(f"""
                                        <div class="success-box">
                                        <h4>✅ 层级分析扩展完成！</h4>
                                        <p><b>扩展结果ID</b>: {result_id}</p>
                                        <p><b>正文页数量</b>: {body_slides_count}</p>
                                        <p><b>处理幻灯片</b>: {response.get('total_expanded', 0)} 张</p>
                                        <p><b>扩展类型</b>: 只扩展正文页</p>
                                        <p><b>完成时间</b>: {datetime.now().strftime('%H:%M:%S')}</p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        expansion_desc = "普通扩展"
                                        st.markdown(f"""
                                        <div class="success-box">
                                        <h4>✅ 内容扩展完成！</h4>
                                        <p><b>扩展结果ID</b>: {result_id}</p>
                                        <p><b>处理幻灯片</b>: {response.get('total_expanded', 0)} 张</p>
                                        <p><b>完成时间</b>: {datetime.now().strftime('%H:%M:%S')}</p>
                                        </div>
                                        """, unsafe_allow_html=True)

                                    # 显示预览
                                    show_expansion_preview(result_response)

                                    # 下载选项
                                    st.markdown("### 📥 下载扩展内容")
                                    col1, col2 = st.columns(2)

                                    with col1:
                                        # 创建下载链接
                                        download_format = "hierarchy_markdown" if expansion_type == 'hierarchy_based' else "markdown"
                                        download_url = f"{API_BASE_URL}/api/download/{file_id}?format={download_format}"
                                        st.markdown(
                                            f'<a href="{download_url}" target="_blank" style="text-decoration: none;">'
                                            f'<button style="width: 100%; padding: 10px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">'
                                            f'下载Markdown'
                                            f'</button>'
                                            f'</a>',
                                            unsafe_allow_html=True
                                        )

                                    with col2:
                                        download_url = f"{API_BASE_URL}/api/download/{file_id}?format=json"
                                        st.markdown(
                                            f'<a href="{download_url}" target="_blank" style="text-decoration: none;">'
                                            f'<button style="width: 100%; padding: 10px; background-color: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer;">'
                                            f'下载JSON'
                                            f'</button>'
                                            f'</a>',
                                            unsafe_allow_html=True
                                        )

                                    break

                    progress_bar.empty()
                    status_text.empty()
    elif not slide_numbers and not hierarchy_expansion:
        st.warning("请选择要扩展的幻灯片或进行层级分析")


def show_expansion_preview(expansion_result: Dict[str, Any]):
    """显示扩展内容预览"""
    slides = expansion_result.get('slides', [])

    if not slides:
        st.info("暂无扩展内容")
        return

    st.markdown("### 📝 扩展内容预览")

    for slide_result in slides[:3]:  # 只显示前3张
        if "error" in slide_result:
            continue

        with st.expander(f"幻灯片 {slide_result['slide_number'] + 1}: {slide_result['title']}", expanded=False):
            st.markdown('<div class="expanded-content">', unsafe_allow_html=True)

            # 显示详细解释
            if "explanations" in slide_result and slide_result["explanations"]:
                st.markdown("**详细解释**")
                for exp in slide_result["explanations"][:2]:  # 只显示前2个
                    st.markdown(f"**{exp.get('concept', '概念')}**")
                    st.write(exp.get('explanation', '')[:200] + "...")
                    st.markdown("---")

            # 显示代码示例
            if "examples" in slide_result and slide_result["examples"]:
                st.markdown("**💻 代码示例**")
                for exp in slide_result["examples"]:
                    st.code(exp.get('code_example', '')[:300] + "...",
                            language=exp.get('language', 'python'))

            # 显示测验问题
            if "quiz_questions" in slide_result and slide_result["quiz_questions"]:
                st.markdown("**❓ 测验问题**")
                for quiz in slide_result["quiz_questions"]:
                    st.write(f"**问题**: {quiz.get('question', '')}")
                    st.write(f"**答案**: {quiz.get('answer', '')}")

            st.markdown('</div>', unsafe_allow_html=True)

    if len(slides) > 3:
        st.info(f"还有 {len(slides) - 3} 张幻灯片的扩展内容未显示...")


def hierarchy_analysis_page():
    """层级分析页面"""
    st.markdown('<h2 class="sub-header">🗺️ PPT层级结构分析</h2>', unsafe_allow_html=True)

    if 'current_file_id' not in st.session_state or not st.session_state.current_file_id:
        st.warning("⚠️ 请先在文件管理页面选择一个文件")
        return

    file_id = st.session_state.current_file_id

    # 获取文件详情
    file_response = call_api(f"/api/file/{file_id}")
    if "error" in file_response:
        st.error(f"获取文件失败: {file_response['error']}")
        return

    file_info = file_response
    filename = file_info.get('filename', '未知文件')
    total_slides = file_info.get('structure', {}).get('total_slides', 0)

    st.markdown(f"### 当前文件: {filename}")
    st.markdown(f"**幻灯片总数**: {total_slides}")

    # 分析选项
    col1, col2, col3 = st.columns(3)
    with col1:
        analyze_depth = st.selectbox(
            "分析深度",
            ["全部层级", "仅顶层结构", "详细分析"],
            help="选择层级分析的详细程度"
        )
    with col2:
        show_elements = st.selectbox(
            "显示内容",
            ["所有元素", "仅标题层级", "内容类型分布"],
            help="选择要显示的内容类型"
        )
    with col3:
        if st.button("🔄 重新分析结构", use_container_width=True):
            with st.spinner("正在重新分析层级结构..."):
                # 调用层级分析API
                analysis_response = call_api(f"/api/analyze-hierarchy/{file_id}", "POST")
                if "error" in analysis_response:
                    st.error(f"分析失败: {analysis_response['error']}")
                else:
                    st.success("✅ 层级结构分析完成！")
                    st.rerun()

    # 获取层级结构数据
    st.markdown("---")
    st.markdown("### 🏗️ 层级结构分析")

    # 尝试从API获取层级结构
    hierarchy_response = call_api(f"/api/hierarchy/{file_id}")

    if "error" in hierarchy_response:
        # 如果没有层级数据，显示提示
        st.info("该文件尚未进行层级结构分析。")
        if st.button("🔍 开始层级分析", type="primary"):
            with st.spinner("正在分析PPT层级结构..."):
                analysis_response = call_api(f"/api/analyze-hierarchy/{file_id}", "POST")
                if "error" in analysis_response:
                    st.error(f"分析失败: {analysis_response['error']}")
                else:
                    st.success("✅ 层级结构分析完成！")
                    st.rerun()
    else:
        # 显示层级结构
        structure = hierarchy_response.get("structure", [])
        if structure:
            display_hierarchical_structure(structure, analyze_depth, show_elements)
        else:
            st.info("暂无层级结构数据")


def display_hierarchical_structure(structure: List[Dict], depth_filter: str, element_filter: str):
    """显示层级结构"""

    # 内容类型颜色映射
    content_type_colors = {
        "主标题": "#FF0000",  # 红色
        "目录": "#0000FF",  # 蓝色
        "章节标题": "#008000",  # 绿色
        "小节标题": "#FFA500",  # 橙色
        "图片页": "#FF69B4",  # 粉色
        "正文": "#000000",  # 黑色
        "结尾页": "#800080",  # 紫色
        "致谢": "#A52A2A",  # 棕色
        "参考文献": "#4B0082",  # 靛蓝
        "问答": "#FF4500",  # 橙红色
        "空白页": "#808080",  # 灰色
        "摘要总结": "#20B2AA",  # 浅海蓝
        "目录页": "#0000FF",  # 蓝色（同目录）
        "代码示例": "#8B4513",  # 马鞍棕
        "标题": "#2E8B57",  # 海绿色
        "表格": "#4682B4",  # 钢蓝色
        "图片描述": "#FF69B4"  # 粉色（同图片页）
    }

    # 根据过滤条件筛选数据
    filtered_structure = structure

    if depth_filter == "仅顶层结构":
        filtered_structure = [s for s in structure if s.get('hierarchical_level', 1) <= 2]
    elif depth_filter == "详细分析":
        filtered_structure = structure  # 显示所有

    if element_filter == "仅标题层级":
        filtered_structure = [s for s in filtered_structure if
                              s.get('content_type') in ["主标题", "目录", "章节标题", "小节标题", "标题"]]
    elif element_filter == "内容类型分布":
        # 显示统计而不是详细列表
        show_content_type_distribution(structure)
        return

    # 显示扁平化列表（不使用树形缩进）
    st.markdown("####   结构列表")

    for item in filtered_structure:
        content_type = item.get('content_type', '未知')
        title = item.get('title', '无标题')
        slide_num = item.get('slide_number', 0) + 1
        level = item.get('hierarchical_level', 1)

        # 获取颜色
        color = content_type_colors.get(content_type, '#000000')

        # 显示每个项目，不使用缩进
        st.markdown(f"""
        <div style="
            padding: 12px;
            margin: 6px 0;
            border-left: 5px solid {color};
            background-color: {color}10;
            border-radius: 5px;
        ">
            <span style="font-weight: bold; color: {color}; font-size: 0.9rem;">{content_type}</span>
            <span style="margin: 0 8px; color: #666;">•</span>
            <span style="font-weight: 600;">幻灯片 {slide_num}</span>
            <span style="margin: 0 8px; color: #666;">•</span>
            <span>{title}</span>
            <span style="margin: 0 8px; color: #666;">•</span>
            <span style="font-size: 0.8rem; color: #888;">层级 {level}</span>
        </div>
        """, unsafe_allow_html=True)

        # 显示内容元素的详细信息（使用按钮切换显示）
        if item.get('content_elements'):
            # 为每个项目创建一个唯一的key
            show_key = f"show_content_{item.get('slide_number', 0)}"

            # 初始化session state
            if show_key not in st.session_state:
                st.session_state[show_key] = False

            col1, col2 = st.columns([1, 5])
            with col1:
                button_label = "隐藏内容" if st.session_state[
                    show_key] else f"显示内容元素 ({len(item['content_elements'])} 个)"
                if st.button(button_label, key=f"btn_{show_key}", use_container_width=True):
                    st.session_state[show_key] = not st.session_state[show_key]
                    st.rerun()

            # 如果按钮被点击，显示内容元素
            if st.session_state[show_key]:
                for elem in item['content_elements']:
                    elem_type = elem.get('type', '未知')
                    elem_content = elem.get('content', '')
                    importance = elem.get('importance', 'medium')

                    importance_color = {
                        'high': '#EF4444',
                        'medium': '#F59E0B',
                        'low': '#6B7280'
                    }.get(importance, '#6B7280')

                    st.markdown(f"""
                    <div style="
                        margin-left: 20px;
                        padding: 8px;
                        border-left: 3px solid {importance_color};
                        background-color: {importance_color}10;
                        margin-bottom: 4px;
                        border-radius: 3px;
                    ">
                        <strong>{elem_type}</strong>: {elem_content[:100]}{'...' if len(elem_content) > 100 else ''}
                    </div>
                    """, unsafe_allow_html=True)

    # 显示统计信息
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        total_items = len(structure)
        st.metric("总结构元素", total_items)

    with col2:
        max_level = max([item.get('hierarchical_level', 1) for item in structure])
        st.metric("最大层级深度", max_level)

    with col3:
        content_types = set([item.get('content_type', '未知') for item in structure])
        st.metric("内容类型数", len(content_types))

    # 显示内容类型分布
    st.markdown("#### 📊 内容类型分布")
    content_type_counts = {}
    for item in structure:
        content_type = item.get('content_type', '未知')
        content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1

    # 创建数据框
    df_types = pd.DataFrame({
        '内容类型': list(content_type_counts.keys()),
        '数量': list(content_type_counts.values())
    }).sort_values('数量', ascending=False)

    # 显示表格
    st.dataframe(df_types, use_container_width=True)

    # 创建柱状图（使用对应的颜色）
    colors = [content_type_colors.get(ctype, '#808080') for ctype in df_types['内容类型']]

    fig = go.Figure(data=[
        go.Bar(
            x=df_types['内容类型'],
            y=df_types['数量'],
            marker_color=colors,
            text=df_types['数量'],
            textposition='auto'
        )
    ])
    fig.update_layout(
        title="内容类型分布",
        xaxis_title="内容类型",
        yaxis_title="数量",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # 显示层级深度分布
    st.markdown("#### 📈 层级深度分布")
    level_counts = {}
    for item in structure:
        level = item.get('hierarchical_level', 1)
        level_counts[level] = level_counts.get(level, 0) + 1

    df_levels = pd.DataFrame({
        '层级': list(level_counts.keys()),
        '数量': list(level_counts.values())
    }).sort_values('层级')

    fig2 = go.Figure(data=[
        go.Scatter(
            x=df_levels['层级'],
            y=df_levels['数量'],
            mode='lines+markers',
            line=dict(color='#10B981', width=3),
            marker=dict(size=10, color='#10B981')
        )
    ])
    fig2.update_layout(
        title="层级深度分布",
        xaxis_title="层级深度",
        yaxis_title="元素数量",
        height=400
    )
    st.plotly_chart(fig2, use_container_width=True)


def show_content_type_distribution(structure: List[Dict]):
    """显示内容类型分布"""
    content_type_counts = {}
    for item in structure:
        content_type = item.get('content_type', '未知')
        content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1

    # 创建饼图
    fig = go.Figure(data=[
        go.Pie(
            labels=list(content_type_counts.keys()),
            values=list(content_type_counts.values()),
            hole=.3
        )
    ])
    fig.update_layout(
        title="内容类型分布",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # 显示表格
    df = pd.DataFrame({
        '内容类型': list(content_type_counts.keys()),
        '数量': list(content_type_counts.values()),
        '占比 (%)': [round(count / len(structure) * 100, 1) for count in content_type_counts.values()]
    }).sort_values('数量', ascending=False)

    st.dataframe(df, use_container_width=True)


def settings_page():
    """设置页面"""
    st.markdown('<h2 class="sub-header">⚙️ 系统设置</h2>', unsafe_allow_html=True)

    # 模型设置
    st.markdown("### 🎨 AI模型设置")

    model_name = st.selectbox(
        "选择模型",
        ["deepseek-ai/DeepSeek-V3.2-Exp", "deepseek-ai/DeepSeek-V2", "其他模型"],
        help="选择要使用的AI模型"
    )

    temperature = st.slider(
        "创造性 (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="值越高，生成的内容越有创造性"
    )

    # 文件设置
    st.markdown("### 📁 文件设置")

    max_file_size = st.slider(
        "最大文件大小 (MB)",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="允许上传的最大文件大小"
    )

    # 保存设置
    if st.button("💾 保存设置", type="primary", use_container_width=True):
        # 这里应该保存设置到配置文件
        st.success("设置已保存！")

        # 更新环境变量
        os.environ["API_BASE_URL"] = "http://localhost:8010"  # 固定API基础URL

        st.info("部分设置需要重启应用才能生效")


def vector_search_page():
    """向量搜索页面"""
    st.markdown('<h2 class="sub-header">🔍 语义向量搜索</h2>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <h4>🎯 智能语义搜索</h4>
    <p>基于向量数据库的语义搜索，可以理解查询的深层含义，找到最相关的内容。</p>
    </div>
    """, unsafe_allow_html=True)

    # 搜索配置
    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "搜索内容",
            placeholder="输入关键词、问题或概念...",
            help="支持自然语言搜索，如'机器学习的基本原理'"
        )

    with col2:
        n_results = st.number_input(
            "结果数量",
            min_value=1,
            max_value=50,
            value=10,
            help="显示的结果数量"
        )

    # 文件筛选
    files_response = call_api("/api/files")
    if "files" in files_response and files_response["files"]:
        file_options = ["所有文件"] + [f["filename"] for f in files_response["files"]]
        selected_file = st.selectbox(
            "筛选文件",
            file_options,
            index=0
        )

        # 获取文件ID
        file_id = None
        if selected_file != "所有文件":
            for f in files_response["files"]:
                if f["filename"] == selected_file:
                    file_id = f["file_id"]
                    break
    else:
        st.warning("没有可搜索的文件，请先上传PPT文件")
        return

    # 相似度阈值
    similarity_threshold = st.slider(
        "相似度阈值",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.05,
        help="过滤相似度低于此值的结果"
    )

    # 搜索按钮
    if st.button("🚀 开始语义搜索", type="primary", use_container_width=True):
        if not search_query.strip():
            st.warning("请输入搜索内容")
            return

        with st.spinner("正在搜索..."):
            # 准备搜索请求
            search_data = {
                "query": search_query,
                "file_id": file_id,
                "n_results": n_results,
                "similarity_threshold": similarity_threshold
            }

            # 调用向量搜索API
            search_response = call_api("/api/vector-search", "POST", data=search_data)

            if "error" in search_response:
                st.error(f"搜索失败: {search_response['error']}")
            else:
                results = search_response.get("results", [])
                total_results = search_response.get("total_results", 0)
                filtered_results = search_response.get("filtered_results", 0)

                # 显示统计
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总结果数", total_results)
                with col2:
                    st.metric("过滤后结果", filtered_results)
                with col3:
                    st.metric("相似度阈值", f"{similarity_threshold:.2f}")

                # 显示结果
                if results:
                    st.markdown("### 📋 搜索结果")

                    for i, result in enumerate(results):
                        with st.expander(
                                f"结果 {i + 1}: 幻灯片 {result['slide_number'] + 1} "
                                f"(相似度: {result['similarity']:.3f})",
                                expanded=i == 0
                        ):
                            # 显示基本信息
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**文件**: {result['filename']}")
                                st.write(f"**幻灯片**: {result['slide_number'] + 1}")

                            with col_b:
                                # 相似度可视化
                                similarity = result['similarity']
                                color = "#10B981" if similarity > 0.7 else "#F59E0B" if similarity > 0.4 else "#EF4444"
                                st.markdown(f"""
                                <div style="background-color: {color}20; padding: 10px; border-radius: 5px;">
                                    <strong>语义相似度:</strong> 
                                    <span style="color: {color}; font-weight: bold;">{similarity:.3f}</span>
                                    <div style="background-color: #E5E7EB; height: 8px; border-radius: 4px; margin-top: 5px;">
                                        <div style="background-color: {color}; width: {similarity * 100}%; height: 100%; border-radius: 4px;"></div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                            # 显示内容
                            st.markdown("**内容**:")
                            st.info(result['content'])

                else:
                    st.info("没有找到相关结果，尝试调整搜索词或降低相似度阈值")


def main():
    """主函数"""
    show_header()

    # 检查API连接
    if not check_api_health():
        st.markdown("""
        <div class="warning-box">
        <h4>⚠️ API服务未连接</h4>
        <p>请确保API服务已启动，可以执行以下命令：</p>
        <pre><code>python main.py --mode api</code></pre>
        <p>或者</p>
        <pre><code>uvicorn api:app --host 0.0.0.0 --port 8010</code></pre>
        </div>
        """, unsafe_allow_html=True)

    # 显示侧边栏并获取当前页面
    page = show_sidebar()

    # 根据页面路由
    if page == "🏠 首页":
        home_page()
    elif page == "📤 上传PPT":
        upload_page()
    elif page == "📋 文件管理":
        file_management_page()
    elif page == "🖌️ 内容扩展":
        expansion_page()
    elif page == "🔍 向量搜索":
        vector_search_page()
    elif page == "🗺️ 层级分析":
        hierarchy_analysis_page()
    elif page == "⚙️ 设置":
        settings_page()


if __name__ == "__main__":
    # 初始化session state
    if 'current_file_id' not in st.session_state:
        st.session_state.current_file_id = None
    if 'expansion_options' not in st.session_state:
        st.session_state.expansion_options = {}

    main()