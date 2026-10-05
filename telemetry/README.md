# Run telemetry

One uniform row of telemetry for every eval run, so the whole lab can be
queried and audited in one place.

- `runs.v1.jsonl` — the ledger: one record per run unit, keyed uniquely by
  repo-relative `run_path`. Generated; do not edit by hand.
- `FINDINGS.md` — repository-wide findings computed from the ledger. Generated;
  do not edit by hand.

Both files are derived from the committed artifacts under `experiments/` by
`scripts/run_telemetry.py`, which reads no network and hand-types no numbers.
The record shape is pinned by `schemas/run-telemetry.v1.schema.json`.

## Regenerate

```bash
uv run --locked python scripts/run_telemetry.py rebuild     # write both files
uv run --locked python scripts/run_telemetry.py verify      # schema + invariants
uv run --locked python scripts/run_telemetry.py --check     # fail if stale (CI)
```

CI runs `--check`, so a run artifact change that is not reflected in the ledger
fails the build.

## What a record covers

Eval runs use five directory conventions, all represented:

| convention | `scope` | example |
| --- | --- | --- |
| `EXP/results.json` | `experiment` | experiment-level aggregate |
| `EXP/<child>/results.json` | `child_run` | run output at the experiment root |
| `EXP/runs/<id>/results.json` | `run` | the canonical run |
| `EXP/runs/<group>/<arm>/results.json` | `nested_run` | EXP-025 arm ablation |
| `EXP/diagnostics/<id>/results.json` | `diagnostic` | a diagnostic probe |

Run directories without a `results.json` are still recorded: `completeness` is
`partial` (predictions only) or `quarantined` (paused/abandoned, or a
`results.json` that does not parse). Nullable fields stay `null`; a metric is
never coerced to `0`.

## Out of scope

Compute telemetry — accelerator, tokens/s, peak VRAM, llama.cpp build, flags —
is not part of the ledger. It lives in `docs/compute/colab-cli.md`.
