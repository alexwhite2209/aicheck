"""PDF-отчёт (ReportLab) с кириллическими шрифтами."""
import io
import os
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from ..legal.score import DISCLAIMER as SCORE_DISCLAIMER

DISCLAIMER = ("Автоматизированный аудит является информационным инструментом и не является юридическим заключением. "
              "Результаты основаны на данных, доступных сервису в момент проверки, и не заменяют консультацию квалифицированного специалиста.")
FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]
STATUS_COLOR = {"FAIL": "#d9433f", "REVIEW": "#d6a21e", "PASS": "#2e9d5b", "UNKNOWN": "#8a8f98", "NA": "#8a8f98"}
STATUS_LABEL = {"FAIL": "Вероятно не выполнено", "REVIEW": "Требует внимания", "PASS": "Выполнено по признакам",
                "UNKNOWN": "Не удалось определить", "NA": "Не применимо"}
STATE_RU = {"VERIFIED_RANGE": "VERIFIED RANGE — рассчитанный диапазон", "ESTIMATED_RANGE": "ESTIMATED RANGE — оценочный диапазон",
            "NOT_DETERMINABLE": "NOT DETERMINABLE — корректная денежная оценка невозможна"}
_FONTS_READY = False


def _fonts() -> tuple[str, str]:
    global _FONTS_READY
    if _FONTS_READY:
        return "Body", "BodyBold"
    for reg, bold in FONT_CANDIDATES:
        if os.path.exists(reg) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("Body", reg))
            pdfmetrics.registerFont(TTFont("BodyBold", bold))
            _FONTS_READY = True
            return "Body", "BodyBold"
    raise RuntimeError("Не найден шрифт с кириллицей (установите fonts-dejavu-core)")


def rub(v: int | float | None) -> str:
    return "—" if v is None else f"{int(v):,}".replace(",", " ") + " ₽"


