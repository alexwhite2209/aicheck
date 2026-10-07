"""Справочник сторонних сервисов.

`jurisdiction` — юрисдикция компании-владельца сервиса (RU / foreign / unknown), известная из открытых
сведений о компании. Это НЕ место расположения серверов: его по домену определить нельзя.
`user_data` — сервис получает данные посетителя (IP, cookie-идентификаторы, данные форм).
"""
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    type: str  # analytics | tag_manager | advertising | payment | maps | video | fonts | cdn | chat | crm | captcha | forms | calltracking | social | auth | protection
    purpose: str
    jurisdiction: str
    owner: str
    domains: tuple[str, ...] = ()
    url_patterns: tuple[str, ...] = ()  # подстроки полного URL
    script_patterns: tuple[str, ...] = ()  # regex по inline-скриптам
    cookie_patterns: tuple[str, ...] = ()  # regex по именам cookie
    user_data: bool = True
    category_ru: str = field(default="")


S = Service
SERVICES: tuple[Service, ...] = (
    # --- аналитика
    S("yandex_metrika", "Яндекс Метрика", "analytics", "Веб-аналитика, Вебвизор", "RU", "ООО «Яндекс»",
      ("mc.yandex.ru", "mc.yandex.com", "mc.yandex.by", "mc.yandex.kz", "mc.webvisor.org", "mc.webvisor.com"),
      ("/metrika/tag.js", "/metrika/watch.js"), (r"\bym\(\s*\d{5,}", r"yaCounter\d+"), (r"^_ym_", r"^yabs-sid$")),
    S("google_analytics", "Google Analytics", "analytics", "Веб-аналитика", "foreign", "Google LLC (США)",
      ("google-analytics.com", "analytics.google.com", "region1.google-analytics.com", "ssl.google-analytics.com"),
      ("googletagmanager.com/gtag/js",), (r"gtag\(\s*['\"]config['\"]\s*,\s*['\"](G|UA)-", r"\bga\(\s*['\"]create"), (r"^_ga$", r"^_ga_", r"^_gid$", r"^_gat")),
    S("google_tag_manager", "Google Tag Manager", "tag_manager", "Управление тегами (загружает другие скрипты)", "foreign", "Google LLC (США)",
      (), ("googletagmanager.com/gtm.js",), (r"GTM-[A-Z0-9]{4,}",), ()),
    S("top_mail_ru", "Top.Mail.Ru", "analytics", "Счётчик посещаемости, ретаргетинг VK Рекламы", "RU", "ООО «ВК»",
      ("top-fwz1.mail.ru", "top.mail.ru"), (), (r"_tmr\s*=|_tmr\.push",), (r"^tmr_",)),
    S("liveinternet", "LiveInternet", "analytics", "Счётчик посещаемости", "RU", "LiveInternet",
      ("counter.yadro.ru",), (), (), ()),
    S("ms_clarity", "Microsoft Clarity", "analytics", "Запись сессий, тепловые карты", "foreign", "Microsoft Corporation (США)",
      ("clarity.ms", "www.clarity.ms"), (), (r"clarity\.ms/tag",), (r"^_clck$", r"^_clsk$", r"^CLID$")),
    S("hotjar", "Hotjar", "analytics", "Запись сессий, тепловые карты", "foreign", "Hotjar Ltd (Мальта)",
      ("hotjar.com", "hotjar.io", "static.hotjar.com"), (), (r"hotjar\.com|_hjSettings",), (r"^_hj",)),
    S("amplitude", "Amplitude", "analytics", "Продуктовая аналитика", "foreign", "Amplitude Inc. (США)",
      ("amplitude.com", "cdn.amplitude.com", "api2.amplitude.com"), (), (), (r"^amp_",)),
    S("mixpanel", "Mixpanel", "analytics", "Продуктовая аналитика", "foreign", "Mixpanel Inc. (США)",
      ("mixpanel.com", "cdn.mxpnl.com"), (), (), (r"^mp_",)),
    # --- коллтрекинг / маркетинговая аналитика (РФ)
    S("roistat", "Roistat", "calltracking", "Сквозная аналитика, коллтрекинг", "RU", "Roistat",
      ("roistat.com", "cloud.roistat.com"), (), (r"roistat",), (r"^roistat",)),
    S("calltouch", "Calltouch", "calltracking", "Коллтрекинг", "RU", "Calltouch",
      ("calltouch.ru", "mod.calltouch.ru"), (), (), (r"^_ct",)),
    S("comagic", "UIS / CoMagic", "calltracking", "Коллтрекинг, онлайн-консультант", "RU", "UIS",
      ("comagic.ru", "uiscom.ru", "app.uiscom.ru", "app.comagic.ru"), (), (), ()),
    S("callibri", "Callibri", "calltracking", "Коллтрекинг", "RU", "Callibri",
      ("callibri.ru", "cdn.callibri.ru"), (), (), ()),
    # --- реклама
    S("yandex_ads", "Рекламная сеть Яндекса / Директ", "advertising", "Показ рекламы, конверсии", "RU", "ООО «Яндекс»",
      ("an.yandex.ru", "yandex.ru/ads", "bs.yandex.ru"), ("yastatic.net/partner-code", "/ads/system/context.js"), (r"yaContextCb|Ya\.Context", r"yandex_rtb_"), ()),
    S("adfox", "ADFOX", "advertising", "Управление рекламой", "RU", "ООО «Яндекс»",
      ("ads.adfox.ru", "adfox.ru", "adfox.yandex.ru"), (), (r"adfox", ), ()),
    S("vk_ads", "VK Реклама / Пиксель VK", "advertising", "Ретаргетинг, конверсии", "RU", "ООО «ВК»",
      ("ads.vk.com", "vk.com/rtrg", "ad.mail.ru", "r.mail.ru"), ("vk.com/js/api/openapi.js",), (r"VK\.Retargeting|vk\.com/rtrg",), ()),
    S("google_ads", "Google Ads / AdSense / DoubleClick", "advertising", "Показ рекламы, конверсии", "foreign", "Google LLC (США)",
      ("googleadservices.com", "googlesyndication.com", "pagead2.googlesyndication.com", "doubleclick.net", "googleads.g.doubleclick.net", "adservice.google.com"), (), (r"adsbygoogle|gtag\(\s*['\"]config['\"]\s*,\s*['\"]AW-",), (r"^_gcl_", r"^IDE$", r"^test_cookie$")),
    S("meta_pixel", "Meta Pixel (Facebook)", "advertising", "Ретаргетинг, конверсии", "foreign", "Meta Platforms Inc. (США; признана экстремистской организацией, деятельность запрещена в РФ)",
      ("connect.facebook.net", "facebook.com/tr"), (), (r"fbq\(\s*['\"]init",), (r"^_fbp$", r"^fr$")),
    S("tiktok_pixel", "TikTok Pixel", "advertising", "Ретаргетинг, конверсии", "foreign", "TikTok Pte. Ltd.",
      ("analytics.tiktok.com",), (), (r"ttq\.load",), (r"^_ttp$",)),
    S("criteo", "Criteo", "advertising", "Ретаргетинг", "foreign", "Criteo S.A. (Франция)",
      ("criteo.com", "criteo.net", "static.criteo.net"), (), (), ()),
    # --- чаты / CRM
    S("jivo", "JivoSite", "chat", "Онлайн-чат", "RU", "Jivo",
      ("jivosite.com", "code.jivosite.com", "code.jivo.ru", "jivo.ru"), (), (r"jivo_api|jivosite",), (r"^jv_",)),
    S("bitrix24", "Битрикс24", "crm", "CRM-формы, онлайн-чат, обратный звонок", "RU", "ООО «1С-Битрикс»",
      ("bitrix24.ru", "bitrix24.by", "bitrix24.kz", "cdn-ru.bitrix24.ru", "cdn.bitrix24.ru"), (), (r"b24form|BX\.SiteButton|bitrix24\.ru/b\d+",), ()),
    S("amocrm", "amoCRM", "crm", "CRM-формы, чат", "RU", "ООО «амоЦРМ»",
      ("amocrm.ru", "gso.amocrm.ru", "forms.amocrm.ru"), (), (r"amo_forms|amoSocialButton|amocrm",), ()),
    S("talk_me", "Talk-Me", "chat", "Онлайн-чат", "RU", "Talk-Me", ("talk-me.ru", "lcab.talk-me.ru"), (), (), ()),
    S("intercom", "Intercom", "chat", "Онлайн-чат", "foreign", "Intercom Inc. (США)",
      ("intercom.io", "widget.intercom.io", "intercomcdn.com"), (), (), (r"^intercom-",)),
    S("tawk", "tawk.to", "chat", "Онлайн-чат", "foreign", "tawk.to Inc.", ("tawk.to", "embed.tawk.to"), (), (), (r"^TawkConnectionTime$", r"^__tawkuuid$")),
    S("crisp", "Crisp", "chat", "Онлайн-чат", "foreign", "Crisp IM SAS (Франция)", ("crisp.chat", "client.crisp.chat"), (), (), (r"^crisp-client",)),
    S("livechat", "LiveChat", "chat", "Онлайн-чат", "foreign", "Text S.A. (Польша)", ("livechatinc.com", "cdn.livechatinc.com"), (), (), ()),
    # --- капча
    S("recaptcha", "Google reCAPTCHA", "captcha", "Защита форм от ботов", "foreign", "Google LLC (США)",
      ("recaptcha.net",), ("google.com/recaptcha", "gstatic.com/recaptcha"), (r"grecaptcha",), (r"^_GRECAPTCHA$",)),
    S("hcaptcha", "hCaptcha", "captcha", "Защита форм от ботов", "foreign", "Intuition Machines Inc. (США)", ("hcaptcha.com", "js.hcaptcha.com"), (), (), ()),
    S("cf_turnstile", "Cloudflare Turnstile", "captcha", "Защита форм от ботов", "foreign", "Cloudflare Inc. (США)", ("challenges.cloudflare.com",), (), (), ()),
    S("yandex_captcha", "Yandex SmartCaptcha", "captcha", "Защита форм от ботов", "RU", "ООО «Яндекс»",
      ("smartcaptcha.yandexcloud.net", "captcha-api.yandex.ru"), (), (), ()),
    # --- шрифты, CDN, защита
    S("google_fonts", "Google Fonts", "fonts", "Загрузка шрифтов", "foreign", "Google LLC (США)", ("fonts.googleapis.com", "fonts.gstatic.com"), (), (), ()),
    S("adobe_fonts", "Adobe Fonts", "fonts", "Загрузка шрифтов", "foreign", "Adobe Inc. (США)", ("use.typekit.net", "p.typekit.net"), (), (), ()),
    S("cloudflare_cdn", "Cloudflare (CDN / защита)", "protection", "CDN, защита от атак", "foreign", "Cloudflare Inc. (США)",
      ("cdnjs.cloudflare.com",), ("/cdn-cgi/",), (), (r"^__cf_bm$", r"^cf_clearance$", r"^__cflb$")),
    S("jsdelivr", "jsDelivr", "cdn", "Загрузка библиотек", "foreign", "jsDelivr (Prospect One, Польша)", ("cdn.jsdelivr.net", "fastly.jsdelivr.net"), (), (), ()),
    S("unpkg", "unpkg", "cdn", "Загрузка библиотек", "foreign", "unpkg (Cloudflare Inc.)", ("unpkg.com",), (), (), ()),
    S("google_cdn", "Google Hosted Libraries", "cdn", "Загрузка библиотек", "foreign", "Google LLC (США)", ("ajax.googleapis.com",), (), (), ()),
    S("yandex_cdn", "Яндекс CDN (yastatic)", "cdn", "Загрузка библиотек и ресурсов", "RU", "ООО «Яндекс»", ("yastatic.net",), (), (), ()),
    # --- карты и видео
    S("yandex_maps", "Яндекс Карты", "maps", "Карта на сайте", "RU", "ООО «Яндекс»", ("api-maps.yandex.ru", "enterprise.api-maps.yandex.ru"), ("yandex.ru/map-widget", "yandex.ru/maps", "yandex.com/map-widget"), (), ()),
    S("2gis", "2ГИС", "maps", "Карта на сайте", "RU", "ООО «ДубльГИС»", ("maps.api.2gis.ru", "widgets.2gis.com", "tile0.maps.2gis.com"), (), (), ()),
    S("google_maps", "Google Maps", "maps", "Карта на сайте", "foreign", "Google LLC (США)", ("maps.googleapis.com", "maps.gstatic.com"), ("google.com/maps", "maps.google."), (), ()),
    S("youtube", "YouTube", "video", "Встроенное видео", "foreign", "Google LLC (США)", ("youtube.com", "youtube-nocookie.com", "ytimg.com", "youtu.be", "googlevideo.com"), (), (), (r"^VISITOR_INFO1_LIVE$", r"^YSC$")),
    S("vimeo", "Vimeo", "video", "Встроенное видео", "foreign", "Vimeo Inc. (США)", ("vimeo.com", "player.vimeo.com", "vimeocdn.com"), (), (), ()),
    S("rutube", "Rutube", "video", "Встроенное видео", "RU", "ООО «Руфорт»", ("rutube.ru",), (), (), ()),
    S("vk_video", "VK Видео", "video", "Встроенное видео", "RU", "ООО «ВК»", (), ("vk.com/video_ext", "vkvideo.ru/video_ext"), (), ()),
    # --- соцсети и мессенджеры
    S("vk_widgets", "Виджеты VK", "social", "Кнопки и виджеты соцсети", "RU", "ООО «ВК»", ("vk.com", "userapi.com", "vk.ru"), (), (), ()),
    S("ok_widgets", "Одноклассники", "social", "Кнопки и виджеты соцсети", "RU", "ООО «ВК»", ("ok.ru", "connect.ok.ru"), (), (), ()),
    S("telegram_widget", "Telegram", "social", "Виджет / кнопка мессенджера", "foreign", "Telegram (ОАЭ)", ("telegram.org",), (), (), ()),
    S("twitter", "X (Twitter)", "social", "Виджеты соцсети", "foreign", "X Corp. (США)", ("platform.twitter.com", "syndication.twitter.com"), (), (), ()),
    # --- конструкторы и внешние обработчики форм
    S("google_forms", "Google Forms", "forms", "Внешний обработчик форм", "foreign", "Google LLC (США)", ("forms.gle",), ("docs.google.com/forms",), (), ()),
    S("typeform", "Typeform", "forms", "Внешний обработчик форм", "foreign", "Typeform S.L. (Испания)", ("typeform.com", "form.typeform.com", "embed.typeform.com"), (), (), ()),
    S("jotform", "Jotform", "forms", "Внешний обработчик форм", "foreign", "Jotform Inc. (США)", ("jotform.com", "form.jotform.com", "jotfor.ms"), (), (), ()),
    S("formspree", "Formspree", "forms", "Внешний обработчик форм", "foreign", "Formspree Inc. (США)", ("formspree.io",), (), (), ()),
    S("getform", "Getform", "forms", "Внешний обработчик форм", "foreign", "Getform", ("getform.io",), (), (), ()),
    S("formsubmit", "FormSubmit", "forms", "Внешний обработчик форм", "foreign", "FormSubmit", ("formsubmit.co",), (), (), ()),
    S("hubspot_forms", "HubSpot Forms", "forms", "Внешний обработчик форм, CRM", "foreign", "HubSpot Inc. (США)", ("hsforms.com", "hsforms.net", "js.hsforms.net", "forms.hubspot.com", "js.hs-scripts.com"), (), (), (r"^hubspotutk$", r"^__hs")),
    S("tally", "Tally", "forms", "Внешний обработчик форм", "foreign", "Tally BV (Бельгия)", ("tally.so",), (), (), ()),
    S("web3forms", "Web3Forms", "forms", "Внешний обработчик форм", "foreign", "Web3Forms", ("api.web3forms.com",), (), (), ()),
    S("ms_forms", "Microsoft Forms", "forms", "Внешний обработчик форм", "foreign", "Microsoft Corporation (США)", ("forms.office.com",), (), (), ()),
    S("yandex_forms", "Яндекс Формы", "forms", "Внешний обработчик форм", "RU", "ООО «Яндекс»", ("forms.yandex.ru",), (), (), ()),
    S("tilda", "Tilda", "forms", "Конструктор сайта и обработчик форм", "unknown", "Tilda Publishing", ("tildacdn.com", "forms.tildacdn.com", "tilda.ws", "tildaapi.com", "static.tildacdn.com"), (), (), (r"^tildauid$", r"^tildasid$")),
    S("marquiz", "Marquiz", "forms", "Квизы и формы", "unknown", "Marquiz", ("marquiz.ru", "script.marquiz.ru"), (), (), ()),
    # --- платежи
    S("yookassa", "ЮKassa", "payment", "Приём платежей", "RU", "НКО «ЮМани»", ("yookassa.ru", "yoomoney.ru", "checkout.yookassa.ru", "yoomoney.ru/checkout"), (), (r"YooMoneyCheckoutWidget|yookassa",), ()),
    S("cloudpayments", "CloudPayments", "payment", "Приём платежей", "RU", "ООО «Клауд Пэйментс»", ("cloudpayments.ru", "widget.cloudpayments.ru"), (), (r"cp\.CloudPayments",), ()),
    S("robokassa", "Robokassa", "payment", "Приём платежей", "RU", "ООО «Робокасса»", ("robokassa.ru", "auth.robokassa.ru", "robokassa.com"), (), (), ()),
    S("tbank", "Т-Банк (эквайринг)", "payment", "Приём платежей", "RU", "АО «ТБанк»", ("securepay.tinkoff.ru", "securepayments.tinkoff.ru", "acdn.tinkoff.ru", "tbank.ru", "securepay.tbank.ru"), (), (), ()),
    S("sber_pay", "СберБанк (эквайринг)", "payment", "Приём платежей", "RU", "ПАО Сбербанк", ("securepayments.sberbank.ru", "ecom.sberbank.ru", "payecom.ru"), (), (), ()),
    S("paykeeper", "PayKeeper", "payment", "Приём платежей", "RU", "PayKeeper", ("paykeeper.ru",), (), (), ()),
    S("prodamus", "Prodamus", "payment", "Приём платежей", "RU", "Prodamus", ("payform.ru", "prodamus.ru"), (), (), ()),
    S("sbp", "Система быстрых платежей", "payment", "Оплата через СБП", "RU", "АО «НСПК»", ("qr.nspk.ru",), (), (), ()),
    S("stripe", "Stripe", "payment", "Приём платежей", "foreign", "Stripe Inc. (США)", ("js.stripe.com", "stripe.com", "checkout.stripe.com"), (), (), (r"^__stripe_",)),
    S("paypal", "PayPal", "payment", "Приём платежей", "foreign", "PayPal Holdings (США)", ("paypal.com", "paypalobjects.com"), (), (), ()),
)

