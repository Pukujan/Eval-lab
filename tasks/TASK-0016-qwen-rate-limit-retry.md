# TASK-0016 — Qwen rate-limit retry

## Goal

Run a separately timestamped Qwen-only recovery study for the `317` blind-holdout
records that were `rate_limited` in EXP-20260921-015. Do not modify or overwrite
EXP-015, and do not retry its single Qwen `provider_error` or any Grok/Luna record.

## Scope

- Worktree: `D:/claude/eval-lab/.worktrees/TASK-0016-qwen-retry`
- Branch: `task/TASK-0016-qwen-rate-limit-retry`
- Experiment: `EXP-20260921-016-qwen-rate-limit-retry`
- Provider: YOLO-Auto only
- Requested model: `qwen3.8-flash`
- Route: `yolo_auto_openai_compatible`
- Input: the exact rate-limited record IDs from committed EXP-015 blind predictions
- Prompt, source pool, gold labels, and canonicalization: unchanged from EXP-015

## Rules

The retry is a new timestamped provider execution and cannot be pooled into the
primary EXP-015 result unless a later, explicitly declared merge analysis is made.
Every selected ID is attempted once in this retry. Provider failures remain unresolved
and receive no fallback label. Streaming remains enabled. No OpenCode, OpenRouter,
Grok, Luna, or Sol calls are permitted.

## Acceptance criteria

- [ ] Preregistration and retry-ID manifest are committed before retry labels.
- [ ] A recovery smoke records the surfaced Qwen model ID and streaming metadata.
- [ ] Exactly the frozen rate-limited IDs are attempted once.
- [ ] Retry accuracy, coverage, Wilson uncertainty, latency, and status counts are
  reported separately from EXP-015.
- [ ] Original EXP-015 artifacts remain byte-identical.
- [ ] Repository contract, Ruff, tests, diff check, and retry checksums pass.

## Checkpoint log

### 2026-09-21 — preregistration created

Status: active; no provider labels requested.

Completed: defined the Qwen-only retry scope, inherited fingerprints, exact excluded
statuses, streaming route, one-pass rule, metrics, and append-only artifact policy.

Exact files changed: this task file, the EXP-016 plan/README/manifest, and the current
checkpoint.

Commands run: worktree creation and repository contract check.

Test results: the first contract check identified missing required task headings; the
headings are now corrected and the contract will be rerun before commit.

Decision: retry only the 317 EXP-015 `rate_limited` Qwen IDs. Do not retry the single
Qwen provider error or any Grok/Luna record. Do not modify EXP-015.

Unresolved questions: whether the YOLO-Auto rate limit has recovered; test that with a
one-record smoke only after this preregistration is committed.

Next atomic action: commit this preregistration, generate the exact retry-ID manifest,
then run the recovery smoke.

## Handoff

Read in order: `PROJECT.md`, `checkpoints/CURRENT.md`, this task file, and
`docs/EXPERIMENT_PROTOCOL.md`. The active worktree is
`D:/claude/eval-lab/.worktrees/TASK-0016-qwen-retry` on branch
`task/TASK-0016-qwen-rate-limit-retry`.

## Next atomic action

Commit this preregistration, generate and commit the 317-ID retry manifest from the
committed EXP-015 prediction artifact, then run a one-record recovery smoke before the
bulk retry.
