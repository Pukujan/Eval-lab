# TASK-0004 — Metrics, Calibration, and Selective Risk

- Status: ready-for-review
- Owner: Codex/local agent
- Priority: P0
- GitHub issue: #8
- Depends on: TASK-0002; TASK-0003 implementation preferred but live provider success not required
- Branch: task/TASK-0004-metrics-calibration

## Goal

Implement statistically correct evaluation, calibration, reliability, and selective-risk analysis over frozen JudgePrediction records.

## Why

Raw accuracy is insufficient. The project requires confidence that means something and a principled way to escalate uncertain cases.

## Inputs

- canonical JudgePrediction/GoldLabel
- synthetic predictions for known-value tests
- Jev predictions when available
- `docs/SDD.md` section 8
- `docs/TDD.md` section 7

## Outputs

- classification metrics
- calibration metrics
- temperature scaling
- binary Platt/logistic scaling
- optional isotonic calibration
- CalibrationArtifact schema/serialization
- risk/coverage utilities
- report generator for aggregate/per-domain results
- tests

## Required implementation

Metrics:
- accuracy
- balanced accuracy
- macro F1
- multiclass Brier
- NLL
- ECE with documented binning
- swap consistency
- risk/coverage
- coverage at target error thresholds
- latency summaries

Calibration:
- fit only on split=calibration
- reject test labels during fit
- scalar temperature for multiclass vectors/scores
- binary Platt/logistic support
- isotonic optional but tested if implemented
- apply fitted artifact to dev/test without refitting

## Allowed files

- `src/eval_lab/calibration/`
- `src/eval_lab/metrics/`
- `src/eval_lab/reporting/`
- schema extensions only for CalibrationArtifact if required
- `tests/`
- this task file
- `checkpoints/CURRENT.md`

## Acceptance criteria

- [x] all required metrics implemented
- [x] known-value tests pass
- [x] fit rejects test split
- [x] calibration artifacts serialize/reload
- [x] calibrated probabilities valid
- [x] risk/coverage reproducible
- [x] per-domain and aggregate report generated from fixture predictions
- [x] unavailable probability metrics handled explicitly
- [x] full local merge gate passes

## Validation

See `docs/TDD.md` section 7.

## Stop conditions

Stop if:
- test labels are needed to select calibration parameters/thresholds;
- metric implementation silently drops provider failures from reliability counts;
- class ordering differs between prediction and calibration artifacts.

## Checkpoint log

Append execution evidence here.

### 2026-09-20 — Codex/local agent

Started from accepted `main` merge commit `a5cfc7982b5babd8dac73ba775276d95db0fd9e8` in dedicated worktree `D:\claude\eval-lab-TASK-0004` on branch `task/TASK-0004-metrics-calibration`.

Read, in order: `PROJECT.md`, `AGENTS.md`, `checkpoints/CURRENT.md`, this task file, SDD section 8, and TDD section 7.

Completed:
- accepted TASK-0003 PR #17 into `main` before creating this worktree;
- established the task-specific branch/worktree boundary;
- no TASK-0004 implementation files changed yet.

Commands and results:
- `git worktree add D:\\claude\\eval-lab-TASK-0004 -b task/TASK-0004-metrics-calibration main` -> created at the accepted `main` head;
- `git status --short --branch` -> clean `task/TASK-0004-metrics-calibration`.

Decision: keep calibration fit inputs explicitly split-aware, preserve provider failures in reliability summaries, and never refit or consume test labels during calibration.

Next atomic action: implement known-value classification metrics and split-safe CalibrationArtifact primitives.

### 2026-09-20 — TASK-0004 local validation

Environment:
- Windows PowerShell on local machine, Python `3.12.10`.
- Dedicated worktree `D:\claude\eval-lab-TASK-0004`, branch `task/TASK-0004-metrics-calibration`.
- Dedicated `.venv` with the project installed editable and the development test tools available.
- No credential file, API key, `.env`, or live provider call was used for TASK-0004.

Implemented files:
- `src/eval_lab/metrics/__init__.py`, `classification.py`, `latency.py`, `risk.py`, `summary.py`.
- `src/eval_lab/calibration/__init__.py`, `artifact.py`, `temperature.py`.
- `src/eval_lab/reporting/__init__.py`, `report.py`.
- `tests/test_metrics.py`, `tests/test_calibration.py`, `tests/test_reporting.py`.
- Updated this task log and `checkpoints/CURRENT.md`.

Commands and exact results:
- `& .venv\\Scripts\\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `& .venv\\Scripts\\ruff.exe check .` -> `All checks passed!`.
- `& .venv\\Scripts\\python.exe -m pytest -q` -> `47 passed in 0.78s`.

Coverage includes hand-computed classification/Brier/NLL/ECE values, deterministic risk/coverage and latency, scalar temperature calibration, binary Platt calibration, artifact JSON round-trip, bounded calibrated probabilities, explicit test-split rejection, provider-failure retention, aggregate/per-domain reporting, and explicit unavailable probability metrics. Calibration accepts only `split=calibration` canonical inputs and records the class order and input semantics in the artifact.

Decisions:
- Keep record domains as an explicit `domain_by_record_id` report input because `JudgeRecord` is provider-neutral and does not contain a domain field.
- Preserve status counts and failed predictions in reports while excluding unsuccessful rows from label metrics.
- Use deterministic pure-Python optimization for scalar temperature and binary logistic parameters; isotonic calibration remains optional and is not included.

Blockers: none. The known GitHub Actions no-runner condition remains external infrastructure and does not change the passing local gate.

Next atomic action: commit the validated TASK-0004 implementation, push `task/TASK-0004-metrics-calibration`, open the review PR, and update this log with its URL before merge.

## Handoff

TASK-0005 uses these metrics and calibration artifacts on a real public dataset.
