from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User


router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthInput(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


def _serialize_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "status": user.status}


@router.post("/register")
def register(payload: AuthInput, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="请输入有效邮箱")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已注册，请直接登录")
    user = User(email=email, name=(payload.name or "").strip() or None, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": _serialize_user(user)}


@router.post("/login")
def login(payload: AuthInput, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="用户已停用")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": _serialize_user(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": _serialize_user(user)}
