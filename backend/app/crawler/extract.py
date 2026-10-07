"""Сырые данные краулера → единый объект фактов (п. 14 ТЗ).

Здесь только факты: что найдено, где и с каким доказательством. Юридических выводов нет.
"""
import hashlib
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlsplit

from . import signatures as sig
from .requisites import extract_requisites
from .site_type import SITE_TYPE_RU, classify, ecommerce_signals

# ---------- поля форм
PD_PATTERNS: list[tuple[str, str]] = [
    ("password", r"парол|password|passwd"),
    ("email", r"e-?mail|электронн\w*\s+почт|эл\.\s?почт|\bпочта\b|\bпочту\b"),
    ("phone", r"phone|tel\b|телефон|мобильн|whatsapp|номер для связи"),
    ("birthdate", r"birth|дата рождения|день рождения|\bdob\b|возраст"),
    ("passport", r"паспорт|passport|серия и номер"),
    ("snils", r"снилс|snils"),
    ("inn", r"\bинн\b|\binn\b"),
    ("card", r"номер карты|card.?number|cvv|cvc"),
    ("address", r"адрес|address|улица|street|город|city|индекс|zip|квартир|дом\b"),
    ("name", r"(^|[^a-z])(f?name|fio|first.?name|last.?name|surname|имя|фамил|отчеств|фио|как к вам обращаться|ваше имя)"),
    ("messenger", r"telegram|телеграм|vk\.com|ник в|username"),
    ("file", r"\bfile\b|файл|резюме|вложени|attachment"),
    ("message", r"message|comment|сообщени|комментари|вопрос|описание|текст обращения|пожелани"),
    ("company", r"company|организаци|компани"),
    ("search", r"search|поиск|\bq\b|query"),
]
SPECIAL_PATTERNS = [
    ("health", r"диагноз|жалоб|симптом|здоров|заболеван|болезн|анамнез|аллерги|беремен|инвалидн|лекарств|медицинск\w* карт|группа крови|рост и вес"),
    ("nationality", r"национальност|раса\b|расов"),
    ("religion", r"вероисповед|религи"),
    ("politics", r"политическ\w* взгляд|партийн"),
]
PD_KINDS = {"email", "phone", "birthdate", "passport", "snils", "inn", "address", "name", "messenger", "file"}
PD_RU = {"email": "email", "phone": "телефон", "birthdate": "дата рождения", "passport": "паспортные данные", "snils": "СНИЛС",
         "inn": "ИНН", "address": "адрес", "name": "имя / ФИО", "messenger": "мессенджер", "file": "файл (может содержать ПД)",
         "message": "сообщение (свободный текст)", "company": "организация", "card": "данные карты", "password": "пароль",
         "health": "сведения о здоровье", "nationality": "национальность", "religion": "вероисповедание", "politics": "политические взгляды"}

CONSENT_RE = re.compile(r"(согла[сш]|даю|принима|ознакомл|подтвержда).{0,120}(персональн|обработк\w* (моих |личных )?данн|конфиденциальн|политик)|"
                        r"персональн\w*\s+данн|обработк\w*\s+(моих\s+|личных\s+)?данн|privacy|personal data", re.I)
IMPLICIT_RE = re.compile(r"(нажимая|нажав|отправляя|оставляя|заполняя|кликая|продолжая)", re.I)
COMBINED_RE = re.compile(
    r"(оферт|пользовательск\w*\s+соглашени|услови\w*\s+(договора|использования|продажи|сервиса|оферты|обслуживани)|"
    r"правил\w*\s+(сайта|сервиса|пользования|оказания|программы)|рассылк|рекламн|новост\w* и акци|получение\s+(информационных|рекламных)|"
    r"договор\w*\s+(оказания|купли|публичн))", re.I)
