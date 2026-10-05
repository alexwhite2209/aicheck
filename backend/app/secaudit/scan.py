"""Пассивный анализ безопасности (S1): собранные данные → находки. Без эксплуатации."""
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

from . import signatures as sig

FAIL, REVIEW, PASS, INFO = "FAIL", "REVIEW", "PASS", "INFO"


@dataclass
class Finding:
    id: str
    skill: str
    category: str
    title: str
    severity: str  # critical|high|medium|low|info
    status: str
    fact: str
    recommendation: str
    evidence: list[dict] = field(default_factory=list)
    touches_pd: bool = False
    confidence: str = "probable"
    tech: str = ""  # техническая деталь для разработчика (мелким шрифтом)

    def as_dict(self) -> dict:
        return {"id": self.id, "skill": self.skill, "category": self.category, "title": self.title, "severity": self.severity,
                "status": self.status, "fact": self.fact, "recommendation": self.recommendation, "evidence": self.evidence[:6],
                "touches_pd": self.touches_pd, "confidence": self.confidence, "tech": self.tech}


def mask(value: str) -> str:
    v = value.strip()
    if len(v) <= 8:
        return v[:2] + "***"
    return v[:4] + "…" + v[-3:] + f" ({len(v)} симв.)"


def _host(u: str) -> str:
    return (urlsplit(u).hostname or "").lower()


def scan(facts: dict, sec: dict) -> list[Finding]:
    """facts — из extract.build_facts; sec — {main_headers, pages_raw, cookies_raw, https, collected, external_js}."""
    out: list[Finding] = []
    headers = {k.lower(): v for k, v in (sec.get("main_headers") or {}).items()}
    pages = sec.get("pages_raw") or []
    https = facts.get("https", {})
    collects_pd = bool([f for f in facts.get("forms", []) if f.get("has_pd")]) or facts.get("mode") == "ecommerce"

    _headers(out, headers, https)
    _cookies(out, sec.get("cookies_raw") or [], https)
    _secrets(out, pages, sec.get("external_js") or [])
    _exposure(out, sec.get("collected") or {})
    _cors(out, sec.get("collected") or {})
    _redirect_params(out, pages)
    _jwt(out, sec.get("cookies_raw") or [], pages)
    _software(out, headers, pages)
    _mixed_content(out, pages, https)
    _api_surface(out, facts, pages)
    _access_hints(out, facts, pages)
    _meta_links(out, pages)

    for f in out:
        if f.touches_pd is False:
            f.touches_pd = collects_pd and f.category in ("Защита данных", "Утечки данных", "Конфигурация")
    return out


def _headers(out, h, https):
    missing = []
    present = []
    for key, spec in sig.SECURITY_HEADERS.items():
        if key == "strict-transport-security" and https.get("final_scheme") != "https":
            continue
        (present if key in h else missing).append((key, spec))
    for key, spec in missing:
        sev = spec["severity"]
        out.append(Finding(f"SEC_HEADERS_{key}", "Защита сайта", "Конфигурация", spec["title"], sev,
                           REVIEW if sev in ("low", "medium") else FAIL, spec["fact"], spec["fix"],
                           confidence="confirmed", tech=f"Отсутствует HTTP-заголовок {spec['tech']}"))
    if present:
        out.append(Finding("SEC_HEADERS_OK", "Защита сайта", "Конфигурация", "Часть базовых защит уже включена", "info", PASS,
                           "На сайте уже настроены некоторые защитные заголовки — это хорошо.",
                           "Проверьте остальные пункты из этого раздела.", confidence="confirmed",
                           tech="Присутствуют: " + ", ".join(sig.SECURITY_HEADERS[k]["tech"] for k, _ in present)))


