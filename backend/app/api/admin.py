"""Админ-панель: дашборд, аудиты, пользователи, правила и их версии, нормативная база, AI, цены, журнал."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai.openrouter import list_models
from ..audit_log import log_action
from ..db import get_db
from ..legal.fixtures import run_cases
from ..legal.rules import REGISTRY
from ..models import Audit, AuditLog, NormativeAct, NormativeArticle, Payment, Price, Rule, RuleVersion, Setting, User
from ..security import hash_password
from .deps import current_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])
SEVERITIES = "^(critical|high|medium|low|info)$"


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    day = datetime.now(timezone.utc) - timedelta(days=1)
    done = db.scalars(select(Audit).where(Audit.status == "done").order_by(Audit.created_at.desc()).limit(500)).all()
    scores = [a.score for a in done if a.score is not None]
    exps = [(a.exposure or {}).get("min") or 0 for a in done]
    failed = db.scalars(select(Audit).where(Audit.status == "failed").order_by(Audit.created_at.desc()).limit(15)).all()
    return {
        "audits_total": db.scalar(select(func.count(Audit.id))),
        "audits_24h": db.scalar(select(func.count(Audit.id)).where(Audit.created_at >= day)),
        "audits_running": db.scalar(select(func.count(Audit.id)).where(Audit.status.in_(("queued", "running")))),
        "audits_failed": db.scalar(select(func.count(Audit.id)).where(Audit.status == "failed")),
        "users": db.scalar(select(func.count(User.id))),
        "revenue_rub": db.scalar(select(func.coalesce(func.sum(Payment.amount_rub), 0)).where(Payment.status == "succeeded")),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "avg_exposure_min": round(sum(exps) / len(exps)) if exps else None,
        "crawler_errors": [{"id": a.id, "url": a.url, "error": a.error, "created_at": a.created_at.isoformat(),
                            "detail": ((a.facts or {}).get("crawl") or {}).get("fatal")} for a in failed],
    }


@router.get("/audits")
def audits(status: str | None = None, q: str | None = None, limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    stmt = select(Audit, User.login).outerjoin(User, User.id == Audit.user_id).order_by(Audit.created_at.desc()).limit(min(limit, 500))
    if status:
        stmt = stmt.where(Audit.status == status)
    if q:
        stmt = stmt.where(Audit.url.ilike(f"%{q[:100]}%"))
    return {"audits": [{"id": a.id, "url": a.url, "user": login, "created_at": a.created_at.isoformat(), "score": a.score,
                        "exposure_min": (a.exposure or {}).get("min"), "exposure_max": (a.exposure or {}).get("max"),
                        "status": a.status, "error": a.error, "site_type": a.site_type} for a, login in db.execute(stmt).all()]}


@router.get("/users")
def users(db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    rows = db.execute(select(User, func.count(Audit.id)).outerjoin(Audit, Audit.user_id == User.id).group_by(User.id).order_by(User.created_at.desc()).limit(500)).all()
    return {"users": [{"id": u.id, "login": u.login, "role": u.role, "created_at": u.created_at.isoformat(), "audits": n,
                       "consent_version": u.consent_version,
                       "unlimited": u.unlimited, "pro": bool(u.role == "admin" or u.unlimited), "is_active": u.is_active}
                      for u, n in rows]}


class UserPatch(BaseModel):
    unlimited: bool | None = None
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    is_active: bool | None = None
    # новый пароль пользователя (восстановления по почте нет — пароль сбрасывает администратор)
    password: str | None = Field(default=None, min_length=8, max_length=128)


@router.put("/users/{user_id}")
def update_user(user_id: str, body: UserPatch, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    """Выдать/снять безлимитный доступ, роль администратора, блокировку, задать новый пароль. Доступно только администратору."""
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Пользователь не найден")
    if u.id == admin.id and (body.role == "user" or body.is_active is False):
        raise HTTPException(400, "Нельзя снять с себя права администратора или заблокировать себя")
    changes = body.model_dump(exclude_none=True, exclude={"password"})
    for k, v in changes.items():
        setattr(u, k, v)
    if body.password:
        u.password_hash = hash_password(body.password)
        changes["password_reset"] = True
    log_action(db, "user.grant", admin.login, u.login, **changes)
    db.commit()
    return {"ok": True, "unlimited": u.unlimited, "role": u.role, "is_active": u.is_active}


# ------------------------------------------------------------------ правила
def version_out(v: RuleVersion) -> dict:
    return {"id": v.id, "version": v.version, "status": v.status, "severity": v.severity, "mode": v.mode, "basis": v.basis,
            "basis_articles": v.basis_articles, "finance": v.finance, "why": v.why, "fix": v.fix,
            "effective_from": v.effective_from.isoformat(), "effective_to": v.effective_to.isoformat() if v.effective_to else None,
            "notes": v.notes, "test_report": v.test_report, "created_by": v.created_by, "created_at": v.created_at.isoformat(),
            "published_by": v.published_by, "published_at": v.published_at.isoformat() if v.published_at else None}


@router.get("/rules")
def rules(db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    out = []
    for r in db.scalars(select(Rule).order_by(Rule.id)).all():
        out.append({"id": r.id, "title": r.title, "category": r.category, "enabled": r.enabled, "implemented": r.id in REGISTRY,
                    "versions": [version_out(v) for v in sorted(r.versions, key=lambda x: -x.version)]})
    return {"rules": out, "unseeded_implementations": sorted(set(REGISTRY) - {r["id"] for r in out})}


class RuleIn(BaseModel):
    id: str = Field(pattern=r"^[A-Z0-9_]{5,64}$")
    title: str = Field(max_length=255)
    category: str = Field(max_length=64)


@router.post("/rules")
def create_rule(body: RuleIn, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    if body.id not in REGISTRY:
        raise HTTPException(422, "Для правила нет реализованного алгоритма. Сначала опишите правило в LEGAL_DATABASE.md и реализуйте проверку.")
    if db.get(Rule, body.id):
        raise HTTPException(409, "Правило уже существует")
    db.add(Rule(id=body.id, title=body.title, category=body.category, enabled=False))
    log_action(db, "rule.create", admin.login, body.id)
    db.commit()
    return {"ok": True}


class RulePatch(BaseModel):
    enabled: bool | None = None
    title: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=64)


@router.put("/rules/{rule_id}")
def update_rule(rule_id: str, body: RulePatch, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    r = db.get(Rule, rule_id)
    if not r:
        raise HTTPException(404, "Правило не найдено")
    changes = body.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(r, k, v)
    log_action(db, "rule.update", admin.login, rule_id, **changes)
    db.commit()
    return {"ok": True}


class VersionIn(BaseModel):
    severity: str = Field(pattern=SEVERITIES)
    basis: list[str] = Field(min_length=1, max_length=10)
    finance: dict | None = None
    why: str = Field(max_length=3000)
    fix: str = Field(max_length=3000)
    effective_from: date
    notes: str = Field(default="", max_length=3000)


@router.post("/rules/{rule_id}/versions")
def create_version(rule_id: str, body: VersionIn, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    """Новая версия правила (черновик). Старые версии не изменяются."""
    r = db.get(Rule, rule_id)
    if not r:
        raise HTTPException(404, "Правило не найдено")
    arts = []
    for key in body.basis:
        art = db.scalars(select(NormativeArticle).where(NormativeArticle.norm_key == key, NormativeArticle.status == "active")
                         .order_by(NormativeArticle.checked_at.desc())).first()
        if not art:
            raise HTTPException(422, f"Норма {key} отсутствует в нормативной базе. Сначала добавьте её с официальным источником.")
        arts.append(art.id)
    last = max((v.version for v in r.versions), default=0)
    prev = max(r.versions, key=lambda v: v.version) if r.versions else None
    v = RuleVersion(rule_id=rule_id, version=last + 1, status="draft", severity=body.severity, mode=prev.mode if prev else "base",
                    basis=body.basis, basis_articles=arts, finance=body.finance, why=body.why, fix=body.fix,
                    effective_from=body.effective_from, notes=body.notes, created_by=admin.login)
    db.add(v)
    log_action(db, "rule.version.create", admin.login, f"{rule_id} v{v.version}")
    db.commit()
    return version_out(v)


@router.post("/rules/{rule_id}/versions/{version_id}/test")
def test_version(rule_id: str, version_id: str, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    v = db.get(RuleVersion, version_id)
    if not v or v.rule_id != rule_id:
        raise HTTPException(404, "Версия не найдена")
    report = run_cases(rule_id)
    report["tested_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    v.test_report = report
    if v.status == "draft" and report["passed"]:
        v.status = "tested"
    log_action(db, "rule.version.test", admin.login, f"{rule_id} v{v.version}", passed=report["passed"])
    db.commit()
    return report


@router.post("/rules/{rule_id}/versions/{version_id}/publish")
def publish_version(rule_id: str, version_id: str, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    v = db.get(RuleVersion, version_id)
    if not v or v.rule_id != rule_id:
        raise HTTPException(404, "Версия не найдена")
    if v.status != "tested":
        raise HTTPException(409, "Публикация возможна только после успешного тестирования")
    today = date.today()
    for old in db.scalars(select(RuleVersion).where(RuleVersion.rule_id == rule_id, RuleVersion.status == "published")):
        if not old.effective_to or old.effective_to > v.effective_from:
            old.effective_to = v.effective_from
        if v.effective_from <= today:
            old.status = "retired"
    v.status, v.published_by, v.published_at = "published", admin.login, datetime.now(timezone.utc)
    log_action(db, "rule.version.publish", admin.login, f"{rule_id} v{v.version}", effective_from=v.effective_from.isoformat())
    db.commit()
    return version_out(v)


# ------------------------------------------------------------------ нормативная база
@router.get("/normative-acts")
def acts(db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    rows = db.scalars(select(NormativeAct).order_by(NormativeAct.id)).all()
    arts = db.scalars(select(NormativeArticle).order_by(NormativeArticle.norm_key, NormativeArticle.checked_at.desc())).all()
    return {"acts": [{"id": a.id, "title": a.title, "short": a.short, "edition": a.edition, "checked_at": a.checked_at.isoformat(),
                      "official_url": a.official_url, "status": a.status} for a in rows],
            "articles": [{"id": x.id, "key": x.norm_key, "act_id": x.act_id, "article": x.article, "part": x.part, "paragraph": x.paragraph,
                          "title": x.title, "text": x.text, "edition": x.edition, "effective_from": x.effective_from.isoformat() if x.effective_from else None,
                          "effective_to": x.effective_to.isoformat() if x.effective_to else None, "checked_at": x.checked_at.isoformat(),
                          "official_url": x.official_url, "status": x.status} for x in arts]}


class ActIn(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9\-]{2,32}$")
    title: str = Field(max_length=1000)
    short: str = Field(max_length=64)
    edition: str = Field(max_length=255)
    official_url: str = Field(pattern=r"^https?://(pravo\.gov\.ru|publication\.pravo\.gov\.ru|[a-z0-9.\-]+\.gov\.ru|rkn\.gov\.ru)(/.*)?$")
    checked_at: date


class ArticleIn(BaseModel):
    key: str = Field(pattern=r"^[A-Za-z0-9\-]+:[^:]+:[^:]*:[^:]*$", max_length=64)
    act_id: str
    article: str = Field(max_length=32)
    part: str = Field(default="", max_length=32)
    paragraph: str = Field(default="", max_length=32)
    title: str = Field(max_length=255)
    text: str = Field(min_length=20, max_length=20000)
    edition: str = Field(max_length=255)
    effective_from: date | None = None
    official_url: str = Field(pattern=r"^https?://(pravo\.gov\.ru|publication\.pravo\.gov\.ru|[a-z0-9.\-]+\.gov\.ru)(/.*)?$")
    checked_at: date


@router.post("/normative-acts")
def upsert_act(body: ActIn, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    """Только официальные источники (pravo.gov.ru, сайты госорганов *.gov.ru)."""
    a = db.get(NormativeAct, body.id) or NormativeAct(id=body.id)
    a.title, a.short, a.edition, a.official_url, a.checked_at = body.title, body.short, body.edition, body.official_url, body.checked_at
    db.add(a)
    log_action(db, "norm.act.upsert", admin.login, body.id)
    db.commit()
    return {"ok": True}


@router.post("/normative-articles")
def add_article(body: ArticleIn, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    """Новая редакция нормы — новая запись; прежняя помечается замещённой, но сохраняется для истории аудитов."""
    if not db.get(NormativeAct, body.act_id):
        raise HTTPException(422, "Акт не найден")
    aid = f"{body.key}@{body.checked_at.isoformat()}"
    if db.get(NormativeArticle, aid):
        raise HTTPException(409, "Редакция с такой датой сверки уже есть")
    for old in db.scalars(select(NormativeArticle).where(NormativeArticle.norm_key == body.key, NormativeArticle.status == "active")):
        old.status, old.effective_to = "superseded", body.effective_from or body.checked_at
    db.add(NormativeArticle(id=aid, norm_key=body.key, act_id=body.act_id, article=body.article, part=body.part, paragraph=body.paragraph,
                            title=body.title, text=body.text, edition=body.edition, effective_from=body.effective_from,
                            checked_at=body.checked_at, official_url=body.official_url))
    log_action(db, "norm.article.add", admin.login, aid)
    db.commit()
    return {"ok": True, "id": aid, "note": "Чтобы правило использовало новую редакцию, создайте новую версию правила, протестируйте и опубликуйте её."}


# ------------------------------------------------------------------ AI и цены
@router.get("/ai/models")
async def ai_models(admin: User = Depends(current_admin)):
    return {"models": await run_in_threadpool(list_models)}


class AISettings(BaseModel):
    model: str = Field(max_length=200)
    temperature: float = Field(ge=0, le=1.5)
    max_tokens: int = Field(ge=200, le=16000)
    enabled: bool = True


@router.get("/ai/settings")
def get_ai(db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    s = db.get(Setting, "ai")
    from ..config import get_settings
    return {"provider": "OpenRouter", "key_configured": bool(get_settings().openrouter_api_key), **(s.value if s else {})}


@router.put("/ai/settings")
def put_ai(body: AISettings, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    s = db.get(Setting, "ai") or Setting(key="ai", value={})
    s.value = {"provider": "openrouter", **body.model_dump()}
    db.add(s)
    log_action(db, "ai.settings", admin.login, body.model)
    db.commit()
    return s.value


class PriceIn(BaseModel):
    code: str = Field(pattern=r"^[a-z_]{3,32}$")
    title: str = Field(max_length=255)
    description: str = Field(default="", max_length=1000)
    amount_rub: float = Field(gt=0, lt=1_000_000)
    active: bool = True
    sort: int = 0


@router.get("/prices")
def prices(db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    return {"prices": [{"code": p.code, "title": p.title, "description": p.description, "amount_rub": p.amount_rub, "active": p.active, "sort": p.sort}
                       for p in db.scalars(select(Price).order_by(Price.sort))]}


@router.put("/prices")
def put_price(body: PriceIn, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    p = db.get(Price, body.code) or Price(code=body.code)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    db.add(p)
    log_action(db, "price.update", admin.login, body.code, amount=body.amount_rub)
    db.commit()
    return {"ok": True}


@router.get("/log")
def audit_log(db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.at.desc()).limit(300)).all()
    return {"log": [{"at": r.at.isoformat(), "actor": r.actor, "action": r.action, "target": r.target, "meta": r.meta} for r in rows]}
