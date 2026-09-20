# Agent Operating Contract

This repository is designed to be usable by multiple independent agents without shared chat history.

## Read order

Before doing work, read only:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. the assigned `tasks/TASK-*.md`
4. the minimum design document needed for the task:
   - product scope: `docs/PDD.md`
   - system design: `docs/SDD.md`
   - testing: `docs/TDD.md`
   - experiment rules: `docs/EXPERIMENT_PROTOCOL.md`

Do not scan unrelated historical files or experiments unless the task explicitly requires them.

## One task, one branch, one worktree

Branch format:

```
task/TASK-0001-short-name
```

Recommended local worktree:

```bash
git fetch origin
git worktree add ../eval-lab-TASK-0001 -b task/TASK-0001-short-name origin/main
```

A task may modify only the files declared in its task file unless the task file is updated first.

## Required checkpoint behavior

At every meaningful stopping point, update the task file with:

- status
- completed work
- exact files changed
- commands run
- test results
- decisions made
- unresolved questions
- next atomic action

If the task becomes blocked, write the blocker before stopping.

When the repository-wide next action changes, update `checkpoints/CURRENT.md`.

## Commit rule

A commit should represent one coherent checkpoint. Commit message:

```
TASK-0001: concise checkpoint description
```

Never leave important state only in a chat transcript.

## Experiment rule

Every experiment must have a directory under `experiments/` and follow `docs/EXPERIMENT_PROTOCOL.md`.

Never overwrite completed experiment results. Create a new experiment ID for a changed dataset, rubric, model, prompt, seed, calibration method, or evaluation protocol.

## Ground-truth rule

Model judgments are never promoted to objective gold merely because the model is strong.

Gold labels must identify their provenance:

- deterministic verifier
- benchmark answer key
- executable test
- human adjudication
- explicitly marked weak/model supervision

## Safety and secrets

Never commit API keys, tokens, private benchmark material, or user data. Use environment variables and local `.env` files ignored by Git.
