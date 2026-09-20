# TASK-0005 — ARC-Challenge Public Benchmark Adapter

- Status: active
- Owner: Codex/local agent
- Priority: P0
- GitHub issue: #9
- Depends on: TASK-0002 and TASK-0004
- Branch: task/TASK-0005-public-benchmark

## Goal

Add a reproducible adapter for the public ARC-Challenge dataset and produce objective canonical judge records suitable for Jev/local comparison.

## Why

Synthetic fixtures prove mechanics. A public benchmark tests whether the pipeline behaves on real, externally defined questions.

## Selected source

- dataset: `allenai/ai2_arc`
- config: `ARC-Challenge`
- expected license metadata: CC BY-SA 4.0
- source format: multiple-choice science QA with answerKey

At runtime resolve and record the exact upstream revision. Do not depend on an unrecorded moving `main`.

## Inputs

- canonical schema
- metrics/calibration code
- `docs/SDD.md` section 9
- `docs/TDD.md` section 8

## Outputs

- `src/eval_lab/datasets/arc.py`
- dataset retrieval/canonicalization config
- stable source revision metadata
- dataset fingerprint
- canonical judge-record builder
- adapter tests using tiny mocked ARC-shaped rows
- a reproducible evaluation slice manifest
- license/source note

## Canonicalization rules

- preserve upstream id as source_problem_id
- prompt includes question and labeled choices
- answerKey -> GoldProvenance.answer_key
- generate deterministic correct candidate from correct choice
- generate deterministic incorrect candidate from a wrong choice
- build pairwise records with deterministic A/B order
- no LLM generation required

Recommended mapping:
- upstream train -> train
- upstream validation -> deterministic dev/calibration partition
- upstream test -> test

## Allowed files

- `src/eval_lab/datasets/arc.py`
- dataset config/fingerprint helpers
- `tests/`
- `pyproject.toml` for required dataset-loading dependency
- small metadata/manifests, not large dataset caches
- this task file
- `checkpoints/CURRENT.md`

## Acceptance criteria

- [x] source/config/license documented
- [x] resolved revision recorded
- [x] fingerprint stable for identical source+adapter
- [x] upstream IDs preserved
- [x] answerKey provenance correct
- [x] candidate construction deterministic
- [x] split mapping deterministic/no leakage
- [x] small local sample canonicalizes
- [x] evaluation slice manifest generated
- [x] full local merge gate passes

## Validation

See `docs/TDD.md` section 8.

## Stop conditions

Stop if:
- source revision cannot be resolved;
- license/provenance cannot be recorded;
- adapter downloads an unexpectedly huge unrelated corpus by default;
- upstream IDs are unstable or lost.

## Checkpoint log

Append execution evidence here.

### 2026-09-20 — Codex/local agent start

Started from accepted TASK-0004 merge commit `ec083499e8ce77c8cf2cf0614b05265ead24dd93` in dedicated worktree `D:\claude\eval-lab-TASK-0005` on branch `task/TASK-0005-public-benchmark`.

Read, in order: `PROJECT.md`, `AGENTS.md`, `checkpoints/CURRENT.md`, this task file, SDD section 9, and TDD section 8. The current repository has no older TASK-0005 file or branch context; `tasks/TASK-0005-public-benchmark.md` is authoritative.

Commands and results:
- `git worktree add D:\\claude\\eval-lab-TASK-0005 -b task/TASK-0005-public-benchmark main` -> created at `ec083499e8ce77c8cf2cf0614b05265ead24dd93`.
- `git status --short --branch` -> clean `task/TASK-0005-public-benchmark`.

Decision: resolve the Hugging Face dataset revision and license through the dataset metadata API, keep retrieval lazy and split-scoped, and make mocked-row canonicalization independent of a local dataset cache.

Next atomic action: implement the ARC metadata, deterministic split mapping, canonical row conversion, fingerprint, and slice-manifest helpers.

### 2026-09-20 — TASK-0005 local validation

Environment:
- Windows PowerShell on local machine, Python `3.12.10`.
- Dedicated worktree `D:\claude\eval-lab-TASK-0005`, branch `task/TASK-0005-public-benchmark`.
- Existing project `.venv` used with `PYTHONPATH=D:\claude\eval-lab-TASK-0005\src`; no credentials or `.env` values were used.

Implemented files:
- `src/eval_lab/datasets/arc.py` and `src/eval_lab/datasets/__init__.py`.
- `pyproject.toml` (`datasets>=3.0` loader dependency).
- `tests/test_arc.py`.
- `manifests/arc-challenge-slice.json` and `manifests/arc-challenge-source.md`.
- Updated this task log and `checkpoints/CURRENT.md`.

Live source evidence:
- Hugging Face metadata API resolved `allenai/ai2_arc`, config `ARC-Challenge`, requested revision `main` to `210d026faf9955653af8916fad021475a3f00453` and reported `CC BY-SA 4.0`.
- Dataset-server retrieval requested two rows each from `train`, `validation`, and `test` at that resolved revision; six canonical pairwise records were generated.
- Manifest fingerprint: `b7a84b15c5ca352f2689f546721d8038ce9b31ecff711be606016a6996e05521`.

Commands and exact results:
- `& D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `& D:\\claude\\eval-lab\\.venv\\Scripts\\ruff.exe check .` -> `All checks passed!`.
- `& D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe -m pytest -q` -> `52 passed in 0.77s`.

Decisions:
- Resolve moving `main` to an exact Hugging Face commit before retrieval; the committed manifest records that commit and fingerprint.
- Keep dataset retrieval lazy and split-scoped through `load_arc_rows`; do not commit raw rows or a dataset cache.
- Emit one deterministic pairwise record per ARC row, with the answer-key candidate and a deterministic wrong-choice candidate in a stable source-ID-seeded A/B order.
- Map validation deterministically to dev or calibration and retain the seed/fraction in metadata and the manifest.

Blockers: none. The known GitHub Actions no-runner condition remains external infrastructure; the local gate is green.

Next atomic action: commit the validated TASK-0005 implementation, push `task/TASK-0005-public-benchmark`, open the review PR, and update this log with its URL before merge.

### 2026-09-20 — TASK-0005 PR handoff

Commit `d8f038d1725ffcc1121bc0381ae6cabad2e4136b` pushed to `task/TASK-0005-public-benchmark`.

Pull request: [#19](https://github.com/Pukujan/Eval-lab/pull/19).

Next atomic action: merge PR #19 after the local merge gate, update local `main`, and only then create the TASK-0006 worktree.

## Handoff

TASK-0006 must evaluate the exact canonical record IDs emitted by this adapter; it must not rebuild a different comparison dataset.
