"""Сборка модуля безопасности: пассивный анализ → триаж (навык 12) → security score + связь с 152-ФЗ."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import NormativeArticle
from .scan import FAIL, INFO, PASS, REVIEW, scan

WEIGHTS = {"critical": 10, "high": 6, "medium": 3, "low": 1, "info": 0}
VALUE = {PASS: 1.0, REVIEW: 0.5, FAIL: 0.0}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
ST_ORDER = {FAIL: 0, REVIEW: 1, INFO: 2, PASS: 3}
SECURITY_DISCLAIMER = ("Проверка безопасности — информационный инструмент и не является аудитом по ГОСТ/PCI DSS, "
                       "пентестом или гарантией защищённости. Выполнены только безопасные проверки публичной части сайта.")
CATEGORIES = ["Конфигурация", "Защита данных", "Утечки данных", "Доступ"]


def triage(findings) -> list:
    """Навык Vulnerability Triage: убрать дубликаты, упорядочить по риску."""
    seen = {}
    for f in findings:
        key = (f.id, f.title)
        if key not in seen:
            seen[key] = f
    ordered = sorted(seen.values(), key=lambda f: (ST_ORDER.get(f.status, 9), SEV_ORDER.get(f.severity, 9)))
    return ordered


def security_score(findings) -> int | None:
    num = den = 0.0
    for f in findings:
        if f.status == INFO:
            continue
        w = WEIGHTS.get(f.severity, 0)
        num += w * VALUE.get(f.status, 0)
        den += w
    return round(100 * num / den) if den else None


def _norm(db: Session, key: str) -> dict | None:
    a = db.scalars(select(NormativeArticle).where(NormativeArticle.norm_key == key, NormativeArticle.status == "active")
                   .order_by(NormativeArticle.checked_at.desc())).first()
    if not a:
        return None
    label = f"{a.act_id.replace('-FZ', '-ФЗ')}, ст. {a.article}" + (f", ч. {a.part}" if a.part else "")
    return {"key": a.norm_key, "label": "152-ФЗ, ст. 19, ч. 1" if key == "152-FZ:19:1:" else label,
            "title": a.title, "text": a.text, "edition": a.edition, "checked_at": a.checked_at.isoformat(),
            "official_url": a.official_url}


def run_security(db: Session, facts: dict, sec: dict, on: date | None = None) -> dict:
    findings = triage(scan(facts, sec))
    pd_norm = _norm(db, "152-FZ:19:1:")
    out = []
    for f in findings:
        d = f.as_dict()
        if f.touches_pd and f.status in (FAIL, REVIEW) and pd_norm:
            d["legal_basis"] = pd_norm
            d["legal_note"] = ("Сайт собирает персональные данные, поэтому эта техническая слабость связана с обязанностью "
                               "оператора принимать меры защиты ПД (152-ФЗ, ст. 19). Недостаточные меры могут образовать "
                               "состав по ст. 13.11 КоАП РФ; конкретную квалификацию и сумму определяет уполномоченный орган.")
        out.append(d)
    counts = {"fail": 0, "review": 0, "pass": 0, "info": 0}
    for f in findings:
        counts[{FAIL: "fail", REVIEW: "review", PASS: "pass", INFO: "info"}[f.status]] += 1
    return {
        "findings": out, "score": security_score(findings), "counts": counts,
        "by_severity": {s: sum(1 for f in findings if f.status == FAIL and f.severity == s) for s in WEIGHTS},
        "disclaimer": SECURITY_DISCLAIMER,
    }
