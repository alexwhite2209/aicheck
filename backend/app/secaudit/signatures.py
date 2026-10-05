"""Сигнатуры для пассивного модуля безопасности (S1). Только детект — без эксплуатации."""
import re

# ---------- заголовки защиты (ожидаемые на любой странице)
# title/fact/fix — простым языком для обычного пользователя; tech — техническая деталь для разработчика
SECURITY_HEADERS = {
    "content-security-policy": {"tech": "Content-Security-Policy", "severity": "medium",
        "title": "Сайт не защищён от внедрения чужого кода",
        "fact": "Нет настройки, которая запрещает браузеру выполнять посторонние скрипты. Если на сайте найдут лазейку, злоумышленнику будет проще подменить содержимое страницы или украсть данные посетителей.",
        "fix": "Попросите разработчика или хостинг включить защиту от внедрения чужого кода (заголовок Content-Security-Policy)."},
    "x-frame-options": {"tech": "X-Frame-Options", "severity": "medium",
        "title": "Страницу можно спрятать внутри чужого сайта",
        "fact": "Ваш сайт можно встроить в поддельную страницу и обманом заставить посетителя нажать не на то, что он видит (приём «кликджекинг»).",
        "fix": "Включите запрет на встраивание сайта в чужие страницы (заголовок X-Frame-Options или frame-ancestors)."},
    "x-content-type-options": {"tech": "X-Content-Type-Options: nosniff", "severity": "low",
        "title": "Браузер может принять загруженный файл за программу",
        "fact": "Без этой настройки браузер иногда сам «угадывает» тип файла и может запустить обычный файл как код.",
        "fix": "Включите защиту от подмены типа файла (заголовок X-Content-Type-Options: nosniff)."},
    "strict-transport-security": {"tech": "Strict-Transport-Security (HSTS)", "severity": "low",
        "title": "Нет принудительного защищённого соединения",
        "fact": "Браузер не обязан всегда открывать сайт по защищённому протоколу — самое первое подключение можно перехватить.",
        "fix": "Включите постоянный переход на защищённое соединение (заголовок HSTS)."},
    "referrer-policy": {"tech": "Referrer-Policy", "severity": "low",
        "title": "Адрес вашей страницы может утекать на чужие сайты",
        "fact": "При переходе по ссылке другим сайтам может передаваться полный адрес вашей страницы — иногда с личными данными, которые попали в ссылку.",
        "fix": "Ограничьте передачу адреса страницы на сторонние сайты (заголовок Referrer-Policy)."},
    "permissions-policy": {"tech": "Permissions-Policy", "severity": "low",
        "title": "Не ограничён доступ к камере, микрофону и геолокации",
        "fact": "Не задано, какие возможности устройства (камера, микрофон, геопозиция) разрешено использовать скриптам на странице.",
        "fix": "Ограничьте доступ страницы к камере, микрофону и геолокации (заголовок Permissions-Policy)."},
}

# ---------- раскрытие версий ПО
SOFTWARE_HEADERS = ("server", "x-powered-by", "x-aspnet-version", "x-generator", "x-drupal-cache", "x-runtime")

