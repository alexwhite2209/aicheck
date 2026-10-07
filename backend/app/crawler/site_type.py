"""Определение типа сайта по признакам. Если уверенность низкая — unknown."""
import re

SITE_TYPES = ("corporate", "landing", "portfolio", "blog", "media", "online_store", "service", "restaurant",
              "medical", "education", "financial", "real_estate", "marketplace", "other")

SITE_TYPE_RU = {
    "corporate": "Корпоративный сайт", "landing": "Лендинг", "portfolio": "Портфолио", "blog": "Блог",
    "media": "СМИ / медиа", "online_store": "Интернет-магазин", "service": "Сайт услуг", "restaurant": "Ресторан / кафе",
    "medical": "Медицина", "education": "Образование", "financial": "Финансы", "real_estate": "Недвижимость",
    "marketplace": "Маркетплейс", "other": "Другое", "unknown": "Не определён",
}

KEYWORDS = {
    "online_store": [r"в корзину", r"добавить в корзину", r"оформить заказ", r"корзина", r"каталог товаров", r"купить в один клик", r"артикул", r"в наличии"],
    "restaurant": [r"меню", r"забронировать столик", r"бронь стола", r"доставка еды", r"бизнес-ланч", r"кухня", r"шеф-повар", r"ресторан", r"кафе", r"кофейн"],
    "medical": [r"клиник", r"врач", r"приём врача", r"запись на при[её]м", r"медицинск", r"стоматолог", r"анализы", r"лицензия на медицинскую деятельность", r"диагностик"],
    "education": [r"курс[ыа]? обучения", r"обучение", r"образовательн", r"лицензия на образовательную деятельность", r"учебн", r"школа", r"вебинар", r"преподавател"],
    "financial": [r"кредит", r"займ", r"вклад", r"процентная ставка", r"банк", r"страхован", r"лицензия банка россии", r"инвестиц", r"микрофинанс"],
    "real_estate": [r"новостройк", r"квартир", r"жилой комплекс", r"\bжк\b", r"ипотек", r"аренда недвижимост", r"планировк", r"застройщик"],
    "media": [r"новости", r"редакция", r"главный редактор", r"свидетельство о регистрации сми", r"сетевое издание", r"статьи", r"18\+"],
    "blog": [r"блог", r"автор", r"комментари", r"подписаться на блог", r"читать далее"],
    "portfolio": [r"портфолио", r"мои работы", r"кейсы", r"фотограф", r"дизайнер"],
    "service": [r"услуги", r"заказать услугу", r"прайс", r"стоимость услуг", r"оставить заявку", r"вызвать мастера", r"рассчитать стоимость"],
    "corporate": [r"о компании", r"вакансии", r"партн[её]рам", r"миссия", r"история компании", r"наша команда", r"пресс-центр"],
    "marketplace": [r"продавцам", r"стать продавцом", r"пункты выдачи", r"маркетплейс", r"магазины партн[её]ров"],
}
SCHEMA = {
    "online_store": {"Product", "Offer", "AggregateOffer", "Store", "OnlineStore"},
    "restaurant": {"Restaurant", "CafeOrCoffeeShop", "FoodEstablishment", "Menu", "Bakery"},
    "medical": {"MedicalOrganization", "MedicalClinic", "Physician", "Dentist", "Hospital", "MedicalBusiness"},
    "education": {"EducationalOrganization", "Course", "School", "CollegeOrUniversity"},
    "financial": {"FinancialService", "BankOrCreditUnion", "LoanOrCredit", "InsuranceAgency"},
    "real_estate": {"RealEstateAgent", "Residence", "Apartment", "RealEstateListing"},
    "media": {"NewsArticle", "NewsMediaOrganization"},
    "blog": {"Blog", "BlogPosting"},
    "service": {"Service", "ProfessionalService", "LocalBusiness", "HomeAndConstructionBusiness", "AutoRepair"},
    "corporate": {"Corporation", "Organization"},
}
PRICE_RE = re.compile(r"\d[\d\s ]{0,8}\s?(?:₽|руб\.?|р\.)", re.I)
CART_LINK_RE = re.compile(r"/(cart|basket|korzina|checkout)(/|\?|$)", re.I)


def ecommerce_signals(pages: list[dict]) -> list[dict]:
    sig: dict[str, str] = {}
    for p in pages:
        text = p.get("text", "")[:60000].lower()
        if re.search(r"(добавить |положить )?в корзину", text):
            sig.setdefault("add_to_cart", f"Кнопка «в корзину» на {p['url']}")
        prices = PRICE_RE.findall(p.get("text", "")[:60000])
        if len(prices) >= 3:
            sig.setdefault("prices", f"Цены ({len(prices)} шт.) на {p['url']}")
        if any(CART_LINK_RE.search(ln.get("href", "")) for ln in p.get("links", [])):
            sig.setdefault("cart_link", f"Ссылка на корзину на {p['url']}")
        if re.search(r"оформ(ить|ление) заказ", text):
            sig.setdefault("checkout_text", f"«Оформить заказ» на {p['url']}")
        if re.search(r"доставк", text) and re.search(r"оплат", text):
            sig.setdefault("delivery_payment", f"Упоминание доставки и оплаты на {p['url']}")
        if set(p.get("ld_types", [])) & SCHEMA["online_store"]:
            sig.setdefault("schema_product", f"schema.org Product/Offer на {p['url']}")
    return [{"signal": k, "evidence": v} for k, v in sig.items()]


def classify(pages: list[dict], ecom: list[dict]) -> tuple[str, float, dict]:
    scores = {t: 0.0 for t in SITE_TYPES}
    for p in pages[:20]:
        text = (p.get("title", "") + " " + p.get("meta", {}).get("description", "") + " " + p.get("text", "")[:30000]).lower()
        for t, kws in KEYWORDS.items():
            for kw in kws:
                if re.search(kw, text):
                    scores[t] += 1.0 if p.get("depth", 0) == 0 else 0.4
        ld = set(p.get("ld_types", []))
        for t, types in SCHEMA.items():
            if ld & types:
                scores[t] += 3.0
    ecom_keys = {e["signal"] for e in ecom}
    strong_ecom = len(ecom_keys & {"add_to_cart", "cart_link", "schema_product", "checkout_text"})
    if strong_ecom >= 2 and "prices" in ecom_keys:
        scores["online_store"] += 6
    elif strong_ecom == 0:
        scores["online_store"] = min(scores["online_store"], 1.5)
    if scores["marketplace"] >= 2 and scores["online_store"] >= 4:
        scores["marketplace"] += 3
    # лендинг: одна-две страницы, мало внутренних ссылок, есть форма
    if len(pages) <= 2 and any(p.get("forms") for p in pages):
        internal = len({ln["href"] for ln in pages[0].get("links", [])}) if pages else 0
        if internal < 25:
            scores["landing"] += 4
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    best, best_score = ranked[0]
    second = ranked[1][1]
    total = sum(v for _, v in ranked if v > 0) or 1
    confidence = round(best_score / total, 2)
    if best_score < 3 or (best_score - second) < 1:
        return "unknown", confidence, {k: round(v, 1) for k, v in ranked[:5]}
    return best, confidence, {k: round(v, 1) for k, v in ranked[:5]}
