# Limitations of the canonical paper

This file mirrors Section 6 of [`paper.md`](paper.md). If the two differ,
`paper.md` wins.

- **One question pool.** It is objective and typed, and dominated by MMLU and
  GSM8K. There are only 108 two-answer questions and no ties. Results may not
  carry over to open-ended or subjective grading.
- **Runs, not models.** Each judge is usually a single run on a single date,
  through a specific route. Only Jev (two runs), Grok 4.6 (three) and Qwen
  Flash (four setups) were repeated. Providers can change behaviour over time.
- **Local models used a different harness** and different length limits.
  Two 9B models were not run.
- **The Qwen explanation is inferred.** It rests on the recorded settings and
  answer times; token counts were not recorded. The InferHub run also changed
  the prompt and route, so its gain cannot be pinned on one factor.
- **Unreadable answers** were recorded, but the raw text was not kept, so we
  cannot tell whether the model, its length, or our parser was at fault.
- **Many comparisons.** Correcting for 325 pairwise tests is conservative.
- **Exclusions.** Luna is excluded by project policy.