def _cookies(out, cookies, https):
    weak = []
    for c in cookies:
        name = c.get("name", "")
        is_auth = bool(re.search(r"sess|sid|auth|token|login|secure|phpsessid|remember|jwt", name, re.I))
        problems = []
        if is_auth or https.get("final_scheme") == "https":
            if not c.get("secure") and https.get("final_scheme") == "https":
                problems.append("без Secure")
            if is_auth and not c.get("httpOnly"):
                problems.append("без HttpOnly")
            same = (c.get("sameSite") or "").lower()
            if same in ("", "none") and is_auth:
                problems.append("SameSite не задан" if not same else "SameSite=None")
        if problems and (is_auth or len(weak) < 8):
            weak.append({"page": "", "label": f"cookie {name}", "snippet": ", ".join(problems)})
    if weak:
        out.append(Finding("SEC_COOKIE_FLAGS_002", "Защита данных", "Защита данных", "Файлы входа (cookie) защищены не полностью", "medium", REVIEW,
                           f"У {len(weak)} служебных файлов-cookie не хватает защитных пометок. Из-за этого их проще перехватить или украсть сессию пользователя — например, войти в чужой личный кабинет.",
                           "Попросите разработчика включить для файлов входа защитные флаги Secure, HttpOnly и SameSite.",
                           evidence=weak, confidence="confirmed", tech="cookie без Secure/HttpOnly/SameSite"))


def _secrets(out, pages, external_js):
    hits: dict[str, dict] = {}
    sources = [(p.get("url", ""), p.get("inline_scripts", "") + "\n" + (p.get("text", "")[:40000])) for p in pages]
    sources += [(j["url"], j["body"]) for j in external_js]
    for url, text in sources:
        if not text:
            continue
        for sid, pattern, label in sig.SECRET_PATTERNS:
            for m in re.finditer(pattern, text):
                raw = m.group(0)
                if sig.SECRET_FALSE_POSITIVE.search(m.group(0)) or (m.groups() and sig.SECRET_FALSE_POSITIVE.search(m.group(1) or "")):
                    continue
                val = m.group(1) if (m.groups() and m.group(1)) else raw
                key = (sid, val[:12])
                if key in hits:
                    continue
                hits[key] = {"page": url, "label": label, "snippet": mask(val)}
    if hits:
        crit = any(k[0] in ("private_key", "aws_secret", "stripe_live", "db_dsn", "github_token", "openai", "basic_auth_url") for k in hits)
        out.append(Finding("SEC_SECRETS_003", "Утечка паролей и ключей", "Утечки данных", "В коде сайта видны пароли или ключи доступа", "critical" if crit else "high", FAIL,
                           f"Прямо в коде страниц нашлись секретные ключи или пароли ({len(hits)} шт.). Их видит любой посетитель — этим могут воспользоваться, чтобы получить доступ к вашим сервисам или деньгам. В отчёте значения скрыты.",
                           "Срочно уберите эти ключи и пароли из кода сайта, смените их на новые и храните только на сервере. Это стоит сделать в первую очередь.",
                           evidence=list(hits.values())[:8], touches_pd=True, confidence="probable", tech="секреты в HTML/JS"))


def _exposure(out, collected):
    human = {
        "git": "Служебная папка с исходным кодом сайта открыта всем",
        "git_head": "Служебная папка с исходным кодом сайта открыта всем",
        "env": "Файл с паролями и настройками сайта открыт всем",
        "svn": "Служебная папка с кодом сайта открыта всем",
        "server_status": "Внутренняя статистика сервера доступна всем",
        "phpinfo": "Страница с настройками сервера доступна всем",
        "backup_zip": "Резервная копия сайта скачивается кем угодно",
        "dump_sql": "Копия базы данных скачивается кем угодно",
        "wpconfig_bak": "Резервная копия файла с паролями базы доступна всем",
    }
    for e in collected.get("exposure", []):
        title = human.get(e["id"], e["title"])
        out.append(Finding(f"SEC_EXPOSURE_{e['id']}", "Утечка файлов", "Утечки данных", title, e["severity"], FAIL,
                           f"По прямой ссылке {e['path']} открывается служебный файл или папка, которые должны быть скрыты. Через них посторонние могут скачать код, пароли или данные сайта.",
                           "Закройте доступ к этому адресу на хостинге и удалите из общего доступа резервные копии и дампы базы. Обратитесь к разработчику или в поддержку хостинга.",
                           evidence=[{"page": e["path"], "label": "Открывается без пароля", "snippet": e["path"]}],
                           touches_pd=True, confidence="confirmed", tech=f"{e['path']} → HTTP {e['status']}"))


