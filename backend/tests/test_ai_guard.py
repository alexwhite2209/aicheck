"""AI не может добавлять нормы, суммы и правила (п. 32 ТЗ)."""
import json

import httpx

from app.ai import openrouter


def _result(rule_id="152FZ_POLICY_001", article="18.1"):
    return {"rule_id": rule_id, "title": "t", "status": "FAIL", "confidence_ru": "вероятно", "fact": "f", "evidence": [],
            "basis": [{"label": f"152-ФЗ, ст. {article}, ч. 2", "article": article, "text": "текст нормы"}]}


def test_clean_rejects_foreign_articles_money_and_guarantees():
    allowed = {"18.1"}
    assert openrouter._clean("Согласно ч. 2 ст. 18.1 нужно опубликовать политику.", allowed)
    assert openrouter._clean("Нарушена ст. 21 закона.", allowed) is None
    assert openrouter._clean("Штраф составит 60 000 руб.", allowed) is None
    assert openrouter._clean("Мы гарантируем соответствие.", allowed) is None


def test_explain_filters_unknown_rules(monkeypatch):
    content = json.dumps({"summary": "Итог без сумм.", "items": [
        {"rule_id": "152FZ_POLICY_001", "explanation": "Политика нужна по ст. 18.1.", "recommendation": "Опубликуйте политику."},
        {"rule_id": "FAKE_RULE", "explanation": "x", "recommendation": "y"},
        {"rule_id": "152FZ_POLICY_001_X", "explanation": "x", "recommendation": "y"},
    ]})

    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": content}}]}

    class Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k): return Resp()

    monkeypatch.setattr(httpx, "Client", Client)
    monkeypatch.setattr(openrouter.get_settings(), "openrouter_api_key", "test-key")
    out = openrouter.explain({"pages": []}, [_result()], {"enabled": True, "model": "m"})
    assert out["used"] and set(out["items"]) == {"152FZ_POLICY_001"}
    assert out["summary"] == "Итог без сумм."
