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

```bash
git clone https://github.com/Pukujan/Eval-lab.git
cd Eval-lab
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

```bash
git worktree add ../eval-lab-TASK-0001 -b task/TASK-0001-bootstrap-lab origin/main
cd ../eval-lab-TASK-0001
```

Create environment:

```bash
python -m venv .venv
```

Activate it using the platform-appropriate command, then:

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
python scripts/check_repo_contract.py
ruff check .
pytest -q
```

If an OpenCode key is available locally:

```bash
export OPENCODE_API_KEY=...
python scripts/jev_smoke.py
```

On PowerShell use:

```powershell
$env:OPENCODE_API_KEY="..."
python scripts/jev_smoke.py
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
