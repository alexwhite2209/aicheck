"""Тестовые наборы фактов для каждого правила (используются pytest и кнопкой «Тестировать» в админке).

Ожидаемые статусы соответствуют алгоритмам из LEGAL_DATABASE.md.
"""
import copy


def base_facts(**over) -> dict:
    f = {
        "url": "https://example.ru/", "final_url": "https://example.ru/", "host": "example.ru", "site_type": "corporate", "site_type_ru": "Корпоративный сайт",
        "mode": "base", "https": {"enabled": True, "cert_valid": True, "http_redirects_to_https": True, "http_status": 301},
        "pages": [{"url": "https://example.ru/", "status": 200, "depth": 0}], "forms": [], "documents": [], "cookies": [],
        "cookie_stats": {"total": 0, "first_party": 0, "third_party": 0, "analytics": 0, "advertising": 0, "other": 0},
        "cookie_banner": None, "analytics": [], "advertising": [], "external_services": [], "foreign_services": [], "payments": [],
        "company_details": {"inn": [], "ogrn": [], "ogrnip": [], "names": [], "addresses": [], "subject_type": "unknown"},
        "contacts": {"emails": [], "phones": []}, "ecommerce_signals": [], "payment_mentions": {"mir": False, "sbp": False, "cash": False, "card": False},
        "ads": {"networks": [], "pixels": [], "labels": 0, "erid_links": [], "slots": 0, "banners": []},
        "auth": {"has_auth": False, "login_links": [], "providers": [], "password_form": False, "phone_auth": False},
        "recommendation_signals": [], "crawl": {"pages": 1, "partial": False, "fatal": None},
    }
    f.update(copy.deepcopy(over))
    return f


def form(ref="F1", kinds=("name", "phone"), consent=None, implicit=None, links=(), purpose="callback", **over) -> dict:
    cbs = [dict({"text": "Я даю согласие на обработку персональных данных", "consent_pd": True, "checked_default": False, "required": True,
                 "links": [], "link_kinds": ["consent"], "combined": False, "policy_ack": False, "ad_consent": False}, **c) for c in (consent or [])]
    f = {"ref": ref, "page": "https://example.ru/contacts", "pages": ["https://example.ru/contacts"], "purpose": purpose, "pd_kinds": list(kinds),
         "special_kinds": [], "has_pd": True, "fields": [{"label": k, "kind": k, "special": None, "required": True} for k in kinds],
         "checkboxes": cbs, "consent_checkboxes": [c for c in cbs if c["consent_pd"]], "implicit_consent": list(implicit or []),
         "consent_texts": list(implicit or []), "link_kinds": list(links), "subscribe": purpose == "subscribe", "external_handler": None,
         "insecure": False, "policy_link_on_pages": {"https://example.ru/contacts": True}, "html": "<form>…</form>", "visible": True}
    f["has_consent_mechanism"] = bool(f["consent_checkboxes"] or f["implicit_consent"])
    f.update(over)
    return f


POLICY = {"kind": "privacy_policy", "url": "https://example.ru/privacy", "found_on": ["https://example.ru/"], "accessible": True, "status": 200,
          "text_len": 12000, "has_pd_words": True, "excerpt": "Политика обработки персональных данных…",
          "sections": {"protection": True, "purposes": True, "categories": True, "legal_basis": True, "rights": True, "operator": True,
                       "retention": True, "cookies": True, "crossborder": True}}
GA = {"service_id": "google_analytics", "name": "Google Analytics", "type": "analytics", "type_ru": "Аналитика", "owner": "Google LLC (США)",
      "jurisdiction": "foreign", "user_data": True, "found_on": ["https://example.ru/"], "evidence": ["script"]}
YM = {"service_id": "yandex_metrika", "name": "Яндекс Метрика", "type": "analytics", "type_ru": "Аналитика", "owner": "ООО «Яндекс»",
      "jurisdiction": "RU", "user_data": True, "found_on": ["https://example.ru/"], "evidence": ["script"]}
