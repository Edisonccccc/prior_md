"""
test_pa_calc.py — every case below comes straight out of the SME's document
or her interview answers. This is where the eval mindset starts: one of her
examples becomes one permanent regression test.

Run:  python3 -m pytest src/ -q      (from the repo root)
"""

import math
from datetime import date, timedelta

from pa_calc import (
    DrugOrder,
    Phase,
    Regimen,
    calculate_regimen_case,
    calculate_case,
    day_supply,
    end_date_for_supply,
    format_one_liner,
    screen_service_codes,
    submission_type_for_payer,
    SubmissionType,
    format_strength,
    doses_per_day,
    schedule,
)

# ---------------------------------------------------------------------------
# Rule 4 — the document's four date examples, one test each
# ---------------------------------------------------------------------------

def test_rule4_21_days():
    assert end_date_for_supply(date(2026, 7, 7), 21) == date(2026, 7, 27)
    assert day_supply(date(2026, 7, 7), date(2026, 7, 27)) == 21

def test_rule4_28_days():
    assert end_date_for_supply(date(2026, 7, 7), 28) == date(2026, 8, 3)

def test_rule4_30_days():
    assert end_date_for_supply(date(2026, 7, 8), 30) == date(2026, 8, 6)

def test_rule4_365_days():
    assert end_date_for_supply(date(2026, 7, 8), 365) == date(2027, 7, 7)

def test_rule4_mismatch_is_flagged():
    """The order says 21 days, the dates say 22. That must be flagged."""
    case = calculate_case(date(2026, 7, 7), date(2026, 7, 28), [], ordered_day_supply=21)
    assert any("21-day supply" in f and "22 days" in f for f in case.flags)

# ---------------------------------------------------------------------------
# Rule 3 — strength formatting: no space before the unit
# ---------------------------------------------------------------------------

def test_rule3_strength_formatting():
    assert format_strength(2000) == "2g"
    assert format_strength(500) == "500mg"
    assert format_strength(335) == "335mg"
    assert format_strength(1000) == "1g"

# ---------------------------------------------------------------------------
# The worked case from Part 2 — cefepime + daptomycin, 07/24 to 09/03.
# The specialist's own answer: 42 days, 84 vials J0692 x336, 42 vials J0878 x14070.
# ---------------------------------------------------------------------------

def _worked_case():
    return calculate_case(
        start=date(2026, 7, 24),
        end=date(2026, 9, 3),
        orders=[
            DrugOrder("Cefepime",   dose_mg=2000, vial_size_mg=2000, frequency="q12h"),
            DrugOrder("Daptomycin", dose_mg=335,  vial_size_mg=500,  frequency="q24h"),
        ],
    )

def test_worked_case_day_supply():
    assert _worked_case().day_supply == 42

def test_worked_case_cefepime():
    cef = _worked_case().drugs[0]
    assert cef.total_vials == 84
    assert cef.jcode == "J0692"
    assert cef.jcode_units == 336

def test_worked_case_daptomycin():
    dap = _worked_case().drugs[1]
    assert dap.total_vials == 42
    assert dap.jcode == "J0878"
    assert dap.jcode_units == 14070

def test_worked_case_one_liner_matches_expert():
    """The whole one-liner matches her submitted output (whitespace normalised)."""
    expert = (
        "Services Requested: Cefepime 2g vial IV q12h (Dose: 2g, Total Qty: 84 vials) "
        "+ Daptomycin 500mg vial IV q24h (Dose: 335mg, Total Qty: 42 vials) – "
        "J0692 x336, J0878 x14070 for T81.49XA + L08.9 "
        "Dates of Service: 07/24/2026 to 09/03/2026 (42 day supply)."
    )
    ours = format_one_liner(_worked_case(), icd_codes=["T81.49XA", "L08.9"])
    assert " ".join(ours.split()) == " ".join(expert.split())

def test_worked_case_daptomycin_waste_flagged():
    """A 335mg dose from a 500mg vial discards 165mg each time. Flag it."""
    dap = _worked_case().drugs[1]
    assert any("165mg" in f for f in dap.flags)

