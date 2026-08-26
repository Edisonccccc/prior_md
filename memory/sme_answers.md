---
name: sme-answers
description: SME's answers/decisions as they arrive — the authoritative rule changes
type: project
---
Log of SME (PA Specialist) decisions, newest first. These override the original reference doc.

## 2026-08-03 — Nursing codes removed from AI workflow (answers interview Q3)
Via iMessage: the doc's nursing figures (Rule 8 table AND the Aztreonam example) were EXAMPLES, not rules — units vary by service dates/day supply of the medication dispensed, mostly weekly. Instruction: "remove the nursing coding from the ai workflow" — it won't apply universally to every provider; most users will use the tool mainly for MEDICATION ADJUDICATION.

Applied: nursing_units table/function deleted from pa_calc.py; system prompt now says NEVER include 99601/99602; both eval cases list 99601/99602 in forbidden_in_output; case-002 expected one-liner drops nursing codes (keeps S9502 x28); new test test_nursing_codes_never_auto_added. All tests/evals green after change.

Product scope insight: target users = multiple providers, primary use = medication adjudication (drug + quantity + J-code + DX for drug coverage). Provider-specific extras (nursing, per-diems) are specialist manual additions, not AI outputs.

Still open from interview guide: Q1 (.49XA vs .42XA), Q2 (L08.9 vs organism codes), Q4 (when S-codes go in one-liner), Q5-Q8, case library — answers now arriving in data/ (2026-08-25), to be logged here as processed.

---

## 2026-08-11 · Q7 — Single-dose-vial rounding  [ENCODED 2026-08-26]

> "round up to the number of whole SDVs needed for each individual dose first,
>  then multiply by the total number of doses. Do not calculate the entire
>  course in milligrams and divide by the vial strength at the end."
>
> "if Daptomycin is supplied as a 500mg SDV and the patient is ordered 700mg IV
>  every 24 hours for 30 days ... The correct authorization quantity is
>  therefore 2 vials per dose x 30 doses = 60 vials."
>
> "One vial does not necessarily equal one J-code unit, so those calculations
>  should always be performed independently."

**Status: the code was ALREADY correct on this.** It was locked before the Q8
refactor could break it — 7 tests in `src/test_pa_calc.py` under the Q7 heading,
including her 60-vs-42 counter-example asserted both ways.

## 2026-08-11 · Q8 — Unusual frequencies  [ENCODED 2026-08-26]

> "never estimate unusual frequencies using a generic daily multiplier. Build
>  the administration schedule from the SOC date forward, count each actual dose
>  that falls within the treatment period."
>
> "the day supply remains 10 days because that is the length of the treatment
>  period. The AI should not confuse dose count with day supply."

**Status: the code WAS wrong** — `total_doses = per_day * days`, and
`FREQUENCY_TABLE` was `dict[str, int]`, which cannot express q48h or weekly at
all. Replaced with `Phase` / `Regimen` / `Administration` and a `schedule()`
function that enumerates every dose; all quantities are now folds over that list.

Her four worked examples are tests, and all four reproduce exactly:

| shape | doses | day supply |
|---|---|---|
| q48h, 10 days | 5 | 10 |
| weekly x 6 weeks | 6 | 42 |
| 1000mg loading + 500mg q24h x 13d | 14 (15 vials) | 14 |
| q8h/q12h/q24h taper, 5d each | 30 | 15 |

`doses_per_day()` now **raises** for q48h / weekly / once rather than returning a
number — inventing one is precisely what she prohibited.

**One spec correction found while implementing:** `docs/engine-design.html`
originally derived day supply from the last dose date. That is wrong for sparse
schedules (q48h over 10 days ends on day 9). Day supply comes from the ordered
treatment length; only dose count comes from the schedule. The doc has been
corrected and carries a note.
