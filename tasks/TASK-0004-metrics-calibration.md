# TASK-0004 — Metrics, Calibration, and Selective Risk

- Status: queued
- Owner: Luna/local agent
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

- [ ] all required metrics implemented
- [ ] known-value tests pass
- [ ] fit rejects test split
- [ ] calibration artifacts serialize/reload
- [ ] calibrated probabilities valid
- [ ] risk/coverage reproducible
- [ ] per-domain and aggregate report generated from fixture predictions
- [ ] unavailable probability metrics handled explicitly
- [ ] full local merge gate passes

## Validation

See `docs/TDD.md` section 7.

## Stop conditions

Stop if:
- test labels are needed to select calibration parameters/thresholds;
- metric implementation silently drops provider failures from reliability counts;
- class ordering differs between prediction and calibration artifacts.

## Checkpoint log

Append execution evidence here.

## Handoff

TASK-0005 uses these metrics and calibration artifacts on a real public dataset.