POLICY_ACK_RE = re.compile(r"(ознакомл|прочитал|принима\w*)\s.{0,40}политик", re.I)
SUBSCRIBE_RE = re.compile(r"подпис|рассылк|новост|акци[ия]|спецпредложени|subscribe|newsletter", re.I)
AD_CONSENT_RE = re.compile(r"(согла|хочу|даю).{0,80}(рекламн|рассылк|получ\w* (новост|информац|предложени|акци))", re.I)

DOC_KINDS = [
    ("recommendation_rules", r"рекомендательн"),
    ("consent", r"согласи\w*.{0,40}(обработк|персональн)|soglasie|consent|soglasiye"),
    ("privacy_policy", r"политик\w*.{0,50}(конфиденциальн|персональн|обработк)|конфиденциальн|privacy|politika|politic|personal[-_ ]?data|персональн\w*\s+данн|/policy|policy\b"),
    ("cookie_policy", r"cookie|куки"),
    ("offer", r"оферт|oferta|offer|договор\w*.{0,20}(купли|оказани|продаж)|условия продажи|terms.of.sale"),
    ("terms", r"пользовательск\w* соглашени|terms|usloviya|правила (пользования|сайта|сервиса)|user.?agreement"),
    ("returns", r"возврат|обмен\w* (и|товар)|vozvrat|returns?\b|refund"),
    ("delivery", r"доставк|delivery|dostavka|shipping"),
    ("payment", r"оплат|payment|oplata"),
    ("requisites", r"реквизит|rekvizit"),
    ("contacts", r"контакт|contacts?\b|kontakt"),
]
DOC_RU = {"privacy_policy": "Политика обработки ПД / конфиденциальности", "consent": "Согласие на обработку ПД", "cookie_policy": "Политика cookie",
          "offer": "Оферта / договор", "terms": "Пользовательское соглашение", "returns": "Возврат и обмен", "delivery": "Доставка",
          "payment": "Оплата", "requisites": "Реквизиты", "contacts": "Контакты", "recommendation_rules": "Правила рекомендательных технологий"}
POLICY_SECTIONS = {
    "protection": r"защит\w*\s+(персональн|данн|информац)|мер\w*.{0,40}(защит|безопасност)|безопасност\w* персональн|требовани\w* к защите",
    "purposes": r"цел[ьиея]\w*\s+(обработк|сбора)|в целях",
    "categories": r"(перечень|состав|категори)\w*.{0,40}(персональн|данн)|обрабатыва\w*\s+следующ",
    "legal_basis": r"правов\w*\s+основани|основани\w*\s+обработк",
    "rights": r"прав\w*\s+субъект|субъект\w*.{0,40}(вправе|имеет право|права)|отозвать согласие|отзыв согласия",
    "operator": r"оператор",
    "retention": r"срок\w*\s+(обработк|хранени)",
    "cookies": r"cookie|куки|метрическ|яндекс\.?\s?метрик|google analytics|веб-аналитик",
    "crossborder": r"трансграничн",
}
RECOMMEND_RE = re.compile(r"рекомендуем (вам|для вас)|персональн\w* рекомендаци|на основе ваших (интересов|предпочтений|просмотров)|вам может понравиться|подобрали для вас|рекомендации для вас", re.I)
LOGIN_RE = re.compile(r"^(войти|вход|личный кабинет|кабинет|регистрация|зарегистрироваться|sign in|log in|login)$", re.I)
RETURN_DAYS_RE = re.compile(r"возврат\w*[^.\n]{0,120}?в течение\s+(\d{1,2})\s*(?:\(\w+\)\s*)?(календарн\w+\s+|рабоч\w+\s+)?(дн|сут)", re.I)


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except Exception:
        return ""


def _reg_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"com", "net", "org", "co", "msk", "spb"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _first_party(host: str, site_host: str) -> bool:
    host = host.lstrip(".")
    return _reg_domain(host) == _reg_domain(site_host)


