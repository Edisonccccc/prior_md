"""
pa_calc.py — PriorMD's deterministic calculation layer.

The principle, learned the hard way in experiment #1: the LLM reads the chart,
extracts fields and makes judgments; every date, quantity and unit conversion
happens here in plain code, where it is 100% reproducible and testable.

Flow:
    LLM extraction -> Regimen (structured) -> calculate_*_case()
                   -> CaseCalc (every number) -> format_one_liner()
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# 1. Lookup tables — reference facts, from the SME's workflow document, Rule 8.
#    Anything not in a table returns a flag. NEVER a guess. (Rule 8)
# ---------------------------------------------------------------------------

# J-code table: drug name -> (J-code, mg per billable unit)
# e.g. J0692 = cefepime per 500mg, so one 2g dose = 2000/500 = 4 units
JCODE_TABLE: dict[str, tuple[str, float]] = {
    "cefepime":    ("J0692", 500.0),
    "daptomycin":  ("J0878", 1.0),
    "ceftriaxone": ("J0696", 250.0),
    "aztreonam":   ("J0834", 500.0),
    # Add a new drug as one line here. A drug that is absent gets flagged,
    # never invented.
}
# STOPGAP, not the design. SME 2026-10-13: "I do not really want to design this
# around a certain number of medications or build a small drug list into the
# system... I want the AI to be able to research the medication when the case
# comes in" — from CMS, FDA labeling, DailyMed, PrescriberPoint and the
# manufacturer's prescribing information. These four rows cover the eval suite
# and nothing more; do not grow this table as if it were the plan. The open
# question is how retrieved billing data passes the zero-trust gate at all,
# since a J-code read off a web page is testimony, not a calculation. Board Q-08.

# Nursing codes (99601/99602) and per-diem codes (S9500/S9501/S9502) are
# SCOPED TO THE BENEFIT, not banned outright. SME, 2026-10-13, narrowing her
# own 2026-08-03 instruction:
#    "when I previously said nursing codes and per diem codes should not be
#     included, I was talking about medication only Part D or CMM submissions.
#     I do not want those codes removed from the entire system. For home
#     infusion and medical benefit authorizations, those codes absolutely
#     still matter. They just need to be handled in the correct workflow and
#     not thrown into every medication PA."
#
# What survives from 2026-08-03 is the narrower claim she has not retracted:
# the AI never CALCULATES nursing units, because they vary by service dates,
# day supply and provider. The specialist supplies them; this layer decides
# only whether the submission in hand is one they belong on.
#
# See screen_service_codes() below.

class SubmissionType(str, Enum):
    """Which authorization this one-liner is being written for.

    The nursing / per-diem rule depends on it, so the pipeline is not allowed
    to leave it implied. UNDETERMINED is a first-class state rather than a
    default, for the same reason an unrecognised drug is flagged instead of
    guessed: the benefit decides what belongs in the output, so an unknown
    benefit produces a flag, never an assumption.
    """
    MEDICATION_ONLY = "medication_only"   # Part D / CMM coverage determination
    MEDICAL_BENEFIT = "medical_benefit"   # home infusion, Part B / commercial medical
    UNDETERMINED = "undetermined"


NURSING_CODES = frozenset({"99601", "99602"})
PER_DIEM_CODES = frozenset({"S9500", "S9501", "S9502"})

# Codes that belong on a medical-benefit authorization and NOT on a
# medication-only one. Her words: "not thrown into every medication PA."
MEDICAL_BENEFIT_ONLY_CODES = NURSING_CODES | PER_DIEM_CODES

# Payer wording -> which authorization it implies. Anything absent here is
# UNDETERMINED on purpose; the specialist confirms the benefit.
_PAYER_SUBMISSION_TYPE: dict[str, SubmissionType] = {
    "part d": SubmissionType.MEDICATION_ONLY,
    "cmm": SubmissionType.MEDICATION_ONLY,
    "coverage determination": SubmissionType.MEDICATION_ONLY,
    "part b": SubmissionType.MEDICAL_BENEFIT,
    "medical": SubmissionType.MEDICAL_BENEFIT,
    "medical benefit": SubmissionType.MEDICAL_BENEFIT,
    "home infusion": SubmissionType.MEDICAL_BENEFIT,
}


def submission_type_for_payer(payer_type: str | None) -> SubmissionType:
    """Map extracted payer wording onto a submission type, or admit ignorance."""
    if not payer_type:
        return SubmissionType.UNDETERMINED
    return _PAYER_SUBMISSION_TYPE.get(_norm(payer_type), SubmissionType.UNDETERMINED)


def screen_service_codes(
    service_codes: list[tuple[str, int]],
    submission_type: SubmissionType,
) -> tuple[list[tuple[str, int]], list[str]]:
    """Decide which specialist-supplied service codes belong on THIS submission.

    Returns (codes_to_print, flags). Nothing is ever dropped silently.

      MEDICATION_ONLY  nursing and per-diem codes are withheld, each with a
                       flag naming where they should go instead
      MEDICAL_BENEFIT  everything the specialist supplied is carried through
      UNDETERMINED     carried through, plus one flag that the benefit is
                       unconfirmed, so the screen was not applied

    This function never adds a code and never computes units. It only filters.
    """
    kept: list[tuple[str, int]] = []
    flags: list[str] = []

    for code, units in service_codes:
        bare = str(code).strip().upper()
        if (submission_type is SubmissionType.MEDICATION_ONLY
                and bare in MEDICAL_BENEFIT_ONLY_CODES):
            kind = "Nursing" if bare in NURSING_CODES else "Per-diem"
            flags.append(
                f"{bare} withheld: {kind.lower()} codes do not belong on a "
                f"medication-only (Part D / CMM) submission. They belong on the "
                f"home-infusion medical-benefit authorization — submit them there."
            )
        else:
            kept.append((code, units))

    if submission_type is SubmissionType.UNDETERMINED and service_codes:
        flags.append(
            "Benefit not determined from the referral, so the nursing/per-diem "
            "screen was NOT applied. Confirm whether this is a medication-only "
            "(Part D / CMM) or a medical-benefit submission before sending."
        )

    return kept, flags


# Frequency table: how the order is written -> (kind, value)
#   ("per_day", n)       n doses a day, every day
#   ("every_n_days", n)  one dose every n days
#   ("once", 1)          exactly one dose for the whole phase (a loading dose)
#
# SME Q8 (2026-08-11):"never estimate unusual frequencies using a generic
# daily multiplier. Build the administration schedule from the SOC date
# forward, count each actual dose that falls within the treatment period."
# q48h and weekly cannot be expressed as "doses per day" at all, which is why
# the shape of this table had to change.
FREQUENCY_TABLE: dict[str, tuple[str, int]] = {
    "q24h": ("per_day", 1), "daily": ("per_day", 1), "qd": ("per_day", 1),
    "q12h": ("per_day", 2), "bid": ("per_day", 2),
    "q8h":  ("per_day", 3), "tid": ("per_day", 3),
    "q6h":  ("per_day", 4),
    "q48h": ("every_n_days", 2), "qod": ("every_n_days", 2),
    "weekly": ("every_n_days", 7), "q7d": ("every_n_days", 7),
    "once": ("once", 1),
}

# ---------------------------------------------------------------------------
# 2. Data structures — also the target shape for the extraction layer's JSON
# ---------------------------------------------------------------------------

@dataclass
class Phase:
    """
    One dosing segment of an order. Loading + maintenance is two phases; a
    three-step taper is three.

    `days` is this segment's CALENDAR LENGTH, not a dose count. The two are
    different numbers and schedule() derives them separately.
    """
    dose_mg: float
    frequency: str          # "q8h" / "q48h" / "weekly" / "once"
    days: int               # required, no default — see __post_init__

    def __post_init__(self) -> None:
        # This layer is the trustworthy half of the system. A zero-vial
        # authorization quantity is a WRONG ANSWER THAT LOOKS LIKE AN ANSWER —
        # the same class of failure as inventing a diagnosis code. So refuse
        # impossible input rather than returning a plausible zero.
        if self.days < 1:
            raise ValueError(f"Phase days must be >= 1, got {self.days}")
        if self.dose_mg <= 0:
            raise ValueError(f"Phase dose_mg must be > 0, got {self.dose_mg}")
        _freq(self.frequency)   # fail at construction, not later at scheduling


@dataclass
class Administration:
    """One dose on the schedule. day_offset is days from SOC; 0 is day one."""
    day_offset: int
    dose_mg: float
    frequency: str


@dataclass
class Regimen:
    """One drug's complete order: a sequence of phases."""
    drug_name: str
    vial_size_mg: float
    phases: list[Phase]

    def __post_init__(self) -> None:
        if not self.phases:
            raise ValueError(f"Regimen for {self.drug_name!r} has no phases")
        if self.vial_size_mg <= 0:
            raise ValueError(f"vial_size_mg must be > 0, got {self.vial_size_mg}")

    @property
    def total_days(self) -> int:
        """Day supply is the sum of the phases' calendar lengths.

        It has nothing to do with how many doses are given.
        """
        return sum(p.days for p in self.phases)


