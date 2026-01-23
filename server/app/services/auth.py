"""
PatPat-Inconsistency-Hunter 用户认证服务
提供用户注册、登录、JWT认证等功能
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..utils.logger import logger
from ..models.database import User


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
SECRET_KEY = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "patpat-secret-key-please-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天


# ==================== Pydantic 模型 ====================

class UserCreate(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    display_name: Optional[str] = Field(None, max_length=64, description="显示名称")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    avatar_color: str
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    """Token数据"""
    user_id: str
    username: str


# ==================== 工具函数 ====================

def _truncate_password(password: str) -> str:
    """截断密码到72字节（bcrypt限制）"""
    return password.encode('utf-8')[:72].decode('utf-8', errors='ignore')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(_truncate_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(_truncate_password(password))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """解码访问令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, username=username)
    except JWTError:
        return None


def generate_user_id() -> str:
    """生成用户ID"""
    return f"user_{uuid.uuid4().hex[:16]}"


def generate_avatar_color() -> str:
    """生成随机头像颜色"""
    import random
    colors = [
        "#ef4444", "#f97316", "#eab308", "#22c55e",
        "#14b8a6", "#0ea5e9", "#6366f1", "#a855f7",
        "#ec4899", "#f43f5e",
    ]
    return random.choice(colors)


# ==================== 用户服务类 ====================

class AuthService:
    """
    用户认证服务
    
    提供用户注册、登录、验证等功能
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def register(self, user_data: UserCreate) -> User:
        """
        用户注册
        
        Args:
            user_data: 注册信息
        
        Returns:
            创建的用户对象
        
        Raises:
            ValueError: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        existing_user = await self.get_user_by_username(user_data.username)
        if existing_user:
            raise ValueError("用户名已存在")
        
        # 检查邮箱是否已存在
        if user_data.email:
            existing_email = await self.get_user_by_email(user_data.email)
            if existing_email:
                raise ValueError("邮箱已被注册")
        
        # 创建用户
        user = User(
            user_id=generate_user_id(),
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            display_name=user_data.display_name or user_data.username,
            avatar_color=generate_avatar_color(),
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"新用户注册: {user.username} ({user.user_id})")
        return user
    
    async def login(self, login_data: UserLogin) -> tuple[User, str]:
        """
        用户登录
        
        Args:
            login_data: 登录信息
        
        Returns:
            (用户对象, 访问令牌)
        
        Raises:
            ValueError: 用户名或密码错误
        """
        # 查找用户
        user = await self.get_user_by_username(login_data.username)
        if not user:
            raise ValueError("用户名或密码错误")
        
        # 验证密码
        if not verify_password(login_data.password, user.password_hash):
            raise ValueError("用户名或密码错误")
        
        # 检查是否激活
        if not user.is_active:
            raise ValueError("账号已被禁用")
        
        # 更新最后登录时间
        user.last_login_at = datetime.now()
        await self.db.commit()
        
        # 生成访问令牌
        access_token = create_access_token(
            data={"sub": user.user_id, "username": user.username}
        )
        
        logger.info(f"用户登录: {user.username}")
        return user, access_token
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据用户ID获取用户"""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """更新用户信息"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if not verify_password(old_password, user.password_hash):
            return False
        
        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
        
        logger.info(f"用户修改密码: {user.username}")
        return True
    
    async def validate_token(self, token: str) -> Optional[User]:
        """
        验证访问令牌
        
        Args:
            token: 访问令牌
        
        Returns:
            用户对象或None
        """
        token_data = decode_access_token(token)
        if not token_data:
            return None
        
        user = await self.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            return None
        
        return user


def user_to_response(user: User) -> UserResponse:
    """将User对象转换为UserResponse"""
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        avatar_color=user.avatar_color,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
    )

