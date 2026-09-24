# EXP-20260924-027-local-decision-bakeoff — local decision-model results

## Public

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| `kev-0.8b` | 648/648 | 1.0000 | 0.4737654320987654 | `[0.43558887492203513, 0.5122512025386523]` | `pairwise: 0.6729084374902945/1.1125800464754083/0.15743124577922357; single: 0.6603481666239317/0.9221343494185363/0.25342329059829055` | 172.07085349946283 | 312.66053364815883 | `{'ok': 648}` |
| `laya-421m` | 638/648 | 0.9846 | 0.4952978056426332 | `[0.45664606826681176, 0.5340058288371486]` | `pairwise: 0.6271602072688058/0.9996759690390556/0.1300147108357693; single: 0.636933791091703/0.901883662539793/0.22980786026200878` | 137.8003540012287 | 214.69738750602116 | `{'ok': 638, 'skipped': 10}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `kev-0.8b` | pairwise | 180 | 0.3778 | 0.3775 | 0.3235 | 0.6729084374902945 | 1.1125800464754083 | 0.15743124577922357 |
| `kev-0.8b` | single | 468 | 0.5107 | 0.5181 | 0.4826 | 0.6603481666239317 | 0.9221343494185363 | 0.25342329059829055 |
| `laya-421m` | pairwise | 180 | 0.4389 | 0.4481 | 0.2796 | 0.6271602072688058 | 0.9996759690390556 | 0.1300147108357693 |
| `laya-421m` | single | 458 | 0.5175 | 0.5202 | 0.5149 | 0.636933791091703 | 0.901883662539793 | 0.22980786026200878 |

## Blind

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| `kev-0.8b` | 760/760 | 1.0000 | 0.5026315789473684 | `[0.46716064963661835, 0.5380760391471714]` | `pairwise: 0.712017136144525/1.1746543346831504/0.21875089795219418; single: 0.6184070705214724/0.8671352680352532/0.22291733128834354` | 176.72883300110698 | 367.60985414694 | `{'ok': 760}` |
| `laya-421m` | 748/760 | 0.9842 | 0.4852941176470588 | `[0.44964460479666996, 0.5210939069708133]` | `pairwise: 0.6456159463523841/1.0230956420421704/0.17790897194070085; single: 0.6573882021874999/0.9298713306076613/0.25766406249999996` | 141.14524999604328 | 272.4938190964167 | `{'ok': 748, 'skipped': 12}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `kev-0.8b` | pairwise | 108 | 0.3148 | 0.3148 | 0.2739 | 0.712017136144525 | 1.1746543346831504 | 0.21875089795219418 |
| `kev-0.8b` | single | 652 | 0.5337 | 0.5351 | 0.5098 | 0.6184070705214724 | 0.8671352680352532 | 0.22291733128834354 |
| `laya-421m` | pairwise | 108 | 0.4815 | 0.4815 | 0.3067 | 0.6456159463523841 | 1.0230956420421704 | 0.17790897194070085 |
| `laya-421m` | single | 640 | 0.4859 | 0.4865 | 0.4821 | 0.6573882021874999 | 0.9298713306076613 | 0.25766406249999996 |

Calibration metrics are reported within each fixed label space in `results.json`; single-answer and pairwise records are not pooled for Brier, NLL, or ECE.
Unresolved model failures remain statuses and are excluded from resolved accuracy. Public-selection results are descriptive and the blind holdout is the primary comparison.

## Model-specific interpretation notes

- `laya-421m`: Upstream warned this checkpoint contains invalid temperatures; it uses a 0.5 fallback for choice:11+ and says affected confidence entries are uncalibrated.
