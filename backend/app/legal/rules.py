"""Логика правил. Каждое правило реализует алгоритм из LEGAL_DATABASE.md и работает только с фактами.

Правило возвращает Outcome: статус, уверенность, описание факта и доказательства.
Метаданные (название, критичность, нормы, финансы, тексты) берутся из опубликованной версии правила в БД.
"""
from collections.abc import Callable
from dataclasses import dataclass, field

PASS, FAIL, REVIEW, UNKNOWN, NA = "PASS", "FAIL", "REVIEW", "UNKNOWN", "NA"
CONFIRMED, PROBABLE, MANUAL, UNDETERMINED = "confirmed", "probable", "manual", "undetermined"


@dataclass
class Outcome:
    status: str
    confidence: str
    fact: str
    evidence: list[dict] = field(default_factory=list)
    severity: str | None = None  # переопределение критичности (по алгоритму правила)
    details: dict = field(default_factory=dict)


RuleFn = Callable[[dict], Outcome]
REGISTRY: dict[str, RuleFn] = {}


def rule(rule_id: str):
    def deco(fn: RuleFn) -> RuleFn:
        REGISTRY[rule_id] = fn
        return fn
    return deco


def _pd_forms(f: dict) -> list[dict]:
    return [x for x in f.get("forms", []) if x.get("has_pd")]


def _form_ev(form: dict, note: str = "") -> dict:
    kinds = ", ".join(form.get("pd_kinds", []) + form.get("special_kinds", []))
    return {"page": form["page"], "label": f"Форма {form['ref']}" + (f" ({kinds})" if kinds else "") + (f": {note}" if note else ""),
            "snippet": form.get("html", "")[:1200]}


def _docs(f: dict, kind: str) -> list[dict]:
    return [d for d in f.get("documents", []) if d["kind"] == kind]


def _collects_pd(f: dict) -> bool:
    return bool(_pd_forms(f)) or f.get("auth", {}).get("has_auth") or f.get("mode") == "ecommerce"


def _crawl_failed(f: dict) -> bool:
    return bool(f.get("crawl", {}).get("fatal")) and not f.get("pages")


# ------------------------------------------------------------------ 152-ФЗ
@rule("152FZ_FORM_PD_001")
def form_pd(f: dict) -> Outcome:
    if _crawl_failed(f):
        return Outcome(UNKNOWN, UNDETERMINED, "Сайт не удалось проверить: страницы не загружены.")
    forms = _pd_forms(f)
    if not forms:
        return Outcome(NA, CONFIRMED, f"На {len(f.get('pages', []))} проверенных страницах форм с полями персональных данных не обнаружено.")
    kinds = sorted({k for x in forms for k in x["pd_kinds"]})
    ru = {"email": "email", "phone": "телефон", "name": "имя", "address": "адрес", "birthdate": "дата рождения", "message": "сообщение",
          "passport": "паспорт", "snils": "СНИЛС", "inn": "ИНН", "messenger": "мессенджер", "file": "файл", "card": "карта"}
    pages = sorted({p for x in forms for p in x["pages"]})
    return Outcome(REVIEW, CONFIRMED,
                   f"Обнаружено форм с персональными данными: {len(forms)} (поля: {', '.join(ru.get(k, k) for k in kinds) or 'встроенные формы'}) "
                   f"на страницах: {len(pages)}. Установлен факт потенциального сбора ПД; правовая оценка — в связанных проверках.",
                   [_form_ev(x) for x in forms[:6]], details={"forms": len(forms), "kinds": kinds})


