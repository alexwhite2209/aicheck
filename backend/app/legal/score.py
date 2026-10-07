"""Russian Website Compliance Score (LEGAL_DATABASE.md, раздел 2.5)."""
WEIGHTS = {"critical": 10, "high": 6, "medium": 3, "low": 1, "info": 0}
VALUE = {"PASS": 1.0, "REVIEW": 0.5, "FAIL": 0.0}
DISCLAIMER = ("Score отражает только результаты автоматических проверок сервиса и не является официальной оценкой "
              "соответствия законодательству РФ.")


def compute(results: list[dict]) -> int | None:
    num = den = 0.0
    for r in results:
        if r["status"] not in VALUE:
            continue
        w = WEIGHTS.get(r["severity"], 0)
        num += w * VALUE[r["status"]]
        den += w
    if den == 0:
        return None
    return round(100 * num / den)


def counts(results: list[dict]) -> dict:
    c = {"fail": 0, "review": 0, "pass": 0, "unknown": 0, "na": 0}
    key = {"FAIL": "fail", "REVIEW": "review", "PASS": "pass", "UNKNOWN": "unknown", "NA": "na"}
    for r in results:
        c[key[r["status"]]] += 1
    c["by_severity"] = {s: sum(1 for r in results if r["status"] == "FAIL" and r["severity"] == s) for s in WEIGHTS}
    return c
