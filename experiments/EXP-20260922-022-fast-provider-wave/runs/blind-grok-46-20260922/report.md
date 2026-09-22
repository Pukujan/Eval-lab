# EXP-20260922-022-fast-provider-wave — blind-grok-46-20260922

Partition: `blind_holdout`; matched records: `760`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `grok` | `grok-4.6` | `grok-4.6-build` | 757/760 | 0.9961 | 0.4346103038309115 | `{'lower': 0.3997160187441202, 'upper': 0.47016488896370856}` | `{'ok': 757, 'provider_error': 1, 'rate_limited': 2}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{}`.