@rule("152FZ_POLICY_001")
def policy(f: dict) -> Outcome:
    if _crawl_failed(f):
        return Outcome(UNKNOWN, UNDETERMINED, "Сайт не удалось проверить.")
    docs = _docs(f, "privacy_policy")
    good = [d for d in docs if d.get("accessible") and d.get("text_len", 0) >= 1500 and d.get("has_pd_words")]
    if not _collects_pd(f) and not docs:
        return Outcome(NA, PROBABLE, "Признаков сбора персональных данных через сайт не обнаружено.")
    if good:
        d = sorted(good, key=lambda x: (x.get("source") == "probe", -len(x.get("found_on", []))))[0]
        note = (" Документ найден по типовому адресу: ссылок на него на проверенных страницах нет (см. проверку ссылок со страниц с формами)."
                if d.get("source") == "probe" and not d.get("found_on") else "")
        return Outcome(PASS, PROBABLE, f"Политика найдена и доступна: {d['url']} (около {max(d['text_len'] // 1000, 1)} тыс. знаков).{note}",
                       [{"page": d["url"], "label": d.get("link_text") or d.get("title") or "Документ политики", "snippet": d.get("excerpt", "")[:600]}],
                       details={"url": d["url"]})
    if docs:
        d = docs[0]
        reason = "недоступен" if d.get("accessible") is False else ("не открыт краулером" if d.get("accessible") is None else "не содержит текста о персональных данных или слишком короткий")
        status = UNKNOWN if d.get("accessible") is None else FAIL
        return Outcome(status, PROBABLE if status == FAIL else UNDETERMINED,
                       f"Ссылка на документ найдена ({d['url']}), но документ {reason} (HTTP {d.get('status') or '—'}).",
                       [{"page": (d.get("found_on") or [d["url"]])[0], "label": d.get("link_text", ""), "snippet": d["url"]}])
    if f.get("crawl", {}).get("partial"):
        return Outcome(UNKNOWN, UNDETERMINED, "Политика не найдена, но обход сайта был прерван по времени — вывод сделать нельзя.")
    return Outcome(FAIL, PROBABLE,
                   f"Документ политики обработки ПД не найден на {len(f.get('pages', []))} проверенных страницах и по типовым адресам "
                   "(/privacy, /policy, /politika-konfidencialnosti и др.).",
                   [_form_ev(x) for x in _pd_forms(f)[:3]])


@rule("152FZ_POLICY_LINK_002")
def policy_link(f: dict) -> Outcome:
    forms = [x for x in _pd_forms(f) if x.get("policy_link_on_pages")]
    if not forms or not _docs(f, "privacy_policy"):
        return Outcome(NA, PROBABLE, "Нет форм с ПД или не найдена политика — проверка ссылок не выполняется.")
    missing = sorted({pg for x in forms for pg, ok in x["policy_link_on_pages"].items() if not ok})
    total = sorted({pg for x in forms for pg in x["policy_link_on_pages"]})
    if not missing:
        return Outcome(PASS, CONFIRMED, f"Ссылка на политику есть на всех {len(total)} страницах с формами сбора ПД.")
    return Outcome(FAIL, PROBABLE, f"На {len(missing)} из {len(total)} страниц с формами сбора ПД нет ссылки на политику.",
                   [{"page": pg, "label": "Страница с формой без ссылки на политику", "snippet": ""} for pg in missing[:8]],
                   details={"missing": missing})


