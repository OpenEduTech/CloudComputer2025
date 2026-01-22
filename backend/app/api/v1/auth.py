from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core import security
from app.core.config import settings
from app.core.database import db
from app.models.user import UserCreate, UserResponse, Token, UserInDB

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate):
    # Check if user exists
    user = await db.db.users.find_one({"email": user_in.email})
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Check if username exists
    user = await db.db.users.find_one({"username": user_in.username})
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    user_data = user_in.model_dump()
    password = user_data.pop("password")
    user_data["hashed_password"] = security.get_password_hash(password)
    user_data["created_at"] = user_data.get("created_at", None)
    
    from datetime import datetime
    if not user_data["created_at"]:
        user_data["created_at"] = datetime.utcnow()
    
    new_user = await db.db.users.insert_one(user_data)
    created_user = await db.db.users.find_one({"_id": new_user.inserted_id})
    
    # Convert ObjectId to string
    if created_user:
        created_user["_id"] = str(created_user["_id"])
    
    return created_user

@router.post("/login/access-token", response_model=Token)
async def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Try to find user by username or email
    user = await db.db.users.find_one({"username": form_data.username})
    if not user:
         user = await db.db.users.find_one({"email": form_data.username})
         
    if not user or not security.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Convert ObjectId to string for token
    user_id = str(user["_id"])
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user_id, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(security.oauth2_scheme)):
    """获取当前登录用户信息"""
    from bson import ObjectId
    
    # 验证 token 并获取用户 ID
    payload = security.decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # 从数据库获取用户
    try:
        user = await db.db.users.find_one({"_id": ObjectId(user_id)})
    except:
        user = await db.db.users.find_one({"_id": user_id})
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Convert ObjectId to string
    user["_id"] = str(user["_id"])
    return user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    grade: str = Body(..., embed=True),
    token: str = Depends(security.oauth2_scheme)
):
    """更新当前用户信息（目前只支持更新年级）"""
    from bson import ObjectId
    
    # 验证 token 并获取用户 ID
    payload = security.decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # 验证年级值
    valid_grades = ["小学", "初中", "高中", "大学", "研究生"]
    if grade not in valid_grades:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid grade. Must be one of: {', '.join(valid_grades)}",
        )
    
    # 更新用户信息
    try:
        result = await db.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"grade": grade}}
        )
    except:
        result = await db.db.users.update_one(
            {"_id": user_id},
            {"$set": {"grade": grade}}
        )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or no changes made",
        )
    
    # 获取更新后的用户信息
    try:
        user = await db.db.users.find_one({"_id": ObjectId(user_id)})
    except:
        user = await db.db.users.find_one({"_id": user_id})
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Convert ObjectId to string
    user["_id"] = str(user["_id"])
    return user
