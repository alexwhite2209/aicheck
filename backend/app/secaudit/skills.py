"""Карта соответствия навыков OWASP (репозиторий Anthropic-Cybersecurity-Skills) нашему модулю.

mode: S1 — пассивная проверка на любом сайте (включена); S2 — активная проба, только для подтверждённого владельцем
домена (в MVP выключена, SECURITY_ACTIVE_ENABLED=false). Эксплойтовые навыки используются как методика для S2 и не
запускаются по чужим сайтам.
"""
REPO = "https://github.com/mukul975/Anthropic-Cybersecurity-Skills"
REPO_SKILL = REPO + "/tree/main/skills/"

# (название, навыки-источники в репозитории, режим, наши проверки, статус)
SKILLS = [
    {"name": "Аудит заголовков безопасности", "category": "Конфигурация", "mode": "S1",
     "sources": ["performing-security-headers-audit"], "checks": ["SEC_HEADERS_*", "SEC_MIXED_CONTENT_010"], "status": "active"},
    {"name": "Чувствительные данные и утечки", "category": "Утечки данных", "mode": "S1",
     "sources": ["testing-for-sensitive-data-exposure", "implementing-secrets-scanning-in-ci-cd"],
     "checks": ["SEC_SECRETS_003", "SEC_EXPOSURE_*"], "status": "active"},
    {"name": "CORS", "category": "Конфигурация", "mode": "S1",
     "sources": ["testing-cors-misconfiguration"], "checks": ["SEC_CORS_005"], "status": "active"},
    {"name": "JWT", "category": "Защита данных", "mode": "S1",
     "sources": ["testing-for-json-web-token-vulnerabilities", "testing-jwt-token-security", "implementing-jwt-signing-and-verification"],
     "checks": ["SEC_JWT_008"], "status": "active"},
    {"name": "Cookie и сессии", "category": "Защита данных", "mode": "S1",
     "sources": ["testing-api-authentication-weaknesses"], "checks": ["SEC_COOKIE_FLAGS_002"], "status": "active"},
    {"name": "Open Redirect", "category": "Конфигурация", "mode": "S1",
     "sources": ["testing-for-open-redirect-vulnerabilities"], "checks": ["SEC_REDIRECT_PARAM_007"], "status": "active"},
    {"name": "SQL Injection (признаки)", "category": "Конфигурация", "mode": "S1",
     "sources": ["testing-for-sensitive-data-exposure", "exploiting-sql-injection-vulnerabilities"], "checks": ["SEC_SQL_ERRORS_006"], "status": "active"},
    {"name": "Безопасность API", "category": "Конфигурация", "mode": "S1",
     "sources": ["conducting-api-security-testing", "detecting-shadow-api-endpoints", "performing-api-inventory-and-discovery"],
     "checks": ["SEC_API_SURFACE_011"], "status": "active"},
    {"name": "Раскрытие версий ПО / CMS", "category": "Конфигурация", "mode": "S1",
     "sources": ["performing-web-application-penetration-test", "performing-web-application-scanning-with-nikto"],
     "checks": ["SEC_SOFTWARE_009"], "status": "active"},
    {"name": "Обход каталога (признаки)", "category": "Конфигурация", "mode": "S1",
     "sources": ["performing-directory-traversal-testing"], "checks": ["SEC_PATH_PARAM_013"], "status": "active"},
    {"name": "CSRF (признаки)", "category": "Защита данных", "mode": "S1",
     "sources": ["performing-csrf-attack-simulation"], "checks": ["SEC_CSRF_014"], "status": "active"},
    {"name": "Broken Access Control / IDOR (признаки)", "category": "Доступ", "mode": "S1",
     "sources": ["testing-for-broken-access-control", "exploiting-idor-vulnerabilities", "detecting-broken-object-property-level-authorization"],
     "checks": ["SEC_ACCESS_HINTS_012"], "status": "active"},
    {"name": "Триаж уязвимостей", "category": "Методология", "mode": "S1",
     "sources": ["performing-web-application-vulnerability-triage"], "checks": ["security score, дедупликация, приоритизация"], "status": "active"},
    # --- S2: активные пробы, только подтверждённый домен (в MVP выключены)
    {"name": "XSS (активная проба)", "category": "Активные пробы", "mode": "S2",
     "sources": ["testing-for-xss-vulnerabilities"], "checks": ["безвредный маркер отражения"], "status": "verified_only"},
    {"name": "SQL Injection (активная проба)", "category": "Активные пробы", "mode": "S2",
     "sources": ["exploiting-sql-injection-vulnerabilities", "performing-second-order-sql-injection"], "checks": ["одиночная кавычка, без извлечения данных"], "status": "verified_only"},
    {"name": "Host Header Injection", "category": "Активные пробы", "mode": "S2",
     "sources": ["testing-for-host-header-injection"], "checks": ["подмена Host, анализ ответа"], "status": "verified_only"},
    {"name": "IDOR / BOLA (активная проба)", "category": "Активные пробы", "mode": "S2",
     "sources": ["exploiting-idor-vulnerabilities", "testing-api-for-broken-object-level-authorization"], "checks": ["только тест-аккаунты владельца"], "status": "verified_only"},
    {"name": "SSRF", "category": "Активные пробы", "mode": "S2",
     "sources": ["performing-blind-ssrf-exploitation"], "checks": ["безвредный коллбэк на тест-домен"], "status": "verified_only"},
]


def manifest() -> dict:
    def url(slugs):
        return [{"slug": s, "url": REPO_SKILL + s} for s in slugs]
    return {
        "repo": REPO, "license": "Apache-2.0 / авторы навыков",
        "note": "Навыки используются как методика. Пассивные проверки (S1) выполняются на любом сайте и не эксплуатируют "
                "уязвимости. Активные пробы (S2) — только для доменов, подтверждённых владельцем, в безвредном режиме; в "
                "текущей версии выключены. Capcha не обходится, доступ к чужим данным и разрушающие действия запрещены.",
        "skills": [{**s, "sources": url(s["sources"])} for s in SKILLS],
        "counts": {"s1": sum(1 for s in SKILLS if s["mode"] == "S1"), "s2": sum(1 for s in SKILLS if s["mode"] == "S2")},
    }