# ---------------------------------------------------------------------------
# The document's aztreonam example — 2g q8h, 07/07 to 08/03 (28 days).
# Its stated answer: 84 vials, J0834 x336.
# ---------------------------------------------------------------------------

def test_aztreonam_example():
    case = calculate_case(
        start=date(2026, 7, 7),
        end=date(2026, 8, 3),
        orders=[DrugOrder("Aztreonam", dose_mg=2000, vial_size_mg=2000, frequency="q8h")],
    )
    azt = case.drugs[0]
    assert case.day_supply == 28
    assert azt.total_vials == 84          # 3 doses/day x 28 days
    assert azt.jcode_units == 336         # 4 units/dose x 84 doses

# ---------------------------------------------------------------------------
# Nursing codes (99601/99602) and per-diem codes (S9500-S9502) — SCOPED to the
# benefit, not banned. SME, 2026-10-13, narrowing her own 2026-08-03 ruling:
#   "when I previously said nursing codes and per diem codes should not be
#    included, I was talking about medication only Part D or CMM submissions.
#    I do not want those codes removed from the entire system. For home
#    infusion and medical benefit authorizations, those codes absolutely still
#    matter. They just need to be handled in the correct workflow and not
#    thrown into every medication PA."
# What still holds from 2026-08-03: the AI never CALCULATES nursing units.
# The specialist supplies them; this layer only routes them.
# ---------------------------------------------------------------------------

def test_nursing_codes_withheld_from_medication_only():
    """A Part D / CMM submission is medication only — nursing codes stay off it."""
    kept, flags = screen_service_codes(
        [("J0834", 336), ("99601", 4)], SubmissionType.MEDICATION_ONLY)
    assert kept == [("J0834", 336)]
    assert any("99601" in f for f in flags)


def test_nursing_codes_kept_on_medical_benefit():
    """Her 2026-10-13 correction: on home infusion they absolutely still matter."""
    codes = [("J0834", 336), ("S9502", 28), ("99601", 4), ("99602", 8)]
    kept, flags = screen_service_codes(codes, SubmissionType.MEDICAL_BENEFIT)
    assert kept == codes
    assert flags == []


def test_per_diem_codes_follow_the_same_scope():
    """She named per-diem codes in the same breath as nursing codes."""
    kept, _ = screen_service_codes([("S9500", 21)], SubmissionType.MEDICATION_ONLY)
    assert kept == []
    kept, _ = screen_service_codes([("S9500", 21)], SubmissionType.MEDICAL_BENEFIT)
    assert kept == [("S9500", 21)]


def test_undetermined_benefit_never_guesses():
    """Unknown benefit = flag, not an assumption. Codes are not thrown away."""
    codes = [("99601", 4)]
    kept, flags = screen_service_codes(codes, SubmissionType.UNDETERMINED)
    assert kept == codes
    assert any("not determined" in f.lower() for f in flags)


def test_screen_never_adds_a_code():
    """The screen only filters. It cannot invent a code or a unit count."""
    for st in SubmissionType:
        kept, _ = screen_service_codes([], st)
        assert kept == []


def test_payer_wording_maps_to_submission_type():
    assert submission_type_for_payer("Part D") is SubmissionType.MEDICATION_ONLY
    assert submission_type_for_payer("CMM") is SubmissionType.MEDICATION_ONLY
    assert submission_type_for_payer("Part B") is SubmissionType.MEDICAL_BENEFIT
    assert submission_type_for_payer("home infusion") is SubmissionType.MEDICAL_BENEFIT
    # Anything unrecognised is undetermined on purpose — never a default guess.
    assert submission_type_for_payer("Aetna PPO") is SubmissionType.UNDETERMINED
    assert submission_type_for_payer(None) is SubmissionType.UNDETERMINED


def test_one_liner_withholds_nursing_on_part_d():
    """End to end through the formatter, which is what a Part D case prints."""
    case = _worked_case()
    ours = format_one_liner(case, icd_codes=["T81.49XA", "L08.9"],
                            service_codes=[("99601", 4)],
                            submission_type=SubmissionType.MEDICATION_ONLY)
    assert "99601" not in ours


