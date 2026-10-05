"""Пассивный модуль безопасности: детект без эксплуатации, маскировка секретов, security score."""
from app.secaudit import scan
from app.secaudit.engine import security_score, triage
from app.secaudit.registries import check_domain_rdap


def _facts(**over):
    f = {"https": {"final_scheme": "https"}, "forms": [], "mode": "base", "auth": {"has_auth": False},
         "company_details": {"inn": []}, "host": "example.ru"}
    f.update(over)
    return f


def _sec(headers=None, pages=None, cookies=None, collected=None, external_js=None):
    return {"main_headers": headers or {}, "pages_raw": pages or [], "cookies_raw": cookies or [],
            "https": {"final_scheme": "https"}, "collected": collected or {}, "external_js": external_js or []}


def test_missing_security_headers_flagged():
    out = scan.scan(_facts(), _sec(headers={"content-type": "text/html"}))
    ids = {f.id for f in out}
    assert "SEC_HEADERS_content-security-policy" in ids
    assert any(f.severity == "medium" for f in out if f.id.startswith("SEC_HEADERS_x-frame"))


def test_secrets_detected_and_masked():
    page = {"url": "https://example.ru/", "inline_scripts": 'var k="AKIAIOSFODNN7EXAMPLE"; const t="sk_live_abcdefghijklmnop1234567";', "text": "", "scripts": [], "links": [], "iframes": []}
    out = [f for f in scan.scan(_facts(), _sec(pages=[page])) if f.id == "SEC_SECRETS_003"]
    assert out and out[0].status == "FAIL"
    blob = " ".join(e["snippet"] for e in out[0].evidence)
    assert "AKIAIOSFODNN7EXAMPLE" not in blob and "sk_live_abcdefghijklmnop1234567" not in blob
    assert "…" in blob or "***" in blob


def test_recaptcha_key_not_flagged_as_secret():
    page = {"url": "https://example.ru/", "inline_scripts": 'data-sitekey="6LcABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ab"', "text": "", "scripts": [], "links": [], "iframes": []}
    assert not [f for f in scan.scan(_facts(), _sec(pages=[page])) if f.id == "SEC_SECRETS_003"]


def test_cors_wildcard_with_credentials_is_fail():
    out = [f for f in scan.scan(_facts(), _sec(collected={"cors": {"acao": "*", "acac": "true"}})) if f.id == "SEC_CORS_005"]
    assert out and out[0].status == "FAIL" and out[0].severity == "high"


def test_cors_reflects_origin():
    out = [f for f in scan.scan(_facts(), _sec(collected={"cors": {"acao": "https://p.example", "acac": "false"}, "probe_origin": "https://p.example"})) if f.id == "SEC_CORS_005"]
    assert out and out[0].severity == "high"


def test_exposed_git_is_critical():
    collected = {"exposure": [{"id": "git", "path": "/.git/config", "title": "Открыт .git", "severity": "critical", "status": 200}]}
    out = [f for f in scan.scan(_facts(), _sec(collected=collected)) if f.id.startswith("SEC_EXPOSURE_")]
    assert out and out[0].severity == "critical" and out[0].status == "FAIL"


def test_cookie_without_flags():
    cookies = [{"name": "PHPSESSID", "value": "x", "secure": False, "httpOnly": False, "sameSite": ""}]
    out = [f for f in scan.scan(_facts(), _sec(cookies=cookies)) if f.id == "SEC_COOKIE_FLAGS_002"]
    assert out and "HttpOnly" in out[0].evidence[0]["snippet"]


def test_jwt_alg_none_flagged():
    import base64, json
    head = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"email": "a@b.ru"}).encode()).decode().rstrip("=")
    cookies = [{"name": "auth", "value": f"{head}.{payload}.", "secure": True, "httpOnly": True, "sameSite": "Lax"}]
    out = [f for f in scan.scan(_facts(), _sec(cookies=cookies)) if f.id == "SEC_JWT_008"]
    assert out and "none" in out[0].evidence[0]["snippet"]


def test_sql_error_leak():
    page = {"url": "https://example.ru/", "text": "You have an error in your SQL syntax; check the manual that corresponds to your MySQL", "inline_scripts": "", "scripts": [], "links": [], "iframes": []}
    out = [f for f in scan.scan(_facts(), _sec(pages=[page])) if f.id == "SEC_SQL_ERRORS_006"]
    assert out and out[0].status == "REVIEW"


def test_pd_touching_finding_marked():
    collected = {"exposure": [{"id": "env", "path": "/.env", "title": "Доступен .env", "severity": "critical", "status": 200}]}
    out = scan.scan(_facts(forms=[{"has_pd": True}]), _sec(collected=collected))
    env = [f for f in out if f.id == "SEC_EXPOSURE_env"][0]
    assert env.touches_pd is True


def test_security_score_excludes_info():
    from app.secaudit.scan import Finding
    fs = [Finding("a", "s", "c", "t", "high", "FAIL", "f", "r"), Finding("b", "s", "c", "t", "low", "PASS", "f", "r"),
          Finding("c", "s", "c", "t", "critical", "INFO", "f", "r")]
    # (6*0 + 1*1) / (6+1) = 1/7 ≈ 14
    assert security_score(fs) == 14


def test_triage_dedup():
    from app.secaudit.scan import Finding
    fs = [Finding("a", "s", "c", "t", "high", "FAIL", "f", "r"), Finding("a", "s", "c", "t", "high", "FAIL", "f", "r")]
    assert len(triage(fs)) == 1


def test_rdap_non_ru_domain_graceful():
    r = check_domain_rdap("example.com")
    assert r["available"] is False