@rule("152FZ_POLICY_CONTENT_003")
def policy_content(f: dict) -> Outcome:
    docs = [d for d in _docs(f, "privacy_policy") if d.get("accessible") and d.get("sections")]
    if not docs:
        return Outcome(NA, PROBABLE, "Доступная политика не найдена — анализ содержания не выполняется.")
    d = max(docs, key=lambda x: x.get("text_len", 0))
    s = d["sections"]
    names = {"protection": "сведения о защите ПД", "purposes": "цели обработки", "categories": "состав ПД", "legal_basis": "правовые основания",
             "rights": "права субъекта", "operator": "сведения об операторе", "retention": "сроки обработки"}
    missing = [names[k] for k in names if not s.get(k)]
    extra = []
    if f.get("analytics") and not s.get("cookies"):
        extra.append("не описаны cookie и сервисы аналитики, обнаруженные на сайте")
    if f.get("foreign_services") and not s.get("crossborder"):
        extra.append("не упомянута трансграничная передача, хотя подключены сервисы иностранных компаний")
    # актуальность политики: ищем год в тексте
    import datetime as _dt
    import re as _re
    years = [int(y) for y in _re.findall(r"\b(20[12]\d)\b", d.get("excerpt", ""))]
    cur = _dt.date.today().year
    if years and max(years) <= cur - 3:
        extra.append(f"последняя дата в политике — {max(years)} г.; возможно, документ устарел и не отражает текущую обработку")
    ev = [{"page": d["url"], "label": "Документ политики", "snippet": d.get("excerpt", "")[:500]}]
    if not s.get("protection"):
        return Outcome(FAIL, PROBABLE, "В политике не найдены сведения о реализуемых требованиях к защите ПД (прямое требование ч. 2 ст. 18.1)."
                       + (f" Также не найдено: {', '.join(m for m in missing if m != names['protection'])}." if len(missing) > 1 else ""), ev,
                       details={"missing": missing, "extra": extra})
    if missing or extra:
        parts = ([f"не найдены разделы: {', '.join(missing)}"] if missing else []) + extra
        return Outcome(REVIEW, MANUAL, "Политика содержит сведения о защите ПД, но " + "; ".join(parts) + ".", ev, details={"missing": missing, "extra": extra})
    return Outcome(PASS, PROBABLE, "В политике найдены ключевые разделы, включая сведения о защите ПД; описаны обнаруженные способы обработки.", ev)


@rule("152FZ_CONSENT_001")
def consent(f: dict) -> Outcome:
    forms = [x for x in _pd_forms(f) if not x.get("embedded")]
    if not forms:
        return Outcome(NA, PROBABLE, "Форм сбора ПД не обнаружено.")
    without = [x for x in forms if not x["has_consent_mechanism"]]
    if not without:
        return Outcome(PASS, PROBABLE, f"Во всех формах сбора ПД ({len(forms)}) есть механизм согласия. Корректность согласия оценивается отдельно.",
                       [_form_ev(x) for x in forms[:3]])
    purposes = {"order": "заказ", "callback": "обратный звонок", "feedback": "обращение", "subscribe": "подписка", "booking": "запись",
                "application": "заявка", "auth": "вход/регистрация", "other": "иное"}
    return Outcome(REVIEW, MANUAL,
                   f"В {len(without)} из {len(forms)} форм не найдено чекбокса или текста согласия на обработку ПД "
                   f"(назначение: {', '.join(sorted({purposes.get(x['purpose'], x['purpose']) for x in without}))}). "
                   "Согласие не требуется, если обработка основана на договоре (п. 5 ч. 1 ст. 6), — это нужно проверить вручную.",
                   [_form_ev(x, "нет механизма согласия") for x in without[:6]])


@rule("152FZ_CONSENT_SEPARATE_002")
def consent_separate(f: dict) -> Outcome:
    forms = [x for x in _pd_forms(f) if x["has_consent_mechanism"]]
    if not forms:
        return Outcome(NA, PROBABLE, "Элементы согласия не обнаружены.")
    combined = [(x, c) for x in forms for c in x["consent_checkboxes"] if c["combined"]]
    if combined:
        x, c = combined[0]
        return Outcome(FAIL, PROBABLE,
                       f"Согласие на обработку ПД объединено с принятием иных документов или подпиской в одном чекбоксе: «{c['text'][:220]}».",
                       [_form_ev(x2, f"«{c2['text'][:160]}»") for x2, c2 in combined[:5]])
    weak = []
    for x in forms:
        cbs = x["consent_checkboxes"]
        if not cbs:
            weak.append((x, "согласие выражено только текстом у кнопки: " + (x["implicit_consent"] or x["consent_texts"] or [""])[0][:160]))
            continue
        for c in cbs:
            if c["policy_ack"]:
                weak.append((x, f"в одном чекбоксе — ознакомление с политикой и согласие: «{c['text'][:140]}»"))
            elif "consent" not in c["link_kinds"] and "consent" not in x["link_kinds"]:
                weak.append((x, "чекбокс не ведёт на отдельный текст согласия (только на политику или без ссылки)"))
    if weak:
        return Outcome(REVIEW, MANUAL, f"Согласие не оформлено явно отдельным документом в {len({w[0]['ref'] for w in weak})} форм(ах): {weak[0][1]}.",
                       [_form_ev(x, note) for x, note in weak[:6]])
    return Outcome(PASS, PROBABLE, "Согласие на обработку ПД оформлено отдельным чекбоксом со ссылкой на отдельный текст согласия.",
                   [_form_ev(x) for x in forms[:3]])