def test_one_liner_keeps_nursing_on_medical_benefit():
    case = _worked_case()
    ours = format_one_liner(case, icd_codes=["T81.49XA", "L08.9"],
                            service_codes=[("S9502", 42), ("99601", 4)],
                            submission_type=SubmissionType.MEDICAL_BENEFIT)
    assert "99601 x4" in ours and "S9502 x42" in ours


def test_ai_still_never_calculates_nursing_units():
    """The half of the 2026-08-03 ruling she did NOT retract: no nursing math.
    With nothing supplied by the specialist, nothing appears."""
    case = _worked_case()
    for st in SubmissionType:
        ours = format_one_liner(case, icd_codes=["T81.49XA", "L08.9"],
                                submission_type=st)
        assert "99601" not in ours and "99602" not in ours


# ---------------------------------------------------------------------------
# Rule 8 — an unrecognised drug never gets a guessed J-code
# ---------------------------------------------------------------------------

def test_unknown_drug_never_guesses():
    case = calculate_case(
        start=date(2026, 7, 7),
        end=date(2026, 7, 27),
        orders=[DrugOrder("Micafungin", dose_mg=100, vial_size_mg=100, frequency="q24h")],
    )
    mica = case.drugs[0]
    assert mica.jcode is None
    assert any("do not guess" in f for f in mica.flags)


# ===========================================================================
# SME Q7 (2026-08-11) — single-dose-vial rounding
#
#   "round up to the number of whole SDVs needed for each individual dose
#    first, then multiply by the total number of doses. Do not calculate the
#    entire course in milligrams and divide by the vial strength at the end."
#
# This whole block is T-sdv-regression. The schedule refactor could quietly
# break exactly this, which is why it was locked down first. Her own
# counter-example sits below: 42 is wrong, 60 is right. Deleting these tests
# deletes the rule.
# ===========================================================================

def _one_drug(dose_mg, vial_mg, freq, days, name="Daptomycin"):
    start = date(2026, 8, 1)
    case = calculate_case(
        start=start,
        end=start + timedelta(days=days - 1),
        orders=[DrugOrder(name, dose_mg=dose_mg, vial_size_mg=vial_mg, frequency=freq)],
    )
    return case, case.drugs[0]


def test_q7_sme_worked_example_700mg_is_60_vials_not_42():
    """Her example verbatim: 700mg q24h for 30 days, 500mg single-dose vials."""
    case, d = _one_drug(700, 500, "q24h", 30)
    assert case.day_supply == 30
    assert d.total_doses == 30
    assert d.total_vials == 60, "ceil(700/500)=2 vials per dose x 30 doses"


def test_q7_the_wrong_way_must_not_be_what_we_compute():
    """
    The wrong way: 21,000mg / 500mg = 42 vials. That assumes the 300mg left
    over from one dose can be carried to the next. Single-dose vials cannot.
    """
    _, d = _one_drug(700, 500, "q24h", 30)
    total_mg = 700 * 30
    wrong = math.ceil(total_mg / 500)
    assert wrong == 42
    assert d.total_vials != wrong


def test_q7_weight_based_dose_rounds_up_the_same_way():
    """780mg is still 2 whole vials, never 1.56."""
    _, d = _one_drug(780, 500, "q24h", 14)
    assert d.total_vials == 2 * 14


def test_q7_exact_multiple_wastes_nothing():
    _, d = _one_drug(1000, 500, "q24h", 10)
    assert d.total_vials == 2 * 10
    assert not any("discarded" in f for f in d.flags)


def test_q7_partial_vial_flags_the_wastage():
    _, d = _one_drug(700, 500, "q24h", 30)
    assert any("discarded" in f for f in d.flags), "300mg discarded per dose should be flagged"


