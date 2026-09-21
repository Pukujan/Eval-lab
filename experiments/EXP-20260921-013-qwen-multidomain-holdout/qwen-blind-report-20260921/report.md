# EXP-20260921-013 — blind_holdout report

Source predictions: `experiments\EXP-20260921-013-qwen-multidomain-holdout\qwen-blind-merged-20260921`

Provider: `yolo-auto`; model: `qwen3.8-flash`.
Gold labels were used only after provider execution for scoring. Provider failures remain unresolved.

| Dataset | Records | Resolved | Accuracy | 95% CI | Balanced accuracy | Macro-F1 | Unresolved | p95 ms | Statuses |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| `allenai/ai2_arc:ARC-Easy` | 100 | 100 | 0.9700 | [0.9155, 0.9897] | 0.9700 | 0.6498 | 0.0000 | 991.6947 | `{'ok': 100}` |
| `cais/mmlu:abstract_algebra` | 40 | 40 | 0.9000 | [0.7695, 0.9604] | 0.9000 | 0.9000 | 0.0000 | 878.8353 | `{'ok': 40}` |
| `cais/mmlu:computer_security` | 40 | 40 | 0.8250 | [0.6805, 0.9125] | 0.8250 | 0.8240 | 0.0000 | 999.2819 | `{'ok': 40}` |
| `cais/mmlu:elementary_mathematics` | 40 | 40 | 0.9000 | [0.7695, 0.9604] | 0.9000 | 0.8997 | 0.0000 | 1067.2525 | `{'ok': 40}` |
| `cais/mmlu:high_school_biology` | 40 | 40 | 1.0000 | [0.9124, 1.0000] | 1.0000 | 1.0000 | 0.0000 | 769.6903 | `{'ok': 40}` |
| `cais/mmlu:high_school_world_history` | 40 | 40 | 0.9750 | [0.8712, 0.9956] | 0.9750 | 0.9750 | 0.0000 | 1037.4576 | `{'ok': 40}` |
| `cais/mmlu:logical_fallacies` | 40 | 38 | 0.8684 | [0.7267, 0.9425] | 0.8667 | 0.8676 | 0.0500 | 801.3024 | `{'ok': 38, 'parse_error': 2}` |
| `cais/mmlu:machine_learning` | 40 | 39 | 0.7949 | [0.6447, 0.8922] | 0.7974 | 0.7937 | 0.0250 | 1007.4978 | `{'parse_error': 1, 'ok': 39}` |
| `cais/mmlu:professional_law` | 40 | 38 | 0.8421 | [0.6958, 0.9256] | 0.8421 | 0.8417 | 0.0500 | 1001.1066 | `{'ok': 38, 'parse_error': 2}` |
| `eval-lab-select-v0.1.0` | 120 | 120 | 0.9917 | [0.9543, 0.9985] | 0.9917 | 0.9917 | 0.0000 | 796.8542 | `{'ok': 120}` |
| `eval-lab-synthetic:arithmetic` | 5 | 5 | 0.6000 | [0.2307, 0.8824] | 0.6250 | 0.5000 | 0.0000 | 1126.6262 | `{'ok': 5}` |
| `eval-lab-synthetic:code` | 5 | 5 | 1.0000 | [0.5655, 1.0000] | 1.0000 | 1.0000 | 0.0000 | 454.1285 | `{'ok': 5}` |
| `eval-lab-synthetic:multiple` | 5 | 4 | 0.2500 | [0.0456, 0.6994] | 0.2500 | 0.1333 | 0.2000 | 4113.8983 | `{'ok': 4, 'parse_error': 1}` |
| `eval-lab-synthetic:structured` | 5 | 5 | 0.2000 | [0.0362, 0.6245] | 0.1250 | 0.1000 | 0.0000 | 593.3304 | `{'ok': 5}` |
| `openai/gsm8k:main` | 200 | 200 | 0.6550 | [0.5868, 0.7174] | 0.6550 | 0.6519 | 0.0000 | 1048.7486 | `{'ok': 200}` |

Overall resolved accuracy: `0.8448`; unresolved rate: `0.0079`.
Overall accuracy 95% interval: `{'lower': 0.8172424224982658, 'upper': 0.868916923823578}`.
Qwen probabilities/logprobs were unavailable, so calibration metrics are not claimed.