def _cors(out, collected):
    cors = collected.get("cors")
    if not cors:
        return
    acao = (cors.get("acao") or "").strip()
    acac = (cors.get("acac") or "").lower() == "true"
    probe = collected.get("probe_origin", "")
    if acao == "*" and acac:
        out.append(Finding("SEC_CORS_005", "Доступ других сайтов к данным", "Конфигурация", "Другие сайты могут читать данные ваших пользователей", "high", FAIL,
                           "Сайт разрешает любому стороннему сайту обращаться к вашим данным вместе с данными входа пользователя. Этим могут воспользоваться, чтобы получить личные данные посетителей с чужой страницы.",
                           "Попросите разработчика разрешить обращение к данным только вашим доверенным адресам, а не «всем подряд».",
                           evidence=[{"page": "", "label": "Настройка доступа", "snippet": "разрешено всем + с передачей данных входа"}], confidence="confirmed", tech="ACAO: * вместе с Allow-Credentials: true"))
    elif acao and (acao == probe or acao == "*"):
        sev = "high" if acao == probe else "low"
        out.append(Finding("SEC_CORS_005", "Доступ других сайтов к данным", "Конфигурация", "Чужие сайты могут обращаться к данным вашего сайта", sev, REVIEW,
                           "Сайт соглашается отдавать данные любому стороннему сайту, который попросит. В зависимости от того, что это за данные, они могут попасть к посторонним."
                           if acao == probe else "Данные сайта доступны для обращения с любого домена — это нормально только для полностью публичной информации.",
                           "Ограничьте круг сайтов, которым разрешено обращаться к данным, списком доверенных адресов.",
                           evidence=[{"page": "", "label": "Настройка доступа", "snippet": f"разрешено: {acao}"}], confidence="confirmed", tech=f"Access-Control-Allow-Origin: {acao}"))



def _redirect_params(out, pages):
    found = {}
    for p in pages:
        for ln in p.get("links", []):
            q = parse_qs(urlsplit(ln.get("href", "")).query)
            for param in q:
                if param.lower() in sig.REDIRECT_PARAMS:
                    found.setdefault(param.lower(), {"page": p.get("url", ""), "label": f"параметр ?{param}=", "snippet": ln.get("href", "")[:160]})
    if found:
        out.append(Finding("SEC_REDIRECT_PARAM_007", "Перенаправление на чужие сайты", "Конфигурация", "Сайт может перенаправлять посетителей на чужие адреса", "low", REVIEW,
                           "На сайте есть ссылки, которые перебрасывают пользователя на адрес из параметра. Если это не ограничено, мошенники могут сделать ссылку с вашего сайта, ведущую на поддельную страницу (фишинг).",
                           "Разрешите переход только на ваши собственные адреса, а не на любой адрес из ссылки.",
                           evidence=list(found.values())[:5], confidence="probable", tech="параметры open redirect: " + ", ".join(found)))