@rule("152FZ_CONSENT_PRECHECKED_003")
def consent_prechecked(f: dict) -> Outcome:
    items = [(x, c) for x in _pd_forms(f) for c in x["consent_checkboxes"]]
    if not items:
        return Outcome(NA, PROBABLE, "Чекбоксы согласия не обнаружены.")
    pre = [(x, c) for x, c in items if c["checked_default"]]
    if pre:
        return Outcome(FAIL, CONFIRMED, f"Чекбокс согласия отмечен по умолчанию (атрибут checked) в {len({x['ref'] for x, _ in pre})} форм(ах).",
                       [_form_ev(x, f"отмечено заранее: «{c['text'][:140]}»") for x, c in pre[:5]])
    return Outcome(PASS, CONFIRMED, f"Чекбоксы согласия ({len(items)}) не отмечены заранее.")


@rule("152FZ_SPECIAL_CAT_004")
def special_categories(f: dict) -> Outcome:
    forms = [x for x in f.get("forms", []) if x.get("special_kinds")]
    if not forms:
        return Outcome(NA, PROBABLE, "Полей со специальными категориями ПД не обнаружено.")
    ru = {"health": "здоровье", "nationality": "национальность", "religion": "вероисповедание", "politics": "политические взгляды"}
    kinds = sorted({ru.get(k, k) for x in forms for k in x["special_kinds"]})
    return Outcome(REVIEW, MANUAL, f"Формы запрашивают сведения специальных категорий: {', '.join(kinds)}. Требуется проверить основание обработки "
                   "(в частности, наличие согласия в письменной форме).", [_form_ev(x) for x in forms[:5]])


@rule("152FZ_LOCALIZATION_005")
def localization(f: dict) -> Outcome:
    ext = [x for x in _pd_forms(f) if x.get("external_handler") and x["external_handler"].get("jurisdiction") == "foreign"]
    if ext:
        names = sorted({x["external_handler"]["name"] for x in ext})
        return Outcome(REVIEW, PROBABLE,
                       f"Форма(ы) сбора ПД отправляют данные напрямую в сервис иностранной компании: {', '.join(names)}. "
                       "Первичная запись данных, по-видимому, происходит во внешнем сервисе. Физическое расположение баз данных по сайту не определяется.",
                       [_form_ev(x, f"обработчик: {x['external_handler']['name']} ({x['external_handler'].get('owner', '')})") for x in ext[:5]],
                       details={"services": names})
    other = sorted({x["external_handler"]["name"] for x in _pd_forms(f) if x.get("external_handler")})
    note = f" Формы отправляются во внешние сервисы: {', '.join(other)} — их юрисдикция и место хранения данных требуют проверки." if other else ""
    return Outcome(UNKNOWN, UNDETERMINED, "По публичной части сайта невозможно достоверно определить место хранения персональных данных." + note)


@rule("152FZ_CROSSBORDER_006")
def crossborder(f: dict) -> Outcome:
    foreign = f.get("foreign_services", [])
    if not foreign:
        return Outcome(PASS, PROBABLE, "Сервисов иностранных компаний, получающих данные посетителей, не обнаружено.")
    strong = [s for s in foreign if s["type"] in ("analytics", "tag_manager", "advertising", "forms", "chat", "captcha", "crm", "calltracking")]
    sev = "high" if strong else "medium"
    lst = "; ".join(f"{s['name']} — {s['owner']}" for s in foreign[:8])
    return Outcome(REVIEW, MANUAL,
                   f"Подключены сервисы иностранных компаний, получающие данные посетителей (IP-адрес, cookie): {lst}. "
                   "Требуется проверить, относятся ли передаваемые данные к ПД и направлено ли уведомление о трансграничной передаче.",
                   [{"page": (s.get("found_on") or [""])[0], "label": f"{s['name']} ({s['type_ru']})", "snippet": "; ".join(s.get("evidence", [])[:2])} for s in foreign[:8]],
                   severity=sev, details={"services": [s["service_id"] for s in foreign]})