# Провайдеры авторизации (для 149-ФЗ ст. 8 ч. 10)
AUTH_PROVIDERS = (
    ("google", "Google", "foreign", ("accounts.google.com",), r"(войти|вход|sign in|login|continue)\s+(через|с помощью|with)\s+google"),
    ("apple", "Apple ID", "foreign", ("appleid.apple.com",), r"(войти|вход|sign in)\s+(через|с помощью|with)\s+apple"),
    ("facebook", "Facebook", "foreign", ("facebook.com/dialog/oauth", "facebook.com/v"), r"(войти|вход|sign in)\s+(через|с помощью|with)\s+facebook"),
    ("microsoft", "Microsoft", "foreign", ("login.microsoftonline.com", "login.live.com"), r"(войти|sign in)\s+(через|with)\s+microsoft"),
    ("github", "GitHub", "foreign", ("github.com/login/oauth",), r"(войти|sign in)\s+(через|with)\s+github"),
    ("vk", "VK ID", "RU", ("id.vk.com", "oauth.vk.com", "id.vk.ru"), r"(войти|вход)\s+(через|с)\s+(vk|вк|вконтакте|vk id)"),
    ("yandex", "Яндекс ID", "RU", ("oauth.yandex.ru", "passport.yandex.ru/auth"), r"(войти|вход)\s+(через|с)\s+(яндекс|yandex)"),
    ("gosuslugi", "Госуслуги (ЕСИА)", "RU", ("esia.gosuslugi.ru",), r"(войти|вход)\s+(через|с помощью)\s+госуслуг"),
    ("sber", "Сбер ID", "RU", ("id.sber.ru", "online.sberbank.ru/CSAFront/oidc"), r"(войти|вход)\s+(через|по)\s+сбер\s?id"),
    ("tbank", "T-ID", "RU", ("id.tbank.ru", "id.tinkoff.ru"), r"(войти|вход)\s+(через|с)\s+(t-id|tinkoff id|т-id)"),
    ("mailru", "Mail ID", "RU", ("oauth.mail.ru",), r"(войти|вход)\s+(через|с)\s+mail"),
)