# ---------- секреты в HTML/JS (значения маскируются). Ключи-«пустышки» публичных сервисов отсеиваются в triage.
SECRET_PATTERNS: list[tuple[str, str, str]] = [
    ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b", "AWS Access Key"),
    ("aws_secret", r"(?i)aws_secret_access_key['\"\s:=]{1,6}([A-Za-z0-9/+]{40})", "AWS Secret Key"),
    ("google_api", r"\bAIza[0-9A-Za-z\-_]{35}\b", "Google API Key"),
    ("private_key", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----", "Приватный ключ"),
    ("stripe_live", r"\bsk_live_[0-9A-Za-z]{20,}\b", "Stripe Secret Key (live)"),
    ("stripe_restricted", r"\brk_live_[0-9A-Za-z]{20,}\b", "Stripe Restricted Key"),
    ("github_token", r"\bgh[pousr]_[0-9A-Za-z]{30,}\b", "GitHub Token"),
    ("slack_token", r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b", "Slack Token"),
    ("openai", r"\bsk-(?:proj-)?[0-9A-Za-z\-_]{20,}\b", "OpenAI/совместимый ключ"),
    ("telegram_bot", r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b", "Telegram Bot Token"),
    ("yandex_oauth", r"\bAQAA[0-9A-Za-z\-_]{30,}\b", "Yandex OAuth токен"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b", "JWT-токен"),
    ("generic_secret", r"(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|passwd|password)['\"\s:=]{1,6}['\"]([^'\"\s]{12,80})['\"]", "Возможный секрет/пароль"),
    ("db_dsn", r"(?i)\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:'\"]+:[^\s@'\"]+@[^\s/'\"]+", "Строка подключения к БД с паролем"),
    ("basic_auth_url", r"https?://[^\s:/@'\"]+:[^\s:/@'\"]+@[^\s/'\"]+", "URL с логином и паролем"),
]

# публичные/клиентские ключи, которые по дизайну открыты — это не утечка
SECRET_FALSE_POSITIVE = re.compile(
    r"(6L[0-9A-Za-z_-]{38})"             # reCAPTCHA site key формата 6L...
    r"|data-sitekey|pk_live_|pk_test_|publishableKey|VAPID|измерител|metrika|gtm-|ga_measurement", re.I)

# ---------- параметры open redirect
REDIRECT_PARAMS = {"url", "next", "redirect", "redirect_uri", "redirect_url", "return", "returnurl", "return_url",
                   "goto", "dest", "destination", "continue", "r", "u", "link", "to", "out", "target", "forward"}

# ---------- типовые адреса утечек (короткий фиксированный список, только GET)
EXPOSURE_PATHS: list[tuple[str, str, str, str]] = [
    # path, id, title, severity
    ("/.git/config", "git", "Открыт репозиторий .git (/.git/config)", "critical"),
    ("/.git/HEAD", "git_head", "Открыт репозиторий .git (/.git/HEAD)", "critical"),
    ("/.env", "env", "Доступен файл .env (переменные окружения, секреты)", "critical"),
    ("/.svn/entries", "svn", "Открыт каталог .svn", "high"),
    ("/.ht_access", "htaccess", "Доступен .ht_access", "medium"),
    ("/server-status", "server_status", "Открыт /server-status (Apache)", "high"),
    ("/phpinfo.php", "phpinfo", "Доступен phpinfo.php", "high"),
    ("/.well-known/security.txt", "securitytxt", "Есть security.txt (информационно)", "info"),
    ("/backup.zip", "backup_zip", "Доступен backup.zip", "critical"),
    ("/dump.sql", "dump_sql", "Доступен дамп БД dump.sql", "critical"),
    ("/wp-config.php.bak", "wpconfig_bak", "Доступна резервная копия wp-config.php", "critical"),
]
EXPOSURE_CONFIRM = {  # как убедиться, что это реально утечка, а не кастомная 200-страница
    "git": lambda b: "[core]" in b or "repositoryformatversion" in b,
    "git_head": lambda b: b.strip().startswith("ref:") or re.fullmatch(r"[0-9a-f]{40}\s*", b or ""),
    "env": lambda b: bool(re.search(r"(?i)^[A-Z0-9_]{3,}=", b or "", re.M)) and "<html" not in (b or "").lower(),
    "svn": lambda b: "dir" in (b or "") and "<html" not in (b or "").lower(),
    "htaccess": lambda b: "<html" not in (b or "").lower() and bool(b),
    "server_status": lambda b: "Apache Server Status" in (b or ""),
    "phpinfo": lambda b: "phpinfo()" in (b or "") or "PHP Version" in (b or ""),
    "securitytxt": lambda b: "contact" in (b or "").lower(),
    "backup_zip": lambda b: True,
    "dump_sql": lambda b: bool(re.search(r"(?i)(INSERT INTO|CREATE TABLE|DROP TABLE)", b or "")),
    "wpconfig_bak": lambda b: "DB_PASSWORD" in (b or "") or "<?php" in (b or ""),
}

# ---------- признаки API
API_HINTS = re.compile(r"/(api|rest|graphql|v\d+/|swagger|openapi|api-docs|wp-json)(/|\b|\.json)", re.I)
SWAGGER_PATHS = ("/swagger", "/swagger-ui.html", "/api-docs", "/openapi.json", "/graphql", "/v3/api-docs")

# ---------- CMS / fingerprint по телу и путям
CMS_PATTERNS = [
    ("WordPress", r"/wp-content/|/wp-includes/|wp-json|generator\"\s+content=\"WordPress"),
    ("1C-Bitrix", r"/bitrix/|BX\.|bitrix_sessid"),
    ("Joomla", r"/components/com_|Joomla!"),
    ("Drupal", r"Drupal\.settings|/sites/default/files"),
    ("Tilda", r"tildacdn|tilda"),
    ("Modx", r"MODX|/manager/assets"),
]

ACCESS_ID_PARAM = re.compile(r"[?&](id|user_id|uid|account|order|order_id|invoice|doc|file_id|num)=\d+", re.I)

# параметры, похожие на путь к файлу (поверхность Path Traversal / LFI)
