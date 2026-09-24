## Task

TASK-____ (GitHub issue: #____)

## Goal

Describe the bounded goal. Include `Task issue: #<issue-number>`; the finalizer closes the issue after merge and cleanup.

## Changes

- 

## Validation

```
python scripts/check_repo_contract.py
ruff check .
pytest -q
```

Results:

## CI and merge

- [ ] Task branch only; no direct push to `main`
- [ ] Required CI checks are enabled and passing or pending
- [ ] Auto-merge requested; no checks or approval gates bypassed
- [ ] Human approval obtained where a protected owner/review gate applies

## Experiments affected

None / EXP-...

## Protocol/schema changes

None / describe.

## Checkpoint/handoff

Task file updated: yes/no

`checkpoints/CURRENT.md` updated if needed: yes/no

GitHub issue and task file updated: yes/no

Async state: PR URL / CI pending / merge confirmed

## Limitations / follow-up

-
