# TASK-0069 — LegalBench objective subset beyond Hearsay

## Status

Frozen. Tracked by GitHub issue #94. EXP-20261006-033 holds the pinned
answer-key subset (`overruling`, `definition_classification`,
`citation_prediction_classification`) built from LegalBench revision
`daec8237410aa23e3faf4bc41ad8b3a7e1696826`. The blind partition is not scored.

## Objective

Widen the legal objective axis beyond the single LegalBench Hearsay task
(EXP-028, unchanged) with a small, answer-key subset so a legal result rests on
more than one task family. No non-objective gold is introduced.

## Scope

- Add `canonicalize_subtask_rows` plus `case_split`/`assign_case_splits` to
  `src/eval_lab/datasets/legalbench.py` (Hearsay canonicalizer untouched).
- Add a build script that freezes the pinned source and emits the canonical
  dataset, split manifest, pool rows, and typed-question spec.
- Add a gold-only public report stating each task's majority-label baseline.
- Add an offline test suite on inline fixtures.

## Gold and safety rules

- Gold is the pinned LegalBench answer key (`GoldProvenance.ANSWER_KEY`) with a
  per-task verifier id; no model judgment is promoted to gold.
- The split unit is the case (normalized text); no case crosses the boundary.
- No model-authored or consensus labels; no CourtListener/opinion-text work.

## Acceptance

1. `canonicalize_subtask_rows(rows, *, task, split, prompt_template)` validates
   the per-task header and fails closed on a mismatch. — done
2. A new experiment ID holds the subset with a committed source manifest pinning
   the revision, license, and per-task row counts. — done (EXP-20261006-033)
3. Splits are case-disjoint on `source_problem_id`. — done
4. Gold stays `GoldProvenance.ANSWER_KEY` with a per-task verifier id. — done
5. `tests/test_legalbench_subset.py` runs offline and asserts header validation,
   split disjointness, and label coverage. — done (23 passed)
6. The public report states each task's majority-label baseline. — done

## Goal

Extend the legal objective track beyond Hearsay with a small answer-key subset,
reusing the shared comparison runner and preserving the objective-gold rule.

## Acceptance criteria

The Acceptance items above are the acceptance criteria for this checkpoint.

## Checkpoint log

### 2026-10-06 — EXP-033 LegalBench answer-key subset frozen

Status: frozen; no model scored.

Completed work: extended `src/eval_lab/datasets/legalbench.py` with the
`SUBTASK_SPECS` registry, `case_split`, `assign_case_splits`,
`canonicalize_subtask_rows`, and the `majority_baseline` helper; added
`scripts/build_legalbench_subset.py` (freeze + build) and
`scripts/report_legalbench_subset.py`; added `tests/test_legalbench_subset.py`
(23 tests); created `experiments/EXP-20261006-033-legalbench-answer-key-subset/`
with `source-manifest.json`, `source/`, `canonical-records.jsonl`,
`records.jsonl`, `split-manifest.json`, `typed-question-spec.json`,
`pool-manifest.json`, `pool-checksums.sha256`, `report.md`, `experiment.yaml`,
and `README.md`. Also pinned `experiments/EXP-20261006-033-legalbench-answer-key-subset/**`
to `text eol=lf` in `.gitattributes`.

Exact files changed: `src/eval_lab/datasets/legalbench.py`,
`scripts/build_legalbench_subset.py`, `scripts/report_legalbench_subset.py`,
`tests/test_legalbench_subset.py`, `.gitattributes`,
`experiments/EXP-20261006-033-legalbench-answer-key-subset/`, this task file,
and `checkpoints/CURRENT.md`.

Commands run: `scripts/build_legalbench_subset.py --freeze`;
`scripts/build_legalbench_subset.py`; `scripts/report_legalbench_subset.py`;
`pytest tests/test_legalbench_subset.py`; ruff check/format; mypy; the full
local gate set.

Test results: `tests/test_legalbench_subset.py` 23 passed. Build emitted 3839
records (overruling 2394, definition_classification 1337,
citation_prediction_classification 108) over 3786 cases; every `source_problem_id`
maps to one split; all gold is `answer_key`. Canonical fingerprint
`sha256:e756b17bbbe301d53f43ab3cd0e3bea72812b6c30db354698a1a545d636cb3d7`.

Decisions made: the split unit is the normalized text (case), because
`citation_prediction_classification` repeats the same text with opposite answers;
gold stays native `Yes`/`No` and the `label_set ["Yes","No"]` contract is
recorded in `typed-question-spec.json` for the future typed-spec scoring path
(the shared single-mode default is `pass`/`fail`, asserted by a canary test);
`definition_classification` is CC BY-SA 4.0 (the other two CC BY 4.0), and the
generated artifacts carry the same per-task licenses; the pinned source has one
fewer test row than the task page reports for `definition_classification`,
preserved as distributed with no fabricated record. The dataset fingerprint is a
raw-byte SHA-256, so the whole experiment tree is pinned `eol=lf` in
`.gitattributes` and every artifact is written with `newline="\n"`; otherwise the
pinned hash would only verify on a CRLF checkout and the committed bytes would
diverge between Windows and Linux.

Unresolved questions: the blind partition is unscored; the typed-spec scoring
path for `Yes`/`No` is documented, not built (a non-goal of this task).

## Handoff

Score the public selection through the typed-spec path with `label_set
["Yes","No"]`, then the blind holdout, gated by the EXP-033 stopping rule. Do
not score a blind split before the manifest, dataset, split, and fingerprints
are committed. The shared single-mode runner defaults to `pass`/`fail`; use a
`Yes`/`No` label set or it will mis-score these records.