@dataclass
class DrugOrder:
    """
    Shorthand for a single-phase order — equivalent to a one-phase Regimen.

    Kept because the pipeline, the eval harness and most tests use it, and
    because most real cases genuinely are one phase.
    """
    drug_name: str          # "Cefepime"
    dose_mg: float          # 2000  (mg per dose)
    vial_size_mg: float     # 2000  (mg per vial)
    frequency: str          # "q12h"

    def as_regimen(self, days: int) -> Regimen:
        return Regimen(self.drug_name, self.vial_size_mg,
                       [Phase(self.dose_mg, self.frequency, days)])

@dataclass
class DrugCalc:
    """Every number for one drug, once calculated."""
    drug_name: str
    dose_display: str       # "2g" / "335mg" — Rule 3: no space before the unit
    vial_display: str
    frequency: str
    doses_per_day: int | None   # None for q48h / weekly / multi-phase orders
    total_doses: int
    total_vials: int
    jcode: str | None
    jcode_units: int | None
    flags: list[str] = field(default_factory=list)
    administrations: list[Administration] = field(default_factory=list)

@dataclass
class CaseCalc:
    """The calculated result for a whole case."""
    start: date
    end: date
    day_supply: int
    drugs: list[DrugCalc]
    flags: list[str] = field(default_factory=list)

