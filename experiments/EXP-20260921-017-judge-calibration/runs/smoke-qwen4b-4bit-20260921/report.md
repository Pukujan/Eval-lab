# EXP-20260921-017-judge-calibration — public_selection

- Records: `1`
- Model: `Qwen/Qwen3-4B`
- Runtime: `cuda:0` / `torch.float16`

| View | Count | Accuracy | Brier | NLL | ECE |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw | 1 | 1.0 | 0.20151886816987552 | 0.3818847219894927 | 0.31742626558767595 |
| calibrated | 1 | 1.0 | 5.1812688584701066e-269 | 0.0 | 0.0 |

Status counts: `{'ok': 1}`.
Calibration is fit only on public_selection records and is never fit on blind labels.
