# EXP-20260921-019-calibrated-judge-study

This report studies rubric-grounded judge construction, split-safe confidence calibration, and independent head-to-head comparison.

Luna and Sol are excluded from the primary study under the vendor-independent orchestrator policy. Their historical artifacts are not used in the tables, pairwise analyses, calibration, adjudication, or conclusions.

## Method

The report reuses the exact EXP-015 pool and typed System-One packet. Gold labels come from benchmark answer keys and deterministic verifiers. Local Qwen 4B probabilities are calibrated with scalar temperature scaling fit only on public-selection records, separately for single and pairwise judgments. External arms are label-only unless they provide a validated probability map; no probability metrics are invented from prose or labels.

## Blind head-to-head results

| Arm | Resolved labels | Accuracy | Balanced accuracy | Macro F1 | 95% Wilson interval |
|---|---:|---:|---:|---:|---|
| Grok Build | 756 | 0.4378 | 0.2693 | 0.1604 | [0.4029, 0.4734] |
| Jev | 760 | 0.9000 | 0.9263 | 0.7483 | [0.8766, 0.9194] |
| Qwen Flash | 759 | 0.9750 | 0.9700 | 0.7814 | [0.9612, 0.9839] |
| Local Qwen 4B | 760 | 0.4461 | 0.3156 | 0.2000 | [0.4111, 0.4816] |

Execution status is retained in the machine-readable artifact for auditability; it is not treated as a model-quality outcome in this study.

## Protocol diagnostics

Grok's blind labels are `{'A': 12, 'B': 1, 'TIE': 94, 'fail': 646, 'pass': 3}`. Its single-record accuracy is `0.5038520801232665` and its pairwise accuracy is `0.037383177570093455`. This mode asymmetry is retained as a protocol diagnostic rather than generalized into a claim about all Grok capability.
A separate direct Grok Build diagnostic used `8` records with streaming enabled, returned `{'ok': 8}`, and surfaced `['grok-4.6-build']`. It reproduced the same mode asymmetry: single accuracy `0.5` and pairwise accuracy `0.0`.

## Same-record agreement

| Pair | Comparable | Agreement |
|---|---:|---:|
| grok vs. jev | 756 | 0.4246 |
| grok vs. qwen_flash | 755 | 0.4411 |
| grok vs. local_qwen4b | 756 | 0.0952 |
| jev vs. qwen_flash | 759 | 0.8999 |
| jev vs. local_qwen4b | 760 | 0.4658 |
| qwen_flash vs. local_qwen4b | 759 | 0.4440 |

## Calibration results

Calibration changes confidence values, not selected labels. The blind local-Qwen result is:

| View | Accuracy | Brier | NLL | ECE |
|---|---:|---:|---:|---:|
| raw | 0.4461 | 0.7037 | 1.0767 | 0.3411 |
| calibrated | 0.4461 | 0.5160 | 0.7430 | 0.0783 |

Fitted temperatures: single `6.864867`; pairwise `403.428793`.
Fitted temperatures are recorded in the calibration artifact and were fit on public-selection labels only. Accuracy and label metrics are unchanged by temperature scaling; Brier, NLL, and ECE are the calibration outcomes.

## Rubric/protocol robustness

Jev's existing robustness canary reports repeatability `1.0`, option-order agreement `1.0`, and rubric-paraphrase agreement `0.9166666666666666`. These are descriptive robustness checks, not objective gold substitutions.

## Limitations

The head-to-head external arms do not expose validated native probabilities in the completed artifacts, so their calibration cannot be ranked. The local-Qwen calibration result is therefore a method demonstration, not evidence that every provider route has calibrated confidence. The study measures objective typed decisions and does not establish universal subjective human-evaluation quality.