def _jwt(out, cookies, pages):
    jwt_re = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*")
    tokens = []
    for c in cookies:
        m = jwt_re.search(c.get("value", "") or "")
        if m:
            tokens.append(("cookie " + c.get("name", ""), m.group(0)))
    for p in pages[:3]:
        for m in jwt_re.finditer(p.get("inline_scripts", "")[:40000]):
            tokens.append((p.get("url", ""), m.group(0)))
            break
    if not tokens:
        return
    import base64
    import json as _json
    problems = []
    for where, tok in tokens[:4]:
        parts = tok.split(".")
        try:
            head = _json.loads(base64.urlsafe_b64decode(parts[0] + "=" * (-len(parts[0]) % 4)))
            payload = _json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        except Exception:
            continue
        issues = []
        if str(head.get("alg", "")).lower() == "none":
            issues.append("alg=none (подпись отсутствует)")
        if head.get("alg", "").upper().startswith("HS") and len(parts[2]) < 20:
            issues.append("слабая/короткая подпись")
        if "exp" not in payload:
            issues.append("нет срока действия exp")
        leak = [k for k in payload if re.search(r"pass|secret|email|phone|card|inn|snils|паспорт", k, re.I)]
        if leak:
            issues.append("в payload чувствительные поля: " + ", ".join(leak[:4]))
        if issues:
            problems.append({"page": where, "label": "JWT", "snippet": "; ".join(issues)})
    if problems:
        out.append(Finding("SEC_JWT_008", "Токены входа защищены слабо", "Защита данных", "Электронные пропуска пользователей защищены слабо", "high", REVIEW,
                           f"Токены, по которым сайт узнаёт вошедшего пользователя, настроены небезопасно ({len(problems)}). В таком виде их проще подделать и войти под чужим именем или прочитать лишние данные. Мы только посмотрели настройку, подбор ключа не делали.",
                           "Попросите разработчика использовать надёжную подпись токена, ограничить срок его жизни и не хранить в нём лишние личные данные.",
                           evidence=problems, touches_pd=True, confidence="probable", tech="JWT: " + "; ".join(p["snippet"] for p in problems[:2])))


def _software(out, headers, pages):
    disclosed = []
    for h in sig.SOFTWARE_HEADERS:
        if h in headers and re.search(r"\d", headers[h]):
            disclosed.append({"page": "", "label": h, "snippet": headers[h][:120]})
    cms = None
    blob = " ".join(p.get("inline_scripts", "")[:4000] + " " + " ".join(p.get("scripts", [])) for p in pages[:3])
    for name, pat in sig.CMS_PATTERNS:
        if re.search(pat, blob, re.I):
            cms = name
            break
    if disclosed or cms:
        parts = []
        if disclosed:
            parts.append("версии ПО в заголовках (" + ", ".join(d["label"] for d in disclosed) + ")")
        if cms:
            parts.append(f"CMS: {cms}")
        out.append(Finding("SEC_SOFTWARE_009", "Видно, на чём сделан сайт", "Конфигурация", "Сайт открыто сообщает свою «начинку» и версии программ", "low", REVIEW,
                           "Сайт показывает, на каких программах он работает и каких версий (" + "; ".join(parts) + "). Зная это, злоумышленнику проще подобрать готовую уязвимость именно под вашу версию.",
                           "Попросите разработчика скрыть версии программ и вовремя обновлять движок сайта (CMS) и его компоненты.",
                           evidence=disclosed[:5], confidence="confirmed", tech="; ".join(f"{d['label']}: {d['snippet']}" for d in disclosed[:3]) or (cms or "")))


def _mixed_content(out, pages, https):
    if https.get("final_scheme") != "https":
        return
    ev = []
    for p in pages:
        for src in p.get("scripts", []) + p.get("iframes", []):
            if src.startswith("http://"):
                ev.append({"page": p.get("url", ""), "label": "HTTP-ресурс на HTTPS-странице", "snippet": src[:160]})
    if ev:
        out.append(Finding("SEC_MIXED_CONTENT_010", "Защищённое и незащищённое вперемешку", "Конфигурация", "На защищённой странице есть незащищённые вставки", "medium", REVIEW,
                           f"Сам сайт открывается по защищённому протоколу, но часть содержимого ({len(ev)}) подгружается по незащищённому. Такие вставки можно перехватить и подменить по дороге.",
                           "Попросите разработчика загружать все картинки, скрипты и вставки только по защищённому протоколу (https).",
                           evidence=ev[:5], confidence="confirmed", tech="HTTP-ресурсы на HTTPS-странице"))


