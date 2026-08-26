"""
run_evals.py — the PriorMD scorer.

Usage:
    python3 run_evals.py                # every case
    python3 run_evals.py case-001       # just one

Each case is scored on five dimensions: extraction / calc / coding / format /
safety.

Where the extraction comes from:
    - extraction_cached.json present -> use the cache (offline, free, repeatable)
    - absent -> SKIP the extraction dimension and score the rest from the
      fields in expected.json
Once a real model API is wired in, swap the live call into get_extraction().
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

# Let evals/ import the code next door in src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pa_calc import DrugOrder, calculate_case, format_one_liner  # noqa: E402
from pipeline import run_pipeline  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent / "cases"

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def norm(s: str) -> str:
    """Normalise whitespace, for the verbatim one-liner comparison."""
    return " ".join(s.split())


# ---------------------------------------------------------------------------
# One scorer per dimension. Each returns (passed?, [reasons it failed])
# ---------------------------------------------------------------------------

def score_extraction(cached: dict | None, expected: dict) -> tuple[bool | None, list[str]]:
    """Compare the key extracted fields. No cache -> return None, meaning SKIP."""
    exp = expected.get("extraction_expected")
    if cached is None or exp is None:
        return None, []
    fails = []

    got_dates = cached.get("therapy_dates") or {}
    for k in ("start", "end"):
        if k in exp.get("therapy_dates", {}) and got_dates.get(k) != exp["therapy_dates"][k]:
            fails.append(f"therapy_dates.{k}: got {got_dates.get(k)!r}, want {exp['therapy_dates'][k]!r}")

    exp_drugs = {d["drug_name"].lower(): d for d in exp.get("drugs", [])}
    got_drugs = {(d.get("drug_name") or "").lower(): d for d in cached.get("drugs", [])}
    for name, ed in exp_drugs.items():
        gd = got_drugs.get(name)
        if gd is None:
            fails.append(f"drug '{name}' not extracted")
            continue
        for k in ("dose_mg", "frequency"):
            if k in ed and gd.get(k) != ed[k]:
                fails.append(f"{name}.{k}: got {gd.get(k)!r}, want {ed[k]!r}")
        if not gd.get("source_quote"):
            fails.append(f"{name}: missing source_quote")
    return not fails, fails


def build_case(expected: dict):
    """Build the calculation input from expected.json, for calc and format."""
    cd = expected["calc"]
    orders = [
        DrugOrder(d["drug_name"], d["dose_mg"], d.get("vial_size_mg") or d["dose_mg"], d["frequency"])
        for d in cd["drugs"]
    ]
    return calculate_case(date.fromisoformat(cd["start"]), date.fromisoformat(cd["end"]), orders)


def score_calc(expected: dict) -> tuple[bool, list[str]]:
    """The calculated numbers must equal the specialist's exactly."""
    fails = []
    case = build_case(expected)
    cd = expected["calc"]
    if case.day_supply != cd["day_supply"]:
        fails.append(f"day_supply: got {case.day_supply}, want {cd['day_supply']}")
    for want, got in zip(cd["drugs"], case.drugs):
        for k, gv in (("total_vials", got.total_vials), ("jcode", got.jcode), ("jcode_units", got.jcode_units)):
            if k in want and gv != want[k]:
                fails.append(f"{want['drug_name']}.{k}: got {gv!r}, want {want[k]!r}")
    return not fails, fails


def score_coding(cached: dict | None, expected: dict) -> tuple[bool | None, list[str]]:
    """
    Layer 4 does not exist yet, so what this currently asserts is that the
    EXTRACTOR stays out of coding — it must not emit ICD codes at all.

    That is the right test while the judgment layer is absent and the wrong one
    the moment it exists. Once it is built, this compares the codes the layer
    chose against expected['icd_codes']. Tracked as T-coding-dimension.
    """
    if cached is None:
        return None, []
    fails = []
    text = json.dumps(cached)
    # documented_diagnoses must stay natural language — no smuggled ICD codes
    import re
    icd_pattern = re.compile(r"\b[A-TV-Z]\d{2}\.?\w{0,4}\b")
    for dx in (cached.get("clinical") or {}).get("documented_diagnoses", []):
        if icd_pattern.search(dx):
            fails.append(f"extractor emitted ICD-like code in diagnoses: {dx!r} (not its job)")
    return not fails, fails


def score_format(expected: dict) -> tuple[bool, list[str]]:
    """The one-liner, verbatim (whitespace normalised), against her submission."""
    case = build_case(expected)
    ours = format_one_liner(case, expected["icd_codes"],
                            service_codes=[tuple(sc) for sc in expected.get("service_codes", [])] or None)
    if norm(ours) == norm(expected["one_liner"]):
        return True, []
    return False, [f"one-liner mismatch:\n      ours: {norm(ours)}\n      want: {norm(expected['one_liner'])}"]


def score_safety(cached: dict | None, expected: dict) -> tuple[bool, list[str]]:
    """Every required flag present, nothing forbidden anywhere."""
    fails = []
    case = build_case(expected)
    all_flags = case.flags + [f for d in case.drugs for f in d.flags]
    if cached is not None:
        _, v = run_pipeline(cached)
        all_flags += v.warnings + v.errors
    flag_text = " | ".join(all_flags)

    for needed in expected.get("required_flags", []):
        if needed.lower() not in flag_text.lower():
            fails.append(f"required flag missing: {needed!r}")

    # `forbidden` is checked ONLY against what would be submitted to the payer
    # (the one-liner). The warning flags may mention these words freely — an
    # honest "osteomyelitis is not documented" is GOOD behaviour, and an earlier
    # version of this scorer failed cases for it.
    output_text = format_one_liner(case, expected["icd_codes"])
    for banned in expected.get("forbidden_in_output", []):
        if banned.lower() in output_text.lower():
            fails.append(f"forbidden content present: {banned!r}")
    return not fails, fails


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_case(case_dir: Path) -> dict:
    expected = json.loads((case_dir / "expected.json").read_text())
    cached_path = case_dir / "extraction_cached.json"
    cached = json.loads(cached_path.read_text()) if cached_path.exists() else None

    results = {
        "extraction": score_extraction(cached, expected),
        "calc":       score_calc(expected),
        "coding":     score_coding(cached, expected),
        "format":     score_format(expected),
        "safety":     score_safety(cached, expected),
    }
    return {"name": case_dir.name, "results": results}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    case_dirs = sorted(d for d in CASES_DIR.iterdir() if d.is_dir())
    if only:
        case_dirs = [d for d in case_dirs if only in d.name]
    if not case_dirs:
        print("No cases found.")
        sys.exit(1)

    total_pass = total_fail = total_skip = 0
    for cd in case_dirs:
        r = run_case(cd)
        print(f"\n📁 {r['name']}")
        for dim, (ok, fails) in r["results"].items():
            if ok is None:
                print(f"   {YELLOW}SKIP{RESET}  {dim} (no cached extraction)")
                total_skip += 1
            elif ok:
                print(f"   {GREEN}PASS{RESET}  {dim}")
                total_pass += 1
            else:
                print(f"   {RED}FAIL{RESET}  {dim}")
                for f in fails:
                    print(f"          - {f}")
                total_fail += 1

    print(f"\n{'=' * 50}")
    print(f"TOTAL: {GREEN}{total_pass} pass{RESET}, {RED}{total_fail} fail{RESET}, {YELLOW}{total_skip} skip{RESET}")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
