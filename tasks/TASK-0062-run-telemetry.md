# TASK-0062: Run telemetry ledger and compute findings for every eval run

GitHub issue #78 — [#78](https://github.com/Pukujan/Eval-lab/issues/78)

## Goal

Give every eval run a single, uniform, reproducible row of telemetry, and compute
repository-wide findings from those rows.

Eval runs are written in at least five different directory conventions
(`EXP/results.json`, `EXP/<child>/results.json`, `EXP/runs/<id>/results.json`,
`EXP/runs/<group>/<arm>/results.json`, `EXP/diagnostics/<id>/results.json`) and
their `results.json` files expose wildly different top-level keys. There is no
single place that answers "what runs exist, which are missing results, and which
fields are actually populated". This task adds that place:

- a committed, append-only-in-spirit JSONL **ledger** with one record per run unit;
- a **JSON Schema** pinning the record shape;
- a deterministic **builder + CLI** that regenerates the ledger and the findings
  from committed artifacts only (offline, no model/provider calls, no hand-typed
  numbers);
- a generated **FINDINGS** document computed from the ledger;
- a CI `--check` step so the committed ledger cannot drift from the artifacts.

Per the issue's scope note, the schema, ledger, CLI, tests/CI, FINDINGS, seeding
and AGENTS.md items are the deliverables; the Colab CLI guide
(`docs/compute/colab-cli.md`) already landed in PR #79.

## Inputs

- `experiments/EXP-*/**/results.json` (committed run artifacts) — read-only.
- `docs/EXPERIMENT_PROTOCOL.md`, `docs/PROVENANCE.md` — conventions.
- `schemas/research-chart-data.v1.schema.json` — precedent for a checked-in
  derived artifact plus a `--check` CLI.

## Outputs / files changed

New:

- `src/eval_lab/telemetry.py` — typed derivation (`build_records`), canonical
  field resolution, deterministic JSONL serialization, findings computation.
- `scripts/run_telemetry.py` — CLI: `rebuild`, `verify`, `findings`, `--check`.
- `schemas/run-telemetry.v1.schema.json` — Draft 2020-12 record schema.
- `telemetry/runs.v1.jsonl` — the seeded, committed ledger.
- `telemetry/FINDINGS.md` — generated findings, computed from the ledger.
- `telemetry/README.md` — what the ledger is, how to regenerate it.
- `tests/test_run_telemetry.py` — unit tests for the builder, resolution,
  determinism, and committed-artifact currency.
- `tasks/TASK-0062-run-telemetry.md` — this file.

Changed:

- `.github/workflows/ci.yml` — one `run_telemetry.py --check` step in the
  `quality` job.
- `AGENTS.md` — a managed block recording the run-telemetry ledger rule.

## Acceptance criteria

- [ ] `build_records(root)` returns one record per run unit, keyed uniquely by
      repo-relative POSIX `run_path`, covering all five directory conventions.
- [ ] Run directories without `results.json` are represented honestly:
      `completeness` is `partial` (or `quarantined` when the directory name marks
      a paused/abandoned run), never silently dropped.
- [ ] Nullable metrics are never coerced to `0`; floats are copied verbatim;
      `accuracy` is resolved only from documented canonical locations, else `null`
      with an `accuracy_source` of `null`.
- [ ] The ledger is byte-deterministic: regenerating it twice yields identical
      bytes; it contains no generated timestamp.
- [ ] `scripts/run_telemetry.py --check` fails when the committed ledger or
      FINDINGS are stale, and passes when current; it is wired into CI.
- [ ] `telemetry/runs.v1.jsonl` validates against
      `schemas/run-telemetry.v1.schema.json`.
- [ ] `telemetry/FINDINGS.md` is computed from the ledger (no hand-typed numbers)
      and states coverage honestly.
- [ ] `check_repo_contract.py`, `check_workspace_policy.py`, `ruff`, `mypy`, and
      `pytest` all pass.

## Decisions

