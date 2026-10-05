# EXP-20261005-031-colab-t4-moe-judge-arms — local decision-model results

## Public

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts | Unresolved reasons |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `maple-preview-20b-a1b` | 648/648 | 1.0000 | 0.49537037037037035 | `[0.4570155658101348, 0.5337797419770454]` | `unavailable` | 252.64999999999998 | 349.74499999999983 | `{'ok': 648}` | `{}` |
| `ornith-1.5-35b-a3b` | 648/648 | 1.0000 | 0.5817901234567902 | `[0.5434383506421256, 0.6191778784510258]` | `unavailable` | 687.05 | 888.4399999999999 | `{'ok': 648}` | `{}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `maple-preview-20b-a1b` | pairwise | 180 | 0.5278 | 0.5415 | 0.2965 | None | None | None |
| `maple-preview-20b-a1b` | single | 468 | 0.4829 | 0.4974 | 0.3362 | None | None | None |
| `ornith-1.5-35b-a3b` | pairwise | 180 | 0.7167 | 0.7228 | 0.4742 | None | None | None |
| `ornith-1.5-35b-a3b` | single | 468 | 0.5299 | 0.5425 | 0.4371 | None | None | None |

## Blind

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts | Unresolved reasons |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `maple-preview-20b-a1b` | 760/760 | 1.0000 | 0.48947368421052634 | `[0.45407625814660774, 0.5249769867182329]` | `unavailable` | 262.4 | 375.22499999999997 | `{'ok': 760}` | `{}` |
| `ornith-1.5-35b-a3b` | 760/760 | 1.0000 | 0.5539473684210526 | `[0.5184238259953757, 0.588928294072316]` | `unavailable` | 704.75 | 952.0599999999998 | `{'ok': 760}` | `{}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `maple-preview-20b-a1b` | pairwise | 108 | 0.4444 | 0.4444 | 0.2419 | None | None | None |
| `maple-preview-20b-a1b` | single | 652 | 0.4969 | 0.4998 | 0.3595 | None | None | None |
| `ornith-1.5-35b-a3b` | pairwise | 108 | 0.6759 | 0.6759 | 0.4407 | None | None | None |
| `ornith-1.5-35b-a3b` | single | 652 | 0.5337 | 0.5363 | 0.4337 | None | None | None |

Calibration metrics are reported within each fixed label space in `results.json`; single-answer and pairwise records are not pooled for Brier, NLL, or ECE.
Unresolved model failures remain statuses and are excluded from resolved accuracy. Public-selection results are descriptive and the blind holdout is the primary comparison.
