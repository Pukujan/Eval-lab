# EXP-20261004-030-grok-harness-correction — blind-20261004

Partition: `blind_holdout`; matched records: `760`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `grok` | `grok-4.6` | `grok-4.6-build` | 760/760 | 1.0000 | 0.9907894736842106 | `{'lower': 0.9811110602091844, 'upper': 0.9955313979676212}` | `{'ok': 760}` |
| `grok_47` | `grok-4.7` | `grok-4.7-build` | 758/760 | 0.9974 | 0.9854881266490765 | `{'lower': 0.9742024590663243, 'upper': 0.9918778080004012}` | `{'ok': 758, 'provider_error': 2}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{"grok__vs__grok_47": {"agreement_count": 746, "agreement_rate": 0.9841688654353562, "comparable_count": 758}}`.
