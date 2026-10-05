from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_log import log_action
from ..config import get_settings
from ..crawler.ssrf import UnsafeURLError, validate_target
from ..db import get_db
from ..models import Audit, Site, User
from ..pipeline import initial_stages
from ..ratelimit import limiter
from ..tasks import enqueue_audit
from .deps import current_user_optional, request_ip_hash

router = APIRouter(prefix="/api/audit", tags=["audit"])
settings = get_settings()


class AuditIn(BaseModel):
    url: str = Field(min_length=3, max_length=2048)
    security: bool = True  # собирать данные платного модуля безопасности и реестров


def is_pro(user: User | None) -> bool:
    """Безлимитный доступ: администратор или пользователь, которому админ выдал unlimited."""
    return bool(user and (user.role == "admin" or user.unlimited))


def has_full_access(a: Audit, user: User | None) -> bool:
    """Доступ к юридическому полному отчёту (доказательства, нормы, AI, PDF)."""
    if not settings.paywall_active or is_pro(user):
        return True
    return bool(a.paid_full)


def has_security_access(a: Audit, user: User | None) -> bool:
    """Security Skills и реестры входят в «Полный аудит» — отдельной покупки нет."""
    return has_full_access(a, user)


def _allowlist() -> set[str] | None:
    if settings.is_prod or not settings.crawler_test_allowlist:
        return None
    return set(filter(None, settings.crawler_test_allowlist.split(",")))


@router.post("")
async def create_audit(body: AuditIn, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional),
                       iph: str = Depends(request_ip_hash)):
    try:
        url = await run_in_threadpool(validate_target, body.url, _allowlist())
    except UnsafeURLError as e:
        raise HTTPException(422, str(e))
    host = urlsplit(url).hostname or ""
    # повторный запуск того же адреса, пока предыдущая проверка идёт
    q = select(Audit).where(Audit.url == url, Audit.status.in_(("queued", "running")),
                            Audit.created_at > datetime.now(timezone.utc) - timedelta(minutes=10))
    q = q.where(Audit.user_id == user.id) if user else q.where(Audit.ip_hash == iph)
    existing = db.scalars(q).first()
    if existing:
        return {"id": existing.id, "status": existing.status, "url": existing.url}
    pro = is_pro(user)
    if not pro:  # безлимитный доступ (админ / выданный unlimited) не ограничивается по частоте
        if user:
            ok, retry = limiter.hit(f"user:{user.id}", settings.rate_limit_user_hour, 3600)
        else:
            ok, retry = limiter.hit(f"ip:{iph}", settings.rate_limit_anon_hour, 3600)
            if ok:
                ok, retry = limiter.hit(f"ipd:{iph}", settings.rate_limit_anon_day, 86400)
        if not ok:
            raise HTTPException(429, f"Слишком много проверок. Повторите через {max(retry // 60, 1)} мин. или войдите в аккаунт.")
        ok, _ = limiter.hit(f"host:{host}", 6, 3600)  # защита проверяемых сайтов от массового сканирования
        if not ok:
            raise HTTPException(429, "Этот сайт уже проверяли несколько раз за последний час. Попробуйте позже.")
    site_id = None
    if user:
        site = db.scalars(select(Site).where(Site.user_id == user.id, Site.host == host)).first()
        site_id = site.id if site else None
    # deep-режим: данные безопасности и реестров собираем всегда (безопасные GET), а показ — по доступу (покупка/безлимит)
    deep = bool(body.security)
    a = Audit(url=url, host=host, user_id=user.id if user else None, site_id=site_id, status="queued",
              stages=initial_stages(deep), deep=deep, ip_hash=iph)
    db.add(a)
    log_action(db, "audit.create", user.login if user else "anonymous", url, iph)
    db.commit()
    enqueue_audit(a.id)
    return {"id": a.id, "status": a.status, "url": a.url}


def _get(db: Session, audit_id: str) -> Audit:
    if not audit_id.isalnum() or len(audit_id) > 32:
        raise HTTPException(404, "Проверка не найдена")
    a = db.get(Audit, audit_id)
    if not a:
        raise HTTPException(404, "Проверка не найдена")
    return a


def display_url(url: str) -> str:
    """Кириллический домен для показа пользователю (xn--... → пиломатериал-52.рф)."""
    try:
        import idna
        parts = urlsplit(url)
        host = parts.hostname or ""
        uni = idna.decode(host) if "xn--" in host else host
        return url.replace(host, uni, 1)
    except Exception:
        return url


def summary(a: Audit, user: User | None) -> dict:
    exp = a.exposure or {}
    return {
        "id": a.id, "url": display_url(a.url), "host": display_url(f"https://{a.host}/")[8:-1], "status": a.status, "error": a.error, "site_type": a.site_type,
        "created_at": a.created_at.isoformat() if a.created_at else None, "finished_at": a.finished_at.isoformat() if a.finished_at else None,
        "score": a.score, "counts": a.counts,
        "exposure": {"state": exp.get("state"), "min": exp.get("min"), "max": exp.get("max"), "subject_ru": exp.get("subject_ru")} if exp else None,
        "full_access": has_full_access(a, user), "paywall": settings.paywall_active, "owned": bool(user and a.user_id == user.id),
        "deep": bool(a.deep), "recheck_of": a.recheck_of,
    }


