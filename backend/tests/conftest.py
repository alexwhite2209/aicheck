import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="norma-test-"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(_tmp / 'test.db').as_posix()}")
os.environ.setdefault("TASK_MODE", "inline")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-0123")
os.environ.setdefault("ADMIN_LOGIN", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin-pass-123")
os.environ.setdefault("OPENROUTER_API_KEY", "")
os.environ.setdefault("YOOKASSA_SHOP_ID", "")
