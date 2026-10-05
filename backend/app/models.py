import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")  # user | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # согласие на обработку ПД пользователя сервиса (отдельный документ, версия текста)
    consent_version: Mapped[str] = mapped_column(String(32), default="")
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # безлимитный доступ: полный отчёт + безопасность бесплатно, без лимитов частоты (выдаёт администратор)
    unlimited: Mapped[bool] = mapped_column(Boolean, default=False)


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (UniqueConstraint("user_id", "host"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    host: Mapped[str] = mapped_column(String(255))
    monitoring: Mapped[str] = mapped_column(String(16), default="off")  # off | daily | weekly | monthly
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_audit_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Audit(Base):
    __tablename__ = "audits"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    url: Mapped[str] = mapped_column(String(2048))
    host: Mapped[str] = mapped_column(String(255), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)  # queued|running|done|failed
    stages: Mapped[list] = mapped_column(JSON, default=list)
    site_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exposure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    counts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    facts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    security: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Security Skills (входят в «Полный аудит»)
    registries: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # проверка по реестрам (входит в «Полный аудит»)
    deep: Mapped[bool] = mapped_column(Boolean, default=False)  # собирались ли данные безопасности
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # версии правил и редакции норм
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    paid_full: Mapped[bool] = mapped_column(Boolean, default=False)  # «Полный аудит»: право + безопасность + реестры + PDF
    recheck_of: Mapped[str | None] = mapped_column(String(32), nullable=True)  # предыдущая проверка (для «Повторной проверки»)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OfficialSource(Base):
    __tablename__ = "official_sources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1024))
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1 — официальное опубликование


class NormativeAct(Base):
    __tablename__ = "normative_acts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # 152-FZ
    title: Mapped[str] = mapped_column(Text)
    short: Mapped[str] = mapped_column(String(64))
    adopted: Mapped[date | None] = mapped_column(Date, nullable=True)
    edition: Mapped[str] = mapped_column(String(255))
    checked_at: Mapped[date] = mapped_column(Date)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("official_sources.id"), nullable=True)
    official_url: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="active")


class NormativeArticle(Base):
    """Конкретная норма (статья/часть/пункт) в конкретной редакции. Новая редакция — новая запись."""
    __tablename__ = "normative_articles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # 152-FZ:18.1:2:@2026-10-03
    norm_key: Mapped[str] = mapped_column(String(64), index=True)  # 152-FZ:18.1:2:
    act_id: Mapped[str] = mapped_column(ForeignKey("normative_acts.id"))
    article: Mapped[str] = mapped_column(String(32))
    part: Mapped[str] = mapped_column(String(32), default="")
    paragraph: Mapped[str] = mapped_column(String(32), default="")
    title: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    edition: Mapped[str] = mapped_column(String(255))
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    checked_at: Mapped[date] = mapped_column(Date)
    official_url: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | superseded


class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    versions: Mapped[list["RuleVersion"]] = relationship(back_populates="rule", order_by="RuleVersion.version")


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    __table_args__ = (UniqueConstraint("rule_id", "version"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|tested|published|retired
    severity: Mapped[str] = mapped_column(String(16))
    mode: Mapped[str] = mapped_column(String(16), default="base")  # base | ecommerce
    basis: Mapped[list] = mapped_column(JSON)  # ключи норм
    basis_articles: Mapped[list] = mapped_column(JSON, default=list)  # id записей normative_articles (редакции)
    finance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    why: Mapped[str] = mapped_column(Text, default="")
    fix: Mapped[str] = mapped_column(Text, default="")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    test_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str] = mapped_column(String(254), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_by: Mapped[str | None] = mapped_column(String(254), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rule: Mapped[Rule] = relationship(back_populates="versions")


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class Price(Base):
    __tablename__ = "prices"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    amount_rub: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    audit_id: Mapped[str | None] = mapped_column(ForeignKey("audits.id", ondelete="SET NULL"), nullable=True)
    product: Mapped[str] = mapped_column(String(32))
    amount_rub: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|succeeded|canceled
    provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    confirmation_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """Журнал значимых действий (безопасность, админка, изменение правил)."""
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(254), default="anonymous")
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(255), default="")
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
