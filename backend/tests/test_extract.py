"""Извлечение фактов из сырых данных краулера (без сети)."""
from app.crawler.extract import build_facts
from app.crawler.requisites import extract_requisites, inn_valid, ogrn_valid


def _page(url, **kw):
    base = {"url": url, "status": 200, "depth": 0, "title": "Магазин", "meta": {}, "text": "", "footer_text": "", "links": [], "forms": [],
            "scripts": [], "inline_scripts": "", "iframes": [], "ld_types": [], "cookie_banner": None,
            "ads": {"labels": 0, "erid_links": [], "slots": 0, "banners": []}, "counts": {"elements": 100}}
    base.update(kw)
    return base


def test_requisites_checksums():
    assert inn_valid("7707083893") and not inn_valid("7707083890")
    assert ogrn_valid("1027700132195") and not ogrn_valid("1027700132190")
    r = extract_requisites(["ООО «Ромашка», ИНН 7707083893, ОГРН 1027700132195. Адрес: 123456, г. Москва, ул. Тверская, д. 1. info@romashka.ru"], [])
    assert r["subject_type"] == "legal" and r["inn"] == ["7707083893"] and r["ogrn"] == ["1027700132195"]
    assert r["names"] == ["ООО «Ромашка»"] and r["emails"] == ["info@romashka.ru"] and r["addresses"]


def test_build_facts_forms_consent_and_services():
    form = {"index": 0, "is_form": True, "action": "https://shop.ru/send", "method": "post", "heading": "Обратный звонок",
            "submit_text": "Перезвоните мне", "consent_texts": [], "links": [], "html": "<form></form>", "visible": True,
            "fields": [
                {"tag": "input", "type": "text", "name": "name", "label": "Ваше имя", "placeholder": "", "required": True},
                {"tag": "input", "type": "tel", "name": "phone", "label": "Телефон", "placeholder": "", "required": True},
                {"tag": "input", "type": "checkbox", "name": "agree", "label": "Принимаю условия оферты и даю согласие на обработку персональных данных",
                 "checked_default": True, "links": [{"href": "https://shop.ru/privacy", "text": "политика"}]},
            ]}
    raw = {
        "final_url": "https://shop.ru/", "https": {"cert_valid": True, "http_redirects_to_https": True},
        "pages": [_page("https://shop.ru/", forms=[form], text="Товар 1 990 ₽ Товар 2 500 ₽ Товар 3 100 ₽ В корзину Оформить заказ доставка и оплата",
                        links=[{"href": "https://shop.ru/privacy", "text": "Политика конфиденциальности", "footer": True},
                               {"href": "https://shop.ru/cart", "text": "Корзина", "footer": False}],
                        scripts=["https://mc.yandex.ru/metrika/tag.js", "https://www.googletagmanager.com/gtag/js?id=G-XXX"])],
        "network": [{"url": "https://mc.yandex.ru/watch/123", "type": "image", "method": "GET"},
                    {"url": "https://region1.google-analytics.com/g/collect", "type": "fetch", "method": "GET"}],
        "cookies": [{"name": "_ym_uid", "domain": ".shop.ru", "expires": -1}, {"name": "_ga", "domain": ".shop.ru", "expires": -1},
                    {"name": "yandexuid", "domain": ".yandex.ru", "expires": -1}],
        "documents_fetched": [], "probes": [], "errors": [],
    }
    f = build_facts(raw, "https://shop.ru/")
    assert len(f["forms"]) == 1
    fm = f["forms"][0]
    assert fm["has_pd"] and set(fm["pd_kinds"]) == {"name", "phone"} and fm["purpose"] == "callback"
    cb = fm["consent_checkboxes"][0]
    assert cb["combined"] and cb["checked_default"]
    ids = {s["service_id"] for s in f["external_services"]}
    assert {"yandex_metrika", "google_analytics"} <= ids
    assert any(s["service_id"] == "google_analytics" for s in f["foreign_services"])
    assert f["cookie_stats"]["total"] == 3 and f["cookie_stats"]["third_party"] == 1 and f["cookie_stats"]["analytics"] >= 2
    assert f["site_type"] == "online_store" and f["mode"] == "ecommerce"
    assert any(d["kind"] == "privacy_policy" for d in f["documents"])
    assert fm["policy_link_on_pages"]["https://shop.ru/"] is True
