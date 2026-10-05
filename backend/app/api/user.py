from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..audit_log import log_action
from ..crawler.ssrf import UnsafeURLError, normalize_url
from ..db import get_db
from ..models import Audit, Payment, Site, User
from ..security import clear_session
from .auth import user_out
from .deps import current_user, request_ip_hash

router = APIRouter(prefix="/api/user", tags=["user"])


def audit_row(a: Audit) -> dict:
    exp = a.exposure or {}
    return {"id": a.id, "url": a.url, "host": a.host, "status": a.status, "score": a.score,
            "exposure_min": exp.get("min"), "exposure_max": exp.get("max"), "exposure_state": exp.get("state"),
            "counts": a.counts, "created_at": a.created_at.isoformat(), "site_id": a.site_id, "paid_full": a.paid_full}


@router.get("/audits")
def my_audits(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Audit).where(Audit.user_id == user.id).order_by(Audit.created_at.desc()).limit(200)).all()
    return {"audits": [audit_row(a) for a in rows]}


@router.post("/audits/{audit_id}/claim")
def claim(audit_id: str, db: Session = Depends(get_db), user: User = Depends(current_user), iph: str = Depends(request_ip_hash)):
    """Сохранить в аккаунт проверку, запущенную до входа (только с того же устройства/IP)."""
    a = db.get(Audit, audit_id)
    if not a:
        raise HTTPException(404, "Проверка не найдена")
    if a.user_id and a.user_id != user.id:
        raise HTTPException(403, "Проверка принадлежит другому пользователю")
    if not a.user_id and a.ip_hash != iph:
        raise HTTPException(403, "Сохранить можно только проверку, запущенную с этого устройства")
    site = db.scalars(select(Site).where(Site.user_id == user.id, Site.host == a.host)).first()
    if not site:
        site = Site(user_id=user.id, url=a.url, host=a.host)
        db.add(site)
        db.flush()
    a.user_id, a.site_id = user.id, site.id
    if a.status == "done":
        site.last_audit_id = a.id
    db.commit()
    return {"ok": True, "site_id": site.id}


class SiteIn(BaseModel):
    url: str = Field(max_length=2048)


class SitePatch(BaseModel):
    monitoring: str = Field(pattern="^(off|daily|weekly|monthly)$")


@router.get("/sites")
def sites(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Site).where(Site.user_id == user.id).order_by(Site.created_at.desc())).all()
    out = []
    for s in rows:
        audits = db.scalars(select(Audit).where(Audit.site_id == s.id, Audit.status == "done").order_by(Audit.created_at.desc()).limit(10)).all()
        out.append({"id": s.id, "url": s.url, "host": s.host, "monitoring": s.monitoring, "created_at": s.created_at.isoformat(),
                    "audits": [audit_row(a) for a in audits]})
    return {"sites": out}


@router.post("/sites")
async def add_site(body: SiteIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        url = await run_in_threadpool(normalize_url, body.url)
    except UnsafeURLError as e:
        raise HTTPException(422, str(e))
    host = urlsplit(url).hostname or ""
    if db.scalars(select(Site).where(Site.user_id == user.id, Site.host == host)).first():
        raise HTTPException(409, "Сайт уже добавлен")
    s = Site(user_id=user.id, url=url, host=host)
    db.add(s)
    db.commit()
    return {"id": s.id, "url": s.url, "host": s.host}


@router.put("/sites/{site_id}")
def patch_site(site_id: str, body: SitePatch, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(Site, site_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Сайт не найден")
    s.monitoring = body.monitoring
    db.commit()
    return {"ok": True, "monitoring": s.monitoring}


@router.delete("/sites/{site_id}")
def delete_site(site_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(Site, site_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Сайт не найден")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.get("/payments")
def payments(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())).all()
    return {"payments": [{"id": p.id, "product": p.product, "amount_rub": p.amount_rub, "status": p.status, "audit_id": p.audit_id,
                          "created_at": p.created_at.isoformat()} for p in rows]}


@router.get("/export")
def export(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Выгрузка данных пользователя (право субъекта на доступ к своим ПД, ст. 14 152-ФЗ)."""
    audits = db.scalars(select(Audit).where(Audit.user_id == user.id)).all()
    sites_ = db.scalars(select(Site).where(Site.user_id == user.id)).all()
    return {"user": user_out(user) | {"consent_version": user.consent_version, "consent_at": user.consent_at.isoformat() if user.consent_at else None},
            "sites": [{"url": s.url, "monitoring": s.monitoring} for s in sites_], "audits": [audit_row(a) for a in audits]}


@router.delete("")
def delete_account(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user), iph: str = Depends(request_ip_hash)):
    """Удаление аккаунта и связанных данных (отзыв согласия)."""
    db.execute(delete(Audit).where(Audit.user_id == user.id))
    log_action(db, "user.delete", user.id, user.id, iph)
    db.delete(user)
    db.commit()
    clear_session(response)
    return {"ok": True}
