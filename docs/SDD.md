# System Design Document — Eval Lab

## 1. Architecture

```
public benchmark
      |
      v
benchmark adapter
      |
      v
canonical source record
      |
      +--> deterministic verifier / answer key --> objective gold
      |
      +--> candidate generator / corruption logic
      |
      v
judge record
      |
      +--> Jev adapter
      +--> local generative adapter
      +--> encoder classifier adapter
      +--> optional external teacher adapter
      |
      v
normalized predictions
      |
      +--> metrics
      +--> calibration
      +--> perturbation analysis
      |
      v
experiment artifact + report
```

## 2. Core modules

Planned package layout:

```
src/eval_lab/
  schema.py
  datasets/
  verifiers/
  judges/
  calibration/
  metrics/
  experiments/
  reporting/
```

### schema

Owns Pydantic/dataclass representations for source records, judge records, predictions, gold provenance, and experiment metadata.

### datasets

Adapters from external benchmark schemas into canonical records. No evaluation logic belongs here.

### verifiers

Deterministic or executable truth functions. Each verifier returns a verdict plus structured evidence.

### judges

Provider/model adapters. Each adapter maps canonical judge input to a normalized prediction.

Normalized prediction should include:

- label
- probability distribution if available
- raw score/logit metadata if available
- model identifier
- prompt/rubric version
- latency
- token accounting if exposed
- provider error metadata

### calibration

Pure post-processing over frozen predictions. Initial methods:

- temperature scaling where logits exist
- Platt/logistic scaling for scalar margins
- isotonic regression when sample size supports it

### metrics

Accuracy, balanced accuracy, macro F1, Brier, NLL, ECE, consistency, latency/cost, and risk/coverage.

### experiments

Loads experiment configuration, resolves dataset splits and judge adapters, runs evaluation, and writes immutable artifacts.

### reporting

Produces machine-readable JSON plus concise Markdown summaries.

## 3. Canonical record

Minimum fields:

```yaml
id:
domain:
source_dataset:
source_problem_id:
split:
prompt:
reference:
rubric:
candidate_a:
candidate_b:
gold:
  label:
  provenance:
  evidence:
metadata:
```

Single-candidate tasks may omit `candidate_b`.

## 4. Split discipline

Split by `source_problem_id`, not by generated variant.

A source problem and all of its perturbations/candidates belong to exactly one split.

Recommended initial proportions:

- dev: 15%
- calibration: 20%
- test: 30%
- training/reserve: 35%

Exact ratios can differ by benchmark but must be declared before test evaluation.

## 5. Experiment identity

Experiment IDs use:

```
EXP-YYYYMMDD-NNN-short-name
```

A completed experiment is immutable. Any change to model, prompt, rubric, dataset fingerprint, split mapping, code commit, calibration method, or seed requires a new experiment ID.

## 6. Task/worktree architecture

Every task gets:

- GitHub issue or task file
- branch `task/TASK-XXXX-short-name`
- optional worktree with the same task ID
- checkpoint updates in the task file
- PR back to `main`

Two agents should not share one worktree.

Cross-task dependencies are recorded in task metadata rather than inferred from chats.

## 7. Provider boundary

Provider credentials are environment variables. Provider-specific response bodies must be normalized before downstream evaluation.

The codebase must remain runnable without Luna/Sol/Grok access.

## 8. Local hardware strategy

Local judge adapters must support configurable context caps. v0 default: 4,096 tokens.

The framework should allow quantized local models but must record quantization format and runtime in experiment metadata.

## 9. Failure handling

Provider failures are not silently converted to wrong labels. They are recorded as execution failures and reported separately.

Verifier uncertainty or ambiguity must be represented explicitly rather than forced into a binary gold label.
