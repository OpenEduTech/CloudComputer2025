from typing import Optional, Dict, Any
from pathlib import Path
import json
from utils.auth import get_password_hash, verify_password

DATA_PATH = Path("./output/users.json")

def _load() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        return {"users": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data: Dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    data = _load()
    for u in data["users"]:
        if u["username"] == username:
            return u
    return None

def register_user(username: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
    if get_user_by_username(username):
        raise ValueError("用户已存在")
    hashed = get_password_hash(password)
    user = {"username": username, "password_hash": hashed, "email": email or "", "goals": {}, "preferences": {}, "plans": []}
    data = _load()
    data["users"].append(user)
    _save(data)
    return {"username": username, "email": user["email"]}

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user

def set_goals(username: str, goals: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    for u in data["users"]:
        if u["username"] == username:
            u["goals"] = goals
            _save(data)
            return u["goals"]
    raise ValueError("用户不存在")

def get_goals(username: str) -> Dict[str, Any]:
    user = get_user_by_username(username)
    return user.get("goals", {}) if user else {}

def save_plan(username: str, plan: Dict[str, Any]) -> None:
    data = _load()
    for u in data["users"]:
        if u["username"] == username:
            if "plans" not in u:
                u["plans"] = []
            u["plans"].append(plan)
            _save(data)
            return
    raise ValueError("用户不存在")

def get_plans(username: str) -> list:
    user = get_user_by_username(username)
    if user:
        return user.get("plans", [])
    return []