"""Unit-тесты для каждого правила (п. 46 ТЗ). Наборы — в app/legal/fixtures.py."""
import json
from pathlib import Path

import pytest

from app.legal.fixtures import CASES
from app.legal.rules import REGISTRY

RULES_JSON = json.loads((Path(__file__).parent.parent / "app" / "legal" / "data" / "rules.json").read_text(encoding="utf-8"))
NORMS_JSON = json.loads((Path(__file__).parent.parent / "app" / "legal" / "data" / "norms.json").read_text(encoding="utf-8"))
ALL_CASES = [(rid, name, facts, exp) for rid, cases in CASES.items() for name, facts, exp in cases]


@pytest.mark.parametrize("rule_id,name,facts,expected", ALL_CASES, ids=[f"{c[0]}::{c[1]}" for c in ALL_CASES])
def test_rule_case(rule_id, name, facts, expected):
    out = REGISTRY[rule_id](facts)
    assert out.status == expected, f"{rule_id} / {name}: {out.status} — {out.fact}"
    assert out.confidence in ("confirmed", "probable", "manual", "undetermined")
    assert out.fact


def test_every_rule_has_tests_and_implementation():
    ids = {r["id"] for r in RULES_JSON["rules"]}
    assert ids == set(REGISTRY), "правила в rules.json и реализации должны совпадать"
    assert ids <= set(CASES), f"нет тестов: {ids - set(CASES)}"


def test_every_basis_exists_in_official_norms():
    keys = {n["id"] for n in NORMS_JSON["articles"]}
    for r in RULES_JSON["rules"]:
        for b in r["basis"]:
            assert b in keys, f"{r['id']}: норма {b} отсутствует в norms.json"
        if r.get("finance"):
            assert r["finance"]["group"] in keys and r["finance"]["group"] in RULES_JSON["sanctions"]


def test_norms_have_official_source_and_text():
    for n in NORMS_JSON["articles"]:
        assert n["official_source"].startswith("http://pravo.gov.ru/"), n["id"]
        assert len(n["text"]) > 40 and n["edition"] and n["checked_at"], n["id"]


def test_unknown_is_never_fail_for_localization():
    from app.legal.fixtures import base_facts, form
    out = REGISTRY["152FZ_LOCALIZATION_005"](base_facts(forms=[form()]))
    assert out.status == "UNKNOWN"
    assert "невозможно достоверно определить" in out.fact
