# Test Design Document — Eval Lab

## 1. Test goals

Tests protect scientific validity as well as code correctness.

Highest-risk failures:
- split leakage
- mislabeled gold provenance
- invalid probability normalization
- provider failures counted as wrong labels
- A/B order bugs
- calibration fit on test labels
- dataset drift without fingerprint change
- local judge comparisons using different examples/context caps
- completed experiment mutation

## 2. Required local merge gate

Every task must run:

~~~powershell
.venv\Scripts\python.exe scripts/check_repo_contract.py
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m pytest -q
~~~

If the environment uses a different shell, equivalent commands are acceptable.

GitHub Actions is desirable but is not the source of truth while the repository/account has no assigned runner. Record local evidence in the task checkpoint.

## 3. Test layers

### Unit tests

No network:
- schemas
- split logic
- verifiers
- probability validation
- provider-response parsing via mocks
- metrics
- calibration
- perturbations
- dataset canonicalization from small local fixtures

### Contract tests

- required project/program docs exist
- task 0002-0006 files exist
- required task headings exist
- dependency order is declared
- completed experiments contain required artifacts

### Integration tests

May use external services/data:
- Jev live smoke
- ARC source retrieval
- local model download/inference

They must fail or skip with an explicit external status, never masquerade as unit-test failure.

### Reproducibility tests

Fixed source IDs + seed must reproduce:
- split assignments
- candidate order
- fixture IDs
- dataset fingerprint
- metrics within numeric tolerance

## 4. Scientific invariants

INV-1: one source_problem_id belongs to exactly one split.

INV-2: calibration fitting rejects any test-split labels.

INV-3: weak_model_supervision cannot be reported as deterministic/objective provenance.

INV-4: pairwise A/B swap maps A->B, B->A, TIE->TIE.

INV-5: probability vectors contain finite values in [0,1] and sum to 1 within tolerance.

INV-6: prediction status != ok implies no scored classification label unless explicitly documented.

INV-7: experiment manifests capture code commit, model ID, prompt/protocol version, dataset fingerprint, context cap, and seed.

INV-8: completed experiment results are append-only.

INV-9: public dataset source revision/fingerprint changes require a new experiment identity.

INV-10: systems in one comparison use the same canonical record IDs.

## 5. TASK-0002 validation

Required tests:
- schema accepts valid single record
- schema accepts valid pairwise record
- pairwise record rejects missing candidate B
- probabilities reject negative, >1, NaN, or non-normalized vectors
- gold provenance serialization round-trip
- source variants inherit one split
- deliberate cross-split source collision is rejected
- swap transform reverses A/B gold and candidates
- TIE remains TIE under swap
- deterministic fixture generation is byte/content stable for fixed seed
- at least four fixture domains exist

## 6. TASK-0003 validation

Mock tests:
- Jev direct 200 response normalizes label/probabilities
- Jev atomic response normalizes criterion results
- 429 maps to rate_limited and preserves Retry-After
- 5xx maps to provider_error
- malformed provider payload maps to parse_error
- API key never appears in serialized error metadata
- pairwise class order is stable

Live test:
- optional when quota available
- successful live prediction records provider/model/protocol metadata
- live 429 is an external blocked condition, not task failure after mock coverage passes

## 7. TASK-0004 validation

Known-value tests:
- accuracy/balanced accuracy/macro F1 on hand-computed arrays
- multiclass Brier on hand-computed probabilities
- NLL on known probabilities
- ECE on a small known-bin example
- risk/coverage monotonic coverage ordering
- A/B swap consistency from paired record IDs

Calibration tests:
- fit rejects test split
- temperature T remains positive
- serialization round-trip preserves fitted outputs
- calibration improves or leaves unchanged NLL on a controlled synthetic calibration example
- isotonic/Platt output remains bounded

## 8. TASK-0005 validation

- adapter loads ARC-Challenge source metadata
- license metadata is recorded
- resolved source revision is recorded
- canonicalization from a small mocked ARC row matches schema
- upstream answerKey becomes answer_key provenance
- deterministic wrong candidate is not equal to correct key
- upstream source ID remains source_problem_id
- validation->dev/calibration mapping is deterministic
- source_problem_id never crosses mapped splits
- fingerprint is stable for the same resolved source/revision
- a changed revision/canonicalization version changes fingerprint

## 9. TASK-0006 validation

Feasibility:
- model/runtime loads without exhausting machine resources
- 20-record smoke run finishes and records latency
- context cap is enforced

Scoring:
- forced-choice class set is exactly legal labels
- returned probabilities normalize
- raw score ordering corresponds to probability ordering
- no sampled explanation is required for verdict

Comparison:
- local and reference systems evaluate identical record IDs
- aggregate and per-domain metrics render
- unavailable probability metrics are marked unavailable rather than imputed

## 10. Program acceptance test

After TASK-0006, one command or documented command sequence must reproduce:
- canonical fixture set
- one public ARC evaluation slice
- one local model prediction file
- metrics
- calibration artifact where supported
- final comparison report

## 11. TASK-0010 selective escalation and publication validation

Core unit tests:
- threshold boundaries and monotonic coverage
- deterministic record routing
- explicit unresolved provider failures
- matched random escalation count
- binomial confidence-bound calculations
- pinned/canary Jev model identity separation
- typed-question schema normalization

The normative metamorphic/differential list is `docs/TASK-0010-METAMORPHIC-DIFFERENTIAL.md`; all offline invariants are merge-blocking.

Leakage tests:
- final-evaluation labels cannot enter threshold selection
- provider/spec choice cannot depend on final labels
- source families cannot cross threshold-selection/final partitions
- paper-generation code may read final results only after preregistration freeze

Statistical validation reports local accepted N, observed errors, empirical risk, and 95% interval/upper bound at each low-error operating point.

Research artifact validation:
- deterministic benchmark rebuild preserves IDs/checksums
- source manifest references pinned upstream revisions
- RO-Crate parses as required JSON-LD structure
- PROV graph parses as RDF
- SHACL positive fixture conforms
- negative fixtures missing required identity/provenance fail
- benchmark checksums match files
- paper tables match results.json within declared formatting tolerance
- CFF 1.2.0 validates once final citation metadata is written

Offline reproduction must regenerate routing summaries, risk-coverage data, result tables, paper tables/figures, and benchmark checksums without provider credentials.

If a LaTeX compiler is available, the archived `paper/archive/selective-escalation/main.tex` must compile; a missing local TeX installation is recorded separately from source validation.
