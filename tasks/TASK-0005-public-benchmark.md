# TASK-0005 — ARC-Challenge Public Benchmark Adapter

- Status: queued
- Owner: Luna/local agent
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

- [ ] source/config/license documented
- [ ] resolved revision recorded
- [ ] fingerprint stable for identical source+adapter
- [ ] upstream IDs preserved
- [ ] answerKey provenance correct
- [ ] candidate construction deterministic
- [ ] split mapping deterministic/no leakage
- [ ] small local sample canonicalizes
- [ ] evaluation slice manifest generated
- [ ] full local merge gate passes

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

## Handoff

TASK-0006 must evaluate the exact canonical record IDs emitted by this adapter; it must not rebuild a different comparison dataset.
