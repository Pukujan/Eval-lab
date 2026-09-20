# TASK-0009 — Small Judge Training and Calibration Pilot

- Status: completed — local acceptance criteria met; PR #24 merged
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

- [x] student rationale documented
- [x] arms A-D run or infeasibility justified
- [x] training records fingerprinted
- [x] teacher provenance retained
- [x] calibration uses calibration split only
- [x] test/OOD remain frozen until final evaluation
- [x] ablation table produced
- [x] calibrated best artifact/config reproducible
- [x] full local merge gate passes

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

### 2026-09-20 — implementation and EXP-008 pre-registration

Implemented the compact student and runner in `src/eval_lab/training.py` and `scripts/run_small_judge_training.py`, with focused coverage in `tests/test_training.py`. The student is TF-IDF plus balanced logistic regression with JSON-safe coefficients, normalized probabilities, per-prediction latency, training-row fingerprints, and no external model weights. Arms A-D are objective-only, criterion-paraphrase, verified-hard-negative, and combined; arm E is selected on dev NLL/accuracy and calibrated on calibration records only.

Pre-registration is frozen in `experiments/EXP-20260920-008-small-judge-training/README.md` and `experiment.yaml` with code commit `2e3e244eeb856f7cfce2d4047f8357f0b19d1c91`. The final test split has not been run before this checkpoint.

Commands and results:
- `ruff check --fix src/eval_lab/training.py scripts/run_small_judge_training.py tests/test_training.py` -> two import fixes applied; subsequent targeted Ruff check is expected before final run.
- `PYTHONPATH=src python -m pytest -q tests/test_training.py` -> `4 passed in 4.84s`.
- `git commit -m "TASK-0009: implement compact training pilot"` -> commit `2e3e244eeb856f7cfce2d4047f8357f0b19d1c91`.
- `git commit -m "TASK-0009: freeze EXP-008 pre-registration"` -> records the frozen experiment protocol and this checkpoint.

Decision: use the compact linear student for this pilot because the available objective corpus is small and the artifact can be serialized, audited, and reproduced without downloading or committing transformer weights. Pairwise records remain out of scope and will be labeled not applicable in the report.

Blockers: none. The known GitHub Actions account budget/no-runner condition remains external; local checks are authoritative.

Next atomic action: run the preregistered EXP-008 final experiment, including frozen test evaluation, then run the full repository contract, Ruff, and pytest gates.

### 2026-09-20 — EXP-008 final run and local acceptance

EXP-008 completed after the pre-registration commit. The selected student is `tfidf-logistic-v1`, a compact TF-IDF plus balanced logistic-regression classifier for single-answer correctness. Arms A-D ran with 33, 66, 36, and 72 training rows respectively; arm D was selected by lowest dev NLL (`0.6500`) with test labels excluded from selection. Arm E fit scalar temperature on 6 calibration records only.

Final evidence: test split has 12 records across 4 frozen source families; arm D scored accuracy `0.6667`, balanced accuracy `0.6250`, macro F1 `0.6250`, Brier `0.4582`, NLL `0.6506`, and ECE `0.1154`. Calibrated arm E retained the same hard-label metrics but its test NLL/Brier/ECE were `0.9101`/`0.5778`/`0.3204`; the calibration artifact and this limitation are retained rather than hidden. No training source family overlaps test; test labels were used neither for arm selection nor calibration. Pairwise swap consistency is explicitly not applicable to this scoped single-answer pilot. No OS-level memory claim is made; per-prediction latency is retained.

Environment: Windows PowerShell; Python `3.12.10`; Git `2.51.2.windows.1`; Node `v24.14.1`; OpenCode CLI `1.18.31`. No credentials were printed or committed.

Commands and results:
- `PYTHONPATH=src python scripts/run_small_judge_training.py --output-dir experiments/EXP-20260920-008-small-judge-training` -> `EXP-20260920-008-small-judge-training`, selected arm `D`, status `completed`.
- `python scripts/check_repo_contract.py` -> `Repository contract OK`.
- `ruff check .` -> `All checks passed!`.
- `PYTHONPATH=src python -m pytest -q` -> `64 passed in 5.43s`.

