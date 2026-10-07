from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Audit, User
from ..pdf.report import build_pdf
from .audit import has_full_access
from .deps import current_user_optional

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/{audit_id}/pdf")
async def pdf(audit_id: str, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    a = db.get(Audit, audit_id) if audit_id.isalnum() else None
    if not a or a.status != "done":
        raise HTTPException(404, "Отчёт не найден")
    if not has_full_access(a, user):
        raise HTTPException(402, "PDF доступен в полном отчёте")
    from .audit import display_url
    data = {"url": display_url(a.url), "host": display_url(f"https://{a.host}/")[8:-1], "created_at": a.created_at.isoformat() if a.created_at else None,
            "finished_at": a.finished_at.isoformat() if a.finished_at else None, "score": a.score, "exposure": a.exposure,
            "counts": a.counts, "facts": a.facts, "results": a.results, "ai": a.ai, "snapshot": a.snapshot,
            "security": a.security, "registries": a.registries}
    content = await run_in_threadpool(build_pdf, data)
    fname = f"audit-{a.host}-{a.created_at:%Y%m%d}.pdf"
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fname}"', "Cache-Control": "private, no-store"})
