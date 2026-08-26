"""
test_pipeline.py — zero-trust tests. Bad JSON must be stopped at the gate,
not allowed to flow into the calculation layer.

Run:  python3 -m pytest src/ -q      (from the repo root)
"""

import json
from pathlib import Path

from pipeline import run_pipeline, validate_extraction

# Located relative to this file, not to cwd, so the tests run from anywhere
HERE = Path(__file__).resolve().parent


def _good() -> dict:
    with open(HERE / "extraction_case01.json") as f:
        return json.load(f)


def test_good_extraction_passes_and_calculates():
    case, v = run_pipeline(_good())
    assert v.ok
    assert case is not None
    assert case.day_supply == 42
    assert case.drugs[0].jcode_units == 336
    assert case.drugs[1].jcode_units == 14070


def test_missing_source_quote_is_hard_error():
    """No source quote means the grounding rule was broken: hard error, halt."""
    data = _good()
    del data["drugs"][0]["source_quote"]
    case, v = run_pipeline(data)
    assert case is None
    assert any("grounding" in e for e in v.errors)


def test_missing_start_date_halts_pipeline():
    data = _good()
    data["therapy_dates"]["start"] = None
    case, v = run_pipeline(data)
    assert case is None
    assert any("start date" in e for e in v.errors)


def test_bad_frequency_is_hard_error():
    """The LLM invented a frequency outside the whitelist: stop, never guess."""
    data = _good()
    data["drugs"][0]["frequency"] = "twice-ish daily"
    case, v = run_pipeline(data)
    assert case is None
    assert any("not in allowed set" in e for e in v.errors)


def test_null_frequency_is_warning_not_crash():
    """An un-normalisable frequency: null is legitimate, but it must warn."""
    data = _good()
    data["drugs"][0]["frequency"] = None
    v = validate_extraction(data)
    assert v.ok  # honest null, so not a hard error
    assert any("frequency could not be normalized" in w for w in v.warnings)


def test_missing_vial_size_is_warning():
    data = _good()
    v = validate_extraction(data)  # cefepime vial_size is null in this fixture
    assert v.ok
    assert any("vial size not documented" in w for w in v.warnings)
