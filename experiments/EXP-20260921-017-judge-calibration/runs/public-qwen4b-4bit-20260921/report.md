# EXP-20260921-017-judge-calibration — public_selection

- Records: `648`
- Model: `Qwen/Qwen3-4B`
- Runtime: `cuda:0` / `torch.float16`

| View | Count | Accuracy | Brier | NLL | ECE |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw | 648 | 0.3950617283950617 | 0.7729421450679119 | 1.2955413327116843 | 0.3718967480719355 |
| calibrated | 648 | 0.3950617283950617 | 0.5416915679366106 | 0.8011710411737264 | 0.09916453499286443 |

Status counts: `{'ok': 648}`.
Calibration is fit only on public_selection records and is never fit on blind labels.
