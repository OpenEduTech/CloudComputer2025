import streamlit as st

def render_sidebar(knowledge_base):
    with st.sidebar:
        st.header("1. 资料摄入")
        input_type = st.radio("选择资料类型", ["PDF文档", "录音音频 (Beta)"])
        uploaded_file = st.file_uploader("上传文件", type=["pdf", "wav"])
        use_ocr = st.checkbox("启用视觉OCR (扫描件)", help="调用Vision模型")

        if uploaded_file and st.button("开始处理"):
            # 保存临时文件并显示进度
            ext = ".pdf" if input_type == "PDF文档" else ".wav"
            file_path = f"temp_input{ext}"
            
            # 计算文件大小
            file_size = uploaded_file.size
            chunk_size = 1024 * 1024  # 1MB
            
            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            status_text.text("开始上传文件...")
            
            # 分块保存文件 - 兼容旧版本Streamlit
            with open(file_path, "wb") as f:
                bytes_written = 0
                
                # 检查是否支持iter_chunks方法
                if hasattr(uploaded_file, 'iter_chunks'):
                    # 使用iter_chunks方法（新版本Streamlit）
                    for chunk in uploaded_file.iter_chunks(chunk_size=chunk_size):
                        f.write(chunk)
                        bytes_written += len(chunk)
                        progress = bytes_written / file_size
                        progress_bar.progress(progress)
                        
                        # 更新状态文本
                        status_text.text(f"上传进度: {int(progress * 100)}% ({bytes_written / (1024 * 1024):.1f}MB / {file_size / (1024 * 1024):.1f}MB)")
                else:
                    # 兼容旧版本Streamlit
                    data = uploaded_file.getvalue()
                    total_size = len(data)
                    
                    # 手动分块写入
                    for i in range(0, total_size, chunk_size):
                        chunk = data[i:i+chunk_size]
                        f.write(chunk)
                        bytes_written += len(chunk)
                        progress = bytes_written / total_size
                        progress_bar.progress(progress)
                        
                        # 更新状态文本
                        status_text.text(f"上传进度: {int(progress * 100)}% ({bytes_written / (1024 * 1024):.1f}MB / {total_size / (1024 * 1024):.1f}MB)")
            
            # 完成文件上传
            progress_bar.progress(100)
            status_text.text("文件上传完成，正在解析资料...")
            
            # 清除进度条和状态文本
            progress_bar.empty()
            
            with st.spinner("正在解析资料..."):
                ftype = "pdf" if input_type == "PDF文档" else "audio"
                n = knowledge_base.build_index(file_path, file_type=ftype, use_ocr=use_ocr)
                
                if n > 0:
                    st.success(f"解析成功！生成 {n} 个知识片段")
                    st.session_state.file_ready = True
                else:
                    st.error("解析失败")
            
            # 清除状态文本
            status_text.empty()