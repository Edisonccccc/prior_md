# AGENT.md — PriorMD Project Handoff

> **Purpose of this file:** complete session record + working context so any AI assistant
> (Claude Code, Cursor, Claude Desktop, etc.) on any machine can continue this project
> exactly where it left off. Read this file first, fully, before doing anything.
>
> Last updated: 2026-08-26. **The project now lives at `/Users/edison/Projects/prior_md/`.**
> It was reorganised out of a temporary unpack folder on that date: code in `src/`,
> prompts in `prompts/`, the design doc in `docs/`, everything confidential in `data/`.
> The old working folder (`Projects/temp/priormd-experiment/`) is kept as a rollback
> point and is NOT the source of truth any more.
>
> **Start with `README.md`** for orientation and how to run things, then this file
> for the full history, then `docs/engine-design.html` for the system design and
> `_matrix/plan.yaml` for what is left to build.

---

## 1. The people and the project

- **Edison** (user, engineer, zhengyuchen2015@u.northwestern.edu): builds the system. Pure
  engineer, new to the medical domain — explain domain concepts from simple examples.
  **Communication preference: respond in Simplified Chinese with ADHD-friendly structure**
  (small chunks, one concept at a time, 划重点 / "key point" callouts, explicit A/B/C
  next-step choices). **Everything written to disk — code, comments, docs, prompts,
  deliverables — is English.** The Chinese is for the conversation only; the repo has
  to be readable by any engineer or AI that picks it up.
  Code, prompts, and deliverables for the SME stay in English.
- **The SME**: a licensed Prior Authorization (PA) Specialist, non-technical. She is the
  domain oracle. Her company/product name is **PriorMD (PriorMD LLC)** — the name comes from
  her reference document, not from us. She communicates by iMessage/email; her feedback
  arrives casually (screenshots) but is authoritative.
- **The product**: an AI assistant that turns clinical referral packets into
  submission-ready prior-authorization outputs (the "PA one-liner", CMM questionnaire
  answers, and warning flags), with the specialist reviewing everything before submission.
  **Scope per SME (2026-08-03): medication adjudication** — drug, quantity, J-codes,
  diagnosis codes. Multi-provider tool. Provider-specific extras (nursing codes, per-diems)
  are manual, not AI outputs. Full autonomy (no human review) is explicitly a non-goal.

## 2. Domain primer (30 seconds)

Prior authorization = proving to an insurance payer that an expensive therapy (here: home IV
infusion) is medically necessary, in the payer's rigid format. Key vocabulary:

- **ICD-10** — diagnosis codes (T81.49XA). Code choice decides approval; highest-judgment task.
- **J-code (HCPCS)** — billing codes for injectable drugs with fixed units. J0692 = cefepime
  per 500mg → a 2g dose = 4 units. J0878 = daptomycin per 1mg. J0696 = ceftriaxone per 250mg.
  J0834 = aztreonam per 500mg.
- **Day supply** — INCLUSIVE date counting: 07/24 to 09/03 = 42 days (both ends count).
- **Part D** — Medicare drug coverage; essentially only pays FDA-approved uses. Off-label →
  the honest answer is "No"; never dress it up.
- **CMM** — payer's coverage-determination questionnaire / submission portal (CoverMyMeds).
  **CORRECTED 2026-08-25** — the old note here said `Answers: "Yes/No." + one sentence`, which
  is wrong about the form. Measured across all 21 CMM PDFs in `data/`: **186 questions, 98
  answered, 88 deliberately blank (47%)**. The form is a *branching tree* — answering a question
  off your branch is noise at best. Of the answered ones ~87% are Yes/No; the rest are enumerated
  picks (`Expedited timeframe`, `Positron emission tomography`) or free text. There is **no field
  for the explanatory sentence** — supporting material goes through `Additional Documentation`
  instead. Rule 7 in `system_prompt.md` ("Yes/No." + ONE sentence) is *phrasing guidance for the
  specialist*, not the form's structure; it is not wrong, it was being read as a schema.

## 3. Source of truth documents

1. `PriorMD AI Workflow Reference.docx` — from the SME. Part 1 = 12 rules; Part 2 = one fully
   worked case (real patient data — **confidential, keep out of any public repo**).
2. `memory/sme_answers.md` — log of SME decisions AFTER the doc; **overrides the doc**.
   So far: 2026-08-03 nursing-codes removal (see §6).
3. The interview answers + case library now arriving in `data/` will extend #2.

## 4. Architecture (deliberate design decisions — do not casually undo)

