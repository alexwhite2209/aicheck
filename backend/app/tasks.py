"""Очередь задач: Celery + Redis (TASK_MODE=celery) или пул потоков в процессе API (TASK_MODE=inline)."""
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

celery_app = None
if settings.task_mode == "celery":
    from celery import Celery

    celery_app = Celery("norma", broker=settings.redis_url, backend=None)
    celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, task_time_limit=settings.total_timeout + 180,
                           task_soft_time_limit=settings.total_timeout + 120, broker_connection_retry_on_startup=True,
                           beat_schedule={"cleanup": {"task": "app.tasks.cleanup_task", "schedule": 6 * 3600}})

    @celery_app.task(name="app.tasks.run_audit_task")
    def run_audit_task(audit_id: str) -> None:
        from .pipeline import run_audit
        run_audit(audit_id)

    @celery_app.task(name="app.tasks.cleanup_task")
    def cleanup_task() -> int:
        return cleanup()

_pool = ThreadPoolExecutor(max_workers=settings.max_parallel_crawls, thread_name_prefix="audit") if settings.task_mode != "celery" else None


def enqueue_audit(audit_id: str) -> None:
    if celery_app is not None:
        celery_app.send_task("app.tasks.run_audit_task", args=[audit_id])
    else:
        from .pipeline import run_audit
        _pool.submit(run_audit, audit_id)


def cleanup() -> int:
    """Удаление анонимных проверок старше срока хранения (минимизация хранимых данных)."""
    from sqlalchemy import delete

    from .db import session_scope
    from .models import Audit
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.anon_audit_retention_days)
    with session_scope() as db:
        res = db.execute(delete(Audit).where(Audit.user_id.is_(None), Audit.paid_full.is_(False), Audit.created_at < cutoff))
        return res.rowcount or 0
