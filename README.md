# PriorMD

> **Status: development stopped, 13 October 2026.** This repository is kept as a
> record, not as an active project. Four of twelve planned checkpoints are met: the
> calculation engine is built and tested, the judgment layer and the payer-questionnaire
> work were never started, and nothing here has been run against a real referral.
>
> **Start with the [handover](https://edisonccccc.github.io/prior_md/docs/handover.html)**
> — what exists, what it is worth, what is missing, and what picking this up would need.
> `AGENT.md` is the technical handoff.

Turn a clinical referral packet into a submission-ready prior authorization
that a PA specialist **approves rather than rewrites**.

Prior authorization is how an insurer is convinced to pay for an expensive
therapy — here, home IV infusion. A licensed specialist reads a referral and
produces three things: a PA one-liner (drug, quantity, vials, billing codes,
dates), the payer questionnaire answers, and a diagnosis code. Three of those
four outputs are arithmetic. The fourth decides whether it gets approved.

**Full autonomy is an explicit non-goal.** The specialist reviews everything
before it is submitted.

---

## Status — verified 2026-08-26

| | |
|---|---|
| Tests | **20 / 20 green** — `python3 -m pytest src/ -q` |
| Evals | **8 pass · 0 fail · 2 skip** — `cd evals && python3 run_evals.py` |
| Built | layers ① prompt · ② zero-trust validation · ③ calculation · eval harness |
| Not built | layer ④ judgment (ICD routing **and** questionnaire answering) |
| Only dependency | `pytest` |

    pip install pytest
    python3 -m pytest src/ -q       # runs from anywhere
    cd evals && python3 run_evals.py

---

## The pipeline

    referral text
      → ① EXTRACTION  (LLM)   fills JSON only. Every field carries a source_quote.
                              Honest nulls, never inference. Frequency whitelist.
      → ② VALIDATION  (code)  zero-trust gate. Missing quote / missing start date /
                              non-whitelisted frequency = HARD ERROR, pipeline halts.
                              An honest null passes with a warning. That distinction
                              is the whole design.
      → ③ CALCULATION (code)  dates, dosing schedule, vials, J-code units, the
                              one-liner. NEVER done by the LLM. Unknown drug or
                              frequency → flag, never guess.
      → ④ JUDGMENT    (LLM)   NOT BUILT. ICD route selection and CMM questionnaire
                              answering. Both constrained: closed candidate sets,
                              rejection reasons mandatory.
      → ⑤ REVIEW      (human) worksheet → approve / correct → submit.

Principles that must survive refactors: deterministic work in code and judgment
work in constrained LLM calls; LLM output is testimony, not fact; a fixed
pipeline rather than a free agent, because auditability is a feature here; and
every SME-approved case becomes a permanent eval.

---

## Layout

    README.md          you are here
    AGENT.md           the full handoff — read this first if you are an AI
                       assistant picking the project up
    docs/
      engine-design.html   the system design: data model, schedule model, the
                           constraints on layer ④, the eval architecture
      overview.html        project explainer (Chinese)
      proposal.html        the proposal sent to the SME (English, no-JS safe)
    src/               pa_calc.py · pipeline.py · tests · one fixture
    prompts/           system_prompt.md (the 12 rules) · extraction_prompt.md
    evals/             run_evals.py · cases/ — the regression suite
    experiments/       01-rules-as-prompt: the experiment that set the architecture
    outbox/            what has been sent to the SME, and when
    memory/            project memory, including every SME ruling with its date
    _matrix/           plan.yaml — the roadmap as code. `matrix handoff` reads it.
    data/              CONFIDENTIAL, gitignored. See data/README.md.

---

## Sources of truth, in order

1. `memory/sme_answers.md` — the SME's rulings after the reference document.
   **These override the document.**
2. `data/sme-source/PriorMD-Interview-Answers.txt` — her Q1–Q8 answers.
3. `data/sme-source/PriorMD AI Workflow Reference.docx` — the original 12 rules.

Every ruling she gives lands as four things at once: a code or prompt change, a
test, an eval assertion, and a dated verbatim quote in the log. Two of those are
the mechanical guarantee that a future refactor cannot quietly undo the rule;
the other two are what stops the reasoning from being lost. The 2026-08-03
nursing-code decision is the worked example.

---

## Conventions

- Development runs on redacted data only. Before production: a BAA with the
  model vendor, encryption, access controls.
- ICD codes are deliberately left blank in worksheets until layer ④ exists.
  The project would rather leave a gap than fill it with something plausible.
- Anything genuinely undecided goes in `_matrix/discussions.md`, not into an
  invented answer.
