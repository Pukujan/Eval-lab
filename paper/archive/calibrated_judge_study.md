# Building and Calibrating Rubric-Grounded Judges: An Independent Head-to-Head Study

## Abstract

This study presents an evaluation-lab method for constructing rubric-grounded
judge models and measuring calibration without treating a model's judgment as
objective truth. The method freezes canonical records, explicit rubrics, typed
legal labels, provenance-bearing gold labels, a public calibration partition,
and an untouched blind partition. It then compares independent judge routes on
the same packet and applies post-hoc temperature scaling only to validated
probability outputs. The primary included arms are direct xAI Grok Build,
Jev, YOLO-Auto Qwen Flash, and a locally hosted Qwen 3-4B judge. Luna and Sol
are excluded under the orchestrator's vendor-independent comparison policy.
Temperature scaling leaves local-Qwen labels unchanged but substantially
improves held-out Brier score, negative log likelihood, and expected
calibration error. The study demonstrates that a calibrated judge is a
protocol-and-measurement pipeline, not merely a model that emits a plausible
verdict.

## 1. Research question

The research question is:

> How do we construct a proper rubric-grounded, calibrated judge in Eval Lab,
> and how do independently implemented judges compare when given the same
> typed rubric packet?

This is a methodology study. It is not a claim that one provider is universally
the best judge, and it is not a provider-reliability study.

## 2. What makes a judge calibrated?

Eval Lab treats a judge as a pipeline with distinct layers:

1. **Rubric layer.** The record contains an explicit criterion and aggregation
   rule. Objective records use answer keys or deterministic verifiers as gold.
2. **Typed decision layer.** The judge receives a stable System-One packet and
   must return one legal label: `pass/fail` for single records or `A/B/TIE` for
   pairwise records.
3. **Normalization layer.** Every output is tied to a canonical record ID,
   model identity, protocol version, route, and execution status.
4. **Probability layer.** Confidence metrics are computed only when the judge
   supplies a validated probability map or a local scorer produces normalized
   class probabilities. A label or verbal confidence claim is not silently
   converted into probability.
5. **Calibration layer.** A calibrator is fit on a separate public calibration
   split and applied unchanged to the blind split. Calibration changes
   confidence values; it does not retrain the judge or change its argmax label.

This separation allows label accuracy, rubric robustness, confidence quality,
and execution missingness to be studied without conflating them.

## 3. Experimental design

The study reuses the exact frozen EXP-015 pool: 1,408 records total, with a
648-record public-selection partition and a 760-record blind holdout. The
typed System-One specification and source-problem-disjoint split are unchanged.

The primary included arms are:

| Arm | Route | Confidence role |
|---|---|---|
| Grok Build | direct authenticated xAI `grok` CLI | label-only in completed run |
| Jev | OpenRouter Jev-only route | label-only in completed run |
| Qwen Flash | YOLO-Auto `qwen3.8-flash` | label-only in completed run |
| Local Qwen 4B | local CUDA 4-bit forced-choice scorer | native local probabilities |

Luna and Sol are excluded from the primary study because the orchestrator
requires a vendor-independent comparison. Their historical artifacts remain
immutable but are not used for primary results, calibration, adjudication, or
paper conclusions. OpenCode is not used for any arm. OpenRouter is used only
for Jev.

## 4. Calibration method

The local Qwen judge scores each legal label by conditional log-likelihood and
normalizes the scores into a probability distribution. Scalar temperature
scaling is fit separately for single and pairwise judgments using only public
calibration labels:

\[
p_{calibrated}(y) = \operatorname{softmax}(\log p(y) / T).
\]

The fitted temperatures were:

- single judgments: `T = 6.864867`;
- pairwise judgments: `T = 403.428793`.

The large values indicate that the raw local-Qwen distributions were much too
sharp, especially for pairwise decisions. The blind labels were never used to
fit these values.

## 5. Results

### 5.1 Independent head-to-head labels

The blind comparison, excluding Luna and Sol, produced:

| Arm | Scored labels | Accuracy | Balanced accuracy | Macro F1 |
|---|---:|---:|---:|---:|
| Grok Build | 756 | 43.78% | 26.93% | 16.04% |
| Jev | 760 | 90.00% | 92.63% | 74.83% |
| Qwen Flash | 759 | 97.50% | 97.00% | 78.14% |
| Local Qwen 4B | 760 | 44.61% | 31.56% | 20.00% |

The Qwen Flash value uses the primary outputs plus the separately frozen retry
outputs for the exact records that lacked a first-pass label. It is reported as
accuracy over scored labels, not as a provider-reliability result.

Jev also showed strong typed-protocol robustness in its existing canary:
repeatability 1.0, option-order agreement 1.0, and rubric-paraphrase agreement
0.9167.

### 5.2 Local Qwen calibration

On the untouched blind holdout:

| View | Accuracy | Brier | NLL | ECE |
|---|---:|---:|---:|---:|
| Raw | 44.61% | 0.7037 | 1.0767 | 0.3411 |
| Calibrated | 44.61% | 0.5160 | 0.7430 | 0.0783 |

Calibration did not change the selected labels, accuracy, balanced accuracy,
or macro F1. It improved Brier score by approximately 26.7%, NLL by 31.0%,
and ECE by approximately 77.0%.

This is the central result: a judge can remain weak in classification while
becoming substantially more honest about its uncertainty. Calibration is not a
substitute for better reasoning or a better rubric.

### 5.3 Same-record agreement

Agreement rates on comparable blind records were:

| Pair | Agreement |
|---|---:|
| Grok–Jev | 42.46% |
| Grok–Qwen Flash | 44.11% |
| Grok–Local Qwen 4B | 9.52% |
| Jev–Qwen Flash | 89.99% |
| Jev–Local Qwen 4B | 46.58% |
| Qwen Flash–Local Qwen 4B | 44.40% |

Agreement is not correctness, but it reveals that the judges are not making
interchangeable decisions despite receiving the same typed packet.

## 6. Grok protocol diagnostic

The full direct Grok run returned 756 successful labels, and a separate
8-record streaming diagnostic returned 8/8 successful outputs with surfaced
model ID `grok-4.6-build`. The diagnostic used the direct xAI Build CLI and
streaming format `grok-streaming-json`.

The behavior was strongly mode-dependent. In the full blind run, Grok reached
approximately 50.4% on single records but only 3.7% on pairwise records. In the
diagnostic sample it returned `fail` for all four single records and `TIE` for
all four pairwise records.

This indicates a systematic typed-protocol or mode-interpretation problem in
this setup, not a general failure to return output. It should not be promoted
into a universal claim about Grok's overall capability.

## 7. What the study establishes

The study establishes a reproducible recipe for a rubric-calibrated judge:

- freeze the evidence packet and rubric before blind evaluation;
- preserve objective-gold provenance;
- require a typed legal label set;
- retain raw scores or native probabilities when available;
- fit calibration only on a declared calibration split;
- evaluate calibration separately from label accuracy;
- compare independent judges on the same records;
- never promote a strong model's output to gold merely because it is strong.

It also shows why “calibrated” must be used carefully. Luna, Jev, Grok, and
Qwen Flash did not expose validated probability maps in the completed runs, so
their labels can be compared head-to-head but their confidence cannot be ranked
with Brier, NLL, or ECE. Local Qwen is the completed demonstration of the
calibration method.

## 8. Limitations and next extensions

The benchmark is objective and typed; it does not establish quality on
subjective human-evaluation tasks. The external label-only arms need
provider-native probabilities or an independently justified confidence
interface before their calibration can be compared directly. The Grok mode
asymmetry also warrants a future prompt/protocol ablation. Any changed model,
prompt, rubric, calibration method, or benchmark requires a new experiment ID.

## 9. Reproducibility

Machine-readable results are in
`experiments/EXP-20260921-019-calibrated-judge-study/results.json`, generated
from the immutable EXP-014 through EXP-017 artifacts. The local calibration
artifact remains in EXP-017, and the direct Grok diagnostic is retained under
the EXP-019 diagnostics directory. No credentials, model weights, or caches
are committed.