```
referral text
  → ① EXTRACTION (LLM):   fills JSON only; every field needs a source_quote; nulls +
                           missing_or_unclear instead of inference; frequency whitelist
  → ② VALIDATION (code):  zero-trust gate. Missing quote / start date / non-whitelisted
                           frequency = HARD ERROR, pipeline halts. Honest nulls = warning.
  → ③ CALCULATION (code): pa_calc.py — dates, vials, J-code units, one-liner template.
                           NEVER done by the LLM. Unknown drug/frequency → flag, never guess.
  → ④ CODING JUDGMENT (LLM): NOT BUILT YET. ICD route selection. Blocked on SME input.
  → ⑤ SPECIALIST REVIEW (human): worksheet → approve/correct → submit.
```

Principles that must survive refactors:
- **Deterministic work in code, judgment work in constrained LLM calls.**
- **Zero trust**: LLM output is testimony, not fact. Fabrication = halt; honest "unknown" = pass with warning.
- **Fixed pipeline, not a free agent** — auditability is a feature in medical workflows.
- **Every SME-approved case becomes a permanent eval; every change must keep all evals green.**
- ICD codes are deliberately left blank in worksheets until layer ④ exists (never guessed).

## 5. Repository map

```
README.md                    orientation + how to run
AGENT.md                     this file — the full handoff
.gitignore                   keeps data/ and machine files out before git exists

src/                         the code, flat (no package — deliberate, D-2026-08-26)
  pa_calc.py                 deterministic calc layer (Chinese comments = teaching notes)
  pipeline.py                zero-trust validator + worksheet renderer
  test_pa_calc.py            14 tests, each from a doc example
  test_pipeline.py           6 zero-trust tests (bad JSON must be caught)
  extraction_case01.json     the fixture both of the above read
prompts/
  system_prompt.md           the 12 rules as a system prompt
  extraction_prompt.md       the extraction LLM's instructions
evals/
  README.md                  how to add a case — follow this when processing data/
  run_evals.py               5-dimension scorer: extraction/calc/coding/format/safety
  cases/case-001-cefepime-dapto/   worked case: referral.md + expected.json + cached extraction
  cases/case-002-aztreonam/        the doc's one-liner example (calc/format only)
experiments/01-rules-as-prompt/
  referral.md                the redacted case used as test input (no answer key)
  ai_output_raw.md           what a fresh LLM produced
  results.md                 scorecard vs expert (~85%; the lessons that became the architecture)
docs/
  engine-design.html         the system design — layer contracts, the schedule model,
                             the constraints on layer 4, the eval architecture
  overview.html              project explainer for Edison (Chinese)
  proposal.html              interactive proposal for the SME (English, degrades without JS)
outbox/                      what was sent to the SME, and when
memory/                      project memory: project_priormd.md, sme_answers.md,
                             user_preferences.md, MEMORY.md
_matrix/                     plan.yaml + discussions.md — the roadmap as code
data/                        CONFIDENTIAL, gitignored — see data/README.md
  sme-source/                her workflow reference (.docx, REAL PATIENT DATA in Part 2),
                             her Q1-Q8 answers, the interview guide
  case-library/              21 cases, 42 PDFs, plus the redaction audit log
```

Run tests: `python3 -m pytest src/ -q`  (works from any directory — 20/20 green)
Run evals: `cd evals && python3 run_evals.py`  (8 pass / 0 fail / 2 skip)
Only dependency: pytest (`pip install pytest`).

## 6. Decision log (chronological, all 2026)

- **07-30 Experiment #1**: rules-as-prompt + redacted case → fresh LLM scored ~85%. All math
  right; reproduced the key judgment (avoid hardware-infection code route on Part D). Missed:
  chose T81.42XA + organism codes where SME chose T81.49XA + L08.9; added service codes to the
  one-liner; answered "Yes" to generic-substitution by inference (violates Rule 6).
  → Conclusions that became the architecture: math must be code; code-route preferences need
  SME cases; format + no-inference rules need validators and evals.
- **07-30 Calc layer built**; stress-testing the doc exposed an internal contradiction
  (Rule 8 nursing table x5/x10 vs Aztreonam example x4/x8 for 28 days) → became interview Q3.
