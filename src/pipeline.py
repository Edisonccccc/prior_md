"""
pipeline.py — wires the layers together:

    LLM extraction (JSON) -> [this file: validate + convert]
                          -> pa_calc (pure maths) -> one-liner + flags

The model is pluggable by construction: this file calls no API. It receives
JSON that some LLM already produced, distrusts it, validates it, and only then
hands it to the deterministic layer. Going live means writing one function,
call_llm(prompt, referral_text) -> str. Nothing else here changes.

Run:  python3 pipeline.py <extraction.json>
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import date

from pa_calc import (
    CaseCalc,
    DrugOrder,
    calculate_case,
    format_one_liner,
    screen_service_codes,
    submission_type_for_payer,
)

VALID_FREQUENCIES = {"q6h", "q8h", "q12h", "q24h", "daily", "weekly", "q48h"}


@dataclass
class ValidationResult:
    """The verdict: either the pipeline may continue, or a person must look."""
    ok: bool
    errors: list[str] = field(default_factory=list)      # hard: the pipeline halts
    warnings: list[str] = field(default_factory=list)    # soft: continue, but show the specialist


# ---------------------------------------------------------------------------
# 1. Validation — zero trust. Everything the LLM said goes through the gate.
#    A fabricated value halts the pipeline; an honest "I don't know" passes
#    with a warning. That distinction is the whole design.
# ---------------------------------------------------------------------------

def validate_extraction(data: dict) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    # --- dates ---
    dates = data.get("therapy_dates") or {}
    if not dates.get("start"):
        errors.append("No therapy start date extracted — cannot calculate day supply.")
    if not dates.get("end") and not dates.get("ordered_day_supply"):
        errors.append("Neither end date nor ordered day supply extracted.")
    if not dates.get("source_quote"):
        errors.append("therapy_dates has no source_quote — grounding rule violated.")

    # --- drugs ---
    drugs = data.get("drugs") or []
    if not drugs:
        errors.append("No drugs extracted from referral.")
    for i, d in enumerate(drugs):
        name = d.get("drug_name") or f"drug[{i}]"
        if not d.get("source_quote"):
            errors.append(f"{name}: no source_quote — grounding rule violated.")
        if not d.get("dose_mg") or d["dose_mg"] <= 0:
            errors.append(f"{name}: missing or invalid dose_mg.")
        freq = d.get("frequency")
        if freq is None:
            warnings.append(
                f"{name}: frequency could not be normalized "
                f"(raw: '{d.get('frequency_raw')}') — specialist must confirm."
            )
        elif freq not in VALID_FREQUENCIES:
            errors.append(f"{name}: frequency '{freq}' not in allowed set {sorted(VALID_FREQUENCIES)}.")
        if d.get("vial_size_mg") is None:
            warnings.append(f"{name}: vial size not documented — confirm before quantity math is final.")

    # --- missing_or_unclear passes straight through to the specialist ---
    for note in data.get("missing_or_unclear") or []:
        warnings.append(f"Extractor flagged: {note}")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


# ---------------------------------------------------------------------------
# 2. Convert and calculate
# ---------------------------------------------------------------------------

def run_pipeline(data: dict) -> tuple[CaseCalc | None, ValidationResult]:
    """validate -> DrugOrder -> calculate_case. No calculation if validation fails."""
    v = validate_extraction(data)
    if not v.ok:
        return None, v

    dates = data["therapy_dates"]
    start = date.fromisoformat(dates["start"])
    end = date.fromisoformat(dates["end"])

    orders = []
    for d in data["drugs"]:
        vial = d.get("vial_size_mg")
        orders.append(DrugOrder(
            drug_name=d["drug_name"],
            dose_mg=float(d["dose_mg"]),
            # No vial size stated: stand in the dose itself (1 vial per dose).
            # The warning was already raised during validation.
            vial_size_mg=float(vial) if vial else float(d["dose_mg"]),
            frequency=d["frequency"],
        ))

    case = calculate_case(start, end, orders,
                          ordered_day_supply=dates.get("ordered_day_supply"))
    return case, v


# ---------------------------------------------------------------------------
# 3. The case worksheet the specialist reads
# ---------------------------------------------------------------------------

def render_worksheet(data: dict, case: CaseCalc, v: ValidationResult,
                     icd_codes: list[str] | None = None,
                     service_codes: list[tuple[str, int]] | None = None) -> str:
    """Every number here came from code. ICD codes are left blank for the
    judgment layer (not built) or the specialist to fill in.

    service_codes are whatever the specialist supplied. They are screened
    against the submission type (nursing and per-diem codes belong on the
    medical-benefit authorization, not on a medication-only Part D / CMM one)
    and anything withheld is reported as a flag, never dropped quietly.
    """
    lines = ["=" * 60, "PA CASE WORKSHEET (auto-generated)", "=" * 60]

    payer = (data.get("insurance") or {}).get("payer_type", "unknown")
    submission_type = submission_type_for_payer(payer)
    kept_codes, code_flags = screen_service_codes(service_codes or [], submission_type)
    lines.append(f"Payer type: {payer}  (submission: {submission_type.value})")
    lines.append(f"Dates: {case.start:%m/%d/%Y} to {case.end:%m/%d/%Y} ({case.day_supply} day supply)")
    lines.append("")

    for d in case.drugs:
        # Day supply and dose count are two different numbers; print both.
        # doses_per_day is None for sparse schedules (q48h, weekly) and for
        # multi-phase orders — there is no daily rate to invent. (SME Q8)
        rate = f"{d.doses_per_day}/day, " if d.doses_per_day else ""
        lines.append(f"  {d.drug_name} {d.dose_display} {d.frequency}: "
                     f"{rate}{d.total_doses} doses over a {case.day_supply}-day supply, "
                     f"{d.total_vials} vials, {d.jcode or '??'} x{d.jcode_units or '??'}")
    lines.append("")

    all_flags = (v.warnings + case.flags
                 + [f for d in case.drugs for f in d.flags]
                 + code_flags)
    if all_flags:
        lines.append("FLAGS FOR SPECIALIST REVIEW:")
        for f in all_flags:
            lines.append(f"  ⚠ {f}")
        lines.append("")

    dx = data.get("clinical", {}).get("documented_diagnoses", [])
    lines.append(f"Documented diagnoses (plain language): {'; '.join(dx) if dx else 'NONE EXTRACTED'}")

    if icd_codes:
        lines.append("")
        lines.append("DRAFT ONE-LINER (pending specialist approval):")
        lines.append(format_one_liner(case, icd_codes, kept_codes,
                                      submission_type=submission_type))
    else:
        lines.append("ICD codes: [awaiting coding-judgment step / specialist]")

    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "extraction.json"
    with open(path) as f:
        data = json.load(f)

    case, v = run_pipeline(data)
    if case is None:
        print("PIPELINE HALTED — extraction failed validation:")
        for e in v.errors:
            print(f"  ✗ {e}")
        sys.exit(1)

    print(render_worksheet(data, case, v))
