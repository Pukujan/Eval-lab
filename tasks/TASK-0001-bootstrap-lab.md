# TASK-0001 — Bootstrap Local Eval Lab

- Status: active
- Owner: Luna/local agent
- Priority: P0
- Depends on: none

## Goal

Verify that a fresh local clone can install, run repository contract checks, run unit tests, and optionally execute the Jev smoke test.

## Why

No research result is trustworthy until another environment can reproduce the lab bootstrap.

## Allowed files

- `pyproject.toml`
- `scripts/`
- `src/eval_lab/`
- `tests/`
- `docs/LOCAL_BOOTSTRAP_LUNA.md`
- this task file
- `checkpoints/CURRENT.md`

Do not modify PDD/SDD/project scope unless a separate task is created.

## Acceptance criteria

- [ ] Python version documented
- [ ] editable install succeeds
- [ ] `python scripts/check_repo_contract.py` passes
- [ ] `ruff check .` passes
- [ ] `pytest -q` passes
- [ ] Jev smoke test runs if `OPENCODE_API_KEY` is available, otherwise skipped with reason
- [ ] any platform-specific setup issue is documented
- [ ] final checkpoint records exact commands/results

## Commands

Follow `docs/LOCAL_BOOTSTRAP_LUNA.md`.

## Checkpoint log

### 2026-09-20 — ChatGPT/Sol

Completed:
- clean project contracts and task architecture created in GitHub
- TASK-0001 prepared for local execution

Evidence:
- repository clean-slate commit existed before task creation

Decisions:
- local bootstrap is delegated because this chat does not have access to the user's local shell
- Luna/local agent should use the repository as its authoritative context

Changed:
- task and protocol documentation

Blocked:
- local execution requires a local-machine-capable agent/session

Next:
- clone/switch main locally and run the bootstrap commands

## Handoff

Receiving agent: follow `docs/LOCAL_BOOTSTRAP_LUNA.md`; update this file before stopping.
