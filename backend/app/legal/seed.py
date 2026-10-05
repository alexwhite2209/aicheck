"""Заполнение нормативной базы и правил из LEGAL_DATABASE (norms.json, rules.json). Идемпотентно."""
import json
import logging
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import NormativeAct, NormativeArticle, OfficialSource, Price, Rule, RuleVersion, Setting, User

log = logging.getLogger(__name__)
DATA = Path(__file__).parent / "data"

# «Экспресс-проверка» (0 ₽) — бесплатный уровень, в таблице цен не хранится
DEFAULT_PRICES = [
    ("full_audit", "Полный аудит", "Законодательство РФ + Security Skills + реестры + финансовая экспозиция + полный PDF-отчёт", 299, 1),
    ("recheck", "Повторная проверка", "Полный повторный аудит + сравнение с предыдущим результатом", 499, 2),
]
LEGACY_PRICE_CODES = ("all_in_one", "full_report", "security_report", "monitoring_month")


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def seed_norms(db: Session) -> dict[str, str]:
    data = json.loads((DATA / "norms.json").read_text(encoding="utf-8"))
    if not db.get(OfficialSource, "pravo_gov_ru"):
        db.add(OfficialSource(id="pravo_gov_ru", name="Официальный интернет-портал правовой информации (ИПС «Законодательство России»)",
                              url="http://pravo.gov.ru", priority=1))
        db.flush()
    for a in data["acts"]:
        act = db.get(NormativeAct, a["id"])
        if not act:
            act = NormativeAct(id=a["id"])
            db.add(act)
        act.title, act.short, act.adopted, act.edition = a["title"], a["short"], _d(a["adopted"]), a["edition"]
        act.checked_at, act.official_url, act.source_id = _d(a["checked_at"]), a["official_source"], "pravo_gov_ru"
    db.flush()
    key_to_id: dict[str, str] = {}
    for n in data["articles"]:
        aid = f"{n['id']}@{n['checked_at']}"
        art = db.get(NormativeArticle, aid)
        if not art:
            # новая редакция нормы: прежние записи с тем же ключом помечаются как замещённые, но не удаляются
            for old in db.scalars(select(NormativeArticle).where(NormativeArticle.norm_key == n["id"], NormativeArticle.status == "active")):
                if old.text.strip() != n["text"].strip():
                    old.status = "superseded"
                    old.effective_to = _d(n["checked_at"])
            art = NormativeArticle(id=aid, norm_key=n["id"])
            db.add(art)
        art.act_id, art.article, art.part, art.paragraph = n["act_id"], n["article"], n["part"], n["paragraph"]
        art.title, art.text, art.edition = n["title"], n["text"], n["edition"]
        art.effective_from, art.checked_at, art.official_url = _d(n["effective_from"]), _d(n["checked_at"]), n["official_source"]
        key_to_id[n["id"]] = aid
    db.flush()
    return key_to_id


def seed_rules(db: Session, key_to_id: dict[str, str]) -> None:
    data = json.loads((DATA / "rules.json").read_text(encoding="utf-8"))
    checked = data["checked_at"]
    for r in data["rules"]:
        rule = db.get(Rule, r["id"])
        if not rule:
            rule = Rule(id=r["id"], category=r["category"], title=r["title"], enabled=True)
            db.add(rule)
            db.flush()
        has_version = db.scalars(select(RuleVersion).where(RuleVersion.rule_id == r["id"])).first()
        if has_version:
            continue  # существующие версии не перезаписываем — изменения только через новую версию
        db.add(RuleVersion(
            rule_id=r["id"], version=1, status="published", severity=r["severity"], mode=r.get("mode", "base"),
            basis=r["basis"], basis_articles=[key_to_id[k] for k in r["basis"] if k in key_to_id], finance=r.get("finance"),
            why=r["why"], fix=r["fix"], params={}, effective_from=_d(r.get("effective_from") or checked),
            notes="Первичная версия по LEGAL_DATABASE.md", created_by="seed", published_by="seed",
            test_report={"status": "seed", "note": "покрыто tests/test_rules.py"},
        ))
    db.flush()


def seed_settings(db: Session) -> None:
    st = get_settings()
    if not db.get(Setting, "ai"):
        db.add(Setting(key="ai", value={"provider": "openrouter", "model": st.openrouter_model, "temperature": 0.2, "max_tokens": 2500, "enabled": True}))
    for code, title, desc, amount, sort in DEFAULT_PRICES:
        if not db.get(Price, code):  # цены, изменённые в админке, не перезаписываем
            db.add(Price(code=code, title=title, description=desc, amount_rub=amount, sort=sort))
    for old in db.scalars(select(Price).where(Price.code.in_(LEGACY_PRICE_CODES))):
        old.active = False  # старые тарифы (в т.ч. отдельная проверка безопасности) больше не продаются
    admin_login = (st.admin_login or st.admin_email).strip().lower()
    if admin_login and st.admin_password:
        from ..security import hash_password
        u = db.scalars(select(User).where(User.login == admin_login)).first()
        if not u:
            db.add(User(login=admin_login, password_hash=hash_password(st.admin_password), role="admin",
                        consent_version="admin-bootstrap"))
        elif u.role != "admin":
            u.role = "admin"


def seed_all(db: Session) -> None:
    keys = seed_norms(db)
    seed_rules(db, keys)
    seed_settings(db)
    db.commit()