- **07-30 Pipeline + eval harness built.** Eval scorer bug found & fixed: forbidden_in_output
  must be checked ONLY in the submission one-liner, not in flags (honest "osteomyelitis not
  documented" flags are good behavior).
- **08-03 SME (iMessage)**: nursing figures were EXAMPLES; vary by service dates/day supply;
  **"remove the nursing coding from the ai workflow"**; tool is mainly medication
  adjudication for many providers. → Applied everywhere: nursing table deleted from
  pa_calc.py; system prompt says NEVER include 99601/99602; both eval cases have 99601/99602
  in forbidden_in_output; test_nursing_codes_never_auto_added added. This is the template for
  handling ALL SME feedback: code/prompt change + test + eval ban + logged decision with date & quote.
- **08-03 Training strategy set**: no fine-tuning for v1. Calibration ladder: prompt rules →
  few-shot from case library → RAG over cases → model routing (cheap model for extraction,
  strongest for judgment; keep a thin model-API abstraction so models are config) → SFT/LoRA
  only if plateau at 1000s of cases. Long-term roadmap (per Edison, in the proposal deck):
  preference training from specialist accept/edit decisions + online policy distillation —
  positioned as 6+ months, volume-dependent, not promised for v1.
- **08-25**: SME returned questionnaire answers + case library → `data/` on the Mac. Handoff created.
- **08-25 Engine design + matrix board.** Plan-as-code instance at `_matrix/` (3 columns: built /
  to a usable copilot / after that). Design doc covers layer contracts, `Sourced[T]` evidence-carrying
  values, the schedule-as-IR rewrite for Q7/Q8, and the closed-candidate-set constraint on layer 4.
  **Two findings worth carrying forward:**
  (a) **CMM answers are an unbuilt third of the output** — nothing generates, validates or scores
  them (`render_worksheet` omits them, no eval dimension, no `cmm_answers` in `expected.json`).
  They are NOT part of layer 4: layer 4 *classifies* (which code), CMM answering *substantiates*
  (does the chart support a Yes). Designed as a three-state answer — `Answered` with quotes /
  `NotApplicable` (off-branch, correctly blank) / `Unsupported` (wanted Yes, no evidence → a BLOCK
  finding). The last two both submit as an empty box, which is exactly why two states are not enough.
  (b) **Eval leakage** — the 21 cases are simultaneously the regression suite and the few-shot
  corpus. Few-shotting layer 4 from cases it is scored on makes the score meaningless. Split
  14 few-shot / 7 held-out, commit the split, never re-draw it. Note 7 held-out means 1/7 ≈ 14%
  granularity: enough to catch regressions, nowhere near enough to claim an accuracy figure.

## 7. Estimates & framing already shared with stakeholders

- Confidence 85–90% for a specialist-in-the-loop copilot; full autonomy is a non-goal.
- Timeline (part-time, 10–15h/wk): P1 usable MVP (API + review UI + PDF/OCR) 2–4 wks;
  P2 judgment layer + eval expansion 3–6 wks (gated on SME); P3 pilot ~4 wks.
- Cash: API <$50/mo, hosting $20–50/mo, ~$200–500 total for dev. Real cost = Edison's time.
- HIPAA: dev on redacted data only; before production, BAA with LLM vendor + encryption +
  access controls (get compliance advice; not a lawyer).

## 8. Open questions for the SME (check data/ answers against this list)

- Q1: why T81.49XA over T81.42XA (general default or case-specific?)
- Q2: why L08.9 secondary instead of documented organism codes (B96.5/B95.62)?
- Q3: ~~nursing units~~ **ANSWERED 08-03** (removed from scope)
- Q4: when do per-diem codes (S9500/S9501/S9502) go into the one-liner?
- Q5: more "diagnosis route" examples like the hardware call
- Q6: top denial reasons (→ pre-submission checks)
- Q7: vial rounding / wastage (JW modifier) rules
- Q8: unusual frequencies: q48h, weekly (dalbavancin), loading+maintenance, tapers
- Case library: 10–20 solved cases (referral + final output + payer response), redacted

## 9. IMMEDIATE NEXT TASK — process `data/`

1. Inventory the folder; report to Edison what arrived (count, formats, redaction status).
   **If patient identifiers are present, redact before anything else enters the repo/evals.**
2. Map her answers to Q1–Q8; append each to `memory/sme_answers.md` (or the project's
   decision log) with date + verbatim quote; convert each into: prompt-rule change and/or
   code change + a test + an eval assertion, following the 08-03 nursing template.
3. Each case → `evals/cases/case-XXX-shortname/` per `evals/README.md`: referral.md +
   expected.json (numbers from her submitted output; **always fill judgment_notes with her why**).
4. Re-run all tests + evals; fix regressions before proceeding.
5. Then build layer ④ (coding judgment): few-shot from judgment_notes; score it via the
   eval `coding` dimension (switch that dimension from "extractor must not emit ICD" to
   "judgment layer output vs expected icd_codes").
6. After that: P1 engineering (real LLM API behind a thin abstraction, simple review UI,
   PDF text extraction). Git: repo not initialized yet — do `git init` early, keep the
   source docx and any PHI out of any public remote.

## 10. Working conventions with Edison

- Teach while building: he wants to learn the domain and LLM engineering, not just receive
  code. Short chunks, examples first, then the general rule.
- Always end multi-option moments with explicit A/B/C choices.
- Deliverables to the SME: friendly, non-technical English; iMessage-length texts split in
  bubbles; email for attachments; her phone opens HTML in Quick Look (no JS) — any HTML sent
  to her must degrade to a scrolling no-JS page (`docs/proposal.html` and `outbox/followup-questions-2026-08-25.html` both do).
- Every artifact she fills or answers comes back as data: log it, encode it, test it.
