# Product Design Document — Eval Lab

## 1. Problem

LLM-as-a-judge systems are convenient but can be expensive, opaque, biased, and poorly calibrated. Small local models are cheaper but may lack general reasoning ability. Structured classification systems such as Jev may be a better fit for rubric evaluation, but claims need objective measurement.

Eval Lab provides a repeatable way to answer that question.

## 2. Users

Primary users are researchers and engineers comparing judge systems, developing evaluators, or deciding when a cheap judge can safely replace or precede a stronger judge.

Secondary users are autonomous coding/research agents that must continue experiments without shared conversational memory.

## 3. Core jobs

The lab must support:

- importing public benchmark examples
- deriving objective gold labels from answer keys or deterministic verifiers
- constructing single-answer and pairwise judge tasks
- running multiple judges over identical records
- storing raw scores/probabilities when available
- fitting calibration without test leakage
- evaluating bias/consistency under controlled perturbations
- comparing latency, cost, and selective risk
- handing work between agents using Git-native state

## 4. Product principles

### Objective first

Prefer executable or answer-key truth over model opinion.

### Separate truth from explanation

A strong teacher may explain a failure or generate hard examples, but its analysis is stored separately from gold provenance.

### Reproducible by default

Every reported result must be traceable to a committed experiment configuration, dataset fingerprint, code commit, and model identifier.

### Short-context first

The first system targets realistic low-resource local hardware. The default judge input budget is 4,096 tokens.

### Calibration is first-class

A judge that knows when it is uncertain can be more useful than a slightly more accurate but overconfident judge.

### Git is project memory

Task and experiment state must live in the repository rather than only in chats.

## 5. v0 scope

Domains:
- arithmetic / short math
- multiple-choice knowledge and reasoning
- machine-checkable instruction following
- structured-output validation
- simple code/output verification

Judges:
- Jev direct and atomic protocols
- Qwen3-0.6B required local feasibility baseline
- Qwen3-1.7B preferred stronger local baseline
- Qwen3-4B optional stretch baseline

Public benchmark:
- ARC-Challenge as the first external objective benchmark

Optional analysis-only teachers:
- Luna
- Sol
- Grok

## 6. Functional requirements

FR-1: canonical examples preserve source IDs and split provenance.

FR-2: variants derived from one source problem cannot cross train/dev/calibration/test boundaries.

FR-3: every gold label records a provenance type and evidence.

FR-4: judge adapters expose normalized predictions and, when available, class probabilities/raw scores.

FR-5: provider errors expose an execution status distinct from prediction labels.

FR-6: calibration fits only on the calibration split.

FR-7: final test evaluation never tunes prompts, thresholds, rubrics, or calibration parameters.

FR-8: perturbation tests include A/B swap and rubric paraphrase where meaningful.

FR-9: reports contain aggregate and per-domain results.

FR-10: experiments are immutable after completion.

FR-11: every active task has a checkpoint.

FR-12: every public dataset run records source revision, license, and fingerprint.

FR-13: every local-model run records hardware-relevant runtime metadata and context cap.

## 7. Required v0 deliverables

D-1: canonical Pydantic data schema.

D-2: deterministic synthetic fixture suite with at least four domains.

D-3: Jev runner supporting direct and criterion-decomposed classification.

D-4: metrics/calibration library and report generator.

D-5: ARC-Challenge adapter with pinned/fingerprinted source metadata.

D-6: at least one locally runnable Qwen baseline on the same canonical records.

D-7: first comparison report with uncertainty/coverage metrics where probabilities exist.

## 8. Quality requirements

- deterministic local tests
- no hidden dependency on old branches or chat history
- no secrets in Git
- unit tests run without paid API access
- provider tests are explicit integration tests
- quota/rate-limit errors are preserved as execution state
- failures preserve enough metadata for audit without leaking secrets
- no reported test metric may be computed from examples used to fit calibration

## 9. Acceptance criteria for v0

A fresh clone can:

1. install dependencies;
2. validate repository and program contracts;
3. reproduce synthetic canonical records;
4. run unit tests without credentials;
5. run Jev when quota/credentials allow;
6. reproduce calibration from a separate calibration split;
7. load and fingerprint ARC-Challenge;
8. run at least Qwen3-0.6B locally or document a concrete runtime incompatibility and use an approved lighter fallback;
9. regenerate the v0 comparison report;
10. resume from `checkpoints/CURRENT.md` and one task file.

## 10. TASK-0010 publication and selective-escalation requirements

FR-14: deterministic confidence-threshold routing with explicit unresolved provider-failure state.

FR-15: threshold/provider/spec selection cannot consume final-evaluation labels.

FR-16: calibrated routing is compared against raw-confidence and matched-random escalation controls.

FR-17: low-error coverage claims include sample counts and uncertainty bounds.

FR-18: pinned OpenRouter Jev and rolling Jev alias are distinct model arms.

FR-19: a backend-neutral typed decision specification can be executed by Jev and an LLM-backed System-One adapter without changing legal labels/semantics.

FR-20: TASK-0010 produces a semantic-versioned compact benchmark release with deterministic reconstruction and checksums.

FR-21: TASK-0010 produces an arXiv-ready paper whose headline tables/figures are generated from committed result artifacts.

FR-22: benchmark, experiment, model, calibration, thresholds, results, tables, and paper have machine-readable provenance.

FR-23: research artifact validation is offline-capable and does not require provider credentials.

Additional deliverables:
- D-8: EvalLab-Select v0.1.0 benchmark release.
- D-9: RO-Crate 1.3 research-object metadata.
- D-10: PROV-O provenance graph plus stable SHACL validation shapes.
- D-11: CITATION.cff 1.2.0 and DataCite-compatible release metadata.
- D-12: arXiv-ready LaTeX paper source with reproducibility and limitations appendices.

A negative or underpowered result is acceptable. The requirement is traceable evidence and calibrated claims, not a predetermined positive result.
