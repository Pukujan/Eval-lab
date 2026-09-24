# Limitations of the canonical paper

This file mirrors Section 6 of [`paper.md`](paper.md). If the two differ,
`paper.md` wins.

- **One pool.** 760 objective, typed blind records dominated by MMLU (320) and
  GSM8K (200); only 108 pairwise records and no `TIE` gold labels. Results do
  not transfer to open-ended, subjective, legal-opinion or expert-adjudicated
  tasks.
- **Runs, not models.** Arms are single runs from different dates, harnesses
  and routes. Only Jev (two runs), Grok 4.6 (three) and Qwen Flash (four
  configurations) have any repetition. Provider behaviour can change between
  dates.
- **Local arms** (EXP-027) use native label scoring and different context caps,
  not the provider typed-output harness. Nimble-9B and Kev-9B were not run.
- **Qwen variance explanation** rests on committed request configuration and
  latency. YOLO-Auto runs recorded no token usage, so hidden reasoning is
  inferred, not observed. EXP-024 also changed prompt and route, so its gain
  cannot be attributed to one factor.
- **Parse failures** in EXP-024 are recorded as `label_not_found`, but raw
  response text was not retained; model, length and parser causes cannot be
  separated.
- **Multiple testing.** Holm over 325 pairs is conservative; shared-record
  tests exclude each arm's unresolved records by construction.
- **Exclusions.** Luna is excluded by project policy.
- **Confidence.** Calibration is outside the research question; only local
  scorers expose probabilities (Appendix A).
