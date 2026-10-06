# TASK-0070 — Jev as a closed-set GLEIF classifier

## Status

Active — tracked by GitHub issue #95. EXP-032 is complete and scored: the blind
split is 2142 items (714 per family), all resolved, chart exports and run
telemetry regenerated, and the static viewer is built and committed at
`site/gleif-classifier/`. All acceptance criteria are met; this checkpoint
finalizes the task.

Renumbered from an initial TASK-0069 label because issue #94 and issue #95 were
both filed as TASK-0069; first-filed #94 (LegalBench, sibling session) keeps
TASK-0069 and this task is #95.

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
- `scripts/build_classifier_viewer_data.py`
- `experiments/EXP-20261005-032-gleif-classifier/`
- `tests/test_gleif_classifier.py`
- `tests/test_chart_data_export.py`
- `paper/data/gleif-classifier.json`, `paper/data/classifier-charts/`, `paper/data/index.json` (generated)
- `telemetry/runs.v1.jsonl`, `telemetry/FINDINGS.md` (regenerated)
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

### 2026-10-06 — viewer built and committed; task complete

Status: all acceptance criteria met.

Completed work:

- Built the static viewer with `app-builder-automation` from
  `classifier-viewer-spec.md`, whose DATA ACCESS section is authoritative and
  replaces the generic `/api/views/*` guidance with six static JSON files.
  Generation ran on the verified model `ih/cx/gpt-5.6-luna` with `--strict`
  (identity self-check passed); the run reported `PASSED`.
- Injected the viewer data (items.json 2142 records, dataset.json, 6 chart
  files) and built with Vite.
- Verified the build in a real browser (Playwright, desktop 1440px + mobile
  390px, deviceScaleFactor 2): zero console/page errors, 6 recharts charts, 6
  summary tiles, 50 table rows, 80 SVGs, and all nine required `data-testid`
  hooks present.
- **Found and fixed three real chart bugs that typecheck, lint and a route
  crawler all passed over** (screenshot review with vision caught them):
  1. `MiniChart` emitted one `<Bar>` per family over the *unsplit* flat data
     array, so every family's series was plotted against every other family's
     rows. Target-error coverage rendered 9 x-slots instead of 3 with
     coincidentally identical bar heights; the confidence histogram collapsed
     into stacked triplets; and the label-performance chart rendered a 300%
     axis with overlapping rotated labels and a 6-entry legend.
  2. Replaced the family-loop bar construction with an explicit pivot by
     x-value (one row per x, one key per family, `null` where absent).
  3. Gave label performance its own composed chart (support bars on a left
     axis, recall lines on a right axis) instead of overloading one
     `MiniChart` with a `second` series.
  Also made series colours stable under filtering via `colorFor(family)`
  indexed against the full family list, so a family keeps its colour when the
  filter changes which families are active.
- Made the bundle subpath-safe: `base: "./"`, relative `data/...` fetch paths,
  the real page title, and removed the `BrowserRouter`/`NotFound` catch-all so
  no deep link can render an empty "page not found".
- Copied **only** built static assets and JSON into `site/gleif-classifier/`
  (12 files, 3.2 MB). No `node_modules`, `package.json`, or lockfile entered
  the checkout.
- Re-verified by serving the committed `site/gleif-classifier/` itself over
  HTTP and re-shooting both viewports.

Files changed: `site/gleif-classifier/**` (new, built assets only),
`paper/data/gleif-classifier.json` and `paper/data/classifier-charts/**` (new
exports), `paper/data/index.json` (regenerated index), the eight unrelated
`paper/data/*.json` files (regenerated provenance — commit/timestamp/hash —
plus one genuine mojibake fix, see decisions), `tasks/TASK-0070-*.md`,
`checkpoints/CURRENT.md`.

Commands run: `npx tsc -b`, `npx vite build`, `node eval/out/shoot-viewer.mjs`,
`node eval/out/interact-viewer.mjs`, `scripts/check_workspace_policy.py`,
`scripts/check_repo_contract.py`, `scripts/export_chart_data.py --check`,
`scripts/run_telemetry.py --check`, `pytest tests -q`.

Test results: 241 passed. Workspace policy OK. Repository contract OK. Export
chart data `--check` exit 0. Run telemetry current (159 records). Browser
verification: 0 errors, all hooks present, both viewports.

Decisions made:

- The viewer is served as static assets from a subpath, so the bundle uses
  relative asset and data paths. This also makes the app render at
  `site/gleif-classifier/` without a server rewrite.
- The eight unrelated `paper/data/*.json` files are included in this
  checkpoint. Their diffs are regenerated provenance only (commit, timestamp,
  `sha256` of the exporter, `generatedAt`); the `data` payloads are
  byte-identical except `local_qwen_calibration.json`, whose subtitle changed
  from `44.61% before and after) Â·` to `… ) ·`. That is a real mojibake fix
  (the double-encoded `Â·` becomes the correct `·`), and it is an improvement
  rather than a regression. EXP-026 artifacts (`experiments/EXP-20260922-026-*`)
  are untouched — `git status` on `experiments/` is clean.
- Per-record gold labels are committed in `site/gleif-classifier/data/items.json`
  because acceptance criterion 5 requires all >=1000 records viewable. The
  repo's chart-data v1 export stays aggregate-only and blind-safe; this is a
  separate, task-authorized deliverable.

Unresolved questions: none.

Next atomic action: publish this checkpoint for issue #95, then finalize it
(confirm the merge, audit tracked/untracked/ignored state, fast-forward the
canonical checkout to `origin/main`).

## Handoff

Do not score the blind split until the preregistration, classifier dataset,
split manifest, and fingerprints are committed. A changed dataset, label set,
prompt, or split needs a new experiment ID. Run the smallest end-to-end slice
(one family, `--limit 20` blind) before scaling to three families at >=1000.