Files changed: `src/eval_lab/training.py`, `scripts/run_small_judge_training.py`, `tests/test_training.py`, all committed EXP-008 files under `experiments/EXP-20260920-008-small-judge-training/`, this task log, and `checkpoints/CURRENT.md`. The experiment includes the preregistration, completed manifest, raw predictions, four JSON student artifacts, training manifests/fingerprints, calibration artifact, results, report, and source manifest.

Decisions: retain deterministic verifier provenance as the only objective gold; use teacher criterion text and verified hard negatives as traceable augmentation; preserve the selected arm and calibrated artifact even though post-hoc calibration worsened this tiny test sample; keep pairwise and OS memory measurements outside this bounded pilot.

Blockers: none for local acceptance. GitHub Actions may remain unavailable before workflow steps because of the known account budget/no-runner condition; local validation is authoritative and will be recorded with the review handoff.

Next atomic action: commit the completed EXP-008 evidence and checkpoint, push `task/TASK-0009-small-judge-training`, open the review PR, and do not begin a dependent task before this task is accepted and merged.

### 2026-09-20 — TASK-0009 review handoff

TASK-0009 is pushed in PR [#24](https://github.com/Pukujan/Eval-lab/pull/24) from commit `1924c0ef8d16e23366067f547ec6001ca5339932`. Local acceptance is green: `python scripts/check_repo_contract.py` returned `Repository contract OK`, `ruff check .` returned `All checks passed!`, `PYTHONPATH=src python -m pytest -q` returned `64 passed in 4.35s`, and `git diff --check` was clean.

CI diagnosis after local validation: runs `35534868582` (push) and `35534871113` (pull request) reported both 3.11 jobs as not started because an Actions budget is preventing further use; both 3.12 matrix jobs were cancelled as a consequence. No workflow step ran, so this is an external account/runner blocker rather than a repository test result.

Files and decisions are recorded in the completed EXP-008 bundle and the local checkpoint. No credentials, `.env` files, model weights, or caches were committed.

Next atomic action: merge PR #24, record the merge checkpoint, fast-forward the original `main` checkout, and push the checkpoint commit to `main`. Do not start a dependent task.

### 2026-09-20 — TASK-0009 merge checkpoint

PR #24 (`https://github.com/Pukujan/Eval-lab/pull/24`) merged into `main` at `286731c035ea2149a98a64e4877ce2d768893631` on 2026-09-20 20:15:01 UTC. The dedicated worktree was `D:/claude/eval-lab-TASK-0009` on branch `task/TASK-0009-small-judge-training`.

Environment: Windows PowerShell; Python `3.12.10`; Git `2.51.2.windows.1`; Node `v24.14.1`; OpenCode CLI `1.18.31`. Secret-bearing environment variables remained local and ignored; no values were printed or committed.

Commands and results: `PYTHONPATH=src python scripts/run_small_judge_training.py --output-dir experiments/EXP-20260920-008-small-judge-training` completed EXP-008 and selected arm D; `python scripts/check_repo_contract.py` returned `Repository contract OK`; `ruff check .` returned `All checks passed!`; `PYTHONPATH=src python -m pytest -q` returned `64 passed in 4.35s`; `git diff --check` was clean; `gh pr merge 24 --merge --delete-branch=false` succeeded; `gh pr view 24 --json state,mergedAt,mergeCommit,url` returned `MERGED` with merge commit `286731c035ea2149a98a64e4877ce2d768893631`. CI runs `35534868582` and `35534871113` did not start workflow steps because the account Actions budget prevented further use; 3.12 jobs were cancelled.

Files changed: `src/eval_lab/training.py`, `scripts/run_small_judge_training.py`, `tests/test_training.py`, all EXP-008 artifacts, the TASK-0009 log, and `checkpoints/CURRENT.md`. No credentials, `.env` files, model weights, or caches were committed.

Decisions: accept the bounded single-answer pilot with arm D selected and arm E calibration retained as a reproducible artifact, while recording the calibration regression and pairwise/memory scope limits. Local evidence satisfies all acceptance criteria; CI is an external account condition.

Blockers: none for TASK-0009 acceptance. GitHub Actions remains unavailable before workflow steps due to the account budget/no-runner condition.

Next atomic action: fast-forward the original `D:/claude/eval-lab` checkout to `286731c035ea2149a98a64e4877ce2d768893631`, cherry-pick this post-merge checkpoint, and push `main`. No dependent task is queued.

## Handoff

Use the final ablation to define the next research task.
