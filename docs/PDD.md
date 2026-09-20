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
- storing raw probabilities when available
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

- multiple-choice knowledge/reasoning
- arithmetic and short-form math
- machine-checkable instruction following
- structured output validation
- small executable code/output tasks when sandboxing is available

Judges:

- Jev
- Qwen3-1.7B
- Qwen3-4B
- compact encoder classifier

Optional analysis-only teachers:

- Luna
- Sol
- Grok

## 6. Functional requirements

FR-1: canonical examples preserve source IDs and split provenance.

FR-2: variants derived from one source problem cannot cross train/dev/calibration/test boundaries.

FR-3: every gold label records a provenance type.

FR-4: judge adapters expose normalized predictions and, when available, class probabilities.

FR-5: calibration fits only on the calibration split.

FR-6: final test evaluation never tunes prompts, thresholds, or rubrics.

FR-7: perturbation tests include A/B swap and rubric paraphrase where meaningful.

FR-8: reports contain aggregate and per-domain results.

FR-9: experiments are immutable after completion.

FR-10: every active task has a checkpoint.

## 7. Quality requirements

- deterministic runs when the provider/model supports it
- no hidden dependency on old branches or chat history
- no secrets in Git
- local unit tests run without paid API access
- paid/free provider tests are explicitly marked integration tests
- failures preserve raw request/response metadata where policy permits

## 8. Acceptance criteria for v0

A fresh clone can:

1. install dependencies;
2. run unit tests;
3. validate repository contract;
4. execute a local synthetic/objective evaluation;
5. optionally call Jev when a key is present;
6. generate metrics and a calibration report;
7. resume work from `checkpoints/CURRENT.md` and a task file.
