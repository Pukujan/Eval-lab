# EXP-20260924-028-legalbench-hearsay — local decision-model results

## Test

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| `kev-0.8b` | 94/94 | 1.0000 | 0.5425531914893617 | `[0.44215447666238733, 0.6396104530149279]` | `all: 0.5008392885106383/0.6928847656932487/0.09382765957446812` | 282.76960399671225 | 317.94871240199427 | `{'ok': 94}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `kev-0.8b` | all | 94 | 0.5426 | 0.5695 | 0.5336 | 0.5008392885106383 | 0.6928847656932487 | 0.09382765957446812 |

Calibration metrics are reported within each fixed label space in `results.json`; single-answer and pairwise records are not pooled for Brier, NLL, or ECE.
Unresolved model failures remain statuses and are excluded from resolved accuracy. Public-selection results are descriptive and the blind holdout is the primary comparison.
