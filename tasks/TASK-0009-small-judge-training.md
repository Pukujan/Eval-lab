# TASK-0009 — Small Judge Training and Calibration Pilot

- Status: queued
- Owner: Luna/local agent
- Priority: P0
- GitHub issue: #14
- Depends on: TASK-0008
- Branch: task/TASK-0009-small-judge-training

## Goal

Train and calibrate the first lightweight rubric judge using objective supervision plus controlled teacher-assisted augmentation.

## Inputs

- verified TASK-0008 corpus
- TASK-0004 calibration/metrics
- local feasibility evidence from TASK-0006

## Outputs

- selected student and rationale
- reproducible training-arm configurations and fingerprints
- ablation table with objective and calibration metrics
- calibrated best artifact/configuration with retained provenance

## Student selection

Eligible:
- Qwen3-0.6B
- Qwen3-1.7B
- compact encoder classifier such as ModernBERT

Qwen3-4B is not required.

## Training arms

A. objective labels only

B. objective labels + concise teacher criterion critiques

C. objective labels + verified teacher hard negatives

D. objective labels + critiques + verified hard negatives

E. best arm + post-hoc calibration

## Splits

Source families separated across train/dev/calibration/test. Reserve untouched OOD/meta-evaluation data.

## Metrics

- verdict accuracy/balanced accuracy
- macro F1
- Brier
- NLL
- ECE
- swap consistency
- risk/coverage
- coverage at <=1%, <=2%, <=5% observed error
- latency/memory

## Acceptance criteria

- [ ] student rationale documented
- [ ] arms A-D run or infeasibility justified
- [ ] training records fingerprinted
- [ ] teacher provenance retained
- [ ] calibration uses calibration split only
- [ ] test/OOD remain frozen until final evaluation
- [ ] ablation table produced
- [ ] calibrated best artifact/config reproducible
- [ ] full local merge gate passes

## Validation

Prove no source-family leakage and no test-label use during fitting/calibration.

## Stop conditions

Stop if training cannot fit resources, data leakage is detected, or teacher examples cannot be traced to objective verification.

## Checkpoint log

Append evidence here.

## Handoff

Use the final ablation to define the next research task.
