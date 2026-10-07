"""Сбор данных для модуля безопасности во время обхода. Только безопасные GET через egress-прокси браузера.

Запускается, когда задан deep-режим. Ничего не эксплуатирует: читает заголовки, пробует короткий фиксированный
список типовых адресов утечек и делает один CORS-запрос с заголовком Origin.
"""
import time
from urllib.parse import urlsplit

from . import signatures as sig

PROBE_ORIGIN = "https://norma-audit-probe.example"


async def collect_security(ctx, base: str, deadline: float) -> dict:
    out: dict = {"exposure": [], "cors": None, "security_txt": False, "probe_origin": PROBE_ORIGIN}

    # --- типовые адреса утечек (GET, небольшой таймаут, не следуем на кастомные редиректы)
    for path, pid, title, severity in sig.EXPOSURE_PATHS:
        if time.monotonic() > deadline - 8:
            break
        url = base + path
        try:
            r = await ctx.request.get(url, timeout=8000, max_redirects=0, fail_on_status_code=False)
            status = r.status
            body = ""
            if status == 200:
                try:
                    body = (await r.text())[:4000]
                except Exception:
                    body = ""
            await r.dispose()
        except Exception:
            continue
        confirm = sig.EXPOSURE_CONFIRM.get(pid, lambda b: True)
        if status == 200 and confirm(body):
            if pid == "securitytxt":
                out["security_txt"] = True
                continue
            if pid == "verify":
                continue
            out["exposure"].append({"id": pid, "path": path, "title": title, "severity": severity, "status": status})

    # --- CORS: запрос с Origin, читаем отражение ACAO/ACAC
    if time.monotonic() < deadline - 6:
        try:
            r = await ctx.request.get(base + "/", headers={"Origin": PROBE_ORIGIN}, timeout=8000, max_redirects=2, fail_on_status_code=False)
            h = await r.all_headers()
            out["cors"] = {"acao": h.get("access-control-allow-origin", ""), "acac": h.get("access-control-allow-credentials", "")}
            await r.dispose()
        except Exception:
            out["cors"] = None
    return out


async def fetch_external_js(ctx, pages: list[dict], site_host: str, deadline: float, limit: int = 6) -> list[dict]:
    """Скачать несколько внешних JS того же домена для поиска секретов (GET, ограниченно)."""
    def reg(host: str) -> str:
        p = host.split(".")
        return ".".join(p[-2:]) if len(p) >= 2 else host
    seen: set[str] = set()
    out: list[dict] = []
    for p in pages:
        for src in p.get("scripts", []):
            if len(out) >= limit or time.monotonic() > deadline - 6:
                return out
            h = (urlsplit(src).hostname or "").lower()
            if not h or reg(h) != reg(site_host) or src in seen:
                continue
            seen.add(src)
            try:
                r = await ctx.request.get(src, timeout=8000, max_redirects=2, fail_on_status_code=False)
                if r.status == 200:
                    body = (await r.text())[:200000]
                    out.append({"url": src, "body": body})
                await r.dispose()
            except Exception:
                continue
    return out