- **Unique key is `run_path`, not `(experiment_id, run_id)`.** EXP-025 reuses
  `run_id` across its groups, so the tuple is not unique; the directory path is.
- **Deterministic rebuild, not append.** A committed JSONL that only ever
  appends would drift from the artifacts and could not be `--check`ed. `rebuild`
  writes the full ledger from `build_records(root)` sorted by `run_path`; the
  file is committed and CI-verified.
- **No compute/Colab fields.** Compute telemetry (accelerator, t/s, VRAM) lives
  in the Colab CLI guide and is explicitly out of scope for the ledger.
- **Accuracy is resolved conservatively** from `metrics.accuracy`,
  `aggregate.metrics.accuracy`, top-level `accuracy`, or a documented
  `correct_count / resolved_count` derivation; arms/partitions files keep
  `accuracy: null` (per-arm accuracy is captured structurally, not flattened).
- **Container directories are not rows.** EXP-025 group directories hold nested
  arm runs; the nested rows already carry the group in their `run_path`, so the
  bare container is not emitted.

## Checkpoint log

### 2026-10-05 — task opened, design fixed

- Enumerated all 140 `results.json` under `experiments/` and grouped them by
  directory convention; found 10 run directories without `results.json`
  (9 predictions-only, 1 paused) and 2 EXP-025 container directories.
- Fixed the record shape, canonical field-resolution order, completeness kinds,
  and the unique key. Advisor review confirmed the plan and flagged
  cross-platform byte determinism (POSIX paths, LF, stable sort) as the main
  risk to address.
- Files changed: `tasks/TASK-0062-run-telemetry.md` (this file).

### 2026-10-05 — implemented, generated, and verified

- Added `src/eval_lab/telemetry.py` (derivation + findings), `scripts/run_telemetry.py`
  (rebuild/findings/verify/--check), `schemas/run-telemetry.v1.schema.json`,
  `telemetry/{runs.v1.jsonl,FINDINGS.md,README.md}`, `tests/test_run_telemetry.py`,
  one CI step, and the AGENTS.md "Run telemetry rule" block.
- Generated ledger: **150 records** (140 with results, 10 without), all five
  directory conventions represented; 16 rows carry a resolved accuracy.
- Commands run:
  - `python scripts/run_telemetry.py rebuild` → 150 records, schema valid, keys unique
  - `python scripts/run_telemetry.py --check` → current (and exit 1 when a byte is
    appended to the ledger, then 0 after restore)
  - `ruff check` + `ruff format --check` → clean; `mypy src/eval_lab` → clean
  - `python scripts/check_repo_contract.py` → OK
  - `python scripts/check_workspace_policy.py --canonical-root D:\development\eval-lab` → OK
  - `python -m pytest tests -q` → **201 passed** (was 186; +15 new)
- Determinism confirmed: two consecutive rebuilds produce byte-identical ledger
  and findings.
- Files changed: the ten files listed under Outputs.

### 2026-10-05 — CI caught a cross-platform hash bug; fixed

- PR #79 CI failed `test_committed_ledger_is_current`: every `results_sha256`
  differed. Root cause: git checks `results.json` out with CRLF on a Windows
  checkout but LF on Linux, and the first version hashed raw working-tree bytes,
  so the ledger was platform-dependent.
- Fix: `sha256_file` now hashes LF-normalized content (equal to the committed
  blob hash), and both `run_telemetry.py --check` and the currency test compare
  text with CRLF normalized to LF. Added
  `test_sha256_file_is_line_ending_insensitive`.
- Regenerated the ledger; verified a record's `results_sha256` equals
  `git cat-file -p HEAD:<path> | sha256`. Commands: `run_telemetry.py rebuild`,
  `--check` (current), `ruff check`/`format --check` clean, `mypy` clean,
  `pytest tests -q` → **202 passed**.

## Handoff

Next atomic action: publish the checkpoint (commit + PR for issue #78) via
`scripts/publish_checkpoint.py` with the ten explicit paths, then let CI confirm
`run_telemetry.py --check` in the quality job. No unresolved questions.
