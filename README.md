# PriorMD

> **Development stopped — 13 October 2026.** This repository is a record, not an
> active project. Four of twelve planned checkpoints are met. The calculation
> engine is built and tested; the judgment layer and the payer-questionnaire work
> were never started; nothing here has been run against a real referral.
>
> The handover is below. A nicer-reading version of it is
> [published here](https://edisonccccc.github.io/prior_md/docs/handover.html).
> `AGENT.md` is the technical handoff for an engineer or an AI assistant.

Turn a clinical referral packet into a submission-ready prior authorization
that a PA specialist **approves rather than rewrites**.

Prior authorization is how an insurer is convinced to pay for an expensive
therapy — here, home IV infusion delivered at a patient's house. A licensed
specialist reads a referral and produces three things: a PA one-liner (drug,
quantity, vials, billing codes, dates), the payer questionnaire answers, and a
diagnosis code. Most of that is arithmetic. The rest decides whether it gets
approved.

**Full autonomy is an explicit non-goal.** The specialist reviews everything
before it is submitted.

---

# Handover

## 1. The idea, and whether it held up

The bet was that **most of this work is arithmetic and only a small part is
judgment**. If that holds, software can do the arithmetic perfectly, leave the
judgment to a person, and still save most of the time.

**It held up.** The arithmetic turned out to be exactly as mechanical as hoped —
counting doses across a treatment period, rounding vials, converting to billing
units, computing day supply — and all of it is built and locked down by tests.
The judgment half turned out to be about as hard as feared, and it is the half
that was never built.

## 2. Where it actually got to

Four of twelve checkpoints. Of the five pipeline stages:

| stage | what it does | state |
|---|---|---|
| ① Read the referral | pull drug, dose, frequency, dates, diagnosis, insurance out of the paperwork | written, **never measured** |
| ② Distrust what was read | check every extracted value before anything is calculated from it | built |
| ③ Do the arithmetic | doses, vials, billing units, day supply, the one-liner | **built and tested** |
| ④ Make the judgment call | which diagnosis code; whether this case will be approved | **not built** |
| ⑤ Specialist reviews and submits | a person approves everything before it goes out | not built |

Stage ① has never run against a real referral, because no real referral was ever
available. That is the blocker in section 5.

## 3. What is worth keeping

**The calculation engine, and specifically the rules inside it.** About 1,300
lines and 48 tests. The code is not the valuable part — a competent engineer
could rewrite it in a week. The valuable part is that every rule came from the
specialist directly and every example she gave is now a permanent test, so a
future refactor cannot quietly undo a ruling. That accumulated set, across two
rounds of interviews and her written answers, is months of expert time.

**The written decision trail.** Every significant design decision is recorded
with its reasoning and with what would overturn it — `_matrix/plan.yaml` for the
roadmap, `_matrix/discussions.md` for what is genuinely undecided,
`memory/sme_answers.md` for every ruling with its date and her exact words.
Nobody has to reverse-engineer intent from code.

**The specialist relationship and her case library.** 21 real solved cases across
16 medications with the insurer's response for each, plus written answers to two
rounds of questions. The only ground truth the project ever had. It is her
confidential data, it is deliberately not in this repository, and section 7
covers it.

## 4. What is missing

**The judgment layer — the part that decides whether a request gets approved.**
Choosing the right diagnosis code is not arithmetic. On the one fully worked
case, the specialist deliberately coded a post-surgical wound infection as a skin
infection rather than a hardware infection, because the first route is clean
under that patient's drug benefit and the second invites a denial. Both codes
were defensible from the chart; only one gets paid. Nothing here makes that kind
of call.

**The payer questionnaire — about a third of the deliverable, zero built.** Every
submission includes one. Across the 21 cases we measured **186 questions: 98
answered, 88 blank**. Nothing generates, checks or scores those answers.

**Stage ① has never been measured.** The extraction code exists; there is no way
to know how well it works.

> **If this restarts, fix this first.** The 21 cases are currently doing two jobs:
> the examples a model would learn from *and* the test set judging whether it
> works. That is circular — a system can score well by having memorised its own
> exam. Split them, roughly 14 to learn from and 7 held back, and commit to the
> split before looking at results. With 7 held-back cases the score moves in jumps
> of about 14 percentage points, so it catches disasters and little else.

## 5. The one thing blocking everything

**No real referral packet was ever obtained.** It was asked for twice. Both times
what arrived was the finished submission and the insurer's response, never the
input document. On 13 October this was confirmed as all there is.

The specialist described what a referral contains: physician's order, progress
notes, hospital records, discharge notes, specialist notes, labs, cultures,
medication history, diagnosis, demographics, insurance — *"sometimes one big PDF
and sometimes several different documents"*, and on one case, *"hundreds of pages
long"*.

That description changes the problem. Reading a tidy two-page order is a parsing
problem. Finding the right facts inside several hundred pages of mixed hospital
records is a search problem, and it fails differently — by *missing* something
that was there, quietly, with no error. The current code was written for the easy
version and has never met the hard one.

**One real de-identified referral packet would be worth more than another twenty
solved cases.** It would settle how the documents are shaped, how noisy they are
and how deep the information sits, and it would turn one existing eval case from
a partial check into a genuine end-to-end one. One — not twenty-one.

## 6. Three questions that need the specialist, not an engineer

Tracked as `Q-05`, `Q-07` and `Q-08` in `_matrix/discussions.md`.

| question | why it is stuck |
|---|---|
| **Can we get one real referral?** | Everything about stage ① depends on it, and it is the cheapest to resolve — one de-identified packet from any case would do. |
| **How should questionnaire blanks be categorised?** | She distinguishes a question the form never asked, a question asked but not applicable to this patient, and a question that needs an answer the chart does not support. The design treats the first two as one. With 88 of 186 blank, getting this wrong makes any questionnaire measurement meaningless. |
| **How should the system look up a drug it has never seen?** | She does not want a fixed medication list built in; she wants the drug researched when the case arrives, from CMS, FDA labeling, DailyMed, PrescriberPoint and manufacturer PI. This collides with the project's central safety rule: a billing code read off a web page is testimony, not a verified fact, and there is no agreed way to let one through the zero-trust gate. **This is the open question that touches the architecture rather than a feature.** |

## 7. The confidential material

> The specialist's source material lives on the development machine and is
> **deliberately excluded from this repository** — one `.gitignore` rule covers the
> whole `data/` directory, verified with `git check-ignore` before anything was
> published. This repository is public. That material is not in it and must not
> end up in it.

| what | detail |
|---|---|
| Reference document | The 12 rules the engine is built on, plus one fully worked case. **That worked case contains real patient data.** |
| Case library | 21 solved cases, 16 medications, 46 files, ~43 MB, de-identified under HIPAA Safe Harbor. |
| Interview answers | Two rounds, including the questionnaire returned 13 October — that file still needs filing alongside the rest. |
| Known gap | One case's questionnaire screenshot still carries a portal header with a name on it. Found, logged, never cleaned; all 46 files were never re-scanned. |

**Recommendation.** No BAA was ever put in place with a model vendor permitting
this material to be processed — that would have been required before any real
use, and the project never got that far. With development stopped there is no
remaining reason to hold a copy. The clean ending is to return it to the
specialist, confirm receipt, then delete the local copy. *Nothing has been
deleted; that is the owner's call.*

## 8. If someone picks this up

- **Read two files on day one.** `AGENT.md` is the full technical handoff — what
  exists, why, what is dangerous, what is unfinished. `docs/engine-design.html` is
  the architecture and the reasoning behind each piece. Everything else can wait.
- **Run the tests first.** Two commands, no setup, no accounts, no network. If 48
  tests pass, the engine is intact and can be trusted while you read.
- **Do not grow the drug table.** `JCODE_TABLE` in `src/pa_calc.py` holds four
  medications and looks like the start of a list. It is not — it covers the eval
  cases and nothing more, and the specialist explicitly does not want a built-in
  list. The comment above it says so.
- **Get access to the specialist, or do not start.** She is the only source of
  truth for every rule here. Without her you can maintain what exists but cannot
  correctly extend it.
- **Get one referral before writing new code.** Section 5. Starting stage ① work
  without one means building against a guess a second time.

## 9. Closing checklist

- [x] Push the final commits
- [x] Status note on the repository front page
- [ ] Archive the repository on GitHub (makes it read-only; published docs stay reachable)
- [ ] Return the confidential material to the specialist and delete the local copy
- [ ] Tell the specialist directly — draft in `outbox/handover-note-to-sme-2026-10-13.md`
- [ ] File the October questionnaire with the rest of her material
- [ ] Clean the one portal header and re-scan the case files (`T-privacy-sweep`)

## 10. Closing assessment

A good idea, built carefully, stopped at an awkward point: past the hard
thinking, short of the useful product. The groundwork is unusually solid for an
unfinished project — the architecture is written down, the reasoning is
preserved, the specialist's rules are encoded and tested, and what is missing is
named rather than left to be discovered later.

What it never got was contact with reality. Not one real referral went through
it, and no specialist ever submitted an authorization from its output. Until that
happens, confidence in it rests on expert interviews and internal consistency,
not evidence. That is the honest answer to how far along it was.

If it restarts, the order is not negotiable: **get one referral, settle the
drug-lookup question, then build the judgment layer.** Out of order, the
groundwork already here is wasted.

---

# Running it

| | |
|---|---|
| Tests | **48 / 48 green** — `python3 -m pytest src/ -q` |
| Evals | **8 pass · 0 fail · 2 skip** — `cd evals && python3 run_evals.py` |
| Built | ① extraction prompt · ② zero-trust validation · ③ calculation · eval harness |
| Not built | ④ judgment — ICD routing **and** questionnaire answering |
| Only dependency | `pytest` |

    pip install pytest
    python3 -m pytest src/ -q       # runs from anywhere
    cd evals && python3 run_evals.py

Verified 2026-10-13 from the repository root, from `src/`, and from an unrelated
working directory.

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

## Layout

    README.md          you are here — the handover is above
    AGENT.md           the full handoff — read this first if you are an engineer
                       or an AI assistant picking the project up
    docs/
      handover.html          this handover, as a published page
      engine-design.html     the system design: data model, schedule model, the
                             constraints on layer ④, the eval architecture
      sme-reply-2026-10-13   what her final answers changed, line by line
      overview.html          project explainer for a reader with no medical background
      proposal.html          the proposal sent to the SME (no-JS safe)
    src/               pa_calc.py · pipeline.py · tests · one fixture
    prompts/           system_prompt.md (the 12 rules) · extraction_prompt.md
    evals/             run_evals.py · cases/ — the regression suite
    experiments/       01-rules-as-prompt: the experiment that set the architecture
    outbox/            what has been sent to the SME, and when
    memory/            project memory, including every SME ruling with its date
    _matrix/           plan.yaml — the roadmap as code. `matrix handoff` reads it.
    data/              CONFIDENTIAL, gitignored. See data/README.md.

## Sources of truth, in order

1. `memory/sme_answers.md` — the SME's rulings after the reference document.
   **These override the document.**
2. `data/sme-source/PriorMD-Interview-Answers.txt` — her Q1–Q8 answers.
3. `data/sme-source/PriorMD AI Workflow Reference.docx` — the original 12 rules.

Every ruling she gives lands as four things at once: a code or prompt change, a
test, an eval assertion, and a dated verbatim quote in the log. Two of those are
the mechanical guarantee that a future refactor cannot quietly undo the rule; the
other two are what stops the reasoning from being lost.

The nursing-code rule is the worked example of why all four matter. Her 2026-08-03
instruction was encoded as a global ban. Her 2026-10-13 answer narrowed it: the
exclusion applied only to medication-only Part D / CMM submissions, and on
home-infusion medical-benefit authorizations those codes *"absolutely still
matter"*. The dated quote in the log is what made the correction traceable; the
test is what had been enforcing the wrong rule in the meantime.

## Conventions

- Development runs on redacted data only. Before production: a BAA with the model
  vendor, encryption, access controls.
- ICD codes are deliberately left blank in worksheets until layer ④ exists. The
  project would rather leave a gap than fill it with something plausible.
- Anything genuinely undecided goes in `_matrix/discussions.md`, not into an
  invented answer.
