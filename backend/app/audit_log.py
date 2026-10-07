from sqlalchemy.orm import Session

from .models import AuditLog


def log_action(db: Session, action: str, actor: str = "anonymous", target: str = "", ip_hash: str | None = None, **meta) -> None:
    db.add(AuditLog(action=action, actor=actor, target=target[:255], ip_hash=ip_hash, meta=meta))