@rule("152FZ_RKN_NOTICE_007")
def rkn_notice(f: dict) -> Outcome:
    if not (_collects_pd(f) or f.get("analytics")):
        return Outcome(NA, PROBABLE, "Признаков обработки персональных данных не обнаружено.")
    cd = f.get("company_details", {})
    ids = ", ".join([f"ИНН {i}" for i in cd.get("inn", [])[:2]] + [f"ОГРН {o}" for o in (cd.get("ogrn", []) + cd.get("ogrnip", []))[:2]])
    if ids:
        fact = (f"Проверка статуса оператора персональных данных требует дополнительных сведений. На сайте найдены реквизиты владельца ({ids}) — "
                "проверьте наличие в реестре операторов ПД Роскомнадзора (pd.rkn.gov.ru).")
    else:
        fact = "Проверка статуса оператора персональных данных требует дополнительных сведений о владельце сайта: реквизиты на сайте не найдены."
    return Outcome(UNKNOWN, UNDETERMINED, fact, details={"inn": cd.get("inn", []), "ogrn": cd.get("ogrn", []) + cd.get("ogrnip", [])})


@rule("152FZ_COOKIES_008")
def cookies(f: dict) -> Outcome:
    st = f.get("cookie_stats", {})
    trackers = st.get("analytics", 0) + st.get("advertising", 0)
    if not trackers and not f.get("analytics") and not f.get("advertising"):
        return Outcome(NA, PROBABLE, f"Cookie аналитики и рекламы не обнаружены (всего cookie: {st.get('total', 0)}).")
    banner = f.get("cookie_banner")
    policy = [d for d in _docs(f, "privacy_policy") if d.get("sections")]
    mentions = any(d["sections"].get("cookies") for d in policy) or bool(_docs(f, "cookie_policy"))
    base = (f"Обнаружено cookie: {st.get('total', 0)} (first-party: {st.get('first_party', 0)}, third-party: {st.get('third_party', 0)}, "
            f"аналитика: {st.get('analytics', 0)}, реклама: {st.get('advertising', 0)}). Cookie установлены при открытии страницы, до любых действий пользователя.")
    ev = [{"page": f.get("final_url", ""), "label": "Уведомление о cookie", "snippet": banner["text"]}] if banner else []
    if banner and mentions:
        return Outcome(PASS, PROBABLE, base + " Есть уведомление о cookie, политика описывает их использование.", ev)
    gaps = ([] if banner else ["уведомление о cookie не найдено"]) + ([] if mentions else ["политика не описывает cookie и аналитику"])
    return Outcome(REVIEW, MANUAL, base + " " + "; ".join(gaps).capitalize() + ".", ev)


# ------------------------------------------------------------------ 149-ФЗ
@rule("149FZ_OWNER_INFO_001")
def owner_info(f: dict) -> Outcome:
    if _crawl_failed(f):
        return Outcome(UNKNOWN, UNDETERMINED, "Сайт не удалось проверить.")
    cd, ct = f.get("company_details", {}), f.get("contacts", {})
    have = {"наименование": bool(cd.get("names")), "адрес": bool(cd.get("addresses")), "email": bool(ct.get("emails"))}
    found = [k for k, v in have.items() if v]
    missing = [k for k, v in have.items() if not v]
    ev = []
    if cd.get("names"):
        ev.append({"page": "", "label": "Наименование", "snippet": "; ".join(cd["names"][:3])})
    if cd.get("addresses"):
        ev.append({"page": "", "label": "Адрес", "snippet": cd["addresses"][0]})
    if ct.get("emails"):
        ev.append({"page": "", "label": "Email", "snippet": ", ".join(ct["emails"][:3])})
    if not missing:
        return Outcome(PASS, PROBABLE, "На сайте найдены наименование владельца, адрес и адрес электронной почты.", ev)
    return Outcome(FAIL, PROBABLE, f"На проверенных страницах не найдено: {', '.join(missing)}." + (f" Найдено: {', '.join(found)}." if found else ""), ev,
                   details={"missing": missing})


