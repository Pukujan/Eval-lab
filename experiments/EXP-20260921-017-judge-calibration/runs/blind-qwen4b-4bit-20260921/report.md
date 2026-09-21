# EXP-20260921-017-judge-calibration — blind_holdout

- Records: `760`
- Model: `Qwen/Qwen3-4B`
- Runtime: `cuda:0` / `torch.float16`

| View | Count | Accuracy | Brier | NLL | ECE |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw | 760 | 0.44605263157894737 | 0.7036824847148387 | 1.076729516647522 | 0.3411375292308107 |
| calibrated | 760 | 0.44605263157894737 | 0.5160339956496602 | 0.7430236501814631 | 0.07834063916107518 |

Status counts: `{'ok': 760}`.
Calibration is fit only on public_selection records and is never fit on blind labels.