ECOM = dict(mode="ecommerce", site_type="online_store", ecommerce_signals=[{"signal": "prices", "evidence": ""}, {"signal": "add_to_cart", "evidence": ""}])
FULL_REQ = {"inn": ["7707083893"], "ogrn": ["1027700132195"], "ogrnip": [], "names": ["ООО «Пример»"], "addresses": ["123456, г. Москва, ул. Тверская, д. 1"], "subject_type": "legal"}


def pol(**sections):
    p = copy.deepcopy(POLICY)
    p["sections"].update(sections)
    return p


# rule_id: [(название, факты, ожидаемый статус)]
CASES: dict[str, list[tuple[str, dict, str]]] = {
    "152FZ_FORM_PD_001": [
        ("телефон в форме → REVIEW", base_facts(forms=[form()]), "REVIEW"),
        ("телефон + согласие → всё равно REVIEW (факт сбора)", base_facts(forms=[form(consent=[{}])]), "REVIEW"),
        ("форм нет → NA", base_facts(), "NA"),
    ],
    "152FZ_POLICY_001": [
        ("форма, политика доступна → PASS", base_facts(forms=[form()], documents=[POLICY]), "PASS"),
        ("форма, политики нет → FAIL", base_facts(forms=[form()]), "FAIL"),
        ("форма, ссылка на политику 404 → FAIL", base_facts(forms=[form()], documents=[dict(POLICY, accessible=False, status=404)]), "FAIL"),
        ("обход прерван, политики нет → UNKNOWN", base_facts(forms=[form()], crawl={"pages": 3, "partial": True, "fatal": None}), "UNKNOWN"),
        ("нет сбора ПД и политики → NA", base_facts(), "NA"),
    ],
    "152FZ_POLICY_LINK_002": [
        ("ссылка на всех страницах → PASS", base_facts(forms=[form()], documents=[POLICY]), "PASS"),
        ("нет ссылки на странице формы → FAIL", base_facts(forms=[form(policy_link_on_pages={"https://example.ru/contacts": False})], documents=[POLICY]), "FAIL"),
        ("нет политики → NA", base_facts(forms=[form()]), "NA"),
    ],
    "152FZ_POLICY_CONTENT_003": [
        ("все разделы → PASS", base_facts(documents=[POLICY]), "PASS"),
        ("нет сведений о защите → FAIL", base_facts(documents=[pol(protection=False)]), "FAIL"),
        ("нет описания cookie при аналитике → REVIEW", base_facts(documents=[pol(cookies=False)], analytics=[YM]), "REVIEW"),
        ("нет политики → NA", base_facts(), "NA"),
    ],
    "152FZ_CONSENT_001": [
        ("телефон + согласие → PASS", base_facts(forms=[form(consent=[{}])]), "PASS"),
        ("телефон без согласия → REVIEW (возможно договорное основание)", base_facts(forms=[form()]), "REVIEW"),
        ("нет форм → NA", base_facts(), "NA"),
    ],
    "152FZ_CONSENT_SEPARATE_002": [
        ("отдельный чекбокс + документ согласия → PASS", base_facts(forms=[form(consent=[{}])]), "PASS"),
        ("согласие + оферта в одном чекбоксе → FAIL", base_facts(forms=[form(consent=[{"text": "Принимаю условия оферты и даю согласие на обработку персональных данных", "combined": True}])]), "FAIL"),
        ("только «нажимая кнопку» → REVIEW", base_facts(forms=[form(implicit=["Нажимая кнопку, вы соглашаетесь с политикой обработки персональных данных"])]), "REVIEW"),
        ("ссылка только на политику → REVIEW", base_facts(forms=[form(consent=[{"link_kinds": ["privacy_policy"]}])]), "REVIEW"),
        ("нет согласия → NA", base_facts(forms=[form()]), "NA"),
    ],
    "152FZ_CONSENT_PRECHECKED_003": [
        ("не отмечен → PASS", base_facts(forms=[form(consent=[{}])]), "PASS"),
        ("отмечен заранее → FAIL", base_facts(forms=[form(consent=[{"checked_default": True}])]), "FAIL"),
        ("нет чекбоксов → NA", base_facts(forms=[form()]), "NA"),
    ],
    "152FZ_SPECIAL_CAT_004": [
        ("поле «жалобы» → REVIEW", base_facts(forms=[form(special_kinds=["health"])]), "REVIEW"),
        ("обычная форма → NA", base_facts(forms=[form()]), "NA"),
    ],
    "152FZ_LOCALIZATION_005": [
        ("форма отправляется в Google Forms → REVIEW", base_facts(forms=[form(external_handler={"service_id": "google_forms", "name": "Google Forms", "jurisdiction": "foreign", "owner": "Google LLC (США)"})]), "REVIEW"),
        ("собственный обработчик → UNKNOWN (не FAIL)", base_facts(forms=[form()]), "UNKNOWN"),
        ("CDN Cloudflare не делает FAIL → UNKNOWN", base_facts(forms=[form()], external_services=[{"service_id": "cloudflare_cdn"}]), "UNKNOWN"),
    ],
    "152FZ_CROSSBORDER_006": [
        ("Google Analytics → REVIEW", base_facts(foreign_services=[GA]), "REVIEW"),
        ("только российские сервисы → PASS", base_facts(external_services=[YM]), "PASS"),
    ],
    "152FZ_RKN_NOTICE_007": [
        ("есть сбор ПД → UNKNOWN", base_facts(forms=[form()]), "UNKNOWN"),
        ("есть ИНН → UNKNOWN с подсказкой", base_facts(forms=[form()], company_details=FULL_REQ), "UNKNOWN"),
        ("нет признаков → NA", base_facts(), "NA"),
    ],
    "152FZ_COOKIES_008": [
        ("аналитика без уведомления → REVIEW", base_facts(analytics=[YM], cookie_stats={"total": 3, "first_party": 3, "third_party": 0, "analytics": 2, "advertising": 0, "other": 1}), "REVIEW"),
        ("уведомление + политика описывает → PASS", base_facts(analytics=[YM], documents=[POLICY], cookie_banner={"text": "Мы используем cookie"},
                                                             cookie_stats={"total": 2, "first_party": 2, "third_party": 0, "analytics": 2, "advertising": 0, "other": 0}), "PASS"),
        ("нет трекеров → NA", base_facts(), "NA"),
    ],
    "149FZ_OWNER_INFO_001": [
        ("всё найдено → PASS", base_facts(company_details=FULL_REQ, contacts={"emails": ["info@example.ru"], "phones": []}), "PASS"),
        ("нет адреса и email → FAIL", base_facts(company_details={**FULL_REQ, "addresses": []}), "FAIL"),
    ],
    "149FZ_AUTH_002": [
        ("вход через Google → REVIEW", base_facts(auth={"has_auth": True, "login_links": [], "providers": [{"id": "google", "name": "Google", "jurisdiction": "foreign", "evidence": ""}], "phone_auth": False}), "REVIEW"),
        ("вход через VK ID → PASS", base_facts(auth={"has_auth": True, "login_links": [], "providers": [{"id": "vk", "name": "VK ID", "jurisdiction": "RU", "evidence": ""}], "phone_auth": False}), "PASS"),
        ("вход есть, способ неизвестен → UNKNOWN", base_facts(auth={"has_auth": True, "login_links": [{"text": "Войти", "href": "/login"}], "providers": [], "phone_auth": False}), "UNKNOWN"),
        ("входа нет → NA", base_facts(), "NA"),
    ],
    "149FZ_RECOMMEND_003": [
        ("магазин с рекомендациями без правил → REVIEW", base_facts(site_type="online_store", recommendation_signals=["рекомендуем вам"]), "REVIEW"),
        ("корпоративный сайт → NA", base_facts(recommendation_signals=["рекомендуем вам"]), "NA"),
    ],
    "38FZ_AD_MARKING_001": [
        ("баннер без пометки → REVIEW", base_facts(ads={"networks": [], "labels": 0, "erid_links": [], "slots": 0, "banners": [{"href": "https://partner.ru/", "alt": "", "container": "banner", "label_near": False}]}), "REVIEW"),
        ("размещение с erid и пометкой → PASS", base_facts(ads={"networks": [], "labels": 1, "erid_links": ["https://p.ru/?erid=abc"], "slots": 0, "banners": []}), "PASS"),
        ("нет рекламы → NA", base_facts(), "NA"),
    ],
    "38FZ_EMAIL_CONSENT_002": [
        ("подписка без согласия на рекламу → REVIEW", base_facts(forms=[form(kinds=("email",), purpose="subscribe")]), "REVIEW"),
        ("подписка с согласием → PASS", base_facts(forms=[form(kinds=("email",), purpose="subscribe", consent=[{"text": "Согласен получать рекламную рассылку", "consent_pd": False, "ad_consent": True}])]), "PASS"),
        ("нет подписки → NA", base_facts(forms=[form()]), "NA"),
    ],
    "ECOM_SELLER_INFO_001": [
        ("магазин, реквизиты полные → PASS", base_facts(**ECOM, company_details=FULL_REQ, contacts={"emails": ["a@b.ru"], "phones": []}), "PASS"),
        ("магазин без ОГРН → FAIL", base_facts(**ECOM, company_details={**FULL_REQ, "ogrn": []}, contacts={"emails": ["a@b.ru"], "phones": []}), "FAIL"),
        ("не магазин → NA", base_facts(), "NA"),
    ],
    "ECOM_OFFER_002": [
        ("оферта найдена → PASS", base_facts(**ECOM, documents=[{"kind": "offer", "url": "https://example.ru/oferta", "link_text": "Оферта"}]), "PASS"),
        ("оферты нет → FAIL", base_facts(**ECOM), "FAIL"),
    ],
    "ECOM_PRECONTRACT_INFO_003": [
        ("нет доставки и оплаты → FAIL", base_facts(**ECOM), "FAIL"),
        ("всё есть → PASS", base_facts(**ECOM, documents=[{"kind": "delivery", "url": "https://example.ru/d"}, {"kind": "payment", "url": "https://example.ru/p"}]), "PASS"),
    ],
    "ECOM_RETURN_INFO_004": [
        ("срок возврата 3 дня → REVIEW", base_facts(**ECOM, documents=[{"kind": "returns", "url": "https://example.ru/r", "return_days": 3}]), "REVIEW"),
        ("раздел возврата есть → PASS", base_facts(**ECOM, documents=[{"kind": "returns", "url": "https://example.ru/r", "return_days": 14}]), "PASS"),
        ("нет информации → REVIEW", base_facts(**ECOM), "REVIEW"),
    ],
    "ECOM_NATIONAL_PAYMENT_005": [
        ("оплата картой без «Мир» → REVIEW", base_facts(**ECOM, payment_mentions={"mir": False, "sbp": False, "cash": False, "card": True}), "REVIEW"),
        ("упомянута СБП → PASS", base_facts(**ECOM, payment_mentions={"mir": False, "sbp": True, "cash": False, "card": True}), "PASS"),
    ],
    "AGE_MARKING_436_001": [
        ("СМИ без маркировки → REVIEW", base_facts(site_type="media"), "REVIEW"),
        ("СМИ с 18+ → PASS", base_facts(site_type="media", age_marks=["18+"]), "PASS"),
        ("корпоративный сайт → NA", base_facts(), "NA"),
    ],
    "SEC_HTTPS_001": [
        ("HTTPS + редирект → PASS", base_facts(forms=[form()]), "PASS"),
        ("форма по HTTP → FAIL", base_facts(forms=[form(insecure=True)]), "FAIL"),
        ("нет редиректа с HTTP → REVIEW", base_facts(https={"enabled": True, "cert_valid": True, "http_redirects_to_https": False, "http_status": 200}), "REVIEW"),
        ("сайт без HTTPS → FAIL", base_facts(https={"enabled": False, "cert_valid": True}), "FAIL"),
    ],
}


def run_cases(rule_id: str) -> dict:
    from .rules import REGISTRY
    fn = REGISTRY[rule_id]
    report = {"rule_id": rule_id, "cases": [], "passed": True}
    for name, facts, expected in CASES.get(rule_id, []):
        try:
            got = fn(facts).status
        except Exception as e:  # noqa: BLE001
            got = f"ERROR: {e}"
        ok = got == expected
        report["passed"] &= ok
        report["cases"].append({"name": name, "expected": expected, "got": got, "ok": ok})
    if not report["cases"]:
        report["passed"] = False
        report["note"] = "Для правила нет тестовых наборов"
    return report