@rule("149FZ_AUTH_002")
def auth(f: dict) -> Outcome:
    a = f.get("auth", {})
    if not a.get("has_auth"):
        return Outcome(NA, PROBABLE, "Вход и регистрация на публичных страницах не обнаружены.")
    foreign = [p for p in a.get("providers", []) if p["jurisdiction"] == "foreign"]
    ru = [p for p in a.get("providers", []) if p["jurisdiction"] == "RU"]
    if foreign:
        return Outcome(REVIEW, MANUAL,
                       f"Обнаружен вход через иностранные сервисы: {', '.join(p['name'] for p in foreign)}"
                       + (f"; российские способы: {', '.join(p['name'] for p in ru)}" if ru else "") + ".",
                       [{"page": "", "label": p["name"], "snippet": p["evidence"]} for p in foreign[:5]])
    if ru or a.get("phone_auth"):
        return Outcome(PASS, PROBABLE, "Обнаружены допустимые способы входа: " + ", ".join([p["name"] for p in ru] + (["по номеру телефона"] if a.get("phone_auth") else [])) + ".")
    return Outcome(UNKNOWN, UNDETERMINED, "На сайте есть вход или регистрация, но способ авторизации по публичным страницам определить нельзя.",
                   [{"page": ln["href"], "label": ln["text"], "snippet": ""} for ln in a.get("login_links", [])[:3]])


@rule("149FZ_RECOMMEND_003")
def recommend(f: dict) -> Outcome:
    if f.get("site_type") not in ("media", "marketplace", "online_store", "blog") or not f.get("recommendation_signals"):
        return Outcome(NA, PROBABLE, "Явных признаков персональных рекомендаций не обнаружено.")
    if _docs(f, "recommendation_rules"):
        return Outcome(PASS, PROBABLE, "Документ о правилах применения рекомендательных технологий найден.")
    return Outcome(REVIEW, MANUAL, f"Найдены признаки персональных рекомендаций («{f['recommendation_signals'][0]}»), документ с правилами применения "
                   "рекомендательных технологий не найден.")


# ------------------------------------------------------------------ реклама
@rule("38FZ_AD_MARKING_001")
def ad_marking(f: dict) -> Outcome:
    ad = f.get("ads", {})
    own = [b for b in ad.get("banners", [])]
    if not (ad.get("networks") or ad.get("slots") or own or ad.get("erid_links") or ad.get("labels")):
        return Outcome(NA, PROBABLE, "Признаков рекламы не обнаружено.")
    unmarked = [b for b in own if not b.get("label_near") and "erid=" not in b.get("href", "").lower()]
    if unmarked:
        return Outcome(REVIEW, MANUAL,
                       f"Обнаружены блоки с внешними ссылками в баннерных контейнерах без пометки «реклама» и идентификатора erid ({len(unmarked)}). "
                       "Является ли размещение рекламой, нужно оценить вручную: основание классификации — внешняя ссылка из блока с классом "
                       f"«{unmarked[0].get('container', '')}».",
                       [{"page": "", "label": b.get("alt") or "Баннер", "snippet": b["href"]} for b in unmarked[:5]])
    if ad.get("networks") or ad.get("slots"):
        return Outcome(REVIEW, MANUAL, f"На сайте размещаются рекламные блоки рекламных систем ({', '.join(ad.get('networks') or ['рекламные слоты'])}). "
                       "Маркировку и идентификатор обычно обеспечивает оператор рекламной системы — проверьте настройки.")
    return Outcome(PASS, PROBABLE, f"Рекламные размещения содержат признаки маркировки (пометок «реклама»: {ad.get('labels', 0)}, ссылок с erid: {len(ad.get('erid_links', []))}).")