def test_q7_vials_and_jcode_units_are_computed_independently():
    """
    "One vial does not necessarily equal one J-code unit, so those
     calculations should always be performed independently."
    Cefepime 2g: one dose is 1 vial, but 4 J0692 units.
    """
    _, d = _one_drug(2000, 2000, "q12h", 42, name="Cefepime")
    assert d.total_doses == 84
    assert d.total_vials == 84          # 1 vial per dose
    assert d.jcode == "J0692"
    assert d.jcode_units == 336         # 4 units per dose
    assert d.total_vials != d.jcode_units


def test_q7_no_multi_dose_vial_carryover_across_doses():
    """
    Across three different durations, vials must equal vials-per-dose x doses
    exactly. Any carry-over at all breaks this identity.
    """
    for days in (1, 7, 31):
        _, d = _one_drug(600, 500, "q24h", days)
        assert d.total_vials == 2 * days


# ===========================================================================
# SME Q8 (2026-08-11) — unusual frequencies: four shapes, four of her examples
#
#   "never estimate unusual frequencies using a generic daily multiplier.
#    Build the administration schedule from the SOC date forward, count each
#    actual dose that falls within the treatment period."
#
# This block is T-unusual-schedules. Every number below is quoted from her answer.
# ===========================================================================

SOC = date(2026, 8, 1)


def test_q8_q48h_five_doses_over_a_ten_day_supply():
    """
    "an order starting 08/01 for 10 days at q48h would generally result in
     doses on 08/01, 08/03, 08/05, 08/07, and 08/09 for 5 total doses, while
     the day supply remains 10 days"
    """
    r = Regimen("Daptomycin", 500, [Phase(500, "q48h", days=10)])
    case = calculate_regimen_case(SOC, [r])
    d = case.drugs[0]

    assert d.total_doses == 5
    assert case.day_supply == 10, "day supply is the treatment period, not the last dose date"
    assert [a.day_offset for a in d.administrations] == [0, 2, 4, 6, 8]
    assert [SOC + timedelta(days=o) for o in (0, 2, 4, 6, 8)] == [
        date(2026, 8, 1), date(2026, 8, 3), date(2026, 8, 5),
        date(2026, 8, 7), date(2026, 8, 9),
    ]


def test_q8_weekly_for_six_weeks_is_six_doses():
    """"if a medication is ordered once weekly for 6 weeks, the expected
        quantity is generally 6 doses" — a 42-day course, 6 doses."""
    r = Regimen("Daptomycin", 500, [Phase(500, "weekly", days=42)])
    case = calculate_regimen_case(SOC, [r])
    assert case.drugs[0].total_doses == 6
    assert case.day_supply == 42
    assert case.drugs[0].total_vials == 6


def test_q8_loading_plus_maintenance_is_fourteen_administrations():
    """
    "1,000mg IV once as a loading dose, then 500mg IV every 24 hours for 13
     additional days" → 1 + 13 = 14 total administrations.
    The two phases must also compute vials separately: 1000mg needs 2 vials,
    500mg needs 1.
    """
    r = Regimen("Daptomycin", 500, [
        Phase(1000, "once", days=1),
        Phase(500, "q24h", days=13),
    ])
    case = calculate_regimen_case(SOC, [r])
    d = case.drugs[0]

    assert d.total_doses == 14
    assert case.day_supply == 14
    assert d.total_vials == 2 + 13 * 1, "2 vials for the loading dose, 1 for each of 13 maintenance doses"
    assert d.administrations[0].dose_mg == 1000
    assert all(a.dose_mg == 500 for a in d.administrations[1:])


def test_q8_three_segment_taper_is_thirty_doses_over_fifteen_days():
    """
    "q8h for 5 days, then q12h for 5 days, then q24h for 5 days" →
    15 + 10 + 5 = 30 doses over a 15-day supply.
    """
    r = Regimen("Daptomycin", 500, [
        Phase(500, "q8h",  days=5),
        Phase(500, "q12h", days=5),
        Phase(500, "q24h", days=5),
    ])
    case = calculate_regimen_case(SOC, [r])
    d = case.drugs[0]

    assert d.total_doses == 30
    assert case.day_supply == 15
    assert d.total_doses != case.day_supply, "dose count and day supply need not match"

    per_segment = [
        len([a for a in d.administrations if 0 <= a.day_offset < 5]),
        len([a for a in d.administrations if 5 <= a.day_offset < 10]),
        len([a for a in d.administrations if 10 <= a.day_offset < 15]),
    ]
    assert per_segment == [15, 10, 5], "each segment counts on its own; never average the frequency"