def _classify_field(f: dict) -> tuple[str | None, str | None]:
    blob = " ".join([f.get("name", ""), f.get("id", ""), f.get("placeholder", ""), f.get("label", "")[:120], f.get("autocomplete", "")]).lower()
    special = next((k for k, p in SPECIAL_PATTERNS if re.search(p, blob)), None)
    t = f.get("type", "")
    if t == "email":
        return "email", special
    if t == "tel":
        return "phone", special
    if t == "password":
        return "password", special
    if t == "file":
        return "file", special
    if t == "search":
        return "search", special
    if t in ("checkbox", "radio", "hidden", "range", "color"):
        return None, special
    if t == "date" and re.search(r"рожд|birth", blob):
        return "birthdate", special
    for kind, pat in PD_PATTERNS:
        if re.search(pat, blob):
            return kind, special
    if f.get("tag") == "textarea":
        return "message", special
    return None, special


def _doc_kind(text: str) -> str | None:
    t = text.lower()
    for kind, pat in DOC_KINDS:
        if re.search(pat, t):
            return kind
    return None


def _form_purpose(kinds: set[str], text: str) -> str:
    t = text.lower()
    if "search" in kinds and not kinds - {"search", "message"}:
        return "search"
    if "password" in kinds:
        return "auth"
    if kinds & {"email", "phone"} and SUBSCRIBE_RE.search(t) and not kinds & {"message", "address", "file"} and len(kinds - {"name"}) <= 2:
        return "subscribe"
    if "address" in kinds and re.search(r"заказ|доставк", t):
        return "order"
    if re.search(r"запис|бронир", t):
        return "booking"
    if re.search(r"перезвон|обратн\w* звон|звонок", t):
        return "callback"
    if "message" in kinds:
        return "feedback"
    if re.search(r"заявк|расчёт|расчет|консультац", t):
        return "application"
    return "other"


