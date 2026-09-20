# TASK-0003 — Jev Free Objective Baseline Runner

- Status: ready for review
- Owner: Codex/local agent
- Priority: P0
- GitHub issue: #7
- Depends on: TASK-0002
- Branch: task/TASK-0003-jev-objective-baseline

## Goal

Evaluate OpenCode Jev Free as a structured classification judge using canonical fixture records.

## Model contract

Required model id: `jev-1.13-free`.

Never automatically fall back to `jev-1.13` or another paid route.

If free Jev is quota-limited, emit `rate_limited` and checkpoint it.

## Inputs

- TASK-0002 schemas/fixtures
- existing Jev client
- relevant SDD/TDD sections
- `docs/ACCESS_MODEL_MATRIX.md`

## Outputs

- normalized Jev adapter
- `jev-direct-v1`
- `jev-atomic-v1`
- deterministic runner
- mocked response tests
- normalized prediction JSONL
- optional live run

## Acceptance criteria

- [x] outgoing default model asserted as `jev-1.13-free`
- [x] test proves no paid fallback
- [x] direct single/pairwise normalized
- [x] atomic normalized
- [x] probabilities retained
- [x] 429 -> rate_limited
- [x] no fabricated labels on provider errors
- [x] no secret leakage
- [x] full local merge gate passes

## Validation

Intercept the outgoing request in tests and assert `model == "jev-1.13-free"`.

## Stop conditions

Stop if provider semantics cannot be mapped reliably or secret persistence would be required.

## Checkpoint log

Append evidence here.

### 2026-09-20 — Codex/local agent

Started from accepted `main` merge commit `1498581774ad5c7c4291f4e1dc68e58547d4126f` in dedicated worktree `D:\claude\eval-lab-TASK-0003` on branch `task/TASK-0003-jev-objective-baseline`.

Read, in order: `PROJECT.md`, `AGENTS.md`, `checkpoints/CURRENT.md`, this task file, SDD sections 6-7 and 12, TDD section 6, and `docs/ACCESS_MODEL_MATRIX.md`.

Completed:
- accepted TASK-0002 PR #16 into `main` before creating this worktree;
- established the task-specific branch/worktree boundary;
- no TASK-0003 implementation files changed yet.

Commands and results:
- `git worktree add D:\\claude\\eval-lab-TASK-0003 -b task/TASK-0003-jev-objective-baseline main` -> created at the accepted `main` head;
- `git status --short --branch` -> clean `task/TASK-0003-jev-objective-baseline`.

Decision: preserve the exact `jev-1.13-free` model contract, normalize provider outcomes into `JudgePrediction`, and treat HTTP 429 as `rate_limited` without fallback or fabricated labels.

Next atomic action: implement and mock-test the normalized direct and atomic Jev protocols.

### 2026-09-20 — final TASK-0003 acceptance checkpoint

Completed:
- enforced exact `jev-1.13-free` requests with no paid-model fallback;
- added direct and atomic request builders and normalized `JudgePrediction` outputs;
- added deterministic local aggregation for atomic criterion results;
- mapped 429, 5xx, malformed JSON, transport/configuration failures to explicit execution statuses without labels;
- added JSONL output and a deterministic synthetic-fixture runner;
- added mocked provider-contract tests and one live quota smoke.

Files changed:
- `src/eval_lab/jev.py`
- `src/eval_lab/jev_runner.py`
- `scripts/run_jev_baseline.py`
- `tests/test_jev_runner.py`
- this task file and `checkpoints/CURRENT.md`

Exact commands and results:
- `.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `.venv\Scripts\python.exe -m pytest -q` -> `37 passed in 0.64s`.
- live smoke with transient `OPENCODE_API_KEY`: `.venv\Scripts\python.exe scripts/run_jev_baseline.py --protocol jev-direct-v1 --limit 1 --output outputs/jev-live-smoke.jsonl` -> `statuses={'rate_limited': 1}`, `error_type=rate_limited`, `retry_after=24496`; output is ignored and no credential was persisted.

Decisions: `jev-1.13-free` is the only default/requested model; provider 429 is an execution state, never an incorrect label; raw provider responses and secrets are not written to prediction artifacts.

Blockers: the live Jev quota remains rate-limited, but all mocked provider-contract coverage passes and the condition does not block TASK-0004.

Next atomic action: commit and push TASK-0003, open its PR, and wait for acceptance/merge before starting TASK-0004.

## Handoff

TASK-0004 consumes normalized predictions. TASK-0007 later revisits Jev in the external-model bakeoff.
