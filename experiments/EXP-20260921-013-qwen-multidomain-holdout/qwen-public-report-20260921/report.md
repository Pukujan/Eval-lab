# EXP-20260921-013 — public_selection report

Source predictions: `experiments\EXP-20260921-013-qwen-multidomain-holdout\qwen-public-merged-20260921`

Provider: `yolo-auto`; model: `qwen3.8-flash`.
Gold labels were used only after provider execution for scoring. Provider failures remain unresolved.

| Dataset | Records | Resolved | Accuracy | 95% CI | Balanced accuracy | Macro-F1 | Unresolved | p95 ms | Statuses |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| `allenai/ai2_arc:ARC-Easy` | 160 | 158 | 0.9747 | [0.9367, 0.9901] | 0.9751 | 0.9747 | 0.0125 | 11766.9881 | `{'ok': 158, 'parse_error': 2}` |
| `cais/mmlu:abstract_algebra` | 20 | 20 | 0.9000 | [0.6990, 0.9721] | 0.9000 | 0.9000 | 0.0000 | 1145.5401 | `{'ok': 20}` |
| `cais/mmlu:computer_security` | 20 | 20 | 0.9000 | [0.6990, 0.9721] | 0.9000 | 0.8990 | 0.0000 | 869.1285 | `{'ok': 20}` |
| `cais/mmlu:elementary_mathematics` | 20 | 20 | 0.8500 | [0.6396, 0.9476] | 0.8500 | 0.8496 | 0.0000 | 1005.9583 | `{'ok': 20}` |
| `cais/mmlu:high_school_biology` | 20 | 20 | 0.9000 | [0.6990, 0.9721] | 0.9000 | 0.9000 | 0.0000 | 690.0154 | `{'ok': 20}` |
| `cais/mmlu:high_school_world_history` | 20 | 20 | 1.0000 | [0.8389, 1.0000] | 1.0000 | 1.0000 | 0.0000 | 762.6556 | `{'ok': 20}` |
| `cais/mmlu:logical_fallacies` | 20 | 20 | 1.0000 | [0.8389, 1.0000] | 1.0000 | 1.0000 | 0.0000 | 721.2467 | `{'ok': 20}` |
| `cais/mmlu:machine_learning` | 20 | 19 | 0.6316 | [0.4104, 0.8085] | 0.6333 | 0.6316 | 0.0500 | 1148.8022 | `{'ok': 19, 'parse_error': 1}` |
| `cais/mmlu:professional_law` | 20 | 20 | 0.8500 | [0.6396, 0.9476] | 0.8500 | 0.8496 | 0.0000 | 1205.6714 | `{'ok': 20}` |
| `eval-lab-select-v0.1.0` | 120 | 120 | 0.9750 | [0.9291, 0.9915] | 0.9750 | 0.9750 | 0.0000 | 11536.0105 | `{'ok': 120}` |
| `eval-lab-synthetic:arithmetic` | 12 | 11 | 1.0000 | [0.7412, 1.0000] | 1.0000 | 1.0000 | 0.0833 | 735.4014 | `{'ok': 11, 'parse_error': 1}` |
| `eval-lab-synthetic:code` | 12 | 11 | 0.8182 | [0.5230, 0.9486] | 0.8667 | 0.7889 | 0.0833 | 819.3497 | `{'ok': 11, 'parse_error': 1}` |
| `eval-lab-synthetic:multiple` | 12 | 12 | 0.4167 | [0.1933, 0.6805] | 0.2500 | 0.1667 | 0.0000 | 2752.9997 | `{'ok': 12}` |
| `eval-lab-synthetic:structured` | 12 | 12 | 0.5833 | [0.3195, 0.8067] | 0.6250 | 0.4933 | 0.0000 | 748.8690 | `{'ok': 12}` |
| `openai/gsm8k:main` | 160 | 156 | 0.6795 | [0.6027, 0.7476] | 0.6795 | 0.6741 | 0.0250 | 1005.8549 | `{'parse_error': 4, 'ok': 156}` |

Overall resolved accuracy: `0.8592`; unresolved rate: `0.0139`.
Overall accuracy 95% interval: `{'lower': 0.8300324604047051, 'upper': 0.8839849597567837}`.
Qwen probabilities/logprobs were unavailable, so calibration metrics are not claimed.
