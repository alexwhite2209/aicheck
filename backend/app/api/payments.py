"""Оплата через ЮKassa. Цены — в БД. Статус платежа всегда перепроверяется запросом к API ЮKassa."""
import re
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_log import log_action
from ..config import get_settings
from ..db import get_db
from ..models import Audit, Payment, Price, User
from ..pipeline import initial_stages
from ..tasks import enqueue_audit
from .deps import current_user

router = APIRouter(tags=["payments"])
YK_API = "https://api.yookassa.ru/v3"
settings = get_settings()


@router.get("/api/prices")
def public_prices(db: Session = Depends(get_db)):
    return {"payments_enabled": settings.payments_enabled, "paywall": settings.paywall_active,
            "prices": [{"code": p.code, "title": p.title, "description": p.description, "amount_rub": p.amount_rub}
                       for p in db.scalars(select(Price).where(Price.active.is_(True)).order_by(Price.sort))]}


RECEIPT_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,24}$")


class PayIn(BaseModel):
    product: str = Field(pattern=r"^[a-z_]{3,32}$")
    audit_id: str | None = Field(default=None, max_length=32)
    # вход — только логин и пароль; email нужен лишь для кассового чека (54-ФЗ) и нигде не сохраняется
    receipt_email: str = Field(default="", max_length=254)


def _yk_auth() -> tuple[str, str]:
    return settings.yookassa_shop_id, settings.yookassa_secret_key


def _apply(db: Session, p: Payment) -> str | None:
    """Применить оплаченный тариф. Для «Повторной проверки» создаёт новую проверку и возвращает её id."""
    if not p.audit_id:
        return None
    a = db.get(Audit, p.audit_id)
    if not a:
        return None
    if p.product == "full_audit":
        a.paid_full = True  # право + Security Skills + реестры + PDF открываются одним флагом
        return None
    if p.product == "recheck":
        new = Audit(url=a.url, host=a.host, user_id=p.user_id, site_id=a.site_id, status="queued", stages=initial_stages(True),
                    deep=True, ip_hash=a.ip_hash, paid_full=True, recheck_of=a.id)
        db.add(new)
        db.flush()
        p.audit_id = new.id  # страница оплаты перейдёт на новую проверку
        return new.id
    return None


@router.post("/api/payments/create")
def create_payment(body: PayIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not settings.payments_enabled:
        raise HTTPException(503, "Онлайн-оплата не настроена")
    price = db.get(Price, body.product)
    if not price or not price.active:
        raise HTTPException(404, "Тариф не найден")
    if body.product not in ("full_audit", "recheck"):
        raise HTTPException(404, "Тариф не найден")
    a = db.get(Audit, body.audit_id or "")
    if not a or a.status != "done":
        raise HTTPException(422, "Проверка не найдена или не завершена")
    if a.user_id and a.user_id != user.id:
        raise HTTPException(403, "Это не ваша проверка")
    if body.product == "full_audit" and a.paid_full:
        raise HTTPException(409, "Полный аудит уже оплачен")
    receipt_email = body.receipt_email.strip()
    if not RECEIPT_EMAIL_RE.match(receipt_email):
        raise HTTPException(422, "Укажите email для кассового чека")
    p = Payment(user_id=user.id, audit_id=body.audit_id, product=price.code, amount_rub=price.amount_rub)
    db.add(p)
    db.flush()
    payload = {
        "amount": {"value": f"{price.amount_rub:.2f}", "currency": "RUB"}, "capture": True,
        "confirmation": {"type": "redirect", "return_url": f"{settings.public_base_url}/audit/{body.audit_id}?payment={p.id}" if body.audit_id else f"{settings.public_base_url}/account?payment={p.id}"},
        "description": f"{price.title}"[:128], "metadata": {"payment_id": p.id, "audit_id": body.audit_id or ""},
        "receipt": {"customer": {"email": receipt_email}, "items": [{"description": price.title[:128], "quantity": "1.00",
                    "amount": {"value": f"{price.amount_rub:.2f}", "currency": "RUB"}, "vat_code": 1, "payment_mode": "full_payment", "payment_subject": "service"}]},
    }
    try:
        r = httpx.post(f"{YK_API}/payments", json=payload, auth=_yk_auth(), headers={"Idempotence-Key": str(uuid.uuid4())}, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        db.rollback()
        raise HTTPException(502, f"Платёжный сервис недоступен: {type(e).__name__}")
    p.provider_id = data["id"]
    p.confirmation_url = data.get("confirmation", {}).get("confirmation_url")
    log_action(db, "payment.create", user.login, p.id, product=price.code, amount=price.amount_rub)
    db.commit()
    return {"payment_id": p.id, "confirmation_url": p.confirmation_url}


def _refresh(db: Session, p: Payment) -> None:
    if not p.provider_id or p.status == "succeeded":
        return
    r = httpx.get(f"{YK_API}/payments/{p.provider_id}", auth=_yk_auth(), timeout=20)
    r.raise_for_status()
    status = r.json().get("status")
    if status == "succeeded" and p.status != "succeeded":
        p.status, p.paid_at = "succeeded", datetime.now(timezone.utc)
        new_audit = _apply(db, p)
        if new_audit:
            db.commit()  # воркер должен увидеть проверку в базе до постановки в очередь
            enqueue_audit(new_audit)
    elif status == "canceled":
        p.status = "canceled"


@router.get("/api/payments/{payment_id}/status")
def payment_status(payment_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = db.get(Payment, payment_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404, "Платёж не найден")
    if settings.payments_enabled:
        try:
            _refresh(db, p)
            db.commit()
        except Exception:
            pass
    return {"status": p.status, "audit_id": p.audit_id}


@router.post("/api/payments/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Уведомление ЮKassa. Телу не доверяем: статус запрашиваем у API по id платежа."""
    try:
        body = await request.json()
        provider_id = body.get("object", {}).get("id", "")
    except Exception:
        raise HTTPException(400, "bad request")
    p = db.scalars(select(Payment).where(Payment.provider_id == str(provider_id)[:64])).first()
    if not p:
        return {"ok": True}
    try:
        _refresh(db, p)
        log_action(db, "payment.webhook", "yookassa", p.id, status=p.status)
        db.commit()
    except Exception:
        raise HTTPException(502, "verification failed")
    return {"ok": True}
