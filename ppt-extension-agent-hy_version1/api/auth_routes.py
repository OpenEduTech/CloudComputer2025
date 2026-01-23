from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from utils.auth import create_access_token, get_current_user
from services.user_service import register_user, authenticate_user

auth_router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None

class LoginRequest(BaseModel):
    username: str
    password: str

@auth_router.post("/auth/register")
async def register(req: RegisterRequest):
    try:
        user = register_user(req.username, req.password, req.email)
        return {"status": "success", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@auth_router.post("/auth/login")
async def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@auth_router.get("/users/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "email": current_user.get("email", ""), "goals": current_user.get("goals", {})}