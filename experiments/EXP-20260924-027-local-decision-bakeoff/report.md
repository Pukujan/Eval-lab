# EXP-20260924-027-local-decision-bakeoff — local decision-model results

## Public

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts | Unresolved reasons |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `kev-0.8b` | 648/648 | 1.0000 | 0.4737654320987654 | `[0.43558887492203513, 0.5122512025386523]` | `pairwise: 0.6729084374902945/1.1125800464754083/0.15743124577922357; single: 0.6603481666239317/0.9221343494185363/0.25342329059829055` | 172.07085349946283 | 312.66053364815883 | `{'ok': 648}` | `{}` |
| `laya-421m` | 638/648 | 0.9846 | 0.4952978056426332 | `[0.45664606826681176, 0.5340058288371486]` | `pairwise: 0.6271602072688058/0.9996759690390556/0.1300147108357693; single: 0.636933791091703/0.901883662539793/0.22980786026200878` | 137.8003540012287 | 214.69738750602116 | `{'ok': 638, 'skipped': 10}` | `{'context_limit': 10}` |
| `verdict-1.4` | 472/648 | 0.7284 | 0.4894067796610169 | `[0.4445774176956652, 0.5344071793489393]` | `pairwise: 0.6185180765191927/1.0203060366558467/0.05672418694178183; single: 0.542085585445054/0.7381724958337018/0.1556292447085422` | 125.29672899108846 | 231.24194834745134 | `{'ok': 472, 'skipped': 176}` | `{'abstention': 164, 'context_limit': 12}` |
| `verdict-original` | 454/648 | 0.7006 | 0.5022026431718062 | `[0.4563851239274221, 0.5479832004378541]` | `pairwise: 0.6211780892591917/0.9913704407453424/0.1587357010516193; single: 0.846014046608925/1.445673026637254/0.4189345582588304` | 69.7923539992189 | 120.72825439536246 | `{'ok': 454, 'skipped': 194}` | `{'abstention': 194}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `kev-0.8b` | pairwise | 180 | 0.3778 | 0.3775 | 0.3235 | 0.6729084374902945 | 1.1125800464754083 | 0.15743124577922357 |
| `kev-0.8b` | single | 468 | 0.5107 | 0.5181 | 0.4826 | 0.6603481666239317 | 0.9221343494185363 | 0.25342329059829055 |
| `laya-421m` | pairwise | 180 | 0.4389 | 0.4481 | 0.2796 | 0.6271602072688058 | 0.9996759690390556 | 0.1300147108357693 |
| `laya-421m` | single | 458 | 0.5175 | 0.5202 | 0.5149 | 0.636933791091703 | 0.901883662539793 | 0.22980786026200878 |
| `verdict-1.4` | pairwise | 151 | 0.4768 | 0.4817 | 0.2989 | 0.6185180765191927 | 1.0203060366558467 | 0.05672418694178183 |
| `verdict-1.4` | single | 321 | 0.4953 | 0.5098 | 0.4628 | 0.542085585445054 | 0.7381724958337018 | 0.1556292447085422 |
| `verdict-original` | pairwise | 165 | 0.5212 | 0.5192 | 0.3469 | 0.6211780892591917 | 0.9913704407453424 | 0.1587357010516193 |
| `verdict-original` | single | 289 | 0.4913 | 0.4981 | 0.4700 | 0.846014046608925 | 1.445673026637254 | 0.4189345582588304 |

## Blind

| Arm | Resolved | Coverage | Accuracy | 95% Wilson interval | Calibration by mode | p50 ms | p95 ms | Status counts | Unresolved reasons |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| `kev-0.8b` | 760/760 | 1.0000 | 0.5026315789473684 | `[0.46716064963661835, 0.5380760391471714]` | `pairwise: 0.712017136144525/1.1746543346831504/0.21875089795219418; single: 0.6184070705214724/0.8671352680352532/0.22291733128834354` | 176.72883300110698 | 367.60985414694 | `{'ok': 760}` | `{}` |
| `laya-421m` | 748/760 | 0.9842 | 0.4852941176470588 | `[0.44964460479666996, 0.5210939069708133]` | `pairwise: 0.6456159463523841/1.0230956420421704/0.17790897194070085; single: 0.6573882021874999/0.9298713306076613/0.25766406249999996` | 141.14524999604328 | 272.4938190964167 | `{'ok': 748, 'skipped': 12}` | `{'context_limit': 12}` |
| `verdict-1.4` | 569/760 | 0.7487 | 0.5149384885764499 | `[0.47391146751744595, 0.5557651554612709]` | `pairwise: 0.6255455812495386/1.0301840370134083/0.13022843934979833; single: 0.5440233778628626/0.741385305890161/0.13664182821265405` | 132.6221874987823 | 334.2588982486631 | `{'ok': 569, 'skipped': 191}` | `{'abstention': 179, 'context_limit': 12}` |
| `verdict-original` | 526/760 | 0.6921 | 0.5038022813688213 | `[0.46120187041739347, 0.5463475576868231]` | `pairwise: 0.6686561907028431/1.0410307145918336/0.2475940749889828; single: 0.8252488251369939/1.5037015008306074/0.40025414852773133` | 70.67289599217474 | 152.86992289766204 | `{'ok': 526, 'skipped': 234}` | `{'abstention': 234}` |

### Class and calibration metrics by fixed label space

| Arm | Mode | N | Accuracy | Balanced accuracy | Macro F1 | Brier | NLL | ECE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `kev-0.8b` | pairwise | 108 | 0.3148 | 0.3148 | 0.2739 | 0.712017136144525 | 1.1746543346831504 | 0.21875089795219418 |
| `kev-0.8b` | single | 652 | 0.5337 | 0.5351 | 0.5098 | 0.6184070705214724 | 0.8671352680352532 | 0.22291733128834354 |
| `laya-421m` | pairwise | 108 | 0.4815 | 0.4815 | 0.3067 | 0.6456159463523841 | 1.0230956420421704 | 0.17790897194070085 |
| `laya-421m` | single | 640 | 0.4859 | 0.4865 | 0.4821 | 0.6573882021874999 | 0.9298713306076613 | 0.25766406249999996 |
| `verdict-1.4` | pairwise | 86 | 0.5116 | 0.5116 | 0.3322 | 0.6255455812495386 | 1.0301840370134083 | 0.13022843934979833 |
| `verdict-1.4` | single | 483 | 0.5155 | 0.5183 | 0.4783 | 0.5440233778628626 | 0.741385305890161 | 0.13664182821265405 |
| `verdict-original` | pairwise | 101 | 0.4752 | 0.4767 | 0.3100 | 0.6686561907028431 | 1.0410307145918336 | 0.2475940749889828 |
| `verdict-original` | single | 425 | 0.5106 | 0.5128 | 0.4940 | 0.8252488251369939 | 1.5037015008306074 | 0.40025414852773133 |

Calibration metrics are reported within each fixed label space in `results.json`; single-answer and pairwise records are not pooled for Brier, NLL, or ECE.
Unresolved model failures remain statuses and are excluded from resolved accuracy. Public-selection results are descriptive and the blind holdout is the primary comparison.

## Model-specific interpretation notes

- `laya-421m`: Upstream warned this checkpoint contains invalid temperatures; it uses a 0.5 fallback for choice:11+ and says affected confidence entries are uncalibrated.
- `verdict-1.4`: The runtime returns a calibrated explicit __insufficient_evidence__ option. Raw distributions are preserved in provider metadata; accuracy and standard class-probability metrics cover only non-abstaining predictions.
- `verdict-original`: This pre-v1.4 runtime also returns an explicit __insufficient_evidence__ option. Raw distributions are preserved in provider metadata; accuracy and standard class-probability metrics cover only non-abstaining predictions.
