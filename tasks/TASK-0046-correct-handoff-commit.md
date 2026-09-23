# TASK-0046 — Correct handoff commit reference

## Status

Complete. The handoff checkpoint was corrected after the audit PR merged; its
historical commit detail is retained as evidence, while the current handoff
now uses stable PR lineage.

## Objective

Prevent the durable handoff from becoming stale every time its documentation
PR itself advances `main`.

## Scope

- replace the transient Eval Lab commit reference in `checkpoints/CURRENT.md`
  with stable merged PR identifiers;
- clarify the historical evidence line in TASK-0045;
- clarify the historical nature of this task's commit evidence.

## Files expected to change

- `checkpoints/CURRENT.md`
- `tasks/TASK-0045-session-handoff-audit.md`
- `tasks/TASK-0046-correct-handoff-commit.md`

## Goal

Ensure a new session sees the exact current `main` commit without ambiguity.

## Acceptance criteria

- The checkpoint names the merged PR lineage and does not claim a historical
  hash is still the current `main` tip.
- TASK-0045 identifies PR #33 and the subsequent correction PRs.
- No experiment artifacts or provider state are changed.

## Commands and evidence

- The normal checkout and `origin/main` were synchronized when this correction
  was made; subsequent commits are expected and do not invalidate the handoff.
- The preceding handoff PR #33 passed all Python 3.11 and 3.12 CI jobs.

## Unresolved questions

- None for this documentation correction.

## Checkpoint log

Corrected the transient commit reference after PR #33 merged; no scientific
or runtime state changed.

## Handoff

Resume from TASK-0045 and `checkpoints/CURRENT.md`; the next research action
remains the preregistered GLEIF snapshot freeze for EXP-026.

## Next atomic action

Freeze the GLEIF source snapshot and implement the canonical adapter before
blind scoring or additional model calls.
