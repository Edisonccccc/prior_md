# Experiment #1 — the AI's raw output, unedited

> Subject: a fresh LLM given only `prompts/system_prompt.md` and `referral.md`.
> It could not see the specialist's answer.

**1) Diagnosis Code Selection**

- **Best DX: T81.42XA** — Infection following a procedure, deep incisional surgical site, initial encounter. The discharge summary documents a surgical wound infection at the ORIF operative site requiring operative I&D with intra-operative deep wound cultures, which supports deep incisional SSI.
- **Secondary DX: B95.62** (MRSA as cause of diseases classified elsewhere) and **B96.5** (Pseudomonas aeruginosa as cause of diseases classified elsewhere) — both organisms are documented on intra-operative wound cultures, so organism codes are appropriate.
- Not sepsis (no sepsis documented), not bacteremia (blood cultures negative), not osteomyelitis (explicitly no imaging/clinical documentation of osteo — do not code M86.- despite retained hardware).

**2) Flags**

- Incision depth (superficial vs. deep) is not stated verbatim; T81.42XA is supported by operative I&D with intra-op cultures, but if the payer requires explicit depth documentation, confirm with the provider (fallback: T81.49XA).
- Retained hardware is documented, but the record does not state the hardware itself is infected — I would not code T84.61- without provider documentation.
- Cefepime vial size not specified on the order; math below assumes 2g single-dose vials (if 1g vials, qty = 168 vials; J0692 units unchanged).
- Daptomycin 335mg from a 500mg SDV leaves 165mg discarded per vial — bill wastage with JW modifier if the payer requires.
- Date math checks out: 07/24/2026–09/03/2026 inclusive = 42 days, matches the signed order. No discrepancy.

**3) Quantity / J-Code Math**

- Cefepime 2g IV q12h x 42 days = 84 doses = **84 x 2g vials**. J0692 (per 500mg): 2000mg ÷ 500mg = 4 units/dose x 84 doses = **J0692 x336**.
- Daptomycin 335mg IV q24h x 42 days = 42 doses = **42 x 500mg vials**. J0878 (per 1mg): 335 units/dose x 42 doses = **J0878 x14,070** (administered dose; 165mg/vial wastage separate per payer policy).
- Per diems: S9500 x42 (daptomycin, daily IV) + S9501 x42 (cefepime, second daily IV therapy, q12h).
- Nursing (41–42 days): **99601 x7 + 99602 x14**.

**4) PA One-Liner**

Services Requested: Cefepime 2g vial IV every 12 hours (Dose: 2g, Total Qty: 84 vials) – J0692 x336, and Daptomycin 500mg vial IV every 24 hours (Dose: 335mg, Total Qty: 42 vials) – J0878 x14070, S9500 x42 + S9501 x42, 99601 x7 + 99602 x14 for T81.42XA + B95.62 + B96.5

Dates of Service: 07/24/2026 to 09/03/2026 (42 day supply).

**5) Dates of Service / Day Supply**

07/24/2026 to 09/03/2026, inclusive = 42-day supply (Jul 24–31 = 8 days + Aug = 31 days + Sep 1–3 = 3 days). Matches signed order.

**6) CMM Answers**

- **Q1:** T81.42XA (deep incisional surgical site infection, initial encounter), with B95.62 (MRSA) and B96.5 (Pseudomonas aeruginosa) supported by intra-operative wound cultures.
- **Q2 – Daptomycin:** Yes. Daptomycin is FDA-approved for complicated skin and skin structure infections caused by MRSA, which matches the documented culture-positive surgical site infection.
- **Q2 – Cefepime:** No. Cefepime's FDA-approved skin indication is limited to uncomplicated skin/skin structure infections due to MSSA or S. pyogenes, so its use for a Pseudomonas surgical site infection is off-label, though compendia-supported for Part D coverage.
- **Q3:** Yes. Both cefepime and daptomycin are prescribed by generic name and will be dispensed as generics.