# ---------------------------------------------------------------------------
# 3. Primitives — each one implements a numbered rule from the SME document
# ---------------------------------------------------------------------------

def day_supply(start: date, end: date) -> int:
    """Rule 4: both ends count. 07/24 to 09/03 is 42 days, not 41."""
    if end < start:
        raise ValueError(f"End date {end} is before start date {start}")
    return (end - start).days + 1


def end_date_for_supply(start: date, days: int) -> date:
    """Rule 4 in reverse: start date + day supply -> end date.

    21 days from 07/07 ends 07/27.
    """
    if days < 1:
        raise ValueError("Day supply must be >= 1")
    return start + timedelta(days=days - 1)


def format_strength(mg: float) -> str:
    """Rule 3: no space before the unit. 2000 -> '2g', 335 -> '335mg'."""
    if mg >= 1000 and mg % 1000 == 0:
        return f"{int(mg // 1000)}g"
    return f"{int(mg) if mg == int(mg) else mg}mg"


def _norm(s: str) -> str:
    """The one normaliser used before every table lookup."""
    return s.strip().lower()


def _freq(frequency: str) -> tuple[str, int]:
    f = _norm(frequency)
    if f not in FREQUENCY_TABLE:
        raise ValueError(f"Unknown frequency '{frequency}' — add it to FREQUENCY_TABLE, do not guess")
    return FREQUENCY_TABLE[f]


def doses_per_day(frequency: str) -> int:
    """
    Only meaningful for frequencies that are a fixed number of doses per day.

    q48h / weekly / once RAISE, deliberately. They have no doses-per-day, and
    forcing one out of them is exactly the "generic daily multiplier" the SME
    prohibited in Q8.
    """
    kind, n = _freq(frequency)
    if kind != "per_day":
        raise ValueError(
            f"'{frequency}' has no doses-per-day — it is a {kind} schedule. "
            f"Use schedule_phase()/calc_regimen() and count the actual administrations."
        )
    return n


def schedule_phase(phase: Phase, day_offset: int = 0) -> list[Administration]:
    """
    Expand one phase into real administrations.

    This is THE ONLY PLACE in the system where a dose count is produced —
    which is what makes the generic-daily-multiplier bug structurally
    impossible rather than merely forbidden.

    day_offset: where this phase starts, in days from SOC.
    """
    kind, n = _freq(phase.frequency)
    if kind == "once":
        offsets = [0]
    elif kind == "per_day":
        offsets = [d for d in range(phase.days) for _ in range(n)]
    else:  # every_n_days
        offsets = list(range(0, phase.days, n))
    return [Administration(day_offset=day_offset + o, dose_mg=phase.dose_mg,
                           frequency=phase.frequency) for o in offsets]


