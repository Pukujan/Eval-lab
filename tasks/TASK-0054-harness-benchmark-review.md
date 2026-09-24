# TASK-0054 — Decision-agent benchmark harness review

GitHub issue: [#58](https://github.com/Pukujan/Eval-lab/issues/58)

## Status

Research written. No harness code changed. No model inference ran. No blind split was scored. Pull request is the next durable step after this file is committed.

## Goal

Review the harnesses Eval Lab already has for GLEIF, SEC EDGAR/XBRL, CourtListener, and every other benchmark adapter, then record external research on how to make those benchmarks — and the ones not yet built — better for typed decision agents.

## Bounds

- Research only. Do not implement adapters.
- Do not touch the canonical checkout on `task/TASK-0053-semif-4b`.
- Do not edit `checkpoints/CURRENT.md`. The other session owns the repository-wide next action.
- Decision agents in scope: Jev 1.13, Qwen3 0.6B/1.7B/4B, Kev-0.8B/4B/9B, Laya-421M, Verdict 1.4 and pre-v1.4, SemIf Qwen3.5-4B, Nimble-9B. Luna, Sol, and Grok are critics only.

## Files in scope

- `tasks/TASK-0054-harness-benchmark-review.md`
- `docs/research/TASK-0054-decision-agent-benchmark-review.md`

## Completed work

- Opened issue #58.
- Created worktree `D:\claude\eval-lab\worktrees\TASK-0054-harness-review` on `task/TASK-0054-harness-review` from `origin/main` at `f661161`.
- Launched Astra on `cb/gpt-6-astra` with `danger-full-access`. That run audited the repository, then the provider rejected the next request (`model_param_invalid`, InferHub request `d6fa290d5b324a64b0fc380078fa0d81`) because the tool payload was too large. No review file was written by that process.
- Finished the review in this session from that audit plus primary sources fetched on 2026-09-24. Live SEC pages returned HTTP 403, so SEC policy details are not re-verified.

## Commands run

- `git worktree add -b task/TASK-0054-harness-review D:\claude\eval-lab\worktrees\TASK-0054-harness-review origin/main`
- Full-privilege Astra launch via `D:\claude\_workspace\pcm-astra-owner\launch-astra.ps1`. Exit code 1. Receipt: `D:\claude\_workspace\eval-lab-astra-harness-review\receipts\20260924T180227Z`.
- Primary-source fetches recorded in the research document. No tests were run because no code changed.

## Decisions

- Do not relaunch the same Astra tool loop. The failure was payload size, not missing evidence.
- Keep this lane research-only so it does not collide with the other harness-benchmark session.
- Do not request auto-merge. The canonical checkout is dirty on another task.

## Unresolved questions

- Whether a public LEI decision benchmark already exists beyond GLEIF's own data-quality checks. Not found in this pass.
- Live SEC developer-page wording. Fetch was blocked.
- Exact context windows for every local decision model beyond the limits already recorded in TASK-0053.

## Next atomic action

Commit these two files, push `task/TASK-0054-harness-review`, and open a research-only pull request that references issue #58. Do not merge while the canonical checkout is dirty.