@router.get("/{audit_id}")
def get_audit(audit_id: str, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    return summary(_get(db, audit_id), user)


@router.get("/{audit_id}/status")
def get_status(audit_id: str, db: Session = Depends(get_db)):
    a = _get(db, audit_id)
    return {"id": a.id, "url": display_url(a.url), "status": a.status, "stages": a.stages or [], "error": a.error}


@router.get("/{audit_id}/result")
def get_result(audit_id: str, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    a = _get(db, audit_id)
    if a.status != "done":
        raise HTTPException(409, "Проверка ещё не завершена" if a.status in ("queued", "running") else (a.error or "Проверка завершилась ошибкой"))
    full = has_full_access(a, user)
    facts = a.facts or {}
    results = a.results or []
    ai = a.ai or {}
    if not full:
        # бесплатный режим: статусы, факты, нормы (ссылки) и базовые рекомендации без доказательств и AI-объяснений
        results = [{**{k: v for k, v in r.items() if k not in ("evidence", "details")},
                    "evidence": [], "basis": [{k: b[k] for k in ("id", "label", "act", "article", "part", "paragraph", "title", "edition", "official_url")} for b in r["basis"]]}
                   for r in results]
        ai = {"used": ai.get("used"), "summary": ai.get("summary"), "items": {}, "locked": True}
    public_facts = {
        "site_type": facts.get("site_type"), "site_type_ru": facts.get("site_type_ru"), "mode": facts.get("mode"),
        "final_url": facts.get("final_url"), "https": facts.get("https"), "pages": facts.get("pages", []),
        "cookie_stats": facts.get("cookie_stats"), "cookie_banner": bool(facts.get("cookie_banner")),
        "external_services": [{k: s[k] for k in ("service_id", "name", "type", "type_ru", "purpose", "owner", "jurisdiction", "domains", "found_on")} for s in facts.get("external_services", [])],
        "unknown_domains": facts.get("unknown_domains", []),
        "documents": [{k: d.get(k) for k in ("kind", "kind_ru", "url", "link_text", "accessible", "status", "source", "text_len")} for d in facts.get("documents", [])],
        "forms": [{k: f.get(k) for k in ("ref", "page", "purpose", "pd_kinds", "special_kinds", "has_pd", "has_consent_mechanism", "external_handler")}
                  | {"fields": f.get("fields", []) if full else []} for f in facts.get("forms", [])],
        "company_details": facts.get("company_details"), "contacts": facts.get("contacts") if full else None,
        "ecommerce_signals": facts.get("ecommerce_signals", []), "crawl": facts.get("crawl"),
        "cookies": facts.get("cookies", []) if full else [],
    }
    sec_access = has_security_access(a, user)
    security = registries = None
    if a.deep and sec_access:  # в бесплатной «Экспресс-проверке» безопасности и реестров нет
        security = a.security
        registries = a.registries
    return {**summary(a, user), "exposure_full": a.exposure, "results": results, "facts": public_facts, "ai": ai,
            "snapshot": a.snapshot, "security": security, "registries": registries, "deep": a.deep,
            "comparison": _comparison(db, a) if full else None,
            "security_access": sec_access, "disclaimer": DISCLAIMER}


def _comparison(db: Session, a: Audit) -> dict | None:
    """«Повторная проверка»: что изменилось относительно предыдущего результата."""
    prev = db.get(Audit, a.recheck_of) if a.recheck_of else None
    if not prev or prev.status != "done":
        return None
    old = {r["rule_id"]: r for r in (prev.results or [])}
    changes, resolved, appeared, unchanged = [], 0, 0, 0
    for r in (a.results or []):
        o = old.get(r["rule_id"])
        if not o or o.get("status") == r.get("status"):
            if r.get("status") == "FAIL":
                unchanged += 1
            continue
        if o.get("status") == "FAIL":
            resolved += 1
        if r.get("status") == "FAIL":
            appeared += 1
        changes.append({"rule_id": r["rule_id"], "title": r.get("title", ""), "was": o.get("status"), "now": r.get("status")})
    return {"previous_id": prev.id, "previous_at": prev.created_at.isoformat() if prev.created_at else None,
            "score_before": prev.score, "score_after": a.score,
            "security_before": (prev.security or {}).get("score"), "security_after": (a.security or {}).get("score"),
            "resolved": resolved, "new_issues": appeared, "unchanged_issues": unchanged, "changes": changes}


DISCLAIMER = ("Автоматизированный аудит является информационным инструментом и не является юридическим заключением. "
              "Результаты основаны на данных, доступных сервису в момент проверки, и не заменяют консультацию квалифицированного специалиста.")