def schedule(regimen: Regimen) -> list[Administration]:
    """The whole order's schedule. Phases run back to back, never overlapping."""
    admins: list[Administration] = []
    cursor = 0
    for ph in regimen.phases:
        admins.extend(schedule_phase(ph, cursor))
        cursor += ph.days
    return admins


# ---------------------------------------------------------------------------
# 4. The calculation itself
# ---------------------------------------------------------------------------

def calc_regimen(regimen: Regimen) -> DrugCalc:
    """
    All of one drug's quantity maths — every number here is a FOLD over the
    schedule that schedule() produced.

    SME Q8: a dose count may only be counted off a real schedule, never
            estimated as frequency x days.
    SME Q7: vials round up PER DOSE and are then summed — not the whole course
            in mg divided by the vial size at the end. Vials and J-code units
            are separate folds because one vial is not one billable unit.
    """
    flags: list[str] = []
    admins = schedule(regimen)
    total_doses = len(admins)

    # Vials: ceil per dose, then sum. Single-dose vials — leftovers never
    # carry over to the next dose.
    total_vials = sum(math.ceil(a.dose_mg / regimen.vial_size_mg) for a in admins)

    # Wastage: one flag per distinct dose that appears in the schedule
    for dose in sorted({a.dose_mg for a in admins}):
        waste = math.ceil(dose / regimen.vial_size_mg) * regimen.vial_size_mg - dose
        if waste > 0:
            flags.append(
                f"{regimen.drug_name}: {format_strength(waste)} discarded per dose "
                f"(dose {format_strength(dose)} from {format_strength(regimen.vial_size_mg)} vial)."
            )

    # J-code units: also ceil-per-dose then sum, but a different divisor.
    # One vial is NOT one billable unit.
    key = _norm(regimen.drug_name)
    if key in JCODE_TABLE:
        jcode, unit_mg = JCODE_TABLE[key]
        jcode_units = sum(math.ceil(a.dose_mg / unit_mg) for a in admins)
    else:
        jcode, jcode_units = None, None
        flags.append(f"{regimen.drug_name}: no J-code in lookup table — verify code manually, do not guess. (Rule 8)")

    doses = list(dict.fromkeys(a.dose_mg for a in admins))   # in given order, not sorted
    freqs = [_norm(p.frequency) for p in regimen.phases]

    # Doses-per-day exists only for a single per_day phase. Everywhere else it
    # is None rather than a number we made up.
    per_day: int | None = None
    if len(regimen.phases) == 1:
        kind, n = _freq(freqs[0])
        if kind == "per_day":
            per_day = n

    return DrugCalc(
        drug_name=regimen.drug_name.strip().capitalize(),
        dose_display=" → ".join(format_strength(d) for d in doses),
        vial_display=format_strength(regimen.vial_size_mg),
        frequency=" → ".join(freqs),
        doses_per_day=per_day,
        total_doses=total_doses,
        total_vials=total_vials,
        jcode=jcode,
        jcode_units=jcode_units,
        administrations=admins,
        flags=flags,
    )


def calc_drug(order: DrugOrder, days: int) -> DrugCalc:
    """Single-phase shorthand — expands to one Phase and takes the same path."""
    return calc_regimen(order.as_regimen(days))


def _assemble(start: date, days: int, regimens: list[Regimen],
              flags: list[str]) -> CaseCalc:
    """Shared by both entry points. Day supply is already decided by the
    caller; this only calculates the drugs and boxes up the result.
    """
    return CaseCalc(
        start=start,
        end=end_date_for_supply(start, days),
        day_supply=days,
        drugs=[calc_regimen(r) for r in regimens],
        flags=flags,
    )


def calculate_case(start: date, end: date, orders: list[DrugOrder],
                   ordered_day_supply: int | None = None) -> CaseCalc:
    """
    Whole-case calculation where THE DATES DECIDE THE DAY SUPPLY.

    Use this for single-phase orders that came with a start and an end date.

    ordered_day_supply: if the order states a day count in words, pass it in
    and it gets cross-checked against the date maths (Rule 4).
    """
    days = day_supply(start, end)
    flags: list[str] = []

    # Rule 4: the stated day count disagrees with the dates -> flag it. The
    # signed order is what governs, not our arithmetic.
    if ordered_day_supply is not None and ordered_day_supply != days:
        flags.append(
            f"Order states {ordered_day_supply}-day supply but {start:%m/%d/%Y} to {end:%m/%d/%Y} "
            f"= {days} days inclusive. Follow what the signed order supports; updated order may be needed."
        )

    return _assemble(start, days, [o.as_regimen(days) for o in orders], flags)


