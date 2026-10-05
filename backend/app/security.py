"""Пароли (scrypt), JWT в httpOnly-cookie, CSRF (double submit), хеширование IP."""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Request, Response

from .config import get_settings

SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_b64, dk_b64 = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except Exception:
        return False


def _secret() -> str:
    s = get_settings()
    if s.is_prod and (not s.jwt_secret or s.jwt_secret == "change-me-in-production" or len(s.jwt_secret) < 32):
        raise RuntimeError("JWT_SECRET должен быть задан (не короче 32 символов) в production")
    return s.jwt_secret


def create_token(user_id: str, role: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "role": role, "iat": now, "exp": now + timedelta(hours=s.jwt_ttl_hours), "jti": secrets.token_hex(8)}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def set_session(response: Response, token: str) -> str:
    s = get_settings()
    csrf = secrets.token_urlsafe(24)
    max_age = s.jwt_ttl_hours * 3600
    response.set_cookie(SESSION_COOKIE, token, max_age=max_age, httponly=True, secure=s.is_prod, samesite="lax", path="/")
    response.set_cookie(CSRF_COOKIE, csrf, max_age=max_age, httponly=False, secure=s.is_prod, samesite="lax", path="/")
    return csrf


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def csrf_ok(request: Request) -> bool:
    """Для запросов с cookie-сессией меняющие методы требуют заголовок, совпадающий с CSRF-cookie."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    if SESSION_COOKIE not in request.cookies:
        return True  # без сессии нет «окружающих» полномочий
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    return bool(cookie) and hmac.compare_digest(cookie, header)


def client_ip(request: Request) -> str:
    s = get_settings()
    if s.trust_proxy_headers:
        # X-Real-IP выставляет наш внешний прокси (nginx/Caddy) и не принимает от клиента
        xri = request.headers.get("x-real-ip")
        if xri:
            return xri.strip()
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def ip_hash(ip: str) -> str:
    s = get_settings()
    key = (s.ip_hash_secret or s.jwt_secret).encode()
    return hmac.new(key, ip.encode(), hashlib.sha256).hexdigest()[:32]
