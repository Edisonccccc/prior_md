# Experiment #1 — rules-as-prompt vs the specialist's answer

**Date:** 2026-07-30
**Setup:** a fresh LLM — no context, no tools, no sight of the answer key.
Input was `prompts/system_prompt.md` + `referral.md`.
**Answer key:** the worked case in Part 2 of *PriorMD AI Workflow Reference.docx*.

## Scorecard

| # | Check | Specialist | AI output | Result |
|---|---|---|---|---|
| 1 | Day supply | 42 days (07/24–09/03, both ends counted) | 42 days, and showed its month-by-month working | ✅ |
| 2 | Cefepime quantity | 84 vials, J0692 x336 | 84 vials, J0692 x336 | ✅ |
| 3 | Daptomycin quantity | 42 vials, J0878 x14070 | 42 vials, J0878 x14070 | ✅ |
| 4 | ⭐ **The hard judgment:** avoid the hardware-infection route | did not use the hardware route | "I would not use T84.61- — the chart never says the hardware itself is infected" | ✅ **reproduced** |
| 5 | Avoid osteomyelitis / bacteraemia / sepsis | avoided all three | avoided all three, for the right reasons | ✅ |
| 6 | Primary diagnosis | T81.49XA (other surgical site infection) | T81.42XA (deep incisional), though it volunteered T81.49XA as a fallback | ⚠️ close but different |
| 7 | Secondary diagnosis | L08.9 (local skin/subcutaneous infection) | B95.62 + B96.5 (organism codes) | ⚠️ different route |
| 8 | One-liner format | J-codes + 2 ICD codes only | added S9500/S9501 and nursing codes; wrote "every 12 hours" instead of "q12h" | ⚠️ format drift |
| 9 | CMM generic-substitution question | "Yes" only when generic was explicitly requested | answered "Yes" by inference | ❌ **broke Rule 6** |

**Roughly 85%. The arithmetic was 100%, the hardest judgment was reproduced,
and the misses were all in code routing and format.**

## Three lessons — which became the first three engineering tasks

### 1. Deterministic calculation belongs in code

The model happened to get every number right this time. That is luck, not a
property. Day counts, vial counts and unit conversions moved into code; the
model's job shrank to extracting fields like "2g q12h, 07/24–09/03".

### 2. Code routing needs a case library, not more rules

T81.42XA vs T81.49XA: both are defensible. The specialist chose .49 for a
reason — and paired it with L08.9 rather than the organism codes, even though
the organisms *were* documented. That preference cannot be written as a general
rule. It needs either more solved cases as few-shot examples, or the specialist
making her reasoning explicit so it can go in the prompt.

This is exactly why 10–20 solved cases were requested. They arrived 2026-08-25,
and her reasoning arrived as the Q1–Q8 answers.

### 3. Format and no-inference need validators, not good intentions

- Service codes leaked into the one-liner → the template moved into code, so
  the model cannot drift from it.
- The generic question was answered by inference → Rule 6 says "Yes" only on an
  explicit request. Rules like this need counter-examples in the prompt **and**
  a dedicated eval assertion, because a model that means well still infers.

## What happened next

1. ✅ Calculation became pure code (`src/pa_calc.py`) — J-code lookup, inclusive
   date maths, per-dose vial rounding.
2. ✅ Asked the specialist directly why .49 over .42, and why L08.9 over the
   organism codes. Both answered in full on 2026-08-11 (Q1 and Q2), and both
   are now encoded — see `memory/sme_answers.md`.
3. ✅ 21 solved cases arrived. Turning them into eval cases is tracked as
   `T-case-conversion` in `_matrix/plan.yaml`.
