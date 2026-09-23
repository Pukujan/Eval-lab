# EXP-20260922-022-fast-provider-wave — blind-grok-47-20260922

Partition: `blind_holdout`; matched records: `760`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `grok_47` | `grok-4.7` | `grok-4.7-build` | 726/760 | 0.9553 | 0.43526170798898073 | `{'lower': 0.3996314815237097, 'upper': 0.4715734235088314}` | `{'ok': 726, 'provider_error': 33, 'rate_limited': 1}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{}`.
