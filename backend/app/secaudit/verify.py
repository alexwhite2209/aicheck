"""Подтверждение владения доменом — чтобы активные проверки безопасности можно было делать законно.

Три способа (любой на выбор):
  file — положить файл /.well-known/norma-verify.txt с токеном;
  meta — добавить на главную <meta name="norma-verify" content="ТОКЕН">;
  dns  — добавить TXT-запись norma-verify=ТОКЕН (если на сервере есть dnspython).
"""
import re
import secrets

import httpx

from ..crawler.ssrf import UnsafeURLError, resolve_public


def new_token() -> str:
    return "norma-verify-" + secrets.token_hex(16)


def instructions(host: str, token: str) -> dict:
    return {
        "token": token,
        "methods": [
            {"id": "file", "title": "Файл на сайте (проще всего)",
             "steps": [f"Создайте файл по адресу https://{host}/.well-known/norma-verify.txt",
                       f"Впишите в него одну строку: {token}", "Нажмите «Проверить»."]},
            {"id": "meta", "title": "Мета-тег на главной",
             "steps": [f"Добавьте в раздел <head> главной страницы: <meta name=\"norma-verify\" content=\"{token}\">",
                       "Нажмите «Проверить»."]},
            {"id": "dns", "title": "DNS-запись (для технических специалистов)",
             "steps": [f"Добавьте TXT-запись для домена {host} со значением: {token}",
                       "Подождите обновления DNS (до часа) и нажмите «Проверить»."]},
        ],
    }


def _check_file(host: str, token: str) -> bool:
    try:
        resolve_public(host, 443)
        r = httpx.get(f"https://{host}/.well-known/norma-verify.txt", timeout=12, follow_redirects=True)
        return r.status_code == 200 and token in r.text[:2000]
    except Exception:
        return False


def _check_meta(host: str, token: str) -> bool:
    try:
        resolve_public(host, 443)
        r = httpx.get(f"https://{host}/", timeout=12, follow_redirects=True)
        if r.status_code != 200:
            return False
        m = re.search(r'<meta[^>]+name=["\']norma-verify["\'][^>]+content=["\']([^"\']+)["\']', r.text[:200000], re.I)
        return bool(m and m.group(1).strip() == token)
    except Exception:
        return False


def _check_dns(host: str, token: str) -> bool:
    try:
        import dns.resolver  # type: ignore
    except Exception:
        return False
    try:
        for rr in dns.resolver.resolve(host, "TXT"):
            if token in rr.to_text().strip('"'):
                return True
    except Exception:
        return False
    return False


def verify(host: str, token: str) -> str | None:
    """Возвращает способ подтверждения (file|meta|dns) или None."""
    host = (host or "").lower().lstrip(".")
    if not token:
        return None
    for method, fn in (("file", _check_file), ("meta", _check_meta), ("dns", _check_dns)):
        if fn(host, token):
            return method
    return None
