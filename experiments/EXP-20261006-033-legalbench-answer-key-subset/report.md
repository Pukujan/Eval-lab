# EXP-033 — LegalBench answer-key subset (public report)

This report is gold-only: it summarizes the frozen answer-key subset and states each task's majority-label baseline. No model has been scored, so there is no `results.json` and no accuracy claim about any judge.

The subset is three binary answer-key tasks. It is a wider legal axis than Hearsay alone, not a general legal-reasoning score.

## Per-task baselines

| task | records | public | blind | Yes | No | majority | baseline accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `overruling` | 2394 | 1180 | 1214 | 1216 | 1178 | Yes | 0.5079 |
| `definition_classification` | 1337 | 632 | 705 | 691 | 646 | Yes | 0.5168 |
| `citation_prediction_classification` | 108 | 58 | 50 | 54 | 54 | No (tie) | 0.5000 |

`public` and `blind` are the calibration and test partitions of the case-disjoint split. The baseline is the accuracy of always predicting the majority gold label across all of a task's records; a tie is shown as a tie rather than an arbitrary pick.

## Interpretation limits

- Gold is the pinned LegalBench answer key (`answer_key` provenance). No model judgment is promoted to gold.
- `citation_prediction_classification` repeats the same text with opposite answers (53 of its 54 distinct texts appear twice), so the case unit is the text and the case-disjoint split keeps every copy of a text on one side. Its majority label is an exact tie, so a majority baseline carries no signal.
- Gold labels are native `Yes`/`No`; the shared single-mode path defaults to `pass`/`fail`, so scoring must use the `label_set ["Yes", "No"]` contract recorded in `typed-question-spec.json`.
- This is a frozen preregistration artifact; the blind partition is not scored.
