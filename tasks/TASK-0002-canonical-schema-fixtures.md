# TASK-0002 — Canonical Schema and Objective Fixtures

- Status: ready for review
- Owner: Codex/local agent
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

- [x] all schema concepts implemented
- [x] fixed-seed generation deterministic
- [x] four required domains represented
- [x] >=24 sources, >=72 single records, >=48 pairwise records
- [x] no source_problem_id crosses splits
- [x] gold provenance round-trips through JSON
- [x] A/B swap transformation correct
- [x] invalid probability vectors rejected
- [x] full local merge gate passes

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

### 2026-09-20 — Codex/local agent

Started from accepted `main` merge commit `ab09600679de8b27ee3f7d25a4d77f09a65d5a28` in dedicated worktree `D:\claude\eval-lab-TASK-0002` on branch `task/TASK-0002-canonical-schema-fixtures`.

Read, in order: `PROJECT.md`, `AGENTS.md`, `checkpoints/CURRENT.md`, `docs/PROGRAM_PLAN.md`, `docs/LUNA_PROGRAM_HANDOFF.md`, this task file, SDD sections 3-5, and TDD section 5.

Completed:
- accepted program PR #11 into `main` before creating this worktree;
- established the task-specific branch/worktree boundary;
- no implementation files changed yet.

Commands and results:
- `git worktree add D:\\claude\\eval-lab-TASK-0002 -b task/TASK-0002-canonical-schema-fixtures main` -> created at the accepted `main` head;
- `git status --short --branch` -> clean `task/TASK-0002-canonical-schema-fixtures`.

Decision: implement provider-neutral schema and deterministic fixtures first; no network/provider calls or later-task functionality will be added.

Next atomic action: implement the canonical schema models and validation primitives, then add focused schema tests before fixture generation.

### 2026-09-20 — canonical schema and fixture implementation checkpoint

Completed:
- implemented the provider-neutral Pydantic schema and probability validation;
- implemented deterministic verifier primitives for arithmetic, multiple choice, structured JSON, and code/output;
- implemented fixed-seed source split assignment, four-domain synthetic sources, 72 single records, and 48 pairwise records;
- implemented deterministic A/B swapping, including TIE preservation;
- added the deterministic fixture export command and focused schema, verifier, and fixture tests.

Files changed:
- `src/eval_lab/schema.py`
- `src/eval_lab/datasets/__init__.py`
- `src/eval_lab/datasets/synthetic.py`
- `src/eval_lab/verifiers/__init__.py`
- `src/eval_lab/verifiers/arithmetic.py`
- `src/eval_lab/verifiers/multiple_choice.py`
- `src/eval_lab/verifiers/structured.py`
- `src/eval_lab/verifiers/code_output.py`
- `scripts/generate_fixtures.py`
- `tests/test_schema.py`
- `tests/test_synthetic.py`
- `tests/test_verifiers.py`

Commands and results from this pre-PR15 checkpoint:
- `.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `.venv\Scripts\python.exe -m pytest -q` -> `27 passed in 1.25s`.
- `.venv\Scripts\python.exe scripts/generate_fixtures.py --seed 20260920 --split-seed 20260920 --output data/synthetic-fixtures.json` -> 24 sources, 120 records, 72 single, 48 pairwise; fingerprint `03cd497da246c641f84a89fd74380e1f340c327eab7850e0476b8379a7a1052c`; generated artifact removed after verification.

Decision: preserve this coherent implementation checkpoint, then rebase it onto the newly accepted PR #15 `main` before final TASK-0002 validation. No provider calls or later-task functionality were added.

Next atomic action: fast-forward local `main` to PR #15 merge commit `de294e10eb10e926c8ed18e7ffeba893ff7c1cf5`, rebase this task branch, and rerun the full local merge gate.

### 2026-09-20 — final TASK-0002 acceptance checkpoint

Completed:
- rebased the implementation onto PR #15's accepted `main` merge commit `de294e10eb10e926c8ed18e7ffeba893ff7c1cf5`;
- added semantic aliases at the schema boundary without changing canonical field serialization;
- verified mapping and sequence forms of the deterministic split policy;
- confirmed generated fixture output is not committed and no network/provider calls are used.

Files changed for TASK-0002:
- `src/eval_lab/schema.py`
- `src/eval_lab/datasets/__init__.py`
- `src/eval_lab/datasets/synthetic.py`
- `src/eval_lab/verifiers/__init__.py`
- `src/eval_lab/verifiers/arithmetic.py`
- `src/eval_lab/verifiers/multiple_choice.py`
- `src/eval_lab/verifiers/structured.py`
- `src/eval_lab/verifiers/code_output.py`
- `scripts/generate_fixtures.py`
- `tests/test_schema.py`
- `tests/test_synthetic.py`
- `tests/test_verifiers.py`
- this task file and `checkpoints/CURRENT.md`

Exact final commands and results on the rebased branch:
- `.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `.venv\Scripts\python.exe -m pytest -q` -> `29 passed in 1.99s`.
- `.venv\Scripts\python.exe scripts/generate_fixtures.py --seed 20260920 --split-seed 20260920 --output data/synthetic-fixtures.json` -> 24 sources, 120 records, 72 single, 48 pairwise; fingerprint `03cd497da246c641f84a89fd74380e1f340c327eab7850e0476b8379a7a1052c`; generated file removed after verification.

Decisions: objective gold is produced only by deterministic verifier modules; source variants inherit one hash-based split; pairwise swaps invert A/B while preserving TIE; provider-specific fields remain outside the canonical gold record.

Blockers: no TASK-0002 implementation blocker remains. GitHub Actions may still fail before runner assignment, so local evidence remains authoritative under the program contract.

Next atomic action: commit and push this checkpoint, open the TASK-0002 PR, and wait for its acceptance/merge before starting TASK-0003.

### 2026-09-20 — PR handoff

Committed final implementation as `bae7955` on `task/TASK-0002-canonical-schema-fixtures`, pushed to origin, and opened PR #16: `https://github.com/Pukujan/Eval-lab/pull/16`.

Next atomic action: merge PR #16 into `main`, update local `main`, and create the dedicated TASK-0003 worktree only after the merge.

## Handoff

On completion, TASK-0003 receives the canonical JudgeRecord/JudgePrediction contract. Do not begin provider-specific schema redesign in TASK-0003.
