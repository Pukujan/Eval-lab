# EXP-20261004-030-grok-harness-correction — public-20261004

Partition: `public_selection`; matched records: `648`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `grok` | `grok-4.6` | `grok-4.6-build` | 648/648 | 1.0000 | 0.9861111111111112 | `{'lower': 0.9738165658316261, 'upper': 0.9926761165144625}` | `{'ok': 648}` |
| `grok_47` | `grok-4.7` | `Qwen/Qwen3-4B, grok-4.7-build, qwen3.8-flash, typesafe/jev-1.13, typesafe/jev-1.13-20260917` | 645/648 | 0.9954 | 0.9798449612403101 | `{'lower': 0.9658239977053485, 'upper': 0.9881840909964236}` | `{'ok': 645, 'provider_error': 2, 'rate_limited': 1}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{"grok__vs__grok_47": {"agreement_count": 639, "agreement_rate": 0.9906976744186047, "comparable_count": 645}}`.
