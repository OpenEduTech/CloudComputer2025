"""
PatPat-Inconsistency-Hunter 用户认证API路由
提供用户注册、登录、获取当前用户等接口
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.auth import (
    AuthService,
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    decode_access_token,
    user_to_response,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from ..models.database import User
from ..utils.db_session import get_db_session
from ..utils.logger import logger
from pydantic import BaseModel


router = APIRouter(prefix="/auth", tags=["认证"])

# Bearer Token 认证
security = HTTPBearer(auto_error=False)


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_color: Optional[str] = None
    avatar_url: Optional[str] = None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    获取当前登录用户
    
    从请求头中提取Bearer Token并验证
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    auth_service = AuthService(db)
    user = await auth_service.validate_token(token)
    return user


async def require_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    要求用户登录
    
    如果未登录则返回401错误
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    用户注册
    
    注册成功后自动登录并返回访问令牌
    """
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.register(user_data)
        
        # 自动登录
        user, access_token = await auth_service.login(
            UserLogin(username=user_data.username, password=user_data.password)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_to_response(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db_session),
):
    """
    用户登录
    
    验证用户名和密码，返回访问令牌
    """
    auth_service = AuthService(db)
    
    try:
        user, access_token = await auth_service.login(login_data)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_to_response(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(require_user),
):
    """
    获取当前登录用户信息
    """
    return user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: ProfileUpdateRequest = Body(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新当前用户信息
    """
    auth_service = AuthService(db)
    
    update_data = {}
    if payload.display_name is not None:
        update_data["display_name"] = payload.display_name
    if payload.email is not None:
        # 检查邮箱是否被占用
        existing = await auth_service.get_user_by_email(payload.email)
        if existing and existing.user_id != current_user.user_id:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        update_data["email"] = payload.email
    if payload.avatar_color is not None:
        update_data["avatar_color"] = payload.avatar_color
    if payload.avatar_url is not None:
        update_data["avatar_url"] = payload.avatar_url
    
    if update_data:
        user = await auth_service.update_user(current_user.user_id, **update_data)
        return user_to_response(user)
    
    return user_to_response(current_user)


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    修改密码
    """
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6个字符")
    
    auth_service = AuthService(db)
    success = await auth_service.change_password(
        current_user.user_id, old_password, new_password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="原密码错误")
    
    return {"message": "密码修改成功"}


@router.post("/logout")
async def logout(
    current_user: User = Depends(require_user),
):
    """
    用户登出
    
    注意：JWT无状态，服务端不存储token，
    登出只是客户端删除token
    """
    logger.info(f"用户登出: {current_user.username}")
    return {"message": "登出成功"}


@router.get("/check")
async def check_auth(
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    检查登录状态
    """
    if current_user:
        return {
            "authenticated": True,
            "user": user_to_response(current_user),
        }
    return {"authenticated": False}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    上传用户头像
    
    接受图片文件，保存到静态目录并更新用户头像URL
    """
    import uuid
    import os
    import aiofiles
    
    # 验证文件类型
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持 JPEG、PNG、GIF、WEBP 格式的图片")
    
    # 验证文件大小（最大5MB）
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过5MB")
    
    # 生成唯一文件名
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    unique_filename = f"{current_user.user_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    
    # 确保上传目录存在（与 main.py 中的 static_dir 保持一致）
    # main.py: static_dir = Path("uploads")  # 即 /app/uploads
    # 所以 auth_routes.py 需要: /app/uploads/avatars
    from pathlib import Path
    static_dir = Path("uploads") / "avatars"
    static_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存文件
    file_path = static_dir / unique_filename
    async with aiofiles.open(str(file_path), 'wb') as f:
        await f.write(file_content)
    
    # 生成访问URL（确保路径正确）
    avatar_url = f"/static/avatars/{unique_filename}"
    
    # 更新用户头像URL
    auth_service = AuthService(db)
    user = await auth_service.update_user(current_user.user_id, avatar_url=avatar_url)
    
    logger.info(f"用户 {current_user.username} 上传了头像: {avatar_url}")
    
    return {
        "message": "头像上传成功",
        "avatar_url": avatar_url,
        "user": user_to_response(user),
    }


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdateRequest = Body(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新用户资料（同 /me，为前端提供别名）
    """
    auth_service = AuthService(db)
    
    update_data = {}
    if payload.display_name is not None:
        update_data["display_name"] = payload.display_name
    if payload.email is not None:
        # 检查邮箱是否被占用
        existing = await auth_service.get_user_by_email(payload.email)
        if existing and existing.user_id != current_user.user_id:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        update_data["email"] = payload.email
    if payload.avatar_color is not None:
        update_data["avatar_color"] = payload.avatar_color
    if payload.avatar_url is not None:
        update_data["avatar_url"] = payload.avatar_url
    
    if update_data:
        user = await auth_service.update_user(current_user.user_id, **update_data)
        return user_to_response(user)
    
    return user_to_response(current_user)

