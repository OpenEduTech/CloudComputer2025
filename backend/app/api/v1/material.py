from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.api import deps
from app.models.user import UserResponse
from app.services.agents.pdf_parser import pdf_parser_agent
import shutil
import os
from bson import ObjectId

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/upload")
async def upload_and_parse_material(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(deps.get_current_user)
):
    """
    上传并解析PDF文件
    直接返回解析后的内容，不保存到数据库
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # 保存临时文件
    file_path = os.path.join(UPLOAD_DIR, f"{ObjectId()}_{file.filename}")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 直接解析PDF
        content = await pdf_parser_agent.parse_pdf(file_path)
        
        # 返回解析结果
        return {
            "filename": file.filename,
            "content": content,
            "content_length": len(content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
