# app.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import shutil
from input_handler import extract_text_from_pptx
from agent_core import process_ppt_slides
from output_formatter import format_as_json

# 初始化 FastAPI 应用
app = FastAPI(
    title="PPT内容扩展智能体",
    description="基于智谱AI glm-4-flash 的 PPT 内容自动扩展与事实校验服务",
    version="1.0.0"
)


@app.post("/expand")
async def expand_ppt(file: UploadFile = File(...)):
    """
    上传 PPTX 文件，返回每页的扩展内容及校验结果。
    
    - 仅支持 .pptx 格式
    - 文件将被临时保存并处理
    - 返回 JSON 结构化结果
    """
    # 1. 检查文件类型
    if not file.filename.lower().endswith('.pptx'):
        raise HTTPException(status_code=400, detail="仅支持 .pptx 格式的 PowerPoint 文件")

    # 2. 保存上传文件到临时路径
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. 提取文本
        slides_data = extract_text_from_pptx(temp_path)

        if not slides_data:
            raise HTTPException(status_code=400, detail="PPT 文件为空或无法提取有效内容")

        # 4. 处理每一页（扩展 + 校验）
        results = process_ppt_slides(slides_data)

        # 5. 格式化为 JSON 返回
        json_result = format_as_json(results)
        return JSONResponse(content={"status": "success", "data": json_result})

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/")
async def root():
    return {"message": "欢迎使用 PPT内容扩展智能体！请 POST /expand 上传 .pptx 文件。"}