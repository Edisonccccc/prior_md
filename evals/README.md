# PriorMD eval set

**The core idea: every case the specialist got right becomes a permanent exam
question.** Any change from here on — a different model, a reworded prompt, a
new rule — has to pass all of them again before it ships.

## Layout

```
evals/
  README.md            this file
  run_evals.py         the scorer:  python3 run_evals.py
  cases/
    case-001-short-name/
      referral.md            input: the de-identified referral, as the
                             extraction LLM would read it
      expected.json          answer key: what the specialist actually submitted
      extraction_cached.json optional: one cached LLM extraction, so the
                             extraction dimension can be scored offline
```

## Adding a case

1. Create `cases/case-XXX-short-name/`.
2. Save the de-identified referral as `referral.md`. **Keep the original
   wording** — do not tidy it up. Messy input is the point.
3. Fill in `expected.json` from the template. The numbers come from her
   submitted output, not from ours.
   **`judgment_notes` is not optional.** She said the reasoning is worth more
   than the submission, and a case without it can score a number but cannot
   teach the judgment layer anything.
4. Run `python3 run_evals.py` and confirm the new case is picked up.

## expected.json fields

| Field | What it holds | How it is scored |
|---|---|---|
| `calc.day_supply / drugs[]` | days, vials, J-code units | exact equality |
| `icd_codes` | the diagnosis codes she actually used | sets must match exactly |
| `one_liner` | the one-liner she submitted | verbatim, whitespace normalised |
| `required_flags` | warnings that must appear | substring match, all required |
| `forbidden_in_output` | content that must never appear | any occurrence fails |
| `extraction_expected` | correct values for the key extracted fields | field by field |
| `judgment_notes` | her "why" | not scored — this is the few-shot corpus |

## The five dimensions, scored per case

1. **extraction** — were the key fields read correctly
2. **calc** — are the numbers right (if extraction passed and this fails, the
   calculation layer has a bug)
3. **coding** — are the ICD codes right. Today this asserts the *extractor*
   emits no ICD codes, which is the right test while layer 4 does not exist and
   the wrong one the moment it does. See the note in `score_coding`.
4. **format** — the one-liner matches verbatim
5. **safety** — every required flag is present and nothing forbidden appears

## A sixth dimension is missing

Nothing scores the CMM questionnaire answers, which are a third of the declared
output. `cmm_answers` and a `cmm` dimension are tracked as `T-cmm-dimension`
in `_matrix/plan.yaml`.