@rule("38FZ_EMAIL_CONSENT_002")
def email_consent(f: dict) -> Outcome:
    forms = [x for x in f.get("forms", []) if x.get("subscribe") and set(x.get("pd_kinds", [])) & {"email", "phone", "messenger"}]
    if not forms:
        return Outcome(NA, PROBABLE, "Форм подписки на рассылку не обнаружено.")
    without = [x for x in forms if not any(c["ad_consent"] for c in x["checkboxes"])]
    if not without:
        return Outcome(PASS, PROBABLE, "В формах подписки есть отдельное согласие на получение рекламы.")
    return Outcome(REVIEW, MANUAL, f"В {len(without)} форм(ах) подписки не найдено отдельного согласия на получение рекламных сообщений.",
                   [_form_ev(x, "подписка без отдельного согласия на рекламу") for x in without[:5]])


# ------------------------------------------------------------------ E-COMMERCE
def _ecom(f: dict) -> bool:
    return f.get("mode") == "ecommerce"


@rule("ECOM_SELLER_INFO_001")
def seller_info(f: dict) -> Outcome:
    if not _ecom(f):
        return Outcome(NA, PROBABLE, "Режим интернет-магазина не включён.")
    cd, ct = f.get("company_details", {}), f.get("contacts", {})
    is_ip = cd.get("subject_type") == "ip"
    have = {
        "наименование": bool(cd.get("names")),
        "ОГРНИП" if is_ip else "ОГРН": bool(cd.get("ogrnip") if is_ip else cd.get("ogrn")),
        "email или телефон": bool(ct.get("emails") or ct.get("phones")),
    }
    if not is_ip:
        have["адрес"] = bool(cd.get("addresses"))
    missing = [k for k, v in have.items() if not v]
    ev = [{"page": "", "label": "Найденные реквизиты", "snippet": "; ".join(cd.get("names", [])[:2] + [f"ОГРН {x}" for x in cd.get("ogrn", [])[:1]]
                                                                     + [f"ОГРНИП {x}" for x in cd.get("ogrnip", [])[:1]] + cd.get("addresses", [])[:1])}]
    if not missing:
        return Outcome(PASS, PROBABLE, "Сведения о продавце найдены: наименование, " + ("ОГРНИП" if is_ip else "ОГРН, адрес") + ", контакты.", ev)
    severe = any(m in missing for m in ("наименование", "ОГРН", "ОГРНИП"))
    return Outcome(FAIL, PROBABLE, f"На проверенных страницах интернет-магазина не найдено: {', '.join(missing)}.", ev,
                   severity=None if severe else "medium", details={"missing": missing})


@rule("ECOM_OFFER_002")
def offer(f: dict) -> Outcome:
    if not _ecom(f):
        return Outcome(NA, PROBABLE, "Режим интернет-магазина не включён.")
    docs = _docs(f, "offer")
    if docs:
        return Outcome(PASS, PROBABLE, f"Оферта найдена: {docs[0]['url']}.", [{"page": docs[0]["url"], "label": docs[0].get("link_text", ""), "snippet": ""}])
    return Outcome(FAIL, PROBABLE, "Публичная оферта (договор купли-продажи, условия продажи) не найдена на проверенных страницах.")


@rule("ECOM_PRECONTRACT_INFO_003")
def precontract(f: dict) -> Outcome:
    if not _ecom(f):
        return Outcome(NA, PROBABLE, "Режим интернет-магазина не включён.")
    sig = {s["signal"] for s in f.get("ecommerce_signals", [])}
    have = {"цены": "prices" in sig,
            "доставка": bool(_docs(f, "delivery")) or "delivery_payment" in sig,
            "оплата": bool(_docs(f, "payment")) or "delivery_payment" in sig}
    missing = [k for k, v in have.items() if not v]
    if not missing:
        return Outcome(PASS, PROBABLE, "Найдены цены и информация о доставке и оплате.")
    return Outcome(FAIL, PROBABLE, f"Не найдена информация: {', '.join(missing)}.", details={"missing": missing})


