import logging
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

_connect_args = {}
if settings.database_url.startswith("sqlite"):
    Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    _connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(settings.database_url, connect_args=_connect_args, pool_pre_ping=True, future=True)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def reset_stale_sqlite() -> None:
    """Локальная SQLite без миграций: если схема файла не совпадает с моделями (после обновления кода),
    старый файл откладывается в .bak-<время>, и создаётся чистая база. Для PostgreSQL ничего не делает."""
    if not settings.database_url.startswith("sqlite"):
        return
    path = Path(settings.database_url.removeprefix("sqlite:///"))
    if not path.exists():
        return
    insp = inspect(engine)
    stale = False
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        db_cols = {c["name"]: c for c in insp.get_columns(table.name)}
        model_cols = {c.name for c in table.columns}
        if model_cols - set(db_cols):
            stale = True
        # лишняя старая колонка NOT NULL без значения по умолчанию сломает вставку новых строк
        if any(not c["nullable"] and c["default"] is None and not c.get("primary_key") and n not in model_cols for n, c in db_cols.items()):
            stale = True
    if not stale:
        return
    engine.dispose()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for suffix in ("", "-wal", "-shm"):
        src = Path(str(path) + suffix)
        if src.exists():
            shutil.move(str(src), f"{src}.bak-{stamp}")
    logging.getLogger(__name__).warning("Схема локальной базы устарела: старый файл сохранён как %s.bak-%s, создана новая база", path.name, stamp)
