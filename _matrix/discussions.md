# PriorMD — discussions
Raise: `matrix discuss "…"` appends the next open Q-nn. Resolve: a prose edit —
tick the box and add a one-line pointer to where the decision landed (a stage,
a block, a parked todo). Ids are never reused.

- [x] **Q-01 · The case library arrived without the original referrals or the judgment notes.** Her questionnaire answer describes each case as referral plus clinical records, plus the submission, plus the payer response, plus a short note on any judgment call. What actually arrived is the CMM submission and the outcome letter only. This is load-bearing in two directions: without a referral there is no input to test the extraction layer against, so the whole EXTRACT row has no evidence and `S1-G4` can only be closed on calc, coding, format and safety; and without the judgment notes the few-shot material for layer 4 is the three interview answers rather than 21 worked examples. Most likely they simply were not packaged. Asked 2026-08-25 — see the drafted follow-up. (raised 2026-08-25)
  · **ANSWERED 2026-10-13, negatively.** Her returned questionnaire describes five referrals in
  prose (Ocrevus, Remicade/Infliximab, Tygacil/Tigecycline, Daptomycin, Ertapenem) but contains
  no attachments, and Edison confirms "that is all i have". The referrals do not exist in any
  form we can run a model against. What the answer *did* give us is the shape: a referral is the
  full medical record — order, progress notes, hospital and discharge records, specialist notes,
  labs, cultures, medication history, demographics, insurance — "sometimes one big PDF and
  sometimes several different documents", and on the Ertapenem case "hundreds of pages long".
  So A4 is settled as a **description** and unsettled as **evidence**. The EXTRACT row stays
  without a measurement; `S1-G4` closes on calc, coding, format and safety only, and the board
  should say so rather than imply it. The judgment-note half is also empty: the few-shot material
  for layer 4 remains her interview answers, not 21 worked rulings. Follow-on: Q-05.

- [x] **Q-02 · How wide is the drug scope, really?** AGENT.md scopes the tool to home IV infusion, and `pa_calc.py` carries a hand-written J-code table with four anti-infectives. The library contains Leqembi, Kisunla, Gammagard, zoledronic acid, milrinone and Vabomere among others. The two readings lead to different engineering: a curated table that grows one SME-confirmed row at a time, or a real HCPCS dataset with the flagging behaviour as the safety net. The second is more work and introduces a data source nobody has validated; the first does not scale past a few dozen drugs. Not decidable without her — asked 2026-08-25. Until it is settled, `T-drug-table-gap` keeps the flag-never-guess behaviour, which is correct under either answer. (raised 2026-08-25)
  · **RESOLVED 2026-10-13 by the SME — neither option.** She rejected the premise: "I do not
  really want to design this around a certain number of medications or build a small drug list
  into the system... I want the AI to be able to research the medication when the case comes in."
  Named sources: CMS, FDA labeling, DailyMed, PrescriberPoint, manufacturer prescribing
  information. This **overturns assumption A5** in the design doc and retires the curated-table
  option entirely. `JCODE_TABLE`'s four rows are now explicitly a stopgap for the cases in the
  eval suite, not the architecture. The flag-never-guess behaviour stays — it is the only part of
  the current design that survives unchanged, and it becomes the fallback when research comes back
  empty rather than when a row is missing. The real work this creates is a retrieval layer with
  citation, which is a new question, not this one: see Q-08.

- [x] **Q-03 · Is Part B versus Part D benefit routing an AI output or specialist-only?** Three library cases were denied under Part D and were Part B territory, the payer citing the Medicare rule that a drug administered through DME is a Part B drug. AGENT.md says provider-specific extras are manual, which argued for leaving this alone; the Q6 answer names wrong-benefit submission as one of the five denial reasons the tool should catch, which argued for building it. (raised 2026-08-25)
  · RESOLVED 2026-08-25, by Edison's delegation, **as a flag and not a decision** — `T-benefit-routing`, under `S1-G6`. The tool surfaces the risk and cites the rule the payer would cite; the specialist decides the benefit. This sits inside the existing architecture rather than adding a sixth layer, keeps full autonomy a non-goal, and is what Q6 actually asks for — a warning while there is still time to fix it. **Revisit if:** the SME says she wants the benefit selected outright rather than flagged; or the flag proves reliable enough over the pilot that leaving the call to a human is just friction. Either would promote this from a gate check to a judgment layer, which is a different shape of work.

