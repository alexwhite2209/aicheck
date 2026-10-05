# Security Skills — пассивные проверки безопасности

Входят в тариф **«Полный аудит» (299 ₽)**; отдельного платного продукта «проверка безопасности» нет.

Принцип работы: **открыл сайт → посмотрел то, что сайт сам публично отдаёт → зафиксировал факт → сопоставил → дал рекомендацию.**

Методика опирается на открытый набор навыков OWASP (https://github.com/mukul975/Anthropic-Cybersecurity-Skills);
соответствие навыков и проверок — `backend/app/secaudit/skills.py`, публично отдаётся на `/methodology`.

## 10 направлений

| # | Направление | Что делаем | Код проверки |
|---|---|---|---|
| 1 | Security Headers | Проверка HTTP-заголовков защиты | `SEC_HEADERS_*`, `SEC_MIXED_CONTENT_010` |
| 2 | Cookie Security | Secure, HttpOnly, SameSite и конфигурация cookie | `SEC_COOKIE_FLAGS_002` |
| 3 | Sensitive Data Exposure | Явно раскрываемые чувствительные данные (публично доступные служебные файлы, бэкапы) | `SEC_EXPOSURE_*` |
| 4 | Secrets Exposure | Потенциальные секреты в публичном HTML/JS; значения всегда маскируются | `SEC_SECRETS_003` |
| 5 | CORS Security | Анализ публичных CORS-заголовков | `SEC_CORS_005` |
| 6 | Open Redirect Signals | Признаки открытого редиректа в параметрах и найденных ссылках, без эксплуатации | `SEC_REDIRECT_PARAM_007` |
| 7 | JWT Security | Публично обнаруженные токены/конфигурация JWT: только декодирование, без подбора ключей и доступа к аккаунтам | `SEC_JWT_008` |
| 8 | Software Disclosure | Раскрытие версий сервера, CMS, фреймворков, компонентов | `SEC_SOFTWARE_009` |
| 9 | API Security Surface | Обнаруженные API, Swagger/OpenAPI, GraphQL, публичная поверхность API | `SEC_API_SURFACE_011` |
| 10 | Access Control / BOLA Signals | Только пассивные признаки потенциальной проблемы доступа, без попытки получить чужой объект | `SEC_ACCESS_HINTS_012` |

**Vulnerability Triage** — не отдельная проверка, а внутренний механизм обработки результатов: дедупликация,
снижение false positive, severity и confidence (`secaudit/engine.py`). Итог — Security score и связь с 152-ФЗ ст. 19
для сайтов, которые собирают персональные данные.

## Чего в сервисе нет (и не будет)

- XSS-проверок с отправкой payload;
- SQL Injection probes;
- Host Header Injection probes;
- активных IDOR/BOLA-запросов;
- любых попыток эксплуатации, подбора ключей, входа в аккаунты, обхода капчи, доступа к чужим данным.

Раньше в документации был режим «S2 — активные пробы» с подтверждением владения доменом. Он удалён полностью:
в коде, настройках (`SECURITY_ACTIVE_ENABLED`), API (`/api/user/sites/{id}/verify`) и интерфейсе.

## Регистры

Домен (RDAP), ЕГРЮЛ/ЕГРИП (DaData или ссылка на egrul.nalog.ru) и реестр операторов ПД РКН — `secaudit/registries.py`.
