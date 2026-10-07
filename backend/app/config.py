from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(BASE_DIR.parent / ".env", BASE_DIR / ".env"), extra="ignore")

    env: str = "development"  # development | production
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'audit.db').as_posix()}"
    redis_url: str = ""
    # celery — задачи через Redis/Celery; inline — фоновые потоки в процессе API (локальная разработка)
    task_mode: str = "inline"

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Реестры: ключ DaData для ЕГРЮЛ/ЕГРИП (если пусто — ссылка на ручную проверку)
    dadata_api_key: str = ""
    # Активные пробы безопасности (S2) — только для подтверждённых доменов. В MVP выключено.
    security_active_enabled: bool = False

    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""

    jwt_secret: str = "change-me-in-production"
    jwt_ttl_hours: int = 72
    # секрет для хеширования IP (IP посетителей в открытом виде не хранится)
    ip_hash_secret: str = ""

    trust_proxy_headers: bool = False  # true, если перед API стоит доверенный прокси (Next.js / nginx)
    public_base_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

    admin_email: str = ""
    admin_password: str = ""

    max_pages: int = 20
    max_depth: int = 2
    page_timeout: int = 30
    total_timeout: int = 180
    max_parallel_crawls: int = 2
    # Только для локальных тестов (игнорируется в production): "127.0.0.1:8765,localhost:8765"
    crawler_test_allowlist: str = ""

    rate_limit_anon_hour: int = 5
    rate_limit_anon_day: int = 15
    rate_limit_user_hour: int = 20
    anon_audit_retention_days: int = 30

    # Если ключи ЮKassa не заданы, полный отчёт открыт всем (paywall выключен).
    paywall: bool = Field(default=True)

    @property
    def is_prod(self) -> bool:
        return self.env == "production"

    @property
    def payments_enabled(self) -> bool:
        return bool(self.yookassa_shop_id and self.yookassa_secret_key)

    @property
    def paywall_active(self) -> bool:
        return self.paywall and self.payments_enabled

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