def calculate_regimen_case(start: date, regimens: list[Regimen]) -> CaseCalc:
    """
    Whole-case calculation where THE ORDER DECIDES THE DAY SUPPLY and the
    dates are derived from it — exactly the inverse of calculate_case().

    SME Q8:"day supply represents the calendar duration of therapy, while dose
    count represents the number of administrations occurring during that
    duration. These numbers do not have to match."
    """
    if not regimens:
        raise ValueError("no regimens")

    lengths = {r.drug_name: r.total_days for r in regimens}
    days = max(lengths.values())
    flags: list[str] = []

    # Drugs of unequal length: taking the longest is a CHOICE, and making it
    # silently would hide the difference. Say it out loud instead.
    if len(set(lengths.values())) > 1:
        detail = ", ".join(f"{n} {d}d" for n, d in lengths.items())
        flags.append(
            f"Drugs have different treatment lengths ({detail}). Day supply shown is the "
            f"longest ({days}d); confirm each drug's own dates before submitting."
        )

    return _assemble(start, days, regimens, flags)


# ---------------------------------------------------------------------------
# 5. One-liner formatting (Rule 2) — the template lives in code, so the LLM
#    cannot drift from it
# ---------------------------------------------------------------------------

def format_one_liner(case: CaseCalc, icd_codes: list[str],
                     service_codes: list[tuple[str, int]] | None = None,
                     *,
                     submission_type: SubmissionType = SubmissionType.UNDETERMINED,
                     ) -> str:
    """
    Rule 2's exact format. Several drugs merge into one line.

    service_codes: optional, e.g. [("S9502", 28)]. Lesson from experiment #1 —
    the specialist sometimes omits service codes entirely, so the CALLER (a
    person) decides whether they appear. The AI never adds them.

    submission_type: which authorization this line is for. Nursing and per-diem
    codes are withheld from a medication-only (Part D / CMM) submission and
    kept on a medical-benefit one — see screen_service_codes(). The default is
    UNDETERMINED, which carries the codes through untouched; callers that know
    the benefit should say so, and the pipeline does. Call screen_service_codes()
    directly when the withholding flags need to be shown to the specialist.
    """
    drug_parts = []
    jcode_parts = []
    for d in case.drugs:
        drug_parts.append(
            f"{d.drug_name} {d.vial_display} vial IV {d.frequency} "
            f"(Dose: {d.dose_display}, Total Qty: {d.total_vials} vials)"
        )
        if d.jcode and d.jcode_units:
            jcode_parts.append(f"{d.jcode} x{d.jcode_units}")

    if service_codes:
        kept, _ = screen_service_codes(service_codes, submission_type)
        jcode_parts.extend(f"{code} x{units}" for code, units in kept)

    return (
        f"Services Requested: {' + '.join(drug_parts)} – "
        f"{', '.join(jcode_parts)} for {' + '.join(icd_codes)}\n\n"
        f"Dates of Service: {case.start:%m/%d/%Y} to {case.end:%m/%d/%Y} "
        f"({case.day_supply} day supply)."
    )

# ---------------------------------------------------------------------------
# 6. Demo — the real worked case from Part 2 of the SME's document
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    case = calculate_case(
        start=date(2026, 7, 24),
        end=date(2026, 9, 3),
        orders=[
            DrugOrder("Cefepime",   dose_mg=2000, vial_size_mg=2000, frequency="q12h"),
            DrugOrder("Daptomycin", dose_mg=335,  vial_size_mg=500,  frequency="q24h"),
        ],
    )

    print(f"Day supply: {case.day_supply}")
    for d in case.drugs:
        print(f"{d.drug_name}: {d.total_vials} vials, {d.jcode} x{d.jcode_units}")
    for f in case.flags + [f for d in case.drugs for f in d.flags]:
        print(f"FLAG: {f}")
    print()
    print(format_one_liner(case, icd_codes=["T81.49XA", "L08.9"]))
