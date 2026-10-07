"""AI-объяснения через OpenRouter. Ключ только на backend.

AI получает факты, сработавшие правила и дословный текст норм, и формулирует объяснения. Статусы, нормы и суммы
AI не меняет. Ответ проходит проверку: ссылки на статьи вне переданных норм, денежные суммы и обещания
гарантий отбрасываются — вместо них используется шаблонный текст правила.
"""
import json
import logging
import re
import time

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — помощник сервиса автоматического аудита сайтов по законодательству РФ. Ты НЕ юрист и НЕ даёшь юридических заключений.
Тебе передают: (1) факты, обнаруженные краулером на сайте; (2) результаты правил со статусом и уверенностью; (3) дословный текст норм.
Твоя задача — для каждого переданного правила простым языком:
- explanation: объяснить, что обнаружено и почему это важно, связав факт с переданной нормой (2–4 предложения);
- recommendation: конкретно, что сделать владельцу сайта (1–3 предложения).
Жёсткие запреты:
- не упоминай статьи, законы и нормы, которых нет в переданном тексте норм этого правила;
- не называй суммы штрафов и любые денежные суммы;
- не придумывай элементы сайта, которых нет в фактах; не утверждай, что элемент отсутствует, если это не следует из факта;
- не меняй статус: REVIEW — «требует проверки», UNKNOWN — «недостаточно данных для автоматического вывода», FAIL — «вероятно не выполнено»;
- не гарантируй соответствие законодательству и не пиши «сайт нарушает закон».
Если данных недостаточно — так и напиши: «Недостаточно данных для автоматического вывода».
Отвечай строго JSON: {"summary": "общий вывод в 2–3 предложениях без сумм", "items": [{"rule_id": "...", "explanation": "...", "recommendation": "..."}],
"policy_remarks": ["замечания к тексту политики, если передан её фрагмент; не более 5"]}"""

ART_RE = re.compile(r"(?:ст\.|стать[яиеюй])\s*(\d+(?:\.\d+)?(?:-\d+)?)", re.I)
MONEY_RE = re.compile(r"\d[\d\s]*\s?(₽|руб|тыс\.|млн)", re.I)
BANNED_RE = re.compile(r"гарантир|нарушает закон|является нарушением закона|юридическое заключение", re.I)


def _allowed_articles(result: dict) -> set[str]:
    return {b["article"] for b in result.get("basis", [])}


def _clean(text: str, allowed: set[str]) -> str | None:
    text = (text or "").strip()
    if not text or len(text) > 1500:
        return None
    if MONEY_RE.search(text) or BANNED_RE.search(text):
        return None
    for art in ART_RE.findall(text):
        if art not in allowed:
            return None
    return text


def _payload(facts: dict, results: list[dict]) -> str:
    items = []
    for r in results:
        items.append({
            "rule_id": r["rule_id"], "title": r["title"], "status": r["status"], "confidence": r["confidence_ru"],
            "fact": r["fact"], "evidence": [e.get("label", "") for e in r.get("evidence", [])][:4],
            "norms": [{"label": b["label"], "text": b["text"][:1400]} for b in r.get("basis", [])],
        })
    summary = {
        "site_type": facts.get("site_type_ru"), "pages_checked": len(facts.get("pages", [])),
        "forms_with_pd": sum(1 for f in facts.get("forms", []) if f.get("has_pd")),
        "services": [s["name"] for s in facts.get("external_services", [])][:20],
        "cookies": facts.get("cookie_stats"),
    }
    policy = next((d for d in facts.get("documents", []) if d["kind"] == "privacy_policy" and d.get("excerpt")), None)
    data = {"site": summary, "rules": items}
    if policy:
        data["policy_excerpt"] = policy["excerpt"][:9000]
    return json.dumps(data, ensure_ascii=False)


def explain(facts: dict, results: list[dict], ai_settings: dict) -> dict:
    st = get_settings()
    targets = [r for r in results if r["status"] in ("FAIL", "REVIEW", "UNKNOWN")][:14]
    out = {"used": False, "model": None, "items": {}, "summary": None, "policy_remarks": [], "error": None}
    if not targets or not st.openrouter_api_key or not ai_settings.get("enabled", True):
        out["error"] = None if targets and st.openrouter_api_key else ("AI отключён" if targets else None)
        return out
    model = ai_settings.get("model") or st.openrouter_model
    body = {
        "model": model, "temperature": float(ai_settings.get("temperature", 0.2)), "max_tokens": int(ai_settings.get("max_tokens", 2500)),
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": _payload(facts, targets)}],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {st.openrouter_api_key}", "HTTP-Referer": st.public_base_url, "X-Title": "Norma Audit"}
    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=90) as client:
            resp = client.post(f"{st.openrouter_base_url}/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", content, re.S)
        data = json.loads(m.group(0) if m else content)
    except Exception as e:
        log.warning("OpenRouter error: %s", e)
        out["error"] = f"AI недоступен: {type(e).__name__}"
        return out
    by_id = {r["rule_id"]: r for r in targets}
    for it in data.get("items", []):
        rid = it.get("rule_id")
        if rid not in by_id:
            continue  # AI не может добавлять правила
        allowed = _allowed_articles(by_id[rid])
        exp = _clean(it.get("explanation", ""), allowed)
        rec = _clean(it.get("recommendation", ""), allowed)
        if exp or rec:
            out["items"][rid] = {"explanation": exp, "recommendation": rec}
    summ = _clean(data.get("summary", ""), {b["article"] for r in targets for b in r.get("basis", [])})
    out["summary"] = summ
    out["policy_remarks"] = [x for x in (_clean(p, set()) for p in data.get("policy_remarks", [])[:5]) if x]
    out.update(used=True, model=model, duration_s=round(time.monotonic() - t0, 1))
    return out


def list_models() -> list[dict]:
    st = get_settings()
    try:
        with httpx.Client(timeout=20) as client:
            r = client.get(f"{st.openrouter_base_url}/models")
            r.raise_for_status()
            models = r.json().get("data", [])
    except Exception as e:
        log.warning("OpenRouter models error: %s", e)
        return []
    res = []
    for m in models:
        p = m.get("pricing", {})
        res.append({"id": m.get("id"), "name": m.get("name"), "context": m.get("context_length"),
                    "prompt_price": p.get("prompt"), "completion_price": p.get("completion")})
    return sorted(res, key=lambda x: x["id"] or "")
