# EXP-20260921-014-independent-jev-benchmark — independent blind evaluation

Pool: `760` blind records; fingerprint `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`.

| Arm | Resolved | Accuracy | 95% Wilson interval | Unresolved | Brier | NLL | ECE | p95 ms |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `jev_pinned` | 760 | 0.9 | `{'lower': 0.8766185431070428, 'upper': 0.9193581520290133}` | 0.0000 | None | None | None | 380.27339499094523 |
| `jev_rolling_canary` | 263 | 0.9467680608365019 | `{'lower': 0.9126433720263865, 'upper': 0.9680293729008167}` | 0.6539 | None | None | None | 321.04886501474533 |
| `qwen_comparison` | 754 | 0.8448275862068966 | `{'lower': 0.8172424224982658, 'upper': 0.868916923823578}` | 0.0079 | None | None | None | 1031.3186949904773 |
| `local_task0009_arm_D` | 652 | 0.5076687116564417 | `{'lower': 0.46936177551021924, 'upper': 0.545885811944806}` | 0.1421 | 0.49762766333294617 | 0.6907462542488322 | 0.023802564683145053 | 0.11971411044370851 |
| `majority_baseline` | 760 | 0.5026315789473684 | `{'lower': 0.46716064963661835, 'upper': 0.5380760391471714}` | 0.0000 | None | None | None | None |

JevBench tasks, labels, and its composite score are excluded from the primary score.

Pinned Jev vs Qwen agreement on comparable records: `0.8647214854111406`.
Pinned Jev vs local student agreement on comparable records: `0.4892638036809816`.
Robustness subset: repeatability `1.0`, option-order agreement `1.0`, rubric-paraphrase agreement `0.9166666666666666`.

Provider failures remain unresolved; rolling Jev is a separate canary and is never pooled with pinned Jev.
