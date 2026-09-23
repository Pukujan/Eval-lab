# TASK-0047 — Stabilize handoff reference

## Status

Complete. The durable checkpoint now records stable PR lineage instead of a
commit hash that becomes historical as soon as the correction merges.

## Objective

Make the next-session handoff remain accurate after future documentation
commits advance `main`.

## Scope

- replace transient `HEAD` references in the handoff narrative;
- preserve PR lineage and the exact current state in normal Git metadata;
- update the prior audit task wording so it is historically accurate.

## Files expected to change

- `checkpoints/CURRENT.md`
- `tasks/TASK-0045-session-handoff-audit.md`
- `tasks/TASK-0046-correct-handoff-commit.md`
- `tasks/TASK-0047-stabilize-handoff-reference.md`

## Goal

Ensure a fresh session can identify the merged work from stable PRs and the
live `main` branch without chasing a stale hash.

## Acceptance criteria

- The current checkpoint names PRs #31–#34 and #39 rather than a transient
  current commit hash.
- Prior task evidence is clearly historical where appropriate.
- No experiment, benchmark, source, or provider data changes.

## Commands and evidence

- `python scripts/check_repo_contract.py` will be run before commit.
- `git diff --check` will be run before commit.

## Unresolved questions

- None for this documentation-only correction.

## Checkpoint log

Removed the final source of self-invalidating exact-`HEAD` wording from the
handoff records.

## Handoff

Start from the live Eval Lab `main` branch and `checkpoints/CURRENT.md`. The
next research action remains the preregistered GLEIF snapshot freeze for
EXP-026.

## Next atomic action

Freeze the GLEIF source snapshot and implement the canonical adapter before
blind scoring or additional model calls.
