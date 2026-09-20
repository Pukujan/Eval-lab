# Test Design Document — Eval Lab

## 1. Test goals

Tests protect scientific validity as well as code correctness.

The highest-risk failures are:

- train/calibration/test leakage
- mislabeled gold provenance
- probability normalization errors
- silently dropped provider failures
- A/B order bugs
- mutated completed experiment artifacts
- reports generated from different inputs than claimed

## 2. Test layers

### Unit tests

No network access.

Cover:

- schema validation
- split grouping by source problem
- verifier behavior
- probability normalization
- calibration fitting and serialization
- metric calculations
- perturbation transforms
- experiment manifest validation

### Contract tests

Validate repository and experiment layout.

Examples:

- required design docs exist
- active task/checkpoint files are parseable
- experiment IDs follow naming convention
- completed experiments contain required provenance fields

### Integration tests

May require provider credentials and must be skipped cleanly without them.

Initial integration target: Jev smoke test.

### Reproducibility tests

Given fixed synthetic data and seed, produce byte-stable or numerically stable metrics within declared tolerance.

## 3. Required tests before merge

Every PR must pass:

```bash
python scripts/check_repo_contract.py
ruff check .
pytest -q
```

Provider integration tests are not mandatory for ordinary PRs unless the PR changes that provider adapter.

## 4. Scientific invariants

INV-1: no `source_problem_id` appears in multiple splits.

INV-2: calibration code cannot consume test labels during fitting.

INV-3: objective gold provenance is never `model` unless explicitly marked weak supervision.

INV-4: A/B swap perturbation also swaps the expected pairwise label.

INV-5: probability vectors sum to one within tolerance.

INV-6: experiment manifests capture code commit, model ID, prompt/rubric version, and dataset fingerprint.

INV-7: completed experiment results are append-only.

## 5. Acceptance testing for TASK-0001

- clean install on Python 3.11+
- repo contract validator succeeds
- unit tests succeed without credentials
- Jev smoke test is runnable when `OPENCODE_API_KEY` is set
- first synthetic dataset can be scored locally