def test_q8_generic_daily_multiplier_is_refused_not_guessed():
    """
    q48h / weekly / once have no doses-per-day. Forcing one out of them is
    precisely what the SME prohibited, so this must raise rather than return 1.
    """
    assert doses_per_day("q8h") == 3
    for freq in ("q48h", "weekly", "once"):
        try:
            doses_per_day(freq)
        except ValueError as e:
            assert "no doses-per-day" in str(e)
        else:
            raise AssertionError(f"doses_per_day({freq!r}) must raise, not invent a number")


def test_q8_unknown_frequency_still_never_guesses():
    try:
        schedule(Regimen("X", 500, [Phase(500, "q36h", days=6)]))
    except ValueError as e:
        assert "do not guess" in str(e)
    else:
        raise AssertionError("an unknown frequency must raise")


# ===========================================================================
# Input guards (2026-08-26)
#
# The calculation layer is the trustworthy half of the system — but the
# zero-trust gate only guards the JSON path. calc_regimen() and
# calculate_regimen_case() are newer entry points that anyone can call directly.
# A zero-vial authorization quantity is a WRONG ANSWER THAT LOOKS LIKE AN
# ANSWER, the same class of failure as inventing a diagnosis code. So these
# refuse impossible input rather than returning a plausible zero.
# ===========================================================================

def _raises(fn, *, contains):
    try:
        fn()
    except (ValueError, ZeroDivisionError) as e:
        assert contains in str(e), f"error should mention {contains!r}, got {e!r}"
    else:
        raise AssertionError(f"expected a raise mentioning {contains!r}, got none")


def test_guard_phase_days_must_be_positive():
    _raises(lambda: Phase(500, "q24h", 0),  contains="days must be >= 1")
    _raises(lambda: Phase(500, "q24h", -3), contains="days must be >= 1")


def test_guard_phase_dose_must_be_positive():
    _raises(lambda: Phase(0, "q24h", 5),    contains="dose_mg must be > 0")
    _raises(lambda: Phase(-100, "q24h", 5), contains="dose_mg must be > 0")


def test_guard_unknown_frequency_fails_at_construction_not_at_use():
    """Fail as early as possible: at construction, not later at scheduling."""
    _raises(lambda: Phase(500, "q36h", 5), contains="do not guess")


def test_guard_regimen_needs_at_least_one_phase():
    _raises(lambda: Regimen("Cefepime", 2000, []), contains="no phases")


def test_guard_vial_size_must_be_positive():
    """This used to be a ZeroDivisionError, thrown far from the actual cause."""
    _raises(lambda: Regimen("Cefepime", 0, [Phase(500, "q24h", 5)]),
            contains="vial_size_mg must be > 0")


def test_unequal_treatment_lengths_are_flagged_not_silently_maxed():
    """
    When two drugs run for different lengths the day supply takes the longest.
    That is a choice, and making it silently would hide the difference.
    """
    case = calculate_regimen_case(date(2026, 8, 1), [
        Regimen("Cefepime",   2000, [Phase(2000, "q12h", 14)]),
        Regimen("Daptomycin",  500, [Phase(500,  "q24h", 42)]),
    ])
    assert case.day_supply == 42
    assert any("different treatment lengths" in f for f in case.flags)


def test_equal_lengths_produce_no_such_flag():
    case = calculate_regimen_case(date(2026, 8, 1), [
        Regimen("Cefepime",   2000, [Phase(2000, "q12h", 42)]),
        Regimen("Daptomycin",  500, [Phase(500,  "q24h", 42)]),
    ])
    assert not any("different treatment lengths" in f for f in case.flags)
