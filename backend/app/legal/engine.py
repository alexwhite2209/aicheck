"""Rule Engine: факты сайта → применимые опубликованные версии правил → результат с доказательствами."""
import json
import logging
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import NormativeAct, NormativeArticle, Rule, RuleVersion
from . import finance, score
from .rules import REGISTRY, UNDETERMINED, UNKNOWN, Outcome

log = logging.getLogger(__name__)
ENGINE_VERSION = "1.0.0"
DATA = Path(__file__).parent / "data"
STATUS_RU = {"PASS": "Требование выполнено по обнаруженным признакам", "FAIL": "Требование, вероятно, не выполнено",
             "REVIEW": "Требует внимания: нужна ручная проверка", "UNKNOWN": "Не удалось определить автоматически", "NA": "Не применимо"}
CONFIDENCE_RU = {"confirmed": "подтверждено", "probable": "вероятно", "manual": "требует ручной проверки", "undetermined": "не удалось определить"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
STATUS_ORDER = {"FAIL": 0, "REVIEW": 1, "UNKNOWN": 2, "PASS": 3, "NA": 4}


def sanctions() -> dict:
    return json.loads((DATA / "rules.json").read_text(encoding="utf-8"))["sanctions"]


def active_versions(db: Session, on: date) -> list[tuple[Rule, RuleVersion]]:
    rows = db.execute(
        select(Rule, RuleVersion).join(RuleVersion, RuleVersion.rule_id == Rule.id)
        .where(Rule.enabled.is_(True), RuleVersion.status == "published", RuleVersion.effective_from <= on)
    ).all()
    out: dict[str, tuple[Rule, RuleVersion]] = {}
    for r, v in rows:
        if v.effective_to and v.effective_to <= on:
            continue
        if r.id not in out or v.version > out[r.id][1].version:
            out[r.id] = (r, v)
    return list(out.values())


def _articles(db: Session, version: RuleVersion, on: date) -> list[dict]:
    res = []
    ids = version.basis_articles or []
    arts = {a.id: a for a in db.scalars(select(NormativeArticle).where(NormativeArticle.id.in_(ids)))} if ids else {}
    acts = {a.id: a for a in db.scalars(select(NormativeAct))}
    for key in version.basis:
        art = next((a for a in arts.values() if a.norm_key == key), None)
        if art is None:  # запасной путь: последняя действующая редакция нормы
            art = db.scalars(select(NormativeArticle).where(NormativeArticle.norm_key == key, NormativeArticle.status == "active")
                             .order_by(NormativeArticle.checked_at.desc())).first()
        if art is None:
            continue
        act = acts.get(art.act_id)
        res.append({"id": art.id, "key": art.norm_key, "act": act.short if act else art.act_id, "act_title": act.title if act else "",
                    "article": art.article, "part": art.part, "paragraph": art.paragraph, "title": art.title, "text": art.text,
                    "edition": art.edition, "effective_from": art.effective_from.isoformat() if art.effective_from else None,
                    "checked_at": art.checked_at.isoformat(), "official_url": art.official_url,
                    "label": basis_label(act.short if act else art.act_id, art.article, art.part, art.paragraph)})
    return res


def basis_label(act: str, article: str, part: str, paragraph: str) -> str:
    if article in ("Правила", "Постановление"):
        return f"{act}, {'Правила, ' if article == 'Правила' else ''}{part}"
    s = f"{act}, ст. {article}"
    if part:
        s += f", {'ч. ' + part if part[0].isdigit() else part}"
    if paragraph:
        s += f", п. {paragraph}"
    return s


def run(db: Session, facts: dict, on: date | None = None) -> dict:
    on = on or date.today()
    sanc = sanctions()
    koap = db.get(NormativeAct, "KOAP")
    koap_date = koap.edition if koap else ""
    subject = facts.get("company_details", {}).get("subject_type", "unknown")
    results = []
    snapshot = {"date": on.isoformat(), "engine": ENGINE_VERSION, "rules": [], "articles": {}}
    for rule, ver in active_versions(db, on):
        if ver.mode == "ecommerce" and facts.get("mode") != "ecommerce":
            pass  # правило само вернёт NA; режим фиксируется в факте
        fn = REGISTRY.get(rule.id)
        if fn is None:
            log.warning("Нет реализации для правила %s", rule.id)
            continue
        try:
            out: Outcome = fn(facts)
        except Exception as e:  # ошибка правила не должна ломать аудит
            log.exception("rule %s failed", rule.id)
            out = Outcome(UNKNOWN, UNDETERMINED, f"Проверка не выполнена из-за внутренней ошибки: {type(e).__name__}")
        severity = out.severity or ver.severity
        basis = _articles(db, ver, on)
        fin = finance.assess(rule.id, out.status, ver.finance, sanc, subject, koap_date)
        results.append({
            "rule_id": rule.id, "version": ver.version, "version_id": ver.id, "title": rule.title, "category": rule.category,
            "severity": severity, "status": out.status, "status_ru": STATUS_RU[out.status],
            "confidence": out.confidence, "confidence_ru": CONFIDENCE_RU[out.confidence],
            "fact": out.fact, "evidence": out.evidence[:8], "details": out.details,
            "basis": basis, "why": ver.why, "fix": ver.fix, "finance": fin,
        })
        snapshot["rules"].append({"rule_id": rule.id, "version": ver.version, "version_id": ver.id})
        for b in basis:
            snapshot["articles"][b["id"]] = b["edition"]
    results.sort(key=lambda r: (STATUS_ORDER[r["status"]], SEVERITY_ORDER.get(r["severity"], 9), r["rule_id"]))
    fin_items = [r["finance"] for r in results if r["finance"].get("min_value") is not None]
    exposure = finance.aggregate(fin_items)
    exposure["subject_type"] = subject
    exposure["subject_ru"] = finance.SUBJECT_RU[subject]
    return {"results": results, "score": score.compute(results), "counts": score.counts(results), "exposure": exposure, "snapshot": snapshot}
