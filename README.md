# Eval Lab

Eval Lab is a clean, reproducible research lab for testing whether lightweight AI judges can make accurate and calibrated rubric decisions across objectively labeled domains.

## Main research goal

Measure lightweight judges such as Jev and small local models against deterministic verifiers and trusted benchmark answer keys, then quantify calibration, bias, selective risk, latency, and cost.

Strong chat models may help design rubrics, analyze failures, or generate adversarial cases, but they are not automatically treated as ground truth.

## Start here

For humans or agents:

1. `PROJECT.md`
2. `AGENTS.md`
3. `checkpoints/CURRENT.md`
4. the active `tasks/TASK-*.md`

Design contracts:

- `docs/PDD.md` — product/research intent
- `docs/SDD.md` — system architecture
- `docs/TDD.md` — test strategy
- `docs/EXPERIMENT_PROTOCOL.md` — scientific experiment contract
- `docs/HANDOFF_PROTOCOL.md` — multi-agent communication
- `docs/CI_CD.md` — push/PR requirements

## Local bootstrap

```bash
python -m venv .venv
# activate .venv
python -m pip install --upgrade pip
pip install -e ".[dev]"
python scripts/check_repo_contract.py
ruff check .
pytest -q
```

For the first local handoff, follow `docs/LOCAL_BOOTSTRAP_LUNA.md`.

Jev integration additionally requires `OPENCODE_API_KEY`:

```bash
python scripts/jev_smoke.py
```

Never commit credentials.

## Coordination model

Git is project memory.

- one task = one task file + branch/worktree
- checkpoints are written before an agent stops
- experiments are immutable after completion
- chats are not authoritative project state
