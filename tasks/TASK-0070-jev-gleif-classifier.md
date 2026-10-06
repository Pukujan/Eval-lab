# TASK-0070 — Jev as a closed-set GLEIF classifier

## Status

Active — tracked by GitHub issue #95. EXP-032 is preregistered. Work is serialized
behind TASK-0069 (issue #94, sibling session) in the single canonical checkout;
this task starts once that PR merges. No blind split has been scored.

Renumbered from an initial TASK-0069 label because issue #94 and issue #95 were
both filed as TASK-0069; first-filed #94 keeps TASK-0069 and this task is #95.

## Objective

Measure Jev 1.13 as a multi-class closed-set classifier, not only a binary claim
verifier. Score a multi-class, objective, entity-disjoint GLEIF dataset blind at
>=1000 items so accuracy, coverage, and calibration are not noise, and emit a
generated static viewer so the per-item records and aggregate charts are
viewable.

## Scope

- Generalize the typed-decision spec to an arbitrary closed label set with
  per-label criteria, backward-compatibly (existing binary behavior unchanged).
- Build the classifier dataset from the frozen 2026-09-24 GLEIF snapshot:
  entity category (6-class, primary), registration status (7-class), legal
  jurisdiction (top-N + OTHER), on an entity-disjoint split.
- Run `typesafe/jev-1.13` through the authorized Decisions route; >=1000 blind
  items; provider failures remain execution statuses.
- Report per-family accuracy, balanced accuracy, macro-F1, coverage,
  valid-label rate, Brier, NLL, ECE, and risk/coverage against a majority-class
  baseline.
- Emit `research-chart-data.v1` and generate a static viewer with
  `app-builder-automation`; commit only built static assets and JSON.

## Gold and safety rules

- Gold is only the frozen GLEIF source field value (`deterministic_verifier`);
  no legal, financial, or investment interpretation is promoted to gold.
- Model judgments are never promoted to gold.
- Entity-disjoint split is mandatory; no LEI appears on both sides.
- No credentials, tokens, or secrets are committed or printed.
- No `node_modules` or Node package in the Eval Lab checkout.
- EXP-026 artifacts are not modified.

## Acceptance

1. EXP-032 is preregistered (task file + experiment.yaml + this issue) before any
   blind scoring.
2. >=1000 blind items scored with >=95% non-error execution status; provider
   failures remain execution statuses, never labels.
3. Per-family accuracy, balanced accuracy, macro-F1, coverage, Brier, NLL, ECE,
   and risk/coverage reported, each against the majority baseline.
4. The blind split is entity-disjoint from the public split (no LEI on both
   sides).
5. A viewer renders all >=1000 records as a table plus >=4 aggregate charts,
   built from `research-chart-data.v1`, with no `node_modules` committed.
6. EXP-026 artifacts are unchanged.

## Files in scope

- `tasks/TASK-0070-jev-gleif-classifier.md`
- `checkpoints/CURRENT.md`
- `src/eval_lab/escalation/spec.py`
- `src/eval_lab/escalation/providers.py`
- `src/eval_lab/datasets/gleif.py`
- `scripts/build_gleif_classifier_dataset.py`
- `scripts/run_gleif_classifier_jev.py`
- `scripts/report_gleif_classifier.py`
- `scripts/export_chart_data.py`
- `experiments/EXP-20261005-032-gleif-classifier/`
- `tests/test_gleif_classifier.py`
- `site/gleif-classifier/` (built static assets only)

## Goal

Answer the practical classifier question the program cannot currently answer —
how accurate and how well-calibrated is Jev across a closed label set, and at
what coverage — using objective GLEIF gold, and make the >=1000 records and
aggregate charts viewable.

## Acceptance criteria

The Objective, Scope, Gold and safety rules, and Acceptance sections above are
the acceptance criteria for this task.

## Checkpoint log

### 2026-10-05 — preregistration

Status: EXP-032 preregistered; no blind split scored. Preregistration artifacts
(task file, `experiment.yaml`, `README.md`) are prepared. Implementation is
serialized behind TASK-0069 (issue #94) in the single canonical checkout.

Next atomic action: after TASK-0069 merges, create
`task/TASK-0070-jev-gleif-classifier`, commit the preregistration, then
generalize the spec and build the classifier dataset.

## Handoff

Do not score the blind split until the preregistration, classifier dataset,
split manifest, and fingerprints are committed. A changed dataset, label set,
prompt, or split needs a new experiment ID. Run the smallest end-to-end slice
(one family, `--limit 20` blind) before scaling to three families at >=1000.
