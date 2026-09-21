# EXP-20260921-015-grok-luna-qwen-bakeoff — smoke-direct-tight-20260921

Partition: `public_selection`; matched records: `1`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `grok` | `grok-4.6` | `grok-4.6-build` | 1/1 | 1.0000 | 0.0 | `{'lower': 0.0, 'upper': 0.7934506856227626}` | `{'ok': 1}` |
| `luna` | `gpt-5.6-luna` | `(none surfaced)` | 1/1 | 1.0000 | 1.0 | `{'lower': 0.20654931437723745, 'upper': 1.0}` | `{'ok': 1}` |
| `qwen_flash` | `qwen3.8-flash` | `(none surfaced)` | 1/1 | 1.0000 | 1.0 | `{'lower': 0.20654931437723745, 'upper': 1.0}` | `{'ok': 1}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{"grok__vs__luna": {"agreement_count": 0, "agreement_rate": 0.0, "comparable_count": 1}, "grok__vs__qwen_flash": {"agreement_count": 0, "agreement_rate": 0.0, "comparable_count": 1}, "luna__vs__qwen_flash": {"agreement_count": 1, "agreement_rate": 1.0, "comparable_count": 1}}`.
