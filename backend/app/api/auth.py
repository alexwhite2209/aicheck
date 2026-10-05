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
CONSENT_VERSION = "2026-10-03"
LOGIN_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")


class RegisterIn(BaseModel):
    login: str = Field(max_length=64)
    password: str = Field(min_length=8, max_length=128)
    consent: bool  # отдельное согласие на обработку ПД (ст. 9 152-ФЗ)
    marketing: bool = False  # отдельное согласие на рассылки (ст. 18 38-ФЗ), необязательное

    @field_validator("login")
    @classmethod
    def _login(cls, v: str) -> str:
        v = v.strip().lower()
        if not LOGIN_RE.match(v):
            raise ValueError("Логин: 3–32 символа, латинские буквы, цифры, «_», «.» или «-»")
        return v


class LoginIn(BaseModel):
    login: str = Field(max_length=64)
    password: str = Field(max_length=128)


def user_out(u: User) -> dict:
    return {"id": u.id, "login": u.login, "role": u.role, "created_at": u.created_at.isoformat(),
            "marketing_consent": u.marketing_consent, "unlimited": u.unlimited,
            "pro": bool(u.role == "admin" or u.unlimited)}


@router.post("/register")
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db), iph: str = Depends(request_ip_hash)):
    if not body.consent:
        raise HTTPException(422, "Для регистрации нужно согласие на обработку персональных данных")
    ok, _ = limiter.hit(f"reg:{iph}", 5, 3600)
    if not ok:
        raise HTTPException(429, "Слишком много попыток регистрации. Попробуйте позже.")
    if db.scalars(select(User).where(User.login == body.login)).first():
        raise HTTPException(409, "Пользователь с таким логином уже зарегистрирован")
    now = datetime.now(timezone.utc)
    u = User(login=body.login, password_hash=hash_password(body.password), consent_version=CONSENT_VERSION, consent_at=now,
             marketing_consent=body.marketing)
    db.add(u)
    db.flush()
    log_action(db, "auth.register", u.login, u.id, iph, consent_version=CONSENT_VERSION, marketing=body.marketing)
    db.commit()
    csrf = set_session(response, create_token(u.id, u.role))
    return {"user": user_out(u), "csrf": csrf}


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db), iph: str = Depends(request_ip_hash)):
    login_name = body.login.strip().lower()
    ok, _ = limiter.hit(f"login:{iph}", 10, 600)
    ok2, _ = limiter.hit(f"login-name:{login_name}", 8, 600)
    if not (ok and ok2):
        raise HTTPException(429, "Слишком много попыток входа. Подождите 10 минут.")
    u = db.scalars(select(User).where(User.login == login_name)).first()
    if not u or not u.is_active or not verify_password(body.password, u.password_hash):
        log_action(db, "auth.login_failed", login_name, "", iph)
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
