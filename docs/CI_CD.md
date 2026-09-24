# CI/CD and Checkpoint Discipline

## Philosophy

This repository is a research system. CI exists to prevent invalid experiments and broken handoffs, not only syntax errors.

## Every push

The `CI` workflow runs on pushes to `main` and `task/**`, pull requests into
`main`, and manual dispatch. It uses the committed `uv.lock` with locked
installs and tests Python 3.11 and 3.12. Each Python job runs:

- repository and single-workspace policy checks
- Ruff lint across the repository
- Ruff format validation for Python files changed by the checkpoint/PR
- mypy over `src/eval_lab`
- the unit-test suite
- a package build

No paid API calls run automatically on ordinary pushes. CI actions are pinned
to immutable commit SHAs, and the workflow has read-only repository permissions.

## Every pull request

PR body must identify:

- task ID
- goal
- files changed
- commands/tests run
- experiment IDs affected
- whether schemas/protocols changed
- checkpoint/handoff state
- known limitations
- the linked GitHub issue (leave it open until merge verification and finalization)

A PR modifying evaluation logic must add or update tests.

A PR modifying an experiment after completion is prohibited; create a new experiment.

## Required checkpoint merge gate

Every coherent, validated checkpoint must be committed and pushed to its task
branch, opened or added to a pull request into `main`, and merged only after
all required CI jobs pass. A task is not complete, and the canonical checkout
must not switch to another task, while its completed checkpoint remains only
local or its required PR is unmerged. Pushes make intermediate work durable;
merges promote reviewed checkpoints to the canonical branch.

Create or update the GitHub issue before implementation. Use
`scripts/publish_checkpoint.py` to validate and commit explicitly selected
files, push the task branch, create/update its PR, and request auto-merge. The
publisher returns without waiting for CI. Keep the issue open until
`scripts/finalize_checkpoint.py` verifies the exact merged PR head, merge SHA,
required checks, and clean worktree cleanup; it records the outcome and closes
the issue. The `Task merge record` workflow independently records the verified
head and merge SHA on the linked issue after GitHub merges the PR.

GitHub branch protection on `main` enforces pull requests, the Python 3.11 and
3.12 CI status checks, and up-to-date branches. Direct pushes, force-pushes,
branch deletion, and administrator bypass are disabled. Task PRs auto-merge
after the required checks pass. Use squash merge for one coherent commit per
checkpoint. Keep the issue and worktree open until the finalizer
records post-merge cleanup.

Configure/verify the protection rule as part of repository setup; documenting a
merge requirement is not an adequate substitute for an enforced GitHub rule.

## Experiment execution

Large/provider-backed experiments should be launched manually from a task worktree. The exact command and commit SHA must be recorded in the experiment manifest before execution.

## Artifact retention

Small reports/configs belong in Git.

Large raw provider outputs should be stored outside Git when necessary and referenced by cryptographic fingerprint plus retrieval note.

## Release/checkpoint tags

Major reproducible milestones may be tagged:

```
v0.1-lab-bootstrap
v0.2-jev-baseline
v0.3-local-baselines
```

Tags should only point to commits with passing CI.
