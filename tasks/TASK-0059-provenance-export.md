# TASK-0059 — Provenance-aware chart data export

## Status

Complete pending PR/CI/merge. Tracked by GitHub issue #69. Research and audit
are in the issue's first comment.

## Goal

Every paper chart gets machine-generated chart data with honest, checkable
provenance, which the Design Bakery interactive chart component
(design-bakery #49, TASK-DB-0054) consumes. Also fix stale provenance and
document what provenance is actually used.

## Scope

- `scripts/export_chart_data.py` (new)
- `paper/data/` (new): `judges-blind-760.json`, `charts/*.json`, `index.json`,
  `sources/arm-metadata.yaml`
- `schemas/research-chart-data.v1.schema.json`,
  `schemas/chart-provenance.shapes.ttl` (new)
- `tests/test_chart_data_export.py` (new)
- `.github/workflows/ci.yml`: `pytest tests`, export `--check`, archived v0.1.0
  validator
- `pyproject.toml`, `uv.lock`: `jsonschema` added to the dev extra
- `experiments/EXP-20260924-029-consolidated-judge-analysis/experiment.yaml`:
  `code_commit` corrected; `results_sha256` added
- `docs/PROVENANCE.md` (new), `docs/RESEARCH_ARTIFACT_STANDARD.md`,
  `docs/VALIDATION_MATRIX.md`, `paper/paper.md` (Appendix F paragraph),
  `paper/README.md`, `paper/reproducibility.md`
- `tasks/TASK-0059-provenance-export.md`, `checkpoints/CURRENT.md`

## Decisions

- Schema follows the design-bakery #49 chart research. It has `schemaVersion`,
  provenance, dimensions, measures (label, format, better, interval, definition),
  entities (shortLabel, headline, structured settings) and observations
  (entity, slice, metric, value, ciLow, ciHigh, n).
- `headline` means the arms plotted in the paper's first body figure
  (`finding_accuracy_range`). It's derived, not curated by hand.
- Thinking, token caps, decision method and temperature are structured in
  `arm-metadata.yaml` with evidence paths. Tests check them against the harness
  text and the recorded `provider_metadata`.
- No per-record file. The 760 records are a blind holdout, so the finest level
  is one row per arm/run. Tests check that no record ID or gold key appears.
- No cross-arm aggregates (paper pooling policy). `aggregates` is empty.
- Exports are JSON-LD, with a `provenance` `@nest` holding PROV-O
  `wasGeneratedBy` / `wasDerivedFrom`. Git time is the commit time, so output is
  deterministic.
- The archived v0.1.0 validator is kept and run in CI rather than retired,
  because it is cheap and still passes. Its release is frozen and documented as
  archived-only.
- The figure manifest was already current after TASK-0058. A test now guards
  it. The generator's commit is recorded in the chart files rather than by
  changing the figure script.

## Acceptance criteria

- Exports are regenerated from a clean tree and re-render byte-identically.
- JSON Schema and SHACL pass. Negative tests fail as expected.
- `uv run --locked python -m pytest tests -q` passes. CI is green. The PR is
  squash-merged with "Closes #69".

## Checkpoint log

### 2026-09-24 — build

Status: complete pending PR/CI/merge.

Commands run (authoring clone on the research box, Linux):

- `uv lock`, `uv lock --check`, `uv sync --locked --extra dev --extra figures`
- `uv run --locked python scripts/export_chart_data.py` (clean tree)
- `uv run --locked ruff check .`, `ruff format --check` (changed files),
  `mypy src/eval_lab`, `python -m pytest tests -q`,
  `scripts/export_chart_data.py --check`,
  `scripts/validate_research_artifacts.py`, `check_repo_contract.py`

## Handoff

design-bakery #49 syncs the files in `paper/data/index.json` from a pinned
Eval Lab commit and checks their SHA-256.

## Next atomic action

After merge, confirm #69 closed and post the consumed-file list on #69 and
design-bakery #49.
