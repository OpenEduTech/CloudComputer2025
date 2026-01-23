import streamlit as st
import os
import time
import traceback # 用于打印详细堆栈

def render_sidebar(knowledge_base):
    with st.sidebar:
        st.header("1. 资料摄入")
        
        # 调试工具：手动清除缓存
        if st.checkbox("🔧 显示调试工具"):
            if st.button("🗑️ 清除所有缓存 (重启后端)"):
                st.session_state.clear()
                st.rerun()
        
        input_type = st.radio("选择资料类型", ["PDF文档", "录音音频 (Beta)"])
        allowed_types = ["pdf"] if input_type == "PDF文档" else ["wav", "mp3"]
        
        uploaded_files = st.file_uploader(
            f"上传文件 ({'/'.join(allowed_types)})", 
            type=allowed_types, 
            accept_multiple_files=True
        )
        
        # ⚠️ 确保这里的 key 不会冲突
        use_ocr = st.checkbox("启用视觉OCR (扫描件)", value=False, help="强制调用视觉模型进行识别")

        if uploaded_files and st.button("开始处理"):
            if not os.path.exists("temp"):
                os.makedirs("temp")
            
            file_paths = []
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            try:
                # 1. 保存文件
                status_text.text("正在保存文件...")
                total_files = len(uploaded_files)
                for i, uploaded_file in enumerate(uploaded_files):
                    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                    file_path = os.path.join("temp", f"temp_input_{int(time.time())}_{i}{file_ext}")
                    file_paths.append(file_path)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                # 2. 调用后端
                status_text.text("正在调用 AI 模型解析 (请耐心等待)...")
                with st.spinner("AI 正在读取文档..."):
                    ftype = "pdf" if input_type == "PDF文档" else "audio"
                    
                    # 打印调试信息到前端，证明用的是新逻辑
                    if use_ocr:
                        st.info("ℹ️ 已启用 OCR 模式")
                    
                    # 核心调用
                    n = knowledge_base.build_index(file_paths, file_type=ftype, use_ocr=use_ocr)
                    
                    if n > 0:
                        st.success(f"✅ 成功！共生成 {n} 个知识片段")
                        st.session_state.file_ready = True
                        time.sleep(1)
                        status_text.empty()
                        progress_bar.empty()
                    else:
                        st.error("⚠️ 解析完成，结果为空。")
                        st.warning("建议：\n1. 检查 API Key 是否欠费\n2. 检查控制台是否有红色报错\n3. 点击上方调试工具清除缓存重试")

            except Exception as e:
                st.error(f"❌ 发生错误: {str(e)}")
                # 将详细错误打印出来
                st.code(traceback.format_exc())