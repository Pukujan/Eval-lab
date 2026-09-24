# EXP-20260924-027-local-decision-bakeoff — local decision-model results

## Public

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| `kev-0.8b` | 648/648 | 1.0000 | 0.4737654320987654 | `[0.43558887492203513, 0.5122512025386523]` | `pairwise: 0.6729084374902945/1.1125800464754083/0.15743124577922357; single: 0.6603481666239317/0.9221343494185363/0.25342329059829055` | 172.07085349946283 | 312.66053364815883 | `{'ok': 648}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `kev-0.8b` | pairwise | 180 | 0.3778 | 0.3775 | 0.3235 | 0.6729084374902945 | 1.1125800464754083 | 0.15743124577922357 |
| `kev-0.8b` | single | 468 | 0.5107 | 0.5181 | 0.4826 | 0.6603481666239317 | 0.9221343494185363 | 0.25342329059829055 |

## Blind

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| `kev-0.8b` | 760/760 | 1.0000 | 0.5026315789473684 | `[0.46716064963661835, 0.5380760391471714]` | `pairwise: 0.712017136144525/1.1746543346831504/0.21875089795219418; single: 0.6184070705214724/0.8671352680352532/0.22291733128834354` | 176.72883300110698 | 367.60985414694 | `{'ok': 760}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `kev-0.8b` | pairwise | 108 | 0.3148 | 0.3148 | 0.2739 | 0.712017136144525 | 1.1746543346831504 | 0.21875089795219418 |
| `kev-0.8b` | single | 652 | 0.5337 | 0.5351 | 0.5098 | 0.6184070705214724 | 0.8671352680352532 | 0.22291733128834354 |

Calibration metrics are reported within each fixed label space in `results.json`; single-answer and pairwise records are not pooled for Brier, NLL, or ECE.
Unresolved model failures remain statuses and are excluded from resolved accuracy. Public-selection results are descriptive and the blind holdout is the primary comparison.
