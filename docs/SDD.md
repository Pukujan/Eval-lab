# System Design Document — Eval Lab

## 1. Architecture

~~~
public/synthetic source
      |
      v
dataset adapter
      |
      v
SourceRecord
      |
      +--> verifier / answer key --> GoldLabel
      |
      +--> candidate construction
      |
      v
JudgeRecord
      |
      +--> Jev adapter
      +--> local Qwen adapter
      |
      v
JudgePrediction
      |
      +--> metrics
      +--> calibration
      +--> perturbation analysis
      |
      v
experiment artifacts + report
~~~

## 2. Planned package layout

~~~
src/eval_lab/
  schema.py
  datasets/
    synthetic.py
    arc.py
  verifiers/
    arithmetic.py
    multiple_choice.py
    structured.py
    code_output.py
  judges/
    base.py
    jev.py
    qwen.py
  calibration/
    temperature.py
    binary.py
    isotonic.py
  metrics/
    classification.py
    calibration.py
    consistency.py
    risk.py
  experiments/
    runner.py
    manifests.py
  reporting/
    report.py
~~~

Existing modules may be moved only when the active task allows it.

## 3. Canonical schema contract

TASK-0002 implements these concepts. Exact Pydantic field names may vary only if tests and docs are updated consistently.

### Split

Allowed values:
- train
- dev
- calibration
- test

### GoldProvenance

Allowed values:
- deterministic_verifier
- answer_key
- executable_test
- human_adjudication
- weak_model_supervision

The first four may be treated as objective/trusted according to experiment policy. weak_model_supervision is never silently reported as objective gold.

### JudgmentMode

- single
- pairwise

### PairwiseLabel

- A
- B
- TIE

### ExecutionStatus

- ok
- rate_limited
- provider_error
- parse_error
- skipped

### SourceRecord

Required semantics:
- stable id
- domain
- source_dataset
- source_problem_id
- split
- prompt
- reference/answer-key data
- source metadata

### RubricCriterion

Required semantics:
- stable criterion id
- human-readable description
- optional weight
- optional deterministic aggregation rule metadata

### GoldLabel

Required semantics:
- label
- provenance
- evidence
- verifier/version identifier when applicable

### JudgeRecord

Required semantics:
- stable record id
- source_problem_id
- mode
- prompt
- rubric
- candidate_a
- optional candidate_b
- gold
- split
- perturbation metadata

### JudgePrediction

Required semantics:
- record id
- judge id/model
- protocol/prompt version
- label when status is ok
- probability map when supported
- raw class scores when supported
- execution status
- latency
- token usage when exposed
- provider/runtime metadata
- error metadata without secrets

## 4. Split discipline

Split assignment is a pure deterministic function of source_problem_id plus declared seed/policy.

Every variant derived from a source problem inherits the same split.

No code path may randomly split JudgeRecord variants independently.

## 5. Dataset fingerprint contract

A dataset artifact fingerprint includes, at minimum:
- adapter name/version
- source dataset identifier
- resolved upstream revision when external
- source split selection
- canonicalization version
- deterministic split policy + seed
- hash of canonical record IDs/content metadata sufficient to detect drift

## 6. Judge interface

Conceptual interface:

~~~python
class Judge:
    def predict(self, records: list[JudgeRecord]) -> list[JudgePrediction]:
        ...
~~~

Adapters may be synchronous or asynchronous internally but must emit the same normalized prediction schema.

## 7. Jev protocols

### jev-direct-v1

Single:
- typed PASS/FAIL decision

Pairwise:
- typed A/B/TIE decision

### jev-atomic-v1

Ask typed criterion-level questions. Aggregate criterion outcomes in deterministic repository code. The provider must not secretly determine an undocumented overall rule.

Returned provider probabilities are retained.

Rate limiting:
- parse Retry-After when present
- return ExecutionStatus.rate_limited
- never fabricate a label
- no automatic multi-hour waiting

## 8. Calibration boundary

Calibration takes frozen predictions plus calibration labels and produces a CalibrationArtifact.

CalibrationArtifact records:
- method
- fitted parameters
- fit split
- class order
- input score/probability semantics
- code version

The API must reject fitting when any input record is split=test.

## 9. ARC-Challenge adapter

TASK-0005 source:
- Hugging Face dataset id: allenai/ai2_arc
- config: ARC-Challenge
- license metadata expected: CC BY-SA 4.0

The adapter must resolve and record the upstream revision used.

Initial canonical conversion:
- prompt = question + labeled answer choices
- answer key = objective gold
- construct deterministic correct and incorrect candidate answers from existing choices
- pairwise A/B order randomized deterministically by source ID/seed
- no LLM-generated candidates required for the first benchmark

Recommended split mapping:
- upstream train -> train/reserve
- upstream validation -> deterministic dev/calibration partition by source ID
- upstream test -> test

Any alternative mapping must be preregistered and tested.

## 10. Local Qwen scoring

TASK-0006 baseline order:
1. Qwen3-0.6B
2. Qwen3-1.7B if feasible
3. Qwen3-4B optional

Default runtime may use Transformers/PyTorch on Windows.

For calibrated classification, prefer forced-choice sequence scoring:
- construct the judge prompt ending at the verdict boundary
- compute conditional log-likelihood of each legal label continuation
- normalize scores with softmax
- emit probabilities and raw log-scores

Do not rely on free-form sampled explanations to derive confidence.

Context cap defaults to 4,096 tokens; a lower cap is permitted if declared before comparison.

## 11. Artifact layout

~~~
outputs/
  runs/<run-id>/
    manifest.json
    predictions.jsonl
    metrics.json
    calibration.json
    report.md
~~~

outputs is gitignored unless a task explicitly promotes a small stable artifact into an experiment directory.

## 12. Failure handling

Provider/runtime failures are counted in reliability summaries but are not silently scored as wrong classifications.

Malformed prediction outputs are parse_error.

Verifier uncertainty is represented explicitly; ambiguous examples should be excluded or adjudicated according to preregistered rules rather than forced into objective gold.

## 13. Task/worktree architecture

Each task:
- starts from the latest accepted main
- gets branch `task/TASK-XXXX-short-name`
- gets one local worktree
- updates only declared files unless task scope is checkpointed first
- records local validation before handoff
- merges before the dependent task starts
