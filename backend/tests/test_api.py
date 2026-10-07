"""API: создание проверки, статус, результат, авторизация, CSRF, админка."""
import pytest
from fastapi.testclient import TestClient

from app.legal.fixtures import FULL_REQ, POLICY, base_facts, form


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    import app.api.audit as audit_api
    monkeypatch_module.setattr(audit_api, "enqueue_audit", lambda _id: None)
    monkeypatch_module.setattr(audit_api, "validate_target", lambda url, allow=None: "https://example.ru/")
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def _finish(audit_id, facts):
    from app.db import session_scope
    from app.legal import engine
    from app.models import Audit
    with session_scope() as db:
        res = engine.run(db, facts)
        a = db.get(Audit, audit_id)
        a.status, a.facts, a.results, a.score, a.counts, a.exposure, a.snapshot = "done", facts, res["results"], res["score"], res["counts"], res["exposure"], res["snapshot"]
        a.ai = {"used": False, "items": {}}
    return res


def test_ssrf_rejected_by_api():
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/api/audit", json={"url": "http://127.0.0.1/admin"})
        assert r.status_code == 422


def test_full_flow(client):
    r = client.post("/api/audit", json={"url": "example.ru"})
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    st = client.get(f"/api/audit/{aid}/status").json()
    assert st["status"] == "queued" and len(st["stages"]) >= 13
    assert client.get(f"/api/audit/{aid}/result").status_code == 409
    facts = base_facts(forms=[form(consent=[{"text": "Принимаю условия оферты и даю согласие на обработку персональных данных", "combined": True}])],
                       company_details=FULL_REQ, contacts={"emails": ["info@example.ru"], "phones": []})
    res = _finish(aid, facts)
    statuses = {x["rule_id"]: x["status"] for x in res["results"]}
    assert statuses["152FZ_POLICY_001"] == "FAIL" and statuses["152FZ_CONSENT_SEPARATE_002"] == "FAIL"
    assert statuses["152FZ_LOCALIZATION_005"] == "UNKNOWN" and statuses["152FZ_RKN_NOTICE_007"] == "UNKNOWN"
    out = client.get(f"/api/audit/{aid}/result").json()
    assert out["full_access"] is True  # ЮKassa не настроена → paywall выключен
    assert out["exposure"]["state"] == "VERIFIED_RANGE" or out["exposure"]["state"] == "ESTIMATED_RANGE"
    assert out["exposure"]["min"] >= 30000  # ч. 3 ст. 13.11 для юрлица
    pol = next(x for x in out["results"] if x["rule_id"] == "152FZ_POLICY_001")
    assert pol["basis"][0]["official_url"].startswith("http://pravo.gov.ru/") and "18.1" in pol["basis"][0]["label"]
    assert out["snapshot"]["rules"] and out["snapshot"]["articles"]
    pdf = client.get(f"/api/report/{aid}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_good_site_scores_high(client):
    aid = client.post("/api/audit", json={"url": "good.ru"}).json()["id"]
    facts = base_facts(forms=[form(consent=[{}])], documents=[POLICY], company_details=FULL_REQ, contacts={"emails": ["a@b.ru"], "phones": []})
    res = _finish(aid, facts)
    assert res["counts"]["fail"] == 0 and res["score"] >= 80 and res["exposure"]["min"] == 0


def test_auth_csrf_and_admin(client):
    r = client.post("/api/auth/register", json={"login": "user1", "password": "password123", "consent": False})
    assert r.status_code == 422
    for bad_login in ("ab", "u@test.ru", "two words", "x" * 33):
        r = client.post("/api/auth/register", json={"login": bad_login, "password": "password123", "consent": True})
        assert r.status_code == 422, bad_login
    r = client.post("/api/auth/register", json={"login": " User1 ", "password": "password123", "consent": True})
    assert r.status_code == 200
    csrf = client.cookies.get("csrf_token")
    me = client.get("/api/auth/me").json()["user"]
    assert me["login"] == "user1" and "email" not in me
    assert client.post("/api/user/sites", json={"url": "example.ru"}).status_code == 403  # без CSRF-заголовка
    assert client.post("/api/user/sites", json={"url": "example.ru"}, headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/api/admin/dashboard").status_code == 403
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    r = client.post("/api/auth/login", json={"login": "admin", "password": "wrong-pass"})
    assert r.status_code == 401
    r = client.post("/api/auth/login", json={"login": "Admin", "password": "admin-pass-123"})
    assert r.status_code == 200
    csrf = client.cookies.get("csrf_token")
    d = client.get("/api/admin/dashboard").json()
    assert d["audits_total"] >= 2
    rules = client.get("/api/admin/rules").json()["rules"]
    assert len(rules) == 24 and all(r["implemented"] for r in rules)
    # новая версия правила → тест → публикация
    v = client.post("/api/admin/rules/152FZ_POLICY_001/versions", headers={"X-CSRF-Token": csrf},
                    json={"severity": "high", "basis": ["152-FZ:18.1:2:"], "finance": {"group": "KOAP:13.11:3:", "kind": "direct"},
                          "why": "t", "fix": "t", "effective_from": "2026-10-03", "notes": "test"}).json()
    assert v["version"] == 2 and v["status"] == "draft"
    assert client.post(f"/api/admin/rules/152FZ_POLICY_001/versions/{v['id']}/publish", headers={"X-CSRF-Token": csrf}).status_code == 409
    t = client.post(f"/api/admin/rules/152FZ_POLICY_001/versions/{v['id']}/test", headers={"X-CSRF-Token": csrf}).json()
    assert t["passed"]
    p = client.post(f"/api/admin/rules/152FZ_POLICY_001/versions/{v['id']}/publish", headers={"X-CSRF-Token": csrf}).json()
    assert p["status"] == "published"
    rule = next(r for r in client.get("/api/admin/rules").json()["rules"] if r["id"] == "152FZ_POLICY_001")
    assert rule["versions"][1]["status"] == "retired" and rule["versions"][1]["effective_to"] == "2026-10-03"
    # норма без официального источника не принимается
    bad = client.post("/api/admin/normative-articles", headers={"X-CSRF-Token": csrf},
                      json={"key": "X-FZ:1:1:", "act_id": "152-FZ", "article": "1", "title": "t", "text": "x" * 30, "edition": "e",
                            "official_url": "https://some-law-blog.ru/x", "checked_at": "2026-10-03"})
    assert bad.status_code == 422


def test_public_rules(client):
    d = client.get("/api/public/rules").json()
    assert len(d["rules"]) == 24 and len(d["acts"]) == 7


def test_security_methodology_public(client):
    d = client.get("/api/public/security-methodology").json()
    assert d["counts"]["s1"] >= 12 and d["counts"]["s2"] >= 3
    assert "github.com" in d["repo"]


def test_admin_grants_unlimited(client):
    # войти админом
    csrf = client.cookies.get("csrf_token")
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    r = client.post("/api/auth/login", json={"login": "admin", "password": "admin-pass-123"})
    assert r.status_code == 200
    csrf = client.cookies.get("csrf_token")
    users = client.get("/api/admin/users").json()["users"]
    target = next(u for u in users if u["login"] == "user1")
    assert target["pro"] is False
    g = client.put(f"/api/admin/users/{target['id']}", headers={"X-CSRF-Token": csrf}, json={"unlimited": True})
    assert g.status_code == 200 and g.json()["unlimited"] is True
    users2 = client.get("/api/admin/users").json()["users"]
    assert next(u for u in users2 if u["login"] == "user1")["pro"] is True
    # админ не может снять с себя роль
    me = next(u for u in users2 if u["login"] == "admin")
    bad = client.put(f"/api/admin/users/{me['id']}", headers={"X-CSRF-Token": csrf}, json={"role": "user"})
    assert bad.status_code == 400
    # сброс пароля пользователю (восстановления по почте нет)
    assert client.put(f"/api/admin/users/{target['id']}", headers={"X-CSRF-Token": csrf}, json={"password": "short"}).status_code == 422
    assert client.put(f"/api/admin/users/{target['id']}", headers={"X-CSRF-Token": csrf}, json={"password": "new-password-1"}).status_code == 200
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert client.post("/api/auth/login", json={"login": "user1", "password": "password123"}).status_code == 401
    assert client.post("/api/auth/login", json={"login": "user1", "password": "new-password-1"}).status_code == 200