@rule("ECOM_RETURN_INFO_004")
def returns(f: dict) -> Outcome:
    if not _ecom(f):
        return Outcome(NA, PROBABLE, "Режим интернет-магазина не включён.")
    docs = _docs(f, "returns")
    short = [d for d in docs if d.get("return_days") is not None and d["return_days"] < 7]
    if short:
        d = short[0]
        return Outcome(REVIEW, PROBABLE, f"На странице {d['url']} указан срок возврата {d['return_days']} дн. — меньше 7 дней, установленных законом.",
                       [{"page": d["url"], "label": "Условия возврата", "snippet": ""}], severity="high")
    if docs:
        return Outcome(PASS, PROBABLE, f"Информация о возврате найдена: {docs[0]['url']}.")
    return Outcome(REVIEW, MANUAL, "Информация о порядке и сроках возврата товара на сайте не найдена.")


@rule("ECOM_NATIONAL_PAYMENT_005")
def national_payment(f: dict) -> Outcome:
    if not _ecom(f):
        return Outcome(NA, PROBABLE, "Режим интернет-магазина не включён.")
    pm = f.get("payment_mentions", {})
    if not (f.get("payments") or pm.get("card")):
        return Outcome(NA, PROBABLE, "Признаки онлайн-оплаты не обнаружены.")
    if pm.get("mir") or pm.get("sbp") or any(p["service_id"] == "sbp" for p in f.get("payments", [])):
        return Outcome(PASS, PROBABLE, "Найдено упоминание оплаты картой «Мир» или через СБП.")
    return Outcome(REVIEW, MANUAL, "Упоминание оплаты национальными платёжными инструментами («Мир», СБП) не найдено. "
                   "Обязанность в части карт «Мир» зависит от выручки продавца.")


# ------------------------------------------------------------------ возрастная маркировка (436-ФЗ)
@rule("AGE_MARKING_436_001")
def age_marking(f: dict) -> Outcome:
    if f.get("site_type") not in ("media", "blog", "education"):
        return Outcome(NA, PROBABLE, "Сайт не относится к типам, для которых возрастная маркировка обычно требуется (СМИ, блог, образование).")
    marks = f.get("age_marks") or []
    if marks:
        return Outcome(PASS, PROBABLE, f"На сайте найдена возрастная маркировка: {', '.join(marks)}.")
    return Outcome(REVIEW, MANUAL, "На сайте не найдена возрастная маркировка («0+», «6+», «12+», «16+» или «18+»). Для сайтов с контентом (новости, статьи, видео, обучающие материалы) она, как правило, требуется.")


# ------------------------------------------------------------------ безопасность
@rule("SEC_HTTPS_001")
def https(f: dict) -> Outcome:
    if _crawl_failed(f):
        return Outcome(UNKNOWN, UNDETERMINED, "Сайт не удалось проверить.")
    h = f.get("https", {})
    pd = _pd_forms(f)
    sev = "high" if pd else "low"
    insecure = [x for x in pd if x.get("insecure")]
    if insecure:
        return Outcome(FAIL, CONFIRMED, f"Данные {len(insecure)} форм(ы) с ПД передаются по незащищённому протоколу HTTP.",
                       [_form_ev(x, "передача по HTTP") for x in insecure[:5]], severity="high")
    if not h.get("enabled"):
        return Outcome(FAIL, CONFIRMED, "Сайт открывается по незащищённому протоколу HTTP.", severity=sev)
    if h.get("cert_valid") is False:
        return Outcome(FAIL, CONFIRMED, "Сертификат HTTPS недействителен (ошибка проверки сертификата браузером).", severity="medium" if not pd else "high")
    if h.get("http_redirects_to_https") is False:
        return Outcome(REVIEW, PROBABLE, f"HTTPS работает, но HTTP-версия сайта не перенаправляет на HTTPS (HTTP {h.get('http_status')}).", severity="low")
    return Outcome(PASS, CONFIRMED, "Сайт работает по HTTPS с действительным сертификатом" + (", HTTP перенаправляет на HTTPS." if h.get("http_redirects_to_https") else "."), severity=sev)
