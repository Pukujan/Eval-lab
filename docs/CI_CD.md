# CI/CD and Change Discipline

## Philosophy

This repository is a research system. CI exists to prevent invalid experiments and broken handoffs, not only syntax errors.

## Every push

GitHub Actions should run:

1. repository contract validation
2. Ruff lint
3. unit tests
4. experiment-manifest checks

No paid API calls run automatically on ordinary pushes.

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

A PR modifying evaluation logic must add or update tests.

A PR modifying an experiment after completion is prohibited; create a new experiment.

## Main branch requirements

Desired repository settings:

- default branch: `main`
- merge by PR
- CI required before merge
- no direct force-pushes to `main`
- stale task branches may be deleted after merge

If branch protection is not configured yet, agents still follow these rules manually.

## CI secrets

Provider keys are optional GitHub Actions secrets and must only be used in explicitly manual or protected integration workflows.

Ordinary CI must succeed without provider secrets.

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
