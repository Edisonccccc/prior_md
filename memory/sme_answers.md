---
name: sme-answers
description: SME's answers/decisions as they arrive — the authoritative rule changes
type: project
---
Log of SME (PA Specialist) decisions, newest first. These override the original reference doc.

## 2026-10-13 — Returned questionnaire (`PriorMD_QuestionnaireAnswers.docx`)

Source: her written answers to the follow-up form sent 2026-08-26. 17,194 characters,
no attachments. The five referral packets she describes (Ocrevus, Remicade/Infliximab,
Tygacil/Tigecycline, Daptomycin, Ertapenem) were NOT included and are not available —
Edison, 2026-10-13: "that is all i have". Treat the prose descriptions as the only
evidence about referral shape. See Q-01 / Q-05.

### A1 — Submission mode: RESOLVED, manual for v1
> "For the first version, I'm okay with the PA specialist still manually submitting
>  through CoverMyMeds or whatever payer portal they are using. I really just need the
>  AI to organize everything correctly and give us the answers in a clean, paste ready way."

Consequence: no portal automation in S1. "Paste ready" is a hard output requirement, not
a nicety — the one-liner and the CMM answers must be copyable field by field.

### A4 — Referral shape: RESOLVED, and much larger than assumed
A referral is the whole medical record: physician order, progress notes, hospital records,
discharge notes, specialist notes, labs, cultures, medication history, diagnosis, demographics,
insurance. "sometimes one big PDF and sometimes several different documents."
On the Ertapenem case: **"The original referral is hundreds of pages long."**

Consequence: layer 1 is a needle-in-haystack retrieval problem over hundreds of pages, not a
single-document parse. The design doc's assumption of a compact referral is wrong.

### Nursing / per-diem codes — she NARROWED her 2026-08-03 ruling  [ENCODED 2026-10-13]
> "when I previously said nursing codes and per diem codes should not be included, I was
>  talking about medication only Part D or CMM submissions. I do not want those codes removed
>  from the entire system. For home infusion and medical benefit authorizations, those codes
>  absolutely still matter. They just need to be handled in the correct workflow and not
>  thrown into every medication PA."

We had encoded the 08-03 instruction as a GLOBAL ban and had a test enforcing it. Fixed:
`SubmissionType` (medication_only / medical_benefit / undetermined), `screen_service_codes()`,
`submission_type_for_payer()` in `pa_calc.py`; pipeline derives the benefit from the extracted
payer and reports anything withheld as a flag; system prompt rule 8 rewritten; 9 scoped tests
replace the single global one. **case-002's ban was removed — that case carries S9502, a
per-diem code, so it is a medical-benefit case and was the wrong place for the ban.**
case-001 keeps it, now justified by Part D rather than by a global rule.
Still in force from 08-03: the AI never CALCULATES nursing units.

### CMM blanks are FOUR states, not three
> "It needs to understand the difference between a question that was never triggered,
>  a question that does not apply, and a question that actually needs an answer but the
>  chart does not support it."

Our design had Answered / NotApplicable / Unsupported. She splits NotApplicable in two:
never-triggered (conditional branch not reached) vs does-not-apply (reached, but not relevant
to this patient). Design doc section on the CMM questionnaire needs the fourth state.

Bigger ask in the same answer: "look at the patient's clinicals and help us determine if the
patient meets the payer's criteria before we even get all the way through the submission."
That is a pre-submission readiness verdict, earlier in the flow than our current output.

### No hand-maintained drug list — research the drug at runtime  (overturns A5 / Q-02)
> "I do not really want to design this around a certain number of medications or build a
>  small drug list into the system... I want the AI to be able to research the medication
>  when the case comes in."

Named sources: CMS, FDA labeling, DailyMed, PrescriberPoint, manufacturer prescribing
information. Consequence: `JCODE_TABLE`'s four hand-written rows are a stopgap, not the design.
Needs a retrieval-with-citation layer, which collides head-on with "never guess" — see Q-08.

### ICD selection — wording latitude, but still no invention
> "Providers do not always document things using the exact ICD description."

So verbatim chart wording cannot be required for a code to be selected. The grounding rule has
to allow clinical synonymy while still refusing unsupported codes. She adds a second output:
the system must say **what is missing and what documentation would unlock a stronger diagnosis**.

### Her one-line definition of the product — better than our north star
> "Is this ready to submit or not? If it is ready, give me what I need... If it is not ready,
>  tell me exactly what is missing, why I need it, and what I need to go back and get from
>  the provider."


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
