# EXP-20260921-013 — blind_holdout report

Source predictions: `experiments\EXP-20260921-013-qwen-multidomain-holdout\qwen-blind-holdout-20260921`

Provider: `yolo-auto`; model: `qwen3.8-flash`.
Gold labels were used only after provider execution for scoring. Provider failures remain unresolved.

| Dataset | Records | Resolved | Accuracy | 95% CI | Balanced accuracy | Macro-F1 | Unresolved | p95 ms | Statuses |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| `allenai/ai2_arc:ARC-Easy` | 100 | 96 | 0.9688 | [0.9121, 0.9893] | 0.9700 | 0.6493 | 0.0400 | 858.1542 | `{'ok': 96, 'parse_error': 4}` |
| `cais/mmlu:abstract_algebra` | 40 | 25 | 0.9600 | [0.8046, 0.9929] | 0.9615 | 0.9600 | 0.3750 | 1074.5876 | `{'ok': 25, 'parse_error': 1, 'rate_limited': 14}` |
| `cais/mmlu:computer_security` | 40 | 0 | NA | NA | NA | NA | 1.0000 | 225.4909 | `{'rate_limited': 40}` |
| `cais/mmlu:elementary_mathematics` | 40 | 0 | NA | NA | NA | NA | 1.0000 | 216.5411 | `{'rate_limited': 40}` |
| `cais/mmlu:high_school_biology` | 40 | 0 | NA | NA | NA | NA | 1.0000 | 215.3120 | `{'rate_limited': 40}` |
| `cais/mmlu:high_school_world_history` | 40 | 0 | NA | NA | NA | NA | 1.0000 | 232.3680 | `{'rate_limited': 40}` |
| `cais/mmlu:logical_fallacies` | 40 | 0 | NA | NA | NA | NA | 1.0000 | 236.3210 | `{'rate_limited': 40}` |
| `cais/mmlu:machine_learning` | 40 | 0 | NA | NA | NA | NA | 1.0000 | 219.2864 | `{'rate_limited': 40}` |
| `cais/mmlu:professional_law` | 40 | 0 | NA | NA | NA | NA | 1.0000 | 231.1316 | `{'rate_limited': 40}` |
| `eval-lab-select-v0.1.0` | 120 | 119 | 0.9916 | [0.9539, 0.9985] | 0.9917 | 0.9916 | 0.0083 | 796.8542 | `{'ok': 119, 'parse_error': 1}` |
| `eval-lab-synthetic:arithmetic` | 5 | 0 | NA | NA | NA | NA | 1.0000 | 199.0734 | `{'rate_limited': 5}` |
| `eval-lab-synthetic:code` | 5 | 0 | NA | NA | NA | NA | 1.0000 | 183.8310 | `{'rate_limited': 5}` |
| `eval-lab-synthetic:multiple` | 5 | 0 | NA | NA | NA | NA | 1.0000 | 221.6815 | `{'rate_limited': 5}` |
| `eval-lab-synthetic:structured` | 5 | 0 | NA | NA | NA | NA | 1.0000 | 207.2534 | `{'rate_limited': 5}` |
| `openai/gsm8k:main` | 200 | 198 | 0.6515 | [0.5828, 0.7144] | 0.6524 | 0.6489 | 0.0100 | 1068.8730 | `{'ok': 198, 'parse_error': 2}` |

Overall resolved accuracy: `0.8311`; unresolved rate: `0.4237`.
Overall accuracy 95% interval: `{'lower': 0.793114914052673, 'upper': 0.8632291075654666}`.
Qwen probabilities/logprobs were unavailable, so calibration metrics are not claimed.
