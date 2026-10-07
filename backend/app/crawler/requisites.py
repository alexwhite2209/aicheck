"""Извлечение реквизитов и контактов из текста страниц с проверкой контрольных чисел."""
import re

INN_RE = re.compile(r"ИНН\s*(?:/\s*КПП)?[:\s№]*?(\d{10}|\d{12})(?!\d)", re.I)
OGRN_RE = re.compile(r"ОГРН(?!\s?ИП)\s*[:\s№]*?(\d{13})(?!\d)", re.I)
OGRNIP_RE = re.compile(r"ОГРН\s?ИП\s*[:\s№]*?(\d{15})(?!\d)", re.I)
EMAIL_RE = re.compile(r"(?<![\w.+-])([a-zA-Z0-9][\w.+-]{0,63}@[a-zA-Z0-9-]{1,63}(?:\.[a-zA-Z0-9-]{1,63})*\.(?:[a-zA-Z]{2,24}|рф))(?![\w-])", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+7|8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")
LEGAL_NAME_RE = re.compile(
    r"\b(ООО|АО|ПАО|НАО|ЗАО|ОАО|АНО|НКО|ФГУП|ГУП|МУП|ФГБУ|ГБУ|МБУ)\s*[«\"“„]\s*([^»\"”\n]{2,90})\s*[»\"”]"
    r"|(Общество с ограниченной ответственностью|Акционерное общество|Публичное акционерное общество)\s*[«\"“„]\s*([^»\"”\n]{2,90})\s*[»\"”]",
)
IP_NAME_RE = re.compile(r"\b(ИП|Индивидуальный предприниматель)\s+([А-ЯЁ][а-яё\-]+(?:\s+[А-ЯЁ][а-яё\-]+){1,2}|[А-ЯЁ][а-яё\-]+\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.)")
ADDRESS_RE = re.compile(
    r"(?:(?:юридический|фактический|почтовый)\s+)?адрес[а-я]*\s*(?:офиса|компании|организации)?\s*[:\-]\s*([^\n]{10,200})"
    r"|(\b\d{6}\b,?\s*(?:Россия,?\s*)?(?:[А-ЯЁ][^\n,]{2,40},\s*){0,3}(?:г\.|город|пос\.|с\.)\s*[А-ЯЁ][^\n]{3,150})"
    r"|((?:г\.|город)\s*[А-ЯЁ][а-яё\-]+,?\s*(?:ул\.|улица|пр-т|проспект|пер\.|переулок|ш\.|шоссе|наб\.|набережная|б-р|бульвар|пл\.|площадь|мкр\.?)\s*[^\n]{3,120})",
    re.I,
)
IMG_EMAIL_RE = re.compile(r"\.(png|jpe?g|gif|webp|svg)$", re.I)


def inn_valid(inn: str) -> bool:
    d = [int(c) for c in inn]
    if len(d) == 10:
        k = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        return sum(a * b for a, b in zip(k, d)) % 11 % 10 == d[9]
    if len(d) == 12:
        k1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        k2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        return (sum(a * b for a, b in zip(k1, d)) % 11 % 10 == d[10]
                and sum(a * b for a, b in zip(k2, d)) % 11 % 10 == d[11])
    return False


def ogrn_valid(ogrn: str) -> bool:
    if len(ogrn) == 13:
        return int(ogrn[:12]) % 11 % 10 == int(ogrn[12])
    if len(ogrn) == 15:
        return int(ogrn[:14]) % 13 % 10 == int(ogrn[14])
    return False


def _uniq(xs, limit=10):
    out = []
    for x in xs:
        x = x.strip()
        if x and x not in out:
            out.append(x)
    return out[:limit]


def normalize_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p)
    if len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
        return f"+7 {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return p.strip()


def extract_requisites(texts: list[str], links: list[dict]) -> dict:
    joined = "\n".join(texts)
    inn = [m for m in INN_RE.findall(joined) if inn_valid(m)]
    ogrn = [m for m in OGRN_RE.findall(joined) if ogrn_valid(m)]
    ogrnip = [m for m in OGRNIP_RE.findall(joined) if ogrn_valid(m)]
    # ОГРНИП, записанный как «ОГРН: 15 цифр»
    ogrnip += [m for m in re.findall(r"ОГРН\s*[:\s№]*?(\d{15})(?!\d)", joined) if ogrn_valid(m)]
    names = []
    for m in LEGAL_NAME_RE.finditer(joined):
        form = m.group(1) or m.group(3)
        name = m.group(2) or m.group(4)
        names.append(f"{form} «{name.strip()}»")
    ip_names = [f"ИП {m.group(2)}" for m in IP_NAME_RE.finditer(joined)]
    addresses = []
    for m in ADDRESS_RE.finditer(joined):
        a = next(g for g in m.groups() if g)
        a = re.split(r"\s{2,}|Тел|тел\.|E-?mail|ИНН|ОГРН|Режим|График|Схема|схема проезда|Обратная связь|Ваше имя|Как добраться|Карта|Время работы|Пн[-–]|\+7|8 \(", a)[0].strip(" ,.;:")
        if len(a) > 160:
            a = a[:160].rsplit(" ", 1)[0] + "…"
        if len(a) >= 10 and re.search(r"\d", a):
            addresses.append(a[:200])
    emails = [e for e in EMAIL_RE.findall(joined) if not IMG_EMAIL_RE.search(e)]
    phones = [normalize_phone(p) for p in PHONE_RE.findall(joined)]
    for ln in links:
        href = ln.get("href", "")
        if href.startswith("mailto:"):
            emails.append(href[7:].split("?")[0])
        elif href.startswith("tel:"):
            phones.append(normalize_phone(href[4:]))
    if ogrn or names:
        subject = "legal"
    elif ogrnip or ip_names:
        subject = "ip"
    else:
        subject = "unknown"
    return {
        "inn": _uniq(inn), "ogrn": _uniq(ogrn), "ogrnip": _uniq(ogrnip),
        "names": _uniq(names + ip_names), "addresses": _uniq(addresses, 5),
        "emails": _uniq([e.lower() for e in emails]), "phones": _uniq(phones),
        "subject_type": subject,
    }
