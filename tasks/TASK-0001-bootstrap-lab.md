# TASK-0001 — Bootstrap Local Eval Lab

- Status: active
- Owner: Luna/local agent
- Priority: P0
- Depends on: none
- GitHub issue: #5

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
- [ ] GitHub Actions runner failure is classified as repo/workflow failure or account/runner infrastructure

## Commands

Follow `docs/LOCAL_BOOTSTRAP_LUNA.md`.

## Checkpoint log

### 2026-09-20 — ChatGPT/Sol

Completed:
- clean project contracts and task architecture created in GitHub
- TASK-0001 prepared for local execution
- CI workflow, repository contract validator, and dependency-light tests added
- GitHub issue #5 created as the task queue mirror
- two accidental test-dependency/lint issues were removed before handoff

Evidence:
- main bootstrap head: `4359e100855f3632c872d0303c571818f538b62d`
- GitHub Actions recognizes `.github/workflows/ci.yml`
- CI runs 97 and 98 created both Python 3.11 and 3.12 jobs
- both jobs failed before any workflow steps were reported; no executable job log was available through the GitHub connection

Decisions:
- do not infer a Python/test failure from the current GitHub Actions result
- local bootstrap is the next source of truth
- local execution is delegated because this chat does not have access to the user's local shell
- Luna/local agent should use the repository as its authoritative context

Changed:
- project/design/testing/handoff documentation
- CI workflow and issue templates
- repository contract validator
- initial unit tests

Blocked:
- local execution requires a local-machine-capable agent/session
- cloud CI runner/account condition remains to be diagnosed after local validation

Next:
- clone/switch main locally and run the bootstrap commands exactly as documented

## Handoff

Receiving agent: follow `docs/LOCAL_BOOTSTRAP_LUNA.md`; update this file before stopping. If local checks pass, investigate why GitHub-hosted jobs terminate before step execution without changing scientific scope.