def _api_surface(out, facts, pages):
    endpoints = set()
    for p in pages:
        for ln in p.get("links", []) + [{"href": s} for s in p.get("scripts", [])]:
            if sig.API_HINTS.search(ln.get("href", "")):
                endpoints.add(urlsplit(ln["href"]).path[:80])
    if endpoints:
        out.append(Finding("SEC_API_SURFACE_011", "У сайта есть программный интерфейс (API)", "Конфигурация", "У сайта есть точки обмена данными (API), их стоит проверить", "info", REVIEW,
                           f"Найдены адреса, через которые сайт обменивается данными с приложениями ({len(endpoints)}). Через них нередко утекают данные, если не настроены проверка входа и ограничения.",
                           "Убедитесь, что эти адреса требуют вход, ограничивают частоту запросов и не отдают лишнего; закройте открытую документацию API, если она не нужна.",
                           evidence=[{"page": e, "label": "Адрес API", "snippet": e} for e in list(endpoints)[:6]], confidence="probable", tech="endpoints: " + ", ".join(list(endpoints)[:6])))




def _form_ev(form: dict) -> dict:
    return {"page": form.get("page", ""), "label": f"Форма {form.get('ref', '')} ({form.get('purpose', '')})", "snippet": ""}


_META_RE = re.compile(r"https?://(?:[\w.-]+\.)?(facebook\.com|fb\.com|instagram\.com|instagr\.am)(/|$)", re.I)


def _meta_links(out, pages):
    hits = {}
    for p in pages:
        for ln in p.get("links", []) + [{"href": s} for s in p.get("iframes", [])]:
            m = _META_RE.search(ln.get("href", ""))
            if m:
                hits.setdefault(ln["href"][:160], {"page": p.get("url", ""), "label": "Ссылка на ресурс Meta", "snippet": ln["href"][:160]})
    if hits:
        out.append(Finding("SEC_META_LINKS_015", "Запрещённые ресурсы", "Внешние сервисы", "На сайте есть ссылки на Facebook / Instagram (Meta)", "medium", REVIEW,
                           f"Найдены ссылки или кнопки на Facebook/Instagram ({len(hits)}). Компания Meta признана в России экстремистской, её соцсети Facebook и Instagram заблокированы. Такие ссылки на сайте — повод для претензий.",
                           "Уберите ссылки и кнопки на Facebook и Instagram. Если упоминаете Meta в тексте, добавляйте пометку, что организация признана экстремистской и запрещена в РФ.",
                           evidence=list(hits.values())[:6], confidence="confirmed", tech="ссылки на facebook.com / instagram.com"))


def _access_hints(out, facts, pages):
    ev = []
    for p in pages:
        if sig.ACCESS_ID_PARAM.search(p.get("url", "")):
            ev.append({"page": p.get("url", ""), "label": "Последовательный идентификатор в URL", "snippet": p.get("url", "")[:160]})
    if facts.get("auth", {}).get("has_auth") and ev:
        out.append(Finding("SEC_ACCESS_HINTS_012", "Можно подобрать чужие страницы по номеру", "Доступ", "Личные страницы можно попробовать открыть, подставив чужой номер", "medium", REVIEW,
                           f"В адресах страниц есть простые номера ({len(ev)}), а на сайте есть вход. Если сайт не проверяет, чьи это данные, пользователь может поменять номер в адресе и открыть чужой заказ или профиль.",
                           "Попросите разработчика проверять на сервере, что пользователь открывает только свои данные. Полную проверку мы можем сделать на подтверждённом домене с тестовыми аккаунтами.",
                           evidence=ev[:5], confidence="manual", tech="последовательные ID в URL + авторизация (IDOR/BOLA)"))
