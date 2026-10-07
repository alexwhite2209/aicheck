from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..legal.engine import _articles, active_versions
from ..models import NormativeAct

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/rules")
def public_rules(db: Session = Depends(get_db)):
    """Публичная методика: действующие правила и их нормативные основания."""
    today = date.today()
    out = []
    for r, v in sorted(active_versions(db, today), key=lambda x: x[0].id):
        out.append({"id": r.id, "title": r.title, "category": r.category, "severity": v.severity, "version": v.version,
                    "effective_from": v.effective_from.isoformat(), "mode": v.mode,
                    "basis": [{"label": b["label"], "edition": b["edition"], "official_url": b["official_url"]} for b in _articles(db, v, today)]})
    acts = [{"id": a.id, "title": a.title, "edition": a.edition, "checked_at": a.checked_at.isoformat(), "official_url": a.official_url}
            for a in db.scalars(select(NormativeAct).order_by(NormativeAct.id))]
    return {"rules": out, "acts": acts}


@router.get("/security-methodology")
def security_methodology():
    """Карта навыков OWASP, по которым работает модуль безопасности."""
    from ..secaudit.skills import manifest
    return manifest()


@router.get("/config")
def public_config():
    s = get_settings()
    return {"paywall": s.paywall_active, "payments_enabled": s.payments_enabled, "max_pages": s.max_pages, "max_depth": s.max_depth}