- [x] **Q-04 · When does this become a git repo, and what is the PHI boundary for a remote?** Deferred by Edison 2026-08-25 — git comes once the repo is cleaner. Two consequences to keep in view while it is deferred: `plan.yaml` is designed to be reviewed in a diff and its structural hand-edits are only ledgered, not versioned, until then; and the source `.docx` contains real patient data in Part 2, so whatever the first commit includes needs deciding before there is a remote, not after. (raised 2026-08-25)
  · **RESOLVED 2026-08-26.** `git init` plus a first commit to `github.com/Edisonccccc/prior_md`,
  **public**, by Edison's decision. The PHI boundary is one `.gitignore` line, `/data/`, verified
  with `git check-ignore` before the push: the SME's source `.docx` with real patient data in
  Part 2, and the 21-case library, are outside the repo. `memory/` and `outbox/` were kept in by
  his decision. The service dates 07/24/2026-09/03/2026 appear in 22 places and were kept as-is,
  also his call, after being shown the alternative. Docs are served from GitHub Pages.
  **Still owed:** `T-privacy-sweep` — CASE-002's CMM page carries a "Logged in as [name]" portal
  header, and all 42 case PDFs want a re-scan. That sits under `/data/` so it is not public, but
  it is a boundary issue, not a cosmetic one.

- [ ] **Q-05 · Can the extraction layer be evaluated at all without referrals?** Held by Edison 2026-08-25 pending Q-01. The tempting workaround is to synthesise a referral from each CMM submission, which is circular: the extractor would be scored on recovering values from a document generated out of those same values. If Q-01 comes back empty, the honest options are to leave the EXTRACT row unmeasured and say so on the board, or to have the SME hand-write a small number of referrals from memory. Not decided. (raised 2026-08-25)
  · **Q-01 came back empty on 2026-10-13, so this is now live and still undecided.** Two facts
  narrow it. First, synthesising referrals from the CMM submissions is now *more* circular than it
  looked: we would be generating a tidy one-page document and scoring extraction on it, while the
  real input is "hundreds of pages" of mixed hospital records — we would be measuring the easy case
  and reporting it as the hard one. Second, the cheapest honest unblock is no longer "a small
  number of referrals" but **one**: a single real de-identified packet would establish the document
  shape, the noise level and the retrieval depth, and would turn one eval case from format-only into
  end-to-end. Twenty-one is a nice-to-have; one is load-bearing. Until there is one, the board
  carries the EXTRACT row as explicitly unmeasured. Decision owner: Edison.

- [x] **Q-06 · This instance lives in a temporary directory.** Everything sat under `Projects/temp/priormd-experiment/` because the Windows handoff was unpacked there while `Projects/prior_md/` was kept clean. (raised 2026-08-25)
  · RESOLVED 2026-08-26 — moved to `Projects/prior_md/`, which was empty. Three decisions from Edison shaped it: **(a) no Python package** — the code stays flat in `src/`, since a package buys little at four modules and the rename cost would have touched AGENT.md, the design doc and this plan; **(b) the SME source documents live under `data/`** rather than a separate `reference/`, so one `.gitignore` line covers everything confidential; **(c) the old folder is kept as a rollback point**, not deleted — `device_bash` cannot delete on this machine anyway. Three location-coupled paths were fixed in the process: a fixture opened relative to cwd, a hardcoded `calc-layer` on the eval harness's `sys.path`, and two stale docstrings. Tests now pass from the repo root, from inside `src/`, and from an unrelated directory — they previously only ran from inside `calc-layer/`. `README.md`, `.gitignore` and `data/README.md` were written as part of the move; `git init` is still deferred (Q-04).
- [ ] **Q-07 · CMM blanks are four states, not three. The SME distinguishes a question that was never triggered (a conditional branch the form never reached), a question that does not apply (reached, but not relevant to this patient), and a question that needs an answer the chart does not support. Our design collapses the first two into NotApplicable. The first two are detectable from the form's own branching logic and the third is a clinical judgment, so they probably do not belong to the same layer: branch state is structural and belongs with the form model, unsupported-by-chart is layer 4. Needs her to confirm the distinction is worth the extra state before it is built, because on the measured corpus 88 of 186 questions are blank and mis-splitting them would make the fill-rate metric meaningless.** (raised 2026-10-13)
- [ ] **Q-08 · Runtime drug research versus never guess. The SME wants the drug researched when the case comes in rather than read from a maintained table, naming CMS, FDA labeling, DailyMed, PrescriberPoint and manufacturer prescribing information. This is the first place the architecture's central rule does not obviously hold: a J-code read off a retrieved page is neither a deterministic calculation nor a constrained judgment call, it is testimony from a third party. Open: which sources rank over which when they disagree, what is cached versus fetched per case, whether a retrieved billing unit may enter a calculation at all or must be specialist-confirmed first, and what the system does when every source is silent. Until this is settled the four-row JCODE_TABLE stands as a stopgap and unknown drugs stay flagged.** (raised 2026-10-13)
