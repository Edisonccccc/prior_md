---
name: priormd-project
description: PriorMD prior-auth AI project — context, experiment results, calc layer, pipeline, evals, deliverables, next steps
type: project
---
User (edison) is an engineer building an AI prior-authorization system for a licensed PA Specialist (the domain SME, non-technical). Source of truth: "PriorMD AI Workflow Reference.docx" in the project folder (12-rule framework + one worked case). SME rule changes are logged in [[sme-answers]] and override the doc.

Experiment #1 (2026-07-30, experiment-01/): Part 1 rules as system prompt + redacted Part 2 case -> fresh LLM, no answer key. ~85%: all math correct; hardware-code-avoidance judgment reproduced; deviations: T81.42XA+organism codes vs expert's T81.49XA+L08.9; one-liner added service codes; inferred "Yes" on generic question (Rule 6 violation).

Calc layer (calc-layer/pa_calc.py): deterministic — J-code lookup, inclusive dates, vial/unit math, one-liner formatter; unknowns flag, never guess. Nursing table REMOVED 2026-08-03 per SME. One-liner matches expert output exactly.

Pipeline (calc-layer/): extraction_prompt.md (referral -> JSON, mandatory source_quote, nulls + missing_or_unclear instead of inference, frequency whitelist) + pipeline.py (zero-trust validator; specialist worksheet; ICD left to future judgment step) + tests. 20/20 green. End-to-end verified with a fresh LLM extractor.

Eval harness (evals/): run_evals.py, 5 dims (extraction/calc/coding/format/safety; forbidden_in_output checked only in one-liner). expected.json includes judgment_notes (SME's why — gold data). Seeded case-001 + case-002; 99601/99602 forbidden in both. 8 pass / 0 fail / 2 skip.

Deliverables sent: interview guide docx; priormd-overview.html (Chinese explainer); priormd-proposal.html (English interactive proposal + fillable questionnaire, mobile-degradable, exports .txt).

Training strategy (2026-08-03): no fine-tuning v1 — prompt rules -> few-shot -> RAG -> model routing -> SFT/LoRA only at scale. Long-term roadmap per edison: preference training + online policy distillation (6+ months, volume-dependent). Fixed pipeline (not free agent) for auditability; MCP reserved for later integrations.

Built: extraction -> zero-trust validation -> deterministic calc -> worksheet; eval harness. NOT built: coding-judgment layer, real LLM API integration, review UI.

2026-08-25: SME returned questionnaire answers + case library into data/ on the Mac; development moves to the Mac. See AGENT.md section 9 for the processing procedure.
