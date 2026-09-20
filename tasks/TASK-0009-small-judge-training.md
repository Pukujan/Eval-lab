# TASK-0009 — Small Judge Training and Calibration Pilot

- Status: in-progress
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

### 2026-09-20 — TASK-0009 start and scope freeze

Created dedicated worktree `D:/claude/eval-lab-TASK-0009` on branch `task/TASK-0009-small-judge-training` from merged TASK-0008 main commit `bce665e8601686a860d14c4ed5671b33afa660ef`. Read `PROJECT.md`, `AGENTS.md`, `checkpoints/CURRENT.md`, this task file, and `docs/TDD.md` plus `docs/EXPERIMENT_PROTOCOL.md`.

Selected student scope: a deterministic compact text classifier (`TF-IDF + logistic regression`) for a bounded single-answer correctness pilot. This is the smallest reproducible classifier that can be trained on the available 33 objective train records plus verified TASK-0008 hard negatives without downloading or committing transformer weights. Pairwise judging remains outside this pilot and is reported as not applicable.

Planned files: `src/eval_lab/training.py`, `scripts/run_small_judge_training.py`, `tests/test_training.py`, `experiments/EXP-20260920-008-small-judge-training/`, this task log, and `checkpoints/CURRENT.md`. The runner will execute arms A-D, select by dev NLL/accuracy only, fit arm E calibration on the calibration split, and evaluate the frozen test split only after pre-registration.

Environment observed: Windows PowerShell; Python `3.12.10`; Git `2.51.2.windows.1`; Node `v24.14.1`; OpenCode CLI `1.18.31`. No credentials are printed or stored in repository artifacts.

Next atomic action: implement the serializable student, leakage-safe arm builder, metrics/prediction runner, and unit tests; then commit the EXP-008 pre-registration before running the final test split.

## Handoff

Use the final ablation to define the next research task.