def build_pdf(audit: dict) -> bytes:
    font, bold = _fonts()
    ss = {
        "h1": ParagraphStyle("h1", fontName=bold, fontSize=20, leading=24, spaceAfter=6, textColor=colors.HexColor("#111318")),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=13.5, leading=17, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#111318")),
        "h3": ParagraphStyle("h3", fontName=bold, fontSize=10.5, leading=13.5, spaceBefore=4, spaceAfter=2),
        "p": ParagraphStyle("p", fontName=font, fontSize=9, leading=12.5, alignment=TA_LEFT),
        "small": ParagraphStyle("small", fontName=font, fontSize=7.6, leading=10, textColor=colors.HexColor("#555b66")),
        "code": ParagraphStyle("code", fontName=font, fontSize=7, leading=9, textColor=colors.HexColor("#3a3f48"), backColor=colors.HexColor("#f3f4f6"),
                               borderPadding=3, spaceBefore=5, spaceAfter=6),
    }
    P = lambda t, s="p": Paragraph(escape(str(t or "")).replace("\n", "<br/>"), ss[s])  # noqa: E731
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Аудит сайта {audit['host']}", author="Норма — AI-аудит сайтов")
    facts = audit.get("facts") or {}
    results = audit.get("results") or []
    exp = audit.get("exposure") or {}
    counts = audit.get("counts") or {}
    ai = audit.get("ai") or {}
    story = []

    created = audit.get("finished_at") or audit.get("created_at")
    when = datetime.fromisoformat(created).strftime("%d.%m.%Y %H:%M UTC") if created else ""
    story += [P("Отчёт об автоматическом аудите сайта", "h1"),
              P(f"{audit['url']}", "h3"),
              P(f"Дата проверки: {when} · Тип сайта: {facts.get('site_type_ru', '—')} · Проверено страниц: {len(facts.get('pages', []))}", "small"),
              Spacer(1, 8)]
    score = audit.get("score")
    head = [["Russian Website Compliance Score", "Финансовая экспозиция"],
            [f"{score if score is not None else '—'} / 100", f"{rub(exp.get('min'))} – {rub(exp.get('max'))}" if exp.get("items") else "0 ₽"]]
    t = Table(head, colWidths=[85 * mm, 93 * mm])
    t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, 0), font), ("FONTSIZE", (0, 0), (-1, 0), 8), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#6b7280")),
                           ("FONTNAME", (0, 1), (-1, 1), bold), ("FONTSIZE", (0, 1), (-1, 1), 17), ("LEADING", (0, 1), (-1, 1), 22),
                           ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d1d5db")), ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#e5e7eb")),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [t, Spacer(1, 4), P(SCORE_DISCLAIMER, "small"),
              P(f"Финансовая оценка: {STATE_RU.get(exp.get('state'), '—')}. {exp.get('note', '')}", "small")]
    if exp.get("potential", {}).get("items"):
        story.append(P(f"Дополнительно по пунктам, требующим проверки (не входит в сумму): {rub(exp['potential']['min'])} – {rub(exp['potential']['max'])}.", "small"))
    story += [Spacer(1, 6),
              P(f"Проблемы: {counts.get('fail', 0)} · Требуют внимания: {counts.get('review', 0)} · Пройдено: {counts.get('pass', 0)} · "
                f"Невозможно определить автоматически: {counts.get('unknown', 0)}", "h3")]
    if ai.get("summary"):
        story += [P("Краткий вывод", "h2"), P(ai["summary"])]

    def card(r: dict) -> list:
        color = STATUS_COLOR.get(r["status"], "#888")
        items = [Paragraph(f'<font color="{color}">●</font> <b>{escape(r["category"].upper())}</b> — {escape(r["title"])}', ss["h3"]),
                 P(f"Статус: {STATUS_LABEL[r['status']]} · Уверенность: {r['confidence_ru']} · Критичность: {r['severity']} · Правило: {r['rule_id']} v{r['version']}", "small"),
                 P(f"Что найдено: {r['fact']}")]
        for e in r.get("evidence", [])[:3]:
            line = " · ".join(x for x in [e.get("label"), e.get("page")] if x)
            if line:
                items.append(P(f"Доказательство: {line}", "small"))
            if e.get("snippet"):
                items.append(P(e["snippet"][:500], "code"))
        for b in r.get("basis", []):
            items.append(P(f"Нормативное основание: {b['label']} ({b['edition']}; сверено {b['checked_at']}). {b['official_url']}", "small"))
            items.append(P(b["text"][:700] + ("…" if len(b["text"]) > 700 else ""), "code"))
        a = (ai.get("items") or {}).get(r["rule_id"], {})
        items.append(P(f"Почему это важно: {a.get('explanation') or r['why']}"))
        items.append(P(f"Что сделать: {a.get('recommendation') or r['fix']}"))
        f = r.get("finance", {})
        if f.get("min_value") is not None:
            items.append(P(f"Финансовая оценка ({STATE_RU.get(f['state'], '')}): {rub(f['min_value'])} – {rub(f['max_value'])}. {f.get('calculation_method', '')}", "small"))
        items.append(Spacer(1, 7))
        return [KeepTogether(items[:4]), *items[4:]]

    groups = [("Найденные проблемы", "FAIL"), ("Требуют внимания", "REVIEW"), ("Невозможно определить автоматически", "UNKNOWN"), ("Пройденные проверки", "PASS")]
    for title, status in groups:
        rs = [r for r in results if r["status"] == status]
        if not rs:
            continue
        story.append(P(f"{title} ({len(rs)})", "h2"))
        for r in rs:
            if status == "PASS":
                story.append(P(f"✓ {r['title']} — {r['fact']} [{r['rule_id']}]", "small"))
            else:
                story += card(r)
    if ai.get("policy_remarks"):
        story += [P("Замечания AI к тексту политики (справочно, на статусы не влияют)", "h2")] + [P(f"• {x}") for x in ai["policy_remarks"]]

    story += [PageBreak(), P("Фактические данные", "h2")]
    svc = facts.get("external_services", [])
    if svc:
        rows = [["Сервис", "Тип", "Назначение", "Владелец"]] + [[s["name"], s["type_ru"], s["purpose"], s["owner"]] for s in svc[:40]]
        tb = Table([[Paragraph(escape(str(c)), ss["small"]) for c in row] for row in rows], colWidths=[40 * mm, 26 * mm, 52 * mm, 60 * mm], repeatRows=1)
        tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6"))]))
        story += [P("Внешние сервисы", "h3"), tb, P("Владелец — компания-правообладатель сервиса; место расположения серверов по домену не определяется.", "small")]
    cs = facts.get("cookie_stats", {})
    story += [P("Cookies", "h3"), P(f"Всего: {cs.get('total', 0)} · first-party: {cs.get('first_party', 0)} · third-party: {cs.get('third_party', 0)} · "
                                    f"аналитика: {cs.get('analytics', 0)} · реклама: {cs.get('advertising', 0)}")]
    docs = facts.get("documents", [])
    if docs:
        story.append(P("Документы на сайте", "h3"))
        for d in docs[:20]:
            story.append(P(f"{d.get('kind_ru', d['kind'])}: {d['url']} — {'доступен' if d.get('accessible') else ('недоступен' if d.get('accessible') is False else 'не проверялся')}", "small"))
    cd = facts.get("company_details", {})
    story += [P("Реквизиты и контакты", "h3"),
              P(f"Наименование: {', '.join(cd.get('names', [])) or 'не найдено'}; ИНН: {', '.join(cd.get('inn', [])) or '—'}; "
                f"ОГРН/ОГРНИП: {', '.join(cd.get('ogrn', []) + cd.get('ogrnip', [])) or '—'}; адрес: {'; '.join(cd.get('addresses', [])[:2]) or 'не найден'}; "
                f"email: {', '.join(facts.get('contacts', {}).get('emails', [])[:3]) or '—'}", "small")]

    sec = audit.get("security") or {}
    if sec.get("findings") is not None:
        story += [PageBreak(), P("Проверка безопасности", "h2"),
                  P(f"Security score: {sec.get('score') if sec.get('score') is not None else '—'} / 100 · "
                    f"проблемы: {sec.get('counts', {}).get('fail', 0)} · требуют внимания: {sec.get('counts', {}).get('review', 0)} · "
                    f"пройдено: {sec.get('counts', {}).get('pass', 0)}", "h3")]
        SEV_RU = {"critical": "критично", "high": "высокий", "medium": "средний", "low": "низкий", "info": "факт"}
        for f in sec["findings"]:
            if f["status"] == "PASS":
                continue
            color = STATUS_COLOR.get("FAIL" if f["status"] == "FAIL" else "REVIEW", "#888")
            items = [Paragraph(f'<font color="{color}">●</font> <b>{escape(f["title"])}</b>', ss["h3"]),
                     P(f"{f['skill']} · критичность: {SEV_RU.get(f['severity'], f['severity'])} · статус: {'проблема' if f['status']=='FAIL' else 'требует внимания'}", "small"),
                     P(f"Что найдено: {f['fact']}")]
            if f.get("tech"):
                items.append(P(f"Технически: {f['tech']}", "small"))
            for e in f.get("evidence", [])[:3]:
                line = " · ".join(x for x in [e.get("label"), e.get("page")] if x)
                if line:
                    items.append(P(line, "small"))
                if e.get("snippet"):
                    items.append(P(str(e["snippet"])[:300], "code"))
            if f.get("legal_basis"):
                items.append(P(f"Связь с законом: {f['legal_basis']['label']} ({f['legal_basis']['edition']}). {f.get('legal_note', '')}", "small"))
            items.append(P(f"Что сделать: {f['recommendation']}"))
            items.append(Spacer(1, 6))
            story += items
        story.append(P(sec.get("disclaimer", ""), "small"))

    reg = audit.get("registries") or {}
    if reg:
        story += [P("Проверка по реестрам", "h2")]
        dom = reg.get("domain", {})
        if dom.get("registered"):
            story.append(P(f"Домен {dom.get('domain')}: зарегистрирован {dom.get('created') or '—'}"
                           + (f", возраст {dom['age_years']} лет" if dom.get("age_years") is not None else "")
                           + f", регистратор {dom.get('registrar') or '—'}, оплачен до {dom.get('expires') or '—'}.", "small"))
        eg = reg.get("egrul", {})
        if eg.get("found"):
            story.append(P(f"ЕГРЮЛ/ЕГРИП: {eg.get('name')} — {eg.get('status')} (ОГРН {eg.get('ogrn')}).", "small"))
        elif eg.get("manual"):
            story.append(P(f"ЕГРЮЛ/ЕГРИП: {eg.get('note')} {eg.get('link', '')}", "small"))
        rkn = reg.get("rkn", {})
        for x in rkn.get("registries", []):
            story.append(P(f"{x['title']}: {x['why']} — {x['link']}", "small"))

    snap = audit.get("snapshot") or {}
    story += [P("Методология", "h2"),
              P("Сервис открывает публичную часть сайта в браузере (до 20 страниц, глубина 2), без авторизации и без отправки форм, "
                "собирает факты (формы, cookies, сетевые запросы, документы, реквизиты) и сопоставляет их с правилами из нормативной базы. "
                "Каждое правило опирается на нормы, выгруженные из официального источника (ИПС «Законодательство России», pravo.gov.ru). "
                "Статусы: «выполнено по признакам», «вероятно не выполнено», «требует внимания», «не удалось определить». "
                "Отсутствие элемента означает, что он не найден на проверенных страницах."),
              P("Score = 100 × Σ(вес × оценка) / Σ вес, где вес: critical 10, high 6, medium 3, low 1; оценка: выполнено 1, требует внимания 0,5, "
                "не выполнено 0; пункты «не удалось определить» не учитываются.", "small"),
              P("Финансовая экспозиция — сумма диапазонов санкций КоАП РФ по пунктам «вероятно не выполнено», без двойного счёта одной части статьи. "
                "Тип субъекта определяется по реквизитам на сайте; ИП без отдельной санкции — как должностные лица (примечание к ст. 2.4 КоАП РФ).", "small"),
              P(f"Версия движка: {snap.get('engine', '—')}. Применены версии правил: " + ", ".join(f"{x['rule_id']} v{x['version']}" for x in snap.get("rules", [])), "small"),
              Spacer(1, 10), P("Disclaimer", "h2"), P(DISCLAIMER)]

    def on_page(canvas, d):
        canvas.saveState()
        canvas.setFont(font, 7)
        canvas.setFillColor(colors.HexColor("#8a8f98"))
        canvas.drawString(16 * mm, 9 * mm, f"Норма · AI-аудит сайтов · {audit['host']} · не является юридическим заключением")
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"стр. {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
