"""Финансовая методика (LEGAL_DATABASE.md, раздел 2.4)."""
VERIFIED, ESTIMATED, NOT_DETERMINABLE = "VERIFIED_RANGE", "ESTIMATED_RANGE", "NOT_DETERMINABLE"
SUBJECT_RU = {"legal": "юридическое лицо", "ip": "индивидуальный предприниматель", "unknown": "тип субъекта не определён"}


def koap_label(group: str) -> str:
    """KOAP:13.11:3: → «ч. 3 ст. 13.11 КоАП РФ»."""
    _, art, part, *_ = (group + "::").split(":")
    return f"ч. {part} ст. {art} КоАП РФ" if part else f"ст. {art} КоАП РФ"


def subject_range(sanction: dict, subject: str) -> tuple[int, int] | None:
    official = sanction.get("official")
    ip = sanction.get("ip") or official  # примечание к ст. 2.4 КоАП
    legal = sanction.get("legal")
    if subject == "legal":
        rng = legal
    elif subject == "ip":
        rng = ip
    else:
        cands = [r for r in (ip, legal) if r]
        rng = [min(r[0] for r in cands), max(r[1] for r in cands)] if cands else None
    if not rng:
        return None
    lo, hi = rng
    if sanction.get("warning"):
        lo = 0
    return int(lo), int(hi)


def assess(rule_id: str, status: str, finance: dict | None, sanctions: dict, subject: str, koap_date: str) -> dict:
    """Денежная оценка по одному результату правила."""
    if not finance or status not in ("FAIL", "REVIEW"):
        return {"state": NOT_DETERMINABLE, "rule_id": rule_id, "reason": "Специальная санкция не определена или требование выполнено"}
    group = finance["group"]
    sanction = sanctions.get(group)
    rng = subject_range(sanction, subject) if sanction else None
    if not rng:
        return {"state": NOT_DETERMINABLE, "rule_id": rule_id, "legal_basis": group, "reason": "Для данного типа субъекта санкция не установлена"}
    verified = status == "FAIL" and finance.get("kind") == "direct" and subject in ("legal", "ip")
    method = (f"Диапазон штрафа по {koap_label(group)} "
              f"для субъекта: {SUBJECT_RU[subject]}"
              + (" (определён по реквизитам на сайте)" if subject != "unknown" else " — взят диапазон от ИП до юридического лица")
              + ("; санкция допускает предупреждение, поэтому минимум — 0 ₽" if sanction.get("warning") else "")
              + ("" if finance.get("kind") == "direct" else "; квалификация по этой части КоАП не однозначна"))
    return {
        "state": VERIFIED if verified else ESTIMATED,
        "rule_id": rule_id, "legal_basis": group, "calculation_method": method,
        "min_value": rng[0], "max_value": rng[1], "date": koap_date, "bucket": "main" if status == "FAIL" else "potential",
    }


def aggregate(items: list[dict]) -> dict:
    """Сумма без двойного счёта: одна часть статьи КоАП — один раз (берётся наибольший диапазон)."""
    def collapse(bucket: str, exclude: set[str]) -> dict[str, dict]:
        groups: dict[str, dict] = {}
        for it in items:
            if it.get("bucket") != bucket or it["legal_basis"] in exclude:
                continue
            g = groups.get(it["legal_basis"])
            if not g or it["max_value"] > g["max_value"]:
                groups[it["legal_basis"]] = it
        return groups

    main = collapse("main", set())
    potential = collapse("potential", set(main))
    main_items = list(main.values())
    pot_items = list(potential.values())
    if main_items:
        state = VERIFIED if all(i["state"] == VERIFIED for i in main_items) else ESTIMATED
    else:
        state = NOT_DETERMINABLE
    return {
        "state": state,
        "min": sum(i["min_value"] for i in main_items), "max": sum(i["max_value"] for i in main_items),
        "items": main_items,
        "potential": {"min": sum(i["min_value"] for i in pot_items), "max": sum(i["max_value"] for i in pot_items), "items": pot_items},
        "currency": "RUB",
        "note": "Оценочный диапазон потенциальных финансовых последствий выявленных рисков. Это не гарантированный штраф: "
                "штраф назначает уполномоченный орган с учётом обстоятельств дела.",
    }
