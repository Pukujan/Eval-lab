# EXP-20260921-015-grok-luna-qwen-bakeoff — smoke

Partition: `public_selection`; matched records: `1`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `grok` | `opencode/grok-4.6` | `(none surfaced)` | 0/1 | 0.0000 | None | `None` | `{'provider_error': 1}` |
| `luna` | `opencode/gpt-5.6-luna` | `(none surfaced)` | 0/1 | 0.0000 | None | `None` | `{'provider_error': 1}` |
| `qwen_flash` | `qwen3.8-flash` | `(none surfaced)` | 1/1 | 1.0000 | 1.0 | `{'lower': 0.20654931437723745, 'upper': 1.0}` | `{'ok': 1}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{"grok__vs__luna": {"agreement_count": 0, "agreement_rate": null, "comparable_count": 0}, "grok__vs__qwen_flash": {"agreement_count": 0, "agreement_rate": null, "comparable_count": 0}, "luna__vs__qwen_flash": {"agreement_count": 0, "agreement_rate": null, "comparable_count": 0}}`.