_COMPILED = [(s, [re.compile(p, re.I) for p in s.script_patterns], [re.compile(p) for p in s.cookie_patterns]) for s in SERVICES]


def _host_matches(host: str, domain: str) -> bool:
    if "/" in domain:
        return False
    return host == domain or host.endswith("." + domain)


def match_url(url: str, host: str) -> Service | None:
    low = url.lower()
    for s in SERVICES:
        if any(_host_matches(host, d) for d in s.domains):
            return s
        if any(p in low for p in s.url_patterns) or any("/" in d and d in low for d in s.domains):
            return s
    return None


def match_inline_script(text: str) -> list[Service]:
    found = []
    for s, pats, _ in _COMPILED:
        if pats and any(p.search(text) for p in pats):
            found.append(s)
    return found


def match_cookie(name: str) -> Service | None:
    for s, _, cpats in _COMPILED:
        if any(p.search(name) for p in cpats):
            return s
    return None


SERVICE_BY_ID = {s.id: s for s in SERVICES}

TYPE_RU = {
    "analytics": "Аналитика", "tag_manager": "Менеджер тегов", "advertising": "Реклама", "payment": "Платежи",
    "maps": "Карты", "video": "Видео", "fonts": "Шрифты", "cdn": "CDN", "chat": "Онлайн-чат", "crm": "CRM",
    "captcha": "Капча", "forms": "Формы", "calltracking": "Коллтрекинг", "social": "Соцсети", "auth": "Авторизация",
    "protection": "CDN / защита", "other": "Прочее",
}
