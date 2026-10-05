"""Security Skills: 10 пассивных направлений + внутренний триаж.

Принцип: открыть сайт → посмотреть то, что он сам публично отдаёт → зафиксировать факт → сопоставить → дать
рекомендацию. Никаких payload-ов, подбора ключей, эксплуатации и запросов к чужим объектам. Активных проверок
(XSS, SQL-инъекции, подмена Host, активные IDOR/BOLA) в сервисе нет. Входят в тариф «Полный аудит».
"""
REPO = "https://github.com/mukul975/Anthropic-Cybersecurity-Skills"
REPO_SKILL = REPO + "/tree/main/skills/"

# (название, навыки-источники в репозитории (методика), наши проверки)
SKILLS = [
    {"name": "Security Headers", "category": "Конфигурация",
     "sources": ["performing-security-headers-audit"], "checks": ["SEC_HEADERS_*", "SEC_MIXED_CONTENT_010"],
     "does": "Проверка HTTP-заголовков защиты."},
    {"name": "Cookie Security", "category": "Защита данных",
     "sources": ["testing-api-authentication-weaknesses"], "checks": ["SEC_COOKIE_FLAGS_002"],
     "does": "Secure, HttpOnly, SameSite и конфигурация cookie."},
    {"name": "Sensitive Data Exposure", "category": "Утечки данных",
     "sources": ["testing-for-sensitive-data-exposure"], "checks": ["SEC_EXPOSURE_*"],
     "does": "Поиск явно раскрываемых чувствительных данных (публично доступные служебные файлы и бэкапы)."},
    {"name": "Secrets Exposure", "category": "Утечки данных",
     "sources": ["implementing-secrets-scanning-in-ci-cd"], "checks": ["SEC_SECRETS_003"],
     "does": "Потенциальные секреты в публичном HTML/JS; значения всегда маскируются."},
    {"name": "CORS Security", "category": "Конфигурация",
     "sources": ["testing-cors-misconfiguration"], "checks": ["SEC_CORS_005"],
     "does": "Анализ публичных CORS-заголовков."},
    {"name": "Open Redirect Signals", "category": "Конфигурация",
     "sources": ["testing-for-open-redirect-vulnerabilities"], "checks": ["SEC_REDIRECT_PARAM_007"],
     "does": "Признаки открытого редиректа в параметрах и найденных ссылках, без эксплуатации."},
    {"name": "JWT Security", "category": "Защита данных",
     "sources": ["testing-for-json-web-token-vulnerabilities", "testing-jwt-token-security"], "checks": ["SEC_JWT_008"],
     "does": "Публично обнаруженные токены/конфигурация JWT: только декодирование, без подбора ключей и доступа к аккаунтам."},
    {"name": "Software Disclosure", "category": "Конфигурация",
     "sources": ["performing-web-application-scanning-with-nikto"], "checks": ["SEC_SOFTWARE_009"],
     "does": "Раскрытие версий сервера, CMS, фреймворков и компонентов."},
    {"name": "API Security Surface", "category": "Конфигурация",
     "sources": ["conducting-api-security-testing", "performing-api-inventory-and-discovery"], "checks": ["SEC_API_SURFACE_011"],
     "does": "Обнаруженные API, Swagger/OpenAPI, GraphQL и публичная поверхность API."},
    {"name": "Access Control / BOLA Signals", "category": "Доступ",
     "sources": ["testing-for-broken-access-control"], "checks": ["SEC_ACCESS_HINTS_012"],
     "does": "Только пассивные признаки потенциальной проблемы доступа, без попытки получить чужой объект."},
]

# Внутренний механизм обработки результатов (не отдельная проверка): дедупликация, снижение false positive,
# severity и confidence. Реализован в secaudit/engine.py::triage.
TRIAGE = {"name": "Vulnerability Triage", "sources": ["performing-web-application-vulnerability-triage"]}


def manifest() -> dict:
    def url(slugs):
        return [{"slug": s, "url": REPO_SKILL + s} for s in slugs]
    return {
        "repo": REPO, "license": "Apache-2.0 / авторы навыков",
        "note": "Навыки используются как методика. Сервис только смотрит то, что сайт сам публично отдаёт: без payload-ов, "
                "подбора ключей, эксплуатации, обхода captcha и доступа к чужим данным.",
        "skills": [{**s, "sources": url(s["sources"])} for s in SKILLS],
        "triage": {**TRIAGE, "sources": url(TRIAGE["sources"])},
        "counts": {"skills": len(SKILLS)},
    }