def build_facts(raw: dict, start_url: str, stage=None) -> dict:
    """stage(key, status, detail) — отметка реальных этапов анализа для экрана прогресса."""
    st = stage or (lambda *a: None)
    pages = raw.get("pages", [])
    final_url = raw.get("final_url") or start_url
    site_host = _host(final_url)
    facts: dict = {
        "url": start_url, "final_url": final_url, "host": site_host,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "https": raw.get("https", {}),
        "redirect_chain": raw.get("redirect_chain", []),
    }
    facts["https"]["enabled"] = urlsplit(final_url).scheme == "https"

    # ---------- страницы
    facts["pages"] = [{"url": p["url"], "title": p.get("title", ""), "status": p.get("status"), "depth": p.get("depth", 0),
                       "forms": len(p.get("forms", []))} for p in pages]

    # ---------- документы (ссылки)
    st("documents", "running", "")
    docs: dict[str, dict] = {}
    for p in pages:
        for ln in p.get("links", []):
            href = ln.get("href", "")
            if not href.startswith(("http://", "https://")) or not _first_party(_host(href), site_host):
                continue
            if urlsplit(href).path in ("", "/") and not urlsplit(href).query:
                continue  # ссылка на главную (часто якорь «Контакты») — не документ
            kind = _doc_kind(f"{ln.get('text', '')} {urlsplit(href).path}")
            if not kind:
                continue
            key = href.split("#")[0].rstrip("/")
            d = docs.setdefault(key, {"kind": kind, "url": href.split("#")[0], "link_text": ln.get("text", "")[:160], "found_on": [], "source": "link"})
            if p["url"] not in d["found_on"] and len(d["found_on"]) < 30:
                d["found_on"].append(p["url"])
    page_by_url = {p["url"].split("#")[0].rstrip("/"): p for p in pages}
    for d in docs.values():
        pg = page_by_url.get(d["url"].rstrip("/"))
        fetched = next((x for x in raw.get("documents_fetched", []) if x["url"].rstrip("/") == d["url"].rstrip("/")), None)
        if pg:
            d.update(accessible=(pg.get("status") or 0) < 400, status=pg.get("status"), title=pg.get("title", ""),
                     text=pg.get("text", ""))
        elif fetched:
            d.update(accessible=fetched["status"] == 200 and len(fetched.get("text", "")) > 200, status=fetched["status"],
                     title="", text=fetched.get("text", ""), file=True, content_type=fetched.get("content_type", ""))
        else:
            d.update(accessible=None, status=None, title="", text="")
    # типовые адреса политики (если по ссылкам не найдено)
    for pr in raw.get("probes", []):
        html = pr.get("html", "")
        if pr.get("status") == 200 and html:
            text = re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", html))
            text = re.sub(r"\s+", " ", unescape(text))
            if re.search(r"персональн\w*\s+данн", text, re.I) and len(text) > 1500:
                key = pr["final_url"].rstrip("/")
                if key not in docs:
                    docs[key] = {"kind": "privacy_policy", "url": pr["final_url"], "link_text": "", "found_on": [], "source": "probe",
                                 "accessible": True, "status": 200, "title": "", "text": text[:200000]}
    for d in docs.values():
        text = d.pop("text", "") or ""
        d["text_len"] = len(text)
        d["kind_ru"] = DOC_RU.get(d["kind"], d["kind"])
        if d["kind"] in ("privacy_policy", "consent", "cookie_policy", "offer", "recommendation_rules", "returns"):
            d["has_pd_words"] = bool(re.search(r"персональн\w*\s+данн", text, re.I))
            if d["kind"] == "privacy_policy":
                d["sections"] = {k: bool(re.search(p, text, re.I)) for k, p in POLICY_SECTIONS.items()}
            d["excerpt"] = text[:60000]
            if d["kind"] == "returns":
                m = RETURN_DAYS_RE.search(text)
                d["return_days"] = int(m.group(1)) if m else None
    facts["documents"] = sorted(docs.values(), key=lambda x: (x["kind"], x["url"]))

    policy_urls = {d["url"].rstrip("/") for d in facts["documents"] if d["kind"] == "privacy_policy"}
    n_pol = len(policy_urls)
    st("documents", "done", f"Документов найдено: {len(facts['documents'])}" + (f", политика ПД: {'да' if n_pol else 'не найдена'}"))

    # ---------- формы
    st("forms", "running", "")
    forms: list[dict] = []
    seen_sig: dict[str, dict] = {}
    for pi, p in enumerate(pages):
        page_links = {ln.get("href", "").split("#")[0].rstrip("/") for ln in p.get("links", [])}
        has_policy_link = bool(page_links & policy_urls) or any(
            _doc_kind(f"{ln.get('text', '')} {urlsplit(ln.get('href', '')).path}") == "privacy_policy" for ln in p.get("links", []))
        for f in p.get("forms", []):
            fields = []
            kinds: set[str] = set()
            specials: set[str] = set()
            for fl in f.get("fields", []):
                kind, special = _classify_field(fl)
                if fl.get("type") in ("checkbox", "radio"):
                    continue
                if kind:
                    kinds.add(kind)
                if special:
                    specials.add(special)
                fields.append({"label": (fl.get("label") or fl.get("placeholder") or fl.get("name"))[:120], "name": fl.get("name", ""),
                               "type": fl.get("type"), "kind": kind, "special": special, "required": bool(fl.get("required"))})
            if not fields:
                continue
            ftext = " ".join([f.get("heading", ""), f.get("submit_text", ""), " ".join(f.get("consent_texts", []))])
            purpose = _form_purpose(kinds, ftext + " " + " ".join(x["label"] for x in fields))
            if purpose == "search":
                continue
            checkboxes = []
            for fl in f.get("fields", []):
                if fl.get("type") != "checkbox":
                    continue
                label = fl.get("label", "")
                is_consent = bool(CONSENT_RE.search(label))
                link_kinds = sorted({k for k in (_doc_kind(f"{l_.get('text', '')} {urlsplit(l_.get('href', '')).path}") for l_ in fl.get("links", [])) if k})
                checkboxes.append({
                    "text": label[:500], "consent_pd": is_consent, "checked_default": bool(fl.get("checked_default")),
                    "required": bool(fl.get("required")), "links": [l_["href"] for l_ in fl.get("links", [])][:6], "link_kinds": link_kinds,
                    "combined": bool(is_consent and COMBINED_RE.search(label)),
                    "policy_ack": bool(is_consent and POLICY_ACK_RE.search(label)),
                    "ad_consent": bool(AD_CONSENT_RE.search(label)),
                })
            implicit = [t for t in f.get("consent_texts", []) if IMPLICIT_RE.search(t) and CONSENT_RE.search(t)]
            any_consent_text = [t for t in f.get("consent_texts", []) if CONSENT_RE.search(t)]
            form_link_kinds = sorted({k for k in (_doc_kind(f"{l_.get('text', '')} {urlsplit(l_.get('href', '')).path}") for l_ in f.get("links", [])) if k})
            action = f.get("action", "")
            action_host = _host(action)
            handler = None
            if action_host and not _first_party(action_host, site_host):
                s = sig.match_url(action, action_host)
                handler = {"service_id": s.id, "name": s.name, "jurisdiction": s.jurisdiction, "owner": s.owner} if s else \
                    {"service_id": None, "name": action_host, "jurisdiction": "unknown", "owner": ""}
            has_pd = bool(kinds & PD_KINDS) or bool(specials)
            # одна и та же форма на разных страницах: action часто содержит адрес страницы и якорь (WordPress CF7 и т.п.)
            act_parts = urlsplit(action) if action else None
            if not action or (act_parts and _first_party(action_host, site_host) and act_parts.path.rstrip("/") == urlsplit(p["url"]).path.rstrip("/")):
                act_key = "self"
            else:
                act_key = f"{action_host}{act_parts.path}" if act_parts else action
            sig_fields = "|".join(sorted(f"{x['type']}:{(x['kind'] or '')}:{re.sub(r'[^а-яёa-z]', '', x['label'].lower())[:30]}" for x in fields))
            signature = hashlib.sha1((sig_fields + "#" + act_key).encode()).hexdigest()[:12]
            if signature in seen_sig:
                prev = seen_sig[signature]
                if p["url"] not in prev["pages"] and len(prev["pages"]) < 30:
                    prev["pages"].append(p["url"])
                    prev["policy_link_on_pages"][p["url"]] = has_policy_link
                continue
            form = {
                "ref": f"F{len(forms) + 1}", "page": p["url"], "pages": [p["url"]], "is_form": f.get("is_form", True),
                "action": action, "action_host": action_host, "method": f.get("method", ""), "purpose": purpose,
                "heading": f.get("heading", ""), "submit_text": f.get("submit_text", ""), "fields": fields,
                "pd_kinds": sorted(kinds & (PD_KINDS | {"message", "card"})), "special_kinds": sorted(specials), "has_pd": has_pd,
                "checkboxes": checkboxes, "consent_checkboxes": [c for c in checkboxes if c["consent_pd"]],
                "implicit_consent": implicit[:3], "consent_texts": any_consent_text[:4], "link_kinds": form_link_kinds,
                "subscribe": purpose == "subscribe" or bool(SUBSCRIBE_RE.search(f.get("heading", "") + " " + f.get("submit_text", ""))),
                "external_handler": handler,
                "insecure": action.startswith("http://") or p["url"].startswith("http://"),
                "policy_link_on_pages": {p["url"]: has_policy_link},
                "html": f.get("html", "")[:2000],
                "visible": f.get("visible", True),
            }
            form["has_consent_mechanism"] = bool(form["consent_checkboxes"] or implicit or any_consent_text)
            seen_sig[signature] = form
            forms.append(form)
    # встроенные iframe-формы иностранных/внешних сервисов
    for p in pages:
        for src in p.get("iframes", []):
            h = _host(src)
            s = sig.match_url(src, h)
            if s and s.type == "forms" and not _first_party(h, site_host):
                forms.append({"ref": f"F{len(forms) + 1}", "page": p["url"], "pages": [p["url"]], "is_form": False, "action": src,
                              "action_host": h, "method": "", "purpose": "embedded", "heading": "Встроенная форма (iframe)",
                              "submit_text": "", "fields": [], "pd_kinds": [], "special_kinds": [], "has_pd": True, "embedded": True,
                              "checkboxes": [], "consent_checkboxes": [], "implicit_consent": [], "consent_texts": [], "link_kinds": [],
                              "subscribe": False, "insecure": src.startswith("http://"), "policy_link_on_pages": {},
                              "external_handler": {"service_id": s.id, "name": s.name, "jurisdiction": s.jurisdiction, "owner": s.owner},
                              "html": f'<iframe src="{src[:300]}">', "visible": True, "has_consent_mechanism": False})
    facts["forms"] = forms
    st("forms", "done", f"Форм: {len(forms)}, с персональными данными: {sum(1 for x in forms if x['has_pd'])}")
    st("external", "running", "")
    facts["personal_data_fields"] = [{"form": f["ref"], "page": f["page"], "kind": x["kind"], "kind_ru": PD_RU.get(x["kind"], x["kind"]), "label": x["label"], "required": x["required"]}
                                     for f in forms for x in f["fields"] if x["kind"] in PD_KINDS or x["special"]]
    facts["consent_elements"] = [{"form": f["ref"], "page": f["page"], "type": "checkbox", **c} for f in forms for c in f["consent_checkboxes"]] + \
                                [{"form": f["ref"], "page": f["page"], "type": "text", "text": t} for f in forms for t in f["implicit_consent"]]

    # ---------- сеть, сервисы
    services: dict[str, dict] = {}
    unknown_domains: dict[str, int] = {}

    def add_service(s: sig.Service, evidence: str, page_url: str = "", domain: str = "") -> None:
        e = services.setdefault(s.id, {"service_id": s.id, "name": s.name, "type": s.type, "type_ru": sig.TYPE_RU.get(s.type, s.type),
                                       "purpose": s.purpose, "owner": s.owner, "jurisdiction": s.jurisdiction, "user_data": s.user_data,
                                       "domains": [], "evidence": [], "found_on": []})
        if domain and domain not in e["domains"] and len(e["domains"]) < 8:
            e["domains"].append(domain)
        if evidence and len(e["evidence"]) < 4 and evidence not in e["evidence"]:
            e["evidence"].append(evidence[:200])
        if page_url and page_url not in e["found_on"] and len(e["found_on"]) < 10:
            e["found_on"].append(page_url)

    for req in raw.get("network", []):
        h = _host(req["url"])
        if not h or _first_party(h, site_host):
            continue
        s = sig.match_url(req["url"], h)
        if s:
            add_service(s, f"{req.get('type', '')}: {req['url'][:160]}", domain=h)
        else:
            unknown_domains[h] = unknown_domains.get(h, 0) + 1
    for p in pages:
        for src in p.get("scripts", []) + p.get("iframes", []):
            h = _host(src)
            if not h or _first_party(h, site_host):
                continue
            s = sig.match_url(src, h)
            if s:
                add_service(s, f"скрипт/iframe: {src[:160]}", p["url"], h)
        for s in sig.match_inline_script(p.get("inline_scripts", "")):
            add_service(s, "код в HTML страницы", p["url"])
        for ln in p.get("links", []):
            h = _host(ln.get("href", ""))
            s = sig.match_url(ln.get("href", ""), h) if h else None
            if s and s.type == "payment":
                add_service(s, f"ссылка: {ln['href'][:120]}", p["url"], h)

    st("external", "done", f"Внешних сервисов распознано: {len(services)}, прочих доменов: {len(unknown_domains)}")

    # ---------- cookies
    st("cookies", "running", "")
    cookies = []
    stats = {"total": 0, "first_party": 0, "third_party": 0, "analytics": 0, "advertising": 0, "other": 0}
    now = datetime.now(timezone.utc).timestamp()
    for c in raw.get("cookies", []):
        dom = (c.get("domain") or "").lstrip(".")
        first = _first_party(dom, site_host)
        s = sig.match_cookie(c.get("name", ""))
        if not s and not first:
            s = sig.match_url("https://" + dom + "/", dom)
        cat = "analytics" if s and s.type in ("analytics", "calltracking", "tag_manager") else ("advertising" if s and s.type == "advertising" else "other")
        if s:
            add_service(s, f"cookie {c.get('name')}", domain=dom)
        exp = c.get("expires", -1)
        cookies.append({"name": c.get("name"), "domain": c.get("domain"), "first_party": first, "category": cat,
                        "service": s.name if s else None, "secure": c.get("secure"), "http_only": c.get("httpOnly"),
                        "same_site": c.get("sameSite"), "expires_days": round((exp - now) / 86400) if exp and exp > 0 else None})
        stats["total"] += 1
        stats["first_party" if first else "third_party"] += 1
        stats[cat] += 1
    facts["cookies"] = cookies
    facts["cookie_stats"] = stats
    facts["cookie_banner"] = next((p["cookie_banner"] for p in pages if p.get("cookie_banner")), None)

    st("cookies", "done", f"Cookies: {stats['total']} (third-party: {stats['third_party']}, аналитика: {stats['analytics']}, реклама: {stats['advertising']})")
    st("analytics", "running", "")
    svc = sorted(services.values(), key=lambda x: (x["type"], x["name"]))
    facts["external_services"] = svc
    facts["analytics"] = [x for x in svc if x["type"] in ("analytics", "tag_manager", "calltracking")]
    st("analytics", "done", ", ".join(x["name"] for x in facts["analytics"]) or "Системы аналитики не обнаружены")
    st("pd", "running", "")
    facts["advertising"] = [x for x in svc if x["type"] == "advertising"]
    facts["payments"] = [x for x in svc if x["type"] == "payment"]
    facts["unknown_domains"] = sorted(unknown_domains, key=lambda d: -unknown_domains[d])[:30]
    facts["foreign_services"] = [x for x in svc if x["jurisdiction"] == "foreign" and x["user_data"]]

    # ---------- реквизиты и контакты (приоритет: футер, контакты, реквизиты)
    texts, links = [], []
    for p in pages:
        is_contact = re.search(r"контакт|contact|kontakt|реквизит|rekvizit|о-компании|about|o-nas|o-kompanii", p["url"] + " " + p.get("title", ""), re.I)
        texts.append(p.get("footer_text", ""))
        texts.append(p.get("text", "")[:80000] if is_contact else p.get("text", "")[:20000])
        links += p.get("links", [])
    req = extract_requisites(texts, links)
    facts["company_details"] = {k: req[k] for k in ("inn", "ogrn", "ogrnip", "names", "addresses", "subject_type")}
    facts["contacts"] = {"emails": req["emails"], "phones": req["phones"]}

    # ---------- интернет-магазин и тип сайта
    ecom = ecommerce_signals(pages)
    facts["ecommerce_signals"] = ecom
    site_type, conf, scores = classify(pages, ecom)
    facts["site_type"] = site_type
    facts["site_type_ru"] = SITE_TYPE_RU.get(site_type, site_type)
    facts["site_type_confidence"] = conf
    facts["site_type_scores"] = scores
    facts["mode"] = "ecommerce" if site_type in ("online_store", "marketplace") else "base"
    all_text = "\n".join(p.get("text", "")[:40000] for p in pages)
    low = all_text.lower()
    facts["payment_mentions"] = {
        "mir": bool(re.search(r"(карт\w*|платёжн\w*|платежн\w*|систем\w*)\s+[«\"]?мир[»\"]?|\bмир\b[^.\n]{0,20}(visa|mastercard|карт)|(visa|mastercard)[^.\n]{0,20}\bмир\b|нспк", low)),
        "sbp": bool(re.search(r"\bсбп\b|систем\w* быстрых платеж", low)),
        "cash": bool(re.search(r"наличн|при получении|курьеру", low)),
        "card": bool(re.search(r"банковск\w* карт|оплат\w* картой|visa|mastercard", low)),
    }

    # ---------- реклама
    ad = {"networks": [x["name"] for x in facts["advertising"] if x["service_id"] in ("yandex_ads", "adfox", "google_ads")],
          "pixels": [x["name"] for x in facts["advertising"] if x["service_id"] not in ("yandex_ads", "adfox", "google_ads")],
          "labels": sum(p.get("ads", {}).get("labels", 0) for p in pages),
          "erid_links": sorted({u for p in pages for u in p.get("ads", {}).get("erid_links", [])})[:20],
          "slots": sum(p.get("ads", {}).get("slots", 0) for p in pages),
          "banners": [b for p in pages for b in p.get("ads", {}).get("banners", [])][:15]}
    facts["ads"] = ad

    # ---------- авторизация
    providers: dict[str, dict] = {}
    login_links = []
    for p in pages:
        for ln in p.get("links", []):
            href, text = ln.get("href", ""), ln.get("text", "")
            if LOGIN_RE.match(text.strip()) and len(login_links) < 5:
                login_links.append({"text": text, "href": href})
            for pid, name, jur, domains, text_re in sig.AUTH_PROVIDERS:
                if any(d in href for d in domains) or re.search(text_re, text, re.I):
                    providers.setdefault(pid, {"id": pid, "name": name, "jurisdiction": jur, "evidence": f"{text[:60]} {href[:120]}".strip()})
        for pid, name, jur, domains, text_re in sig.AUTH_PROVIDERS:
            if re.search(text_re, p.get("text", "")[:60000], re.I):
                providers.setdefault(pid, {"id": pid, "name": name, "jurisdiction": jur, "evidence": f"текст на {p['url']}"})
    has_pwd_form = any(f["purpose"] == "auth" for f in forms)
    phone_auth = bool(re.search(r"(вход|войти)\s+по\s+(номеру\s+)?телефон|код из смс|sms-код", low))
    facts["auth"] = {"has_auth": bool(login_links or providers or has_pwd_form), "login_links": login_links,
                     "providers": list(providers.values()), "password_form": has_pwd_form, "phone_auth": phone_auth}

    facts["recommendation_signals"] = sorted({m.group(0) for m in RECOMMEND_RE.finditer(all_text)})[:5]

    # возрастная маркировка (436-ФЗ): знаки 0+/6+/12+/16+/18+ в тексте и футере
    mark_text = all_text + " " + " ".join(p.get("footer_text", "") for p in pages)
    facts["age_marks"] = sorted({f"{m}+" for m in re.findall(r"(?<![\d.,])(0|6|12|16|18)\s?\+", mark_text)}, key=lambda x: int(x[:-1]))

    # ---------- итог обхода
    facts["crawl"] = {
        "pages": len(pages), "duration_s": raw.get("duration_s"), "partial": raw.get("partial", False),
        "errors": raw.get("errors", [])[:20], "blocked": raw.get("blocked", [])[:20],
        "aborted_methods": len(raw.get("aborted_methods", [])), "fatal": raw.get("fatal"),
        "documents_files": len(raw.get("documents_fetched", [])), "probes": len(raw.get("probes", [])),
        "network_requests": len(raw.get("network", [])),
    }
    st("pd", "done", f"Полей ПД: {len(facts['personal_data_fields'])}, иностранных сервисов: {len(facts['foreign_services'])}, тип сайта: {facts['site_type_ru']}")
    return facts
