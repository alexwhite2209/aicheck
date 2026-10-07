import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_log import log_action
from ..db import get_db
from ..models import User
from ..ratelimit import limiter
from ..security import clear_session, create_token, hash_password, set_session, verify_password
from .deps import current_user, request_ip_hash

router = APIRouter(prefix="/api/auth", tags=["auth"])
CONSENT_VERSION = "2026-10-07"
LOGIN_RE = re.compile(r"^[a-zа-яё0-9_.-]{3,32}$")


def normalize_login(v: str) -> str:
    return v.strip().lower()


class RegisterIn(BaseModel):
    login: str = Field(max_length=64)
    password: str = Field(min_length=8, max_length=128)
    consent: bool  # отдельное согласие на обработку ПД (ст. 9 152-ФЗ)

    @field_validator("login")
    @classmethod
    def _login(cls, v: str) -> str:
        v = normalize_login(v)
        if not LOGIN_RE.match(v):
            raise ValueError("Логин: от 3 до 32 символов — буквы, цифры, точка, дефис или подчёркивание")
        return v


class LoginIn(BaseModel):
    login: str = Field(max_length=64)
    password: str = Field(max_length=128)


def user_out(u: User) -> dict:
    return {"id": u.id, "login": u.login, "role": u.role, "created_at": u.created_at.isoformat(),
            "unlimited": u.unlimited, "pro": bool(u.role == "admin" or u.unlimited)}


@router.post("/register")
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db), iph: str = Depends(request_ip_hash)):
    if not body.consent:
        raise HTTPException(422, "Для регистрации нужно согласие на обработку персональных данных")
    ok, _ = limiter.hit(f"reg:{iph}", 5, 3600)
    if not ok:
        raise HTTPException(429, "Слишком много попыток регистрации. Попробуйте позже.")
    if db.scalars(select(User).where(User.login == body.login)).first():
        raise HTTPException(409, "Этот логин уже занят")
    now = datetime.now(timezone.utc)
    u = User(login=body.login, password_hash=hash_password(body.password), consent_version=CONSENT_VERSION, consent_at=now)
    db.add(u)
    db.flush()
    log_action(db, "auth.register", u.login, u.id, iph, consent_version=CONSENT_VERSION)
    db.commit()
    csrf = set_session(response, create_token(u.id, u.role))
    return {"user": user_out(u), "csrf": csrf}


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db), iph: str = Depends(request_ip_hash)):
    login_ = normalize_login(body.login)
    ok, _ = limiter.hit(f"login:{iph}", 10, 600)
    ok2, _ = limiter.hit(f"login-name:{login_}", 8, 600)
    if not (ok and ok2):
        raise HTTPException(429, "Слишком много попыток входа. Подождите 10 минут.")
    u = db.scalars(select(User).where(User.login == login_)).first()
    if not u or not u.is_active or not verify_password(body.password, u.password_hash):
        log_action(db, "auth.login_failed", login_, "", iph)
        db.commit()
        raise HTTPException(401, "Неверный логин или пароль")
    log_action(db, "auth.login", u.login, u.id, iph)
    db.commit()
    csrf = set_session(response, create_token(u.id, u.role))
    return {"user": user_out(u), "csrf": csrf}


@router.post("/logout")
def logout(response: Response):
    clear_session(response)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"user": user_out(user)}
