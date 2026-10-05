"""Проверка по публичным реестрам. Официальные источники; капчу не обходим.

Без ключей работает RDAP (данные о домене .ru/.рф). ЕГРЮЛ/ЕГРИП и реестры РКН — через ключ провайдера, если задан;
иначе возвращаем «требует ручной проверки» и прямую ссылку на официальный источник.
"""
import logging
import re

import httpx
import idna

from ..config import get_settings

log = logging.getLogger(__name__)


def _reg_link_egrul(inn: str) -> str:
    return "https://egrul.nalog.ru/"


def check_domain_rdap(host: str) -> dict:
    """Возраст и регистратор домена .ru/.рф через RDAP ТЦИ (публично, без капчи)."""
    host = (host or "").lower().lstrip(".")
    base = host[4:] if host.startswith("www.") else host
    try:
        ascii_host = idna.encode(base, uts46=True).decode()
    except Exception:
        ascii_host = base
    tld = ascii_host.rsplit(".", 1)[-1]
    if tld not in ("ru", "рф", "xn--p1ai", "su"):
        return {"available": False, "note": "RDAP реализован для доменов .ru/.рф.", "domain": base}
    data = None
    for endpoint in (f"https://rdap.tcinet.ru/domain/{ascii_host}", f"https://rdap.nic.ru/domain/{ascii_host}"):
        try:
            r = httpx.get(endpoint, timeout=15, follow_redirects=True)
            if r.status_code == 404:
                return {"available": True, "registered": False, "domain": base, "free": True, "note": "Домен не найден в реестре."}
            r.raise_for_status()
            data = r.json()
            break
        except Exception:
            continue
    if data is None:
        return {"available": False, "free": True, "note": "Реестр доменов временно не ответил.", "domain": base,
                "link": f"https://www.nic.ru/whois/?searchWord={ascii_host}"}
    events = {e.get("eventAction"): e.get("eventDate") for e in data.get("events", [])}
    registrar = ""
    for ent in data.get("entities", []):
        if "registrar" in (ent.get("roles") or []):
            registrar = ent.get("handle", "") or ent.get("fn", "")
    created = events.get("registration", "")
    age_years = None
    if created:
        m = re.match(r"(\d{4})", created)
        if m:
            from datetime import date
            age_years = date.today().year - int(m.group(1))
    return {"available": True, "registered": True, "free": True, "domain": base, "registrar": registrar,
            "created": created[:10], "expires": (events.get("expiration", "") or "")[:10], "age_years": age_years,
            "status": data.get("status", [])}


def check_egrul(inn: str) -> dict:
    """ЕГРЮЛ/ЕГРИП по ИНН. Через DaData (если задан ключ), иначе — ссылка на официальный источник."""
    st = get_settings()
    key = getattr(st, "dadata_api_key", "") or ""
    if not inn or not re.fullmatch(r"\d{10}|\d{12}", inn):
        return {"available": False, "note": "ИНН не найден или некорректен."}
    if not key:
        return {"available": False, "inn": inn, "manual": True, "free": True, "link": _reg_link_egrul(inn),
                "note": "Проверьте бесплатно на egrul.nalog.ru по ИНН. Для автоматической проверки подключите бесплатный "
                        "ключ DaData (тариф «Бесплатно», до 10 000 запросов в сутки) — переменная DADATA_API_KEY."}
    try:
        r = httpx.post("https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party",
                       headers={"Authorization": f"Token {key}", "Content-Type": "application/json"},
                       json={"query": inn}, timeout=15)
        r.raise_for_status()
        items = r.json().get("suggestions", [])
    except Exception as e:
        return {"available": False, "inn": inn, "note": f"Сервис ЕГРЮЛ недоступен: {type(e).__name__}", "link": _reg_link_egrul(inn)}
    if not items:
        return {"available": True, "inn": inn, "found": False, "note": "По ИНН запись в ЕГРЮЛ/ЕГРИП не найдена."}
    d = items[0]["data"]
    return {"available": True, "inn": inn, "found": True,
            "name": items[0].get("value"), "ogrn": d.get("ogrn"), "status": (d.get("state") or {}).get("status"),
            "type": d.get("type"), "address": (d.get("address") or {}).get("value"),
            "registration_date": _ts(d.get("ogrn_date")), "kind": "Юридическое лицо" if d.get("type") == "LEGAL" else "Индивидуальный предприниматель"}


def _ts(ms) -> str:
    if not ms:
        return ""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()


def check_rkn(inn: str, host: str) -> dict:
    """Публичные реестры Роскомнадзора (бесплатные). Где стоит капча — даём прямую ссылку, не обходим."""
    q = f"?q={inn}" if inn else ""
    registries = [
        {"id": "operators", "title": "Реестр операторов персональных данных",
         "why": "Зарегистрирован ли владелец сайта как оператор ПД (ст. 22 152-ФЗ).",
         "link": "https://pd.rkn.gov.ru/operators-registry/operators-list/" + q, "captcha": True},
        {"id": "hosting", "title": "Реестр провайдеров хостинга",
         "why": "Легален ли хостинг сайта (ст. 10.1 149-ФЗ). Если хостинг-провайдера нет в реестре — риск блокировки.",
         "link": "https://rkn.gov.ru/it/hosting/", "captcha": False},
        {"id": "blocklist", "title": "Единый реестр запрещённой информации",
         "why": f"Не заблокирован ли домен {host} или его страницы.",
         "link": "https://eais.rkn.gov.ru/", "captcha": True},
        {"id": "ori", "title": "Реестр организаторов распространения информации (ОРИ)",
         "why": "Нужно для форумов, мессенджеров, соцсетей и сервисов с перепиской (ст. 10.1 149-ФЗ).",
         "link": "https://rkn.gov.ru/communication/register/operator/", "captcha": False},
    ]
    return {"available": True, "free": True, "inn": inn or None, "registries": registries,
            "note": "Реестры Роскомнадзора публичные и бесплатные. Проверка по ним выполняется по прямым ссылкам; "
                    "там, где стоит капча, сервис её не обходит."}


def run_registries(facts: dict) -> dict:
    cd = facts.get("company_details", {}) or {}
    inn = (cd.get("inn") or [None])[0]
    host = facts.get("host", "")
    return {
        "domain": check_domain_rdap(host),
        "egrul": check_egrul(inn),
        "rkn": check_rkn(inn, host),
        "note": "Данные реестров приводятся с официальных источников. Там, где доступ ограничен капчей, сервис даёт прямую ссылку, а не обходит защиту.",
    }
