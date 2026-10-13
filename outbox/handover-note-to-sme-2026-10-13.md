# Draft note to the SME — development stopping

(Replace `[her name]` and `[your name]` before sending.)

Short, because she answered two rounds of questions in good faith and deserves a
plain statement rather than a progress report. Adapt the voice; do not send as-is
without reading it.

---

Hi [her name],

I want to tell you directly rather than let it go quiet: we are stopping development
on PriorMD. This is not about anything in your answers — your 13 October replies were
the clearest material we got, and two of them corrected things we had built wrong.

Where it ended up, honestly:

- **The arithmetic works.** Day supply, dose counts, vial rounding, J-code units and the
  one-liner are built and locked down by 48 automated tests. Every rule in there came
  from you, and each of your examples is now a permanent test — including the 700mg
  daptomycin case and all four of your unusual-frequency examples.
- **Your nursing-code correction is in.** We had applied your August instruction too
  broadly, across the whole system. It is now scoped the way you described: off the
  medication-only Part D and CMM submissions, kept on the home-infusion medical-benefit
  ones. We had it backwards on one of our test cases and that is fixed.
- **The judgment half was never built.** Choosing the diagnosis code, and answering the
  payer questionnaire, are the two things that would have made this actually useful to
  you, and neither was started.
- **Nothing was ever run on a real referral.** We never had one. That turned out to matter
  more than anything else.

Two practical things:

1. Your source document, the 21-case library and your interview answers were kept out of
   the public code repository throughout. I would like to return everything to you and
   then delete our copies — tell me the format you want and I will send it over.
2. The design documents are written up and readable in a browser. If this is ever picked
   up again, by us or anyone else, they explain what was built and what was still open.
   I am happy to hand those over to you to keep.

Thank you for the time you put into this. The interview answers were the most useful part
of the whole project, and they are the part that would survive if it ever restarts.

[your name]
