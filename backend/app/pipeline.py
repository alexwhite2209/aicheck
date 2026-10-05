"""Полный цикл аудита: краулер → факты → Rule Engine → AI → сохранение. Этапы пишутся в БД по мере выполнения."""
import asyncio
import logging
import traceback
from datetime import datetime, timezone

from .ai.openrouter import explain
from .crawler.browser import crawl
from .crawler.extract import build_facts
from .db import session_scope
from .legal import engine
from .models import Audit, Setting, Site

log = logging.getLogger(__name__)

STAGES = [
    ("connect", "Подключение"), ("https", "HTTPS"), ("html", "HTML"), ("dom", "DOM"), ("pages", "Обход страниц"),
    ("documents", "Документы"), ("forms", "Формы"), ("external", "Внешние сервисы"), ("cookies", "Cookies"),
    ("analytics", "Analytics"), ("pd", "Персональные данные"), ("legal", "Сопоставление с законодательством РФ"),
    ("report", "Формирование отчёта"),
]
DEEP_STAGES = [("security", "Проверка безопасности"), ("registries", "Проверка по реестрам")]


def stages_for(deep: bool) -> list[dict]:
    items = STAGES[:-1] + DEEP_STAGES + STAGES[-1:] if deep else STAGES
    return [{"key": k, "label": l, "status": "pending", "detail": "", "at": None} for k, l in items]
FRIENDLY_ERRORS = [
    ("ERR_NAME_NOT_RESOLVED", "Домен не найден. Проверьте адрес сайта."),
    ("ERR_CONNECTION_REFUSED", "Сайт отклонил подключение."),
    ("ERR_CONNECTION_TIMED_OUT", "Сайт не ответил вовремя."),
    ("ERR_TIMED_OUT", "Сайт не ответил вовремя."),
    ("Timeout", "Сайт не ответил вовремя."),
    ("ERR_TUNNEL_CONNECTION_FAILED", "Подключение заблокировано защитой сервиса (адрес не прошёл проверку безопасности)."),
    ("ERR_PROXY", "Подключение заблокировано защитой сервиса."),
    ("HTTP 4", "Сайт вернул ошибку доступа."),
    ("HTTP 5", "Сайт вернул ошибку сервера."),
]


def initial_stages(deep: bool = False) -> list[dict]:
    return stages_for(deep)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _update_stage(audit_id: str, key: str, status: str, detail: str = "") -> None:
    with session_scope() as db:
        a = db.get(Audit, audit_id)
        if not a:
            return
        stages = [dict(s) for s in (a.stages or initial_stages())]
        for s in stages:
            if s["key"] == key:
                s["status"], s["detail"], s["at"] = status, detail[:200], _now()
        a.stages = stages


def _friendly(err: str) -> str:
    for needle, text in FRIENDLY_ERRORS:
        if needle in err:
            return text
    return "Не удалось открыть сайт."


def _trim(facts: dict) -> dict:
    for d in facts.get("documents", []):
        if d.get("excerpt"):
            d["excerpt"] = d["excerpt"][:20000]
    return facts


def run_audit(audit_id: str) -> None:
    with session_scope() as db:
        a = db.get(Audit, audit_id)
        if not a or a.status not in ("queued", "running"):
            return
        deep = bool(a.deep)
        a.status, a.started_at, a.stages = "running", datetime.now(timezone.utc), initial_stages(deep)
        url = a.url

    async def stage(key: str, status: str, detail: str) -> None:
        _update_stage(audit_id, key, status, detail)

    try:
        raw = asyncio.run(crawl(url, stage, deep=deep))
        if raw.get("fatal") and not raw.get("pages"):
            with session_scope() as db:
                a = db.get(Audit, audit_id)
                a.status, a.finished_at = "failed", datetime.now(timezone.utc)
                a.error = _friendly(raw["fatal"])
                a.facts = {"crawl": {"fatal": raw["fatal"], "errors": raw.get("errors", [])[:5], "blocked": raw.get("blocked", [])[:5]}}
                stages = [dict(s) for s in a.stages]
                for s in stages:
                    if s["status"] in ("pending", "running"):
                        s["status"] = "error" if s["status"] == "running" else "skipped"
                a.stages = stages
            return

        facts = build_facts(raw, url, stage=lambda k, s, d: _update_stage(audit_id, k, s, d))

        _update_stage(audit_id, "legal", "running")
        with session_scope() as db:
            res = engine.run(db, facts)
        c = res["counts"]
        _update_stage(audit_id, "legal", "done", f"Правил применено: {len(res['results']) - c['na']}, проблем: {c['fail']}, требуют внимания: {c['review']}")

        security = registries = None
        if deep:
            _update_stage(audit_id, "security", "running")
            try:
                from .secaudit.engine import run_security
                sec_input = {"main_headers": raw.get("main_headers") or {}, "pages_raw": raw.get("pages", []),
                             "cookies_raw": raw.get("cookies", []), "https": facts.get("https", {}),
                             "collected": (raw.get("security") or {}), "external_js": (raw.get("security") or {}).get("external_js", [])}
                with session_scope() as db:
                    security = run_security(db, facts, sec_input)
                sc = security["counts"]
                _update_stage(audit_id, "security", "done", f"Проверок: {len(security['findings'])}, проблем: {sc['fail']}, внимание: {sc['review']}")
            except Exception as e:
                log.exception("security failed")
                _update_stage(audit_id, "security", "error", str(e)[:120])
            _update_stage(audit_id, "registries", "running")
            try:
                from .secaudit.registries import run_registries
                registries = run_registries(facts)
                dom = registries.get("domain", {})
                _update_stage(audit_id, "registries", "done", f"Домен: {dom.get('age_years', '?')} лет" if dom.get("registered") else "Проверено")
            except Exception as e:
                log.exception("registries failed")
                _update_stage(audit_id, "registries", "error", str(e)[:120])

        _update_stage(audit_id, "report", "running")
        with session_scope() as db:
            ai_settings = (db.get(Setting, "ai").value if db.get(Setting, "ai") else {})
        ai = explain(facts, res["results"], ai_settings)
        with session_scope() as db:
            a = db.get(Audit, audit_id)
            a.facts = _trim(facts)
            a.results = res["results"]
            a.score = res["score"]
            a.counts = res["counts"]
            a.exposure = res["exposure"]
            a.snapshot = res["snapshot"]
            a.ai = ai
            a.security = security
            a.registries = registries
            a.site_type = facts.get("site_type")
            a.status, a.finished_at = "done", datetime.now(timezone.utc)
            if a.site_id:
                site = db.get(Site, a.site_id)
                if site:
                    site.last_audit_id = a.id
        _update_stage(audit_id, "report", "done", "AI-объяснения добавлены" if ai.get("used") else "Отчёт сформирован по шаблонам правил")
    except Exception as e:
        log.error("audit %s failed: %s\n%s", audit_id, e, traceback.format_exc())
        with session_scope() as db:
            a = db.get(Audit, audit_id)
            if a:
                a.status, a.finished_at = "failed", datetime.now(timezone.utc)
                a.error = "Внутренняя ошибка при проверке сайта. Попробуйте повторить позже."
                stages = [dict(s) for s in (a.stages or [])]
                for s in stages:
                    if s["status"] == "running":
                        s["status"] = "error"
                    elif s["status"] == "pending":
                        s["status"] = "skipped"
                a.stages = stages
