# TASK-0002 — Canonical Schema and Objective Fixtures

- Status: queued
- Owner: Luna/local agent
- Priority: P0
- GitHub issue: #6
- Depends on: TASK-0001
- Branch: task/TASK-0002-canonical-schema-fixtures

## Goal

Implement the canonical evaluation schema, deterministic split policy, four-domain synthetic objective fixture suite, and verifier primitives that all later judges share.

## Why

If data identity, provenance, splits, and pairwise transformations are not correct, later accuracy/calibration numbers are meaningless.

## Inputs

- `PROJECT.md`
- `docs/SDD.md` sections 3-5
- `docs/TDD.md` section 5
- `docs/VALIDATION_MATRIX.md`

## Outputs

Required:
- `src/eval_lab/schema.py`
- `src/eval_lab/datasets/__init__.py`
- `src/eval_lab/datasets/synthetic.py`
- `src/eval_lab/verifiers/__init__.py`
- verifier modules for arithmetic, multiple choice, structured output, and simple code/output
- deterministic fixture generation command/script
- tests
- small generated fixture file only if stable and useful; otherwise generate during tests
- updated checkpoint

## Required implementation

Implement:
- Split enum
- GoldProvenance enum
- JudgmentMode
- PairwiseLabel
- ExecutionStatus
- RubricCriterion
- SourceRecord
- GoldLabel
- JudgeRecord
- JudgePrediction

Probability validation belongs in JudgePrediction.

Implement deterministic split assignment by source_problem_id and fixed seed/policy.

Create at least 24 source problems total:
- >=6 arithmetic
- >=6 multiple choice
- >=6 structured/instruction
- >=6 simple code/output

Generate at least:
- 72 single-candidate judge records
- 48 pairwise records
- both correct and subtle incorrect candidates
- deterministic A/B order

No network access.

## Allowed files

- `src/eval_lab/schema.py`
- `src/eval_lab/datasets/`
- `src/eval_lab/verifiers/`
- `scripts/` for fixture generation
- `tests/`
- `data/` for tiny stable fixture metadata
- `pyproject.toml` only if a necessary dependency is missing
- this task file
- `checkpoints/CURRENT.md`

## Acceptance criteria

- [ ] all schema concepts implemented
- [ ] fixed-seed generation deterministic
- [ ] four required domains represented
- [ ] >=24 sources, >=72 single records, >=48 pairwise records
- [ ] no source_problem_id crosses splits
- [ ] gold provenance round-trips through JSON
- [ ] A/B swap transformation correct
- [ ] invalid probability vectors rejected
- [ ] full local merge gate passes

## Validation

Run task-specific tests plus:

~~~powershell
.venv\Scripts\python.exe scripts/check_repo_contract.py
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m pytest -q
~~~

Required tests are listed in `docs/TDD.md` section 5.

## Stop conditions

Stop before proceeding if:
- schema requires model/provider-specific fields in core gold records;
- same source can land in multiple splits;
- fixture generation is nondeterministic;
- objective provenance cannot be established for a fixture.

## Checkpoint log

Append execution evidence here.

## Handoff

On completion, TASK-0003 receives the canonical JudgeRecord/JudgePrediction contract. Do not begin provider-specific schema redesign in TASK-0003.
