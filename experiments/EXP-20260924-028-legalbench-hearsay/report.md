# EXP-20260924-028-legalbench-hearsay — local decision-model results

## Test

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts | Unresolved reasons |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `kev-0.8b` | 94/94 | 1.0000 | 0.5425531914893617 | `[0.44215447666238733, 0.6396104530149279]` | `all: 0.5008392885106383/0.6928847656932487/0.09382765957446812` | 282.76960399671225 | 317.94871240199427 | `{'ok': 94}` | `{}` |
| `kev-4b` | 94/94 | 1.0000 | 0.723404255319149 | `[0.6255660780959044, 0.8036998027100012]` | `all: 0.3690732846808511/0.5494439747570009/0.05095744680851068` | 1506.3694789932924 | 1789.4753103981202 | `{'ok': 94}` | `{}` |
| `laya-421m` | 94/94 | 1.0000 | 0.6170212765957447 | `[0.5159955881639535, 0.7088579684486636]` | `all: 0.48820023808510643/0.6875063454523375/0.14961170212765956` | 218.4038534978754 | 259.5422642574704 | `{'ok': 94}` | `{}` |
| `semif-qwen35-4b` | 94/94 | 1.0000 | 0.48936170212765956 | `[0.3907276290915208, 0.5888311384891503]` | `all: 0.4884388348572359/0.6820163046910145/0.1466773290093349` | 1993.9584795065457 | 2599.9477914505405 | `{'ok': 94}` | `{}` |
| `verdict-1.4` | 94/94 | 1.0000 | 0.43617021276595747 | `[0.34038166214603166, 0.5369709433379954]` | `all: 0.5267011846331394/0.720047731465492/0.12665138706367984` | 273.8405209966004 | 290.9574936522404 | `{'ok': 94}` | `{}` |
| `verdict-original` | 94/94 | 1.0000 | 0.43617021276595747 | `[0.34038166214603166, 0.5369709433379954]` | `all: 0.7536348955899022/1.0024813209200443/0.35670273762014393` | 122.31174999033101 | 129.8065397022583 | `{'ok': 94}` | `{}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `kev-0.8b` | all | 94 | 0.5426 | 0.5695 | 0.5336 | 0.5008392885106383 | 0.6928847656932487 | 0.09382765957446812 |
| `kev-4b` | all | 94 | 0.7234 | 0.7326 | 0.7233 | 0.3690732846808511 | 0.5494439747570009 | 0.05095744680851068 |
| `laya-421m` | all | 94 | 0.6170 | 0.5693 | 0.5215 | 0.48820023808510643 | 0.6875063454523375 | 0.14961170212765956 |
| `semif-qwen35-4b` | all | 94 | 0.4894 | 0.5444 | 0.4125 | 0.4884388348572359 | 0.6820163046910145 | 0.1466773290093349 |
| `verdict-1.4` | all | 94 | 0.4362 | 0.5000 | 0.3037 | 0.5267011846331394 | 0.720047731465492 | 0.12665138706367984 |
| `verdict-original` | all | 94 | 0.4362 | 0.5000 | 0.3037 | 0.7536348955899022 | 1.0024813209200443 | 0.35670273762014393 |

Calibration metrics are reported within each fixed label space in `results.json`; single-answer and pairwise records are not pooled for Brier, NLL, or ECE.
Unresolved model failures remain statuses and are excluded from resolved accuracy. Public-selection results are descriptive and the blind holdout is the primary comparison.

## Model-specific interpretation notes

- `laya-421m`: Upstream warned this checkpoint contains invalid temperatures; it uses a 0.5 fallback for choice:11+ and says affected confidence entries are uncalibrated.
- `verdict-1.4`: The runtime returns a calibrated explicit __insufficient_evidence__ option. Raw distributions are preserved in provider metadata; accuracy and standard class-probability metrics cover only non-abstaining predictions.
- `verdict-original`: This pre-v1.4 runtime also returns an explicit __insufficient_evidence__ option. Raw distributions are preserved in provider metadata; accuracy and standard class-probability metrics cover only non-abstaining predictions.
