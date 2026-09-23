# EXP-20260921-015-grok-luna-qwen-bakeoff — blind-stream-parallel-20260921

Partition: `blind_holdout`; matched records: `760`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `grok` | `grok-4.6` | `grok-4.6-build` | 756/760 | 0.9947 | 0.43783068783068785 | `{'lower': 0.4028680841708985, 'upper': 0.47342189855011296}` | `{'ok': 756, 'provider_error': 4}` |
| `luna` | `gpt-5.6-luna` | `(none surfaced)` | 760/760 | 1.0000 | 0.9842105263157894 | `{'lower': 0.9726056610063369, 'upper': 0.9909450752109941}` | `{'ok': 760}` |
| `qwen_flash` | `qwen3.8-flash` | `qwen3.8-flash` | 442/760 | 0.5816 | 0.9909502262443439 | `{'lower': 0.9769649509924175, 'upper': 0.9964752516033298}` | `{'ok': 442, 'provider_error': 1, 'rate_limited': 317}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{"grok__vs__luna": {"agreement_count": 332, "agreement_rate": 0.43915343915343913, "comparable_count": 756}, "grok__vs__qwen_flash": {"agreement_count": 174, "agreement_rate": 0.39635535307517084, "comparable_count": 439}, "luna__vs__qwen_flash": {"agreement_count": 436, "agreement_rate": 0.9864253393665159, "comparable_count": 442}}`.
