# Local Bootstrap Handoff for Luna / Local Agent

## Mission

Set up Eval Lab on the user's local machine and complete TASK-0001 without changing project scope.

Do not redesign the project. Follow repository contracts.

## Read first

1. `PROJECT.md`
2. `AGENTS.md`
3. `checkpoints/CURRENT.md`
4. `tasks/TASK-0001-bootstrap-lab.md`
5. `docs/TDD.md`

## Local actions

From a parent directory:

```powershell
git clone https://github.com/Pukujan/Eval-lab.git D:\development\eval-lab
cd D:\development\eval-lab
git fetch --all --prune
git switch main
```

If obsolete local worktrees exist from an older clone:

```bash
git worktree list
git worktree prune
```

Remove only obsolete worktrees the user no longer needs.

Create task worktree:

```powershell
git worktree add D:\development\eval-lab-wt\TASK-0001-bootstrap-lab -b task/TASK-0001-bootstrap-lab origin/main
cd D:\development\eval-lab-wt\TASK-0001-bootstrap-lab
```

The worktree reuses the canonical root `.venv`; never create a second environment in it.

Create or synchronize the one project environment from the canonical checkout
(`uv sync` builds the root `.venv` from `pyproject.toml` and `uv.lock`; do not use pip):

```powershell
uv sync --extra dev
uv run python scripts/check_repo_contract.py
uv run ruff check .
uv run pytest -q
```

If an OpenCode key is available locally:

```bash
export OPENCODE_API_KEY=...
uv run python scripts/jev_smoke.py
```

On PowerShell use:

```powershell
$env:OPENCODE_API_KEY="..."
uv run python scripts/jev_smoke.py
```

Never print or commit the key.

## Required deliverable

Complete TASK-0001 exactly as defined. Update its checkpoint log with:

- OS/Python version
- installation result
- tests
- Jev smoke outcome or explicit reason skipped
- any compatibility changes
- next action

Commit using:

```
TASK-0001: bootstrap local eval lab
```

## Stop conditions

Stop and checkpoint rather than improvising if:

- Python dependency resolution requires a major version change
- Jev endpoint behavior conflicts with the adapter contract
- tests indicate source split leakage or scientific invariant failure
- a change would modify project scope rather than bootstrap the lab
