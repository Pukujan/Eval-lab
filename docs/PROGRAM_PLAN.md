# Eval Lab Program Plan — TASK-0002 through TASK-0009

## Purpose

Build the measurement foundation first, then fully utilize the user's existing model subscriptions/resources for a controlled external-model bakeoff, verified teacher augmentation, and a small-judge training pilot.

## Sequence

1. TASK-0002 — canonical schema + deterministic fixtures.
2. TASK-0003 — Jev Free objective baseline.
3. TASK-0004 — metrics, calibration, and selective-risk analysis.
4. TASK-0005 — ARC-Challenge public benchmark adapter.
5. TASK-0006 — lightweight local judge baseline.
6. TASK-0007 — external judge and teacher bakeoff.
7. TASK-0008 — verified teacher-assisted hard negatives.
8. TASK-0009 — small-judge training and calibration pilot.

If Jev remains rate-limited, TASK-0003 may close implementation-complete/provider-blocked after local/mock contract tests pass. Later tasks continue.

## Program invariants

- Objective gold never comes solely from an LLM judgment.
- Variants sharing one source_problem_id never cross split boundaries.
- Calibration fit never consumes test labels.
- Provider failure is distinct from a wrong answer.
- Every prediction records provider, model, protocol/access path, and execution status.
- Subscription-covered resources should be used when relevant and technically available.
- A subscription/free failure must not silently fall back to a separately metered endpoint.
- Teacher identity remains separate from gold provenance.
- Teacher-generated objective examples require independent re-verification.
- Completed experiments are immutable.

## TASK-0002 — Canonical schema and deterministic fixtures

Implement the stable SourceRecord/JudgeRecord/GoldLabel/JudgePrediction contracts, deterministic split policy, provenance rules, and four synthetic objective domains.

## TASK-0003 — Jev Free objective baseline

Required model id: `jev-1.13-free`.

Required protocols:
- `jev-direct-v1`
- `jev-atomic-v1`

Do not automatically fall back to `jev-1.13`.

## TASK-0004 — Metrics and calibration

Implement accuracy, balanced accuracy, macro F1, Brier, NLL, ECE, A/B swap consistency, risk/coverage, target-error coverage, latency summaries, and post-hoc calibration. Fit calibration only on the calibration split.

## TASK-0005 — ARC-Challenge

Use `allenai/ai2_arc`, config `ARC-Challenge`. Record exact source revision, license, canonicalization version, split policy, and fingerprint.

## TASK-0006 — Lightweight local judge

Run the smallest viable local baseline first:
1. Qwen3-0.6B
2. Qwen3-1.7B if feasible
3. Qwen3-4B optional

Prefer forced-choice scoring with normalized probabilities when available.

## TASK-0007 — External judge and teacher bakeoff

Fully exercise the user's existing model access on the same frozen objective records.

Required/expected arms when available:
- Jev Free: `jev-1.13-free`
- YOLO-Auto Qwen3.8 Flash:
  - base URL `https://yolo-auto.com/v1`
  - model `qwen3.8-flash`
  - local key via `YOLO_AUTO_API_KEY`
- SuperGrok through supported subscription OAuth/OpenCode integration, exact surfaced model recorded
- OpenCode free general models, preferably `nemotron-3.5-lightning-free` and `mimo-v2.5-free`
- local Qwen from TASK-0006
- ChatGPT Luna and Sol as reproducible audit/teacher batch arms

TASK-0007 produces a model/access census, prediction coverage table, provider-failure summary, and comparison report.

## TASK-0008 — Verified teacher-assisted hard negatives

Use:
- YOLO-Auto Qwen3.8 Flash for bulk structured generation/critique
- SuperGrok for adversarial cases and failure analysis
- Luna for larger audit/triage batches
- Sol for the hardest disagreements and research audit
- selected OpenCode free models for diversity where useful

Generate subtle wrong answers, reasoning traps, requirement omissions, formatting failures, verbosity traps, rubric paraphrases, and A/B adversaries.

Every accepted objective example must be independently re-verified by deterministic verifier, answer key, structured constraint, or executable test.

## TASK-0009 — Small-judge training and calibration pilot

Student selection is evidence-gated from prior tasks:
- Qwen3-0.6B
- Qwen3-1.7B
- compact encoder classifier such as ModernBERT

Required ablations:
A. objective labels only
B. objective labels + teacher criterion critiques
C. objective labels + verified hard negatives
D. objective labels + critiques + verified hard negatives
E. best arm + post-hoc calibration

Use source-family-separated train/dev/calibration/test sets and untouched OOD/meta-evaluation.

## Final program output

Report every successfully exercised system on frozen objective records, including:
- access path
- execution coverage/failure rate
- accuracy
- Brier/NLL/ECE when probabilities exist
- swap consistency
- selective-risk coverage
- latency
- resource/cost metadata where available

Unavailable/blocked values are marked explicitly, never guessed.

## TASK-0010 — Selective escalation and research release

TASK-0010 is the active research phase after completed TASK-0009.

It evaluates the frozen local student's confidence as a routing signal, compares pinned OpenRouter Jev and YOLO-Auto Qwen3.8 Flash, adds matched-random controls and System-One differential testing, and publishes the result as EvalLab-Select v0.1.0 plus an arXiv-ready research report.

Scientific provenance follows `docs/RESEARCH_ARTIFACT_STANDARD.md`.
