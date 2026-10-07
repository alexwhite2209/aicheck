import json
from pathlib import Path

from app.legal import finance, score

SANCTIONS = json.loads((Path(__file__).parent.parent / "app" / "legal" / "data" / "rules.json").read_text(encoding="utf-8"))["sanctions"]


def test_policy_fine_verified_for_legal_entity():
    r = finance.assess("152FZ_POLICY_001", "FAIL", {"group": "KOAP:13.11:3:", "kind": "direct"}, SANCTIONS, "legal", "ред. 2026")
    assert r["state"] == finance.VERIFIED and (r["min_value"], r["max_value"]) == (30000, 60000)


def test_ip_uses_official_range_when_not_specified():
    r = finance.assess("X", "FAIL", {"group": "KOAP:13.11:1:", "kind": "estimated"}, SANCTIONS, "ip", "")
    assert (r["min_value"], r["max_value"]) == (50000, 100000) and r["state"] == finance.ESTIMATED


def test_unknown_subject_is_estimated_wide_range():
    r = finance.assess("X", "FAIL", {"group": "KOAP:13.11:3:", "kind": "direct"}, SANCTIONS, "unknown", "")
    assert r["state"] == finance.ESTIMATED and (r["min_value"], r["max_value"]) == (10000, 60000)


def test_warning_sanction_min_zero():
    r = finance.assess("ECOM_SELLER_INFO_001", "FAIL", {"group": "KOAP:14.8:1:", "kind": "direct"}, SANCTIONS, "legal", "")
    assert r["min_value"] == 0 and r["max_value"] == 10000


def test_no_double_count_and_review_goes_to_potential():
    items = [
        finance.assess("A", "FAIL", {"group": "KOAP:13.11:3:", "kind": "direct"}, SANCTIONS, "legal", ""),
        finance.assess("B", "FAIL", {"group": "KOAP:13.11:3:", "kind": "estimated"}, SANCTIONS, "legal", ""),
        finance.assess("C", "REVIEW", {"group": "KOAP:13.11:8:", "kind": "estimated"}, SANCTIONS, "legal", ""),
    ]
    agg = finance.aggregate(items)
    assert (agg["min"], agg["max"]) == (30000, 60000)
    assert agg["potential"]["min"] == 1_000_000
    assert agg["state"] == finance.VERIFIED


def test_pass_has_no_money():
    r = finance.assess("A", "PASS", {"group": "KOAP:13.11:3:", "kind": "direct"}, SANCTIONS, "legal", "")
    assert r["state"] == finance.NOT_DETERMINABLE and "min_value" not in r


def test_score_ignores_unknown():
    res = [{"status": "PASS", "severity": "high"}, {"status": "FAIL", "severity": "high"}, {"status": "UNKNOWN", "severity": "critical"},
           {"status": "REVIEW", "severity": "medium"}, {"status": "NA", "severity": "high"}, {"status": "REVIEW", "severity": "info"}]
    # (6*1 + 6*0 + 3*0.5) / (6+6+3) = 7.5/15 = 50
    assert score.compute(res) == 50
    assert score.compute([{"status": "UNKNOWN", "severity": "high"}]) is None
    c = score.counts(res)
    assert c["pass"] == 1 and c["fail"] == 1 and c["unknown"] == 1 and c["review"] == 2
