# EXP-20260922-022-fast-provider-wave — blind-qwen-flash-20260922

Partition: `blind_holdout`; matched records: `760`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `qwen_flash` | `qwen3.8-flash` | `qwen3.8-flash` | 759/760 | 0.9987 | 0.9736495388669302 | `{'lower': 0.9596503218066281, 'upper': 0.9828784195015983}` | `{'ok': 759, 'parse_error': 1}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{}`.
