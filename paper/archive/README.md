# Archived paper drafts

These drafts are superseded by the canonical paper [`../paper.md`](../paper.md)
(TASK-0056). They are kept unchanged for history and are **not** maintained;
numbers in them may use older framings (for example, EXP-013 described as a
broader collection, when it scores the same 760-record pool).

| Path | What it was |
| --- | --- |
| `selective-escalation/main.tex` | arXiv-style LaTeX draft on calibrated selective escalation (TASK-0010), with its `generated/` tables, `limitations.md` and `reproducibility.md`. Still built/validated by `scripts/generate_research_artifacts.py` and `scripts/validate_research_artifacts.py`. |
| `calibrated_judge_study.md` | EXP-019 calibrated judge study draft. |
| `benchmark_comparison_study.md` | Multi-wave benchmark comparison draft (EXP-013 to EXP-028), last updated by TASK-0055. |

Figures referenced only by the archived drafts (`direct_wave_accuracy_coverage`,
`inferhub_wave_accuracy_coverage`, `local_decision_models`) were removed from
`paper/figures/benchmark/`; they can be recovered from commit `51256cb`.

Topics moved out of the canonical paper (selective escalation and routing,
LegalBench Hearsay, InferHub provider selection, GLEIF/EDGAR/CourtListener,
hard negatives, TF-IDF student) are listed as future work in Section 7 of
`paper.md`.
