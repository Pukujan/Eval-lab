# EXP-20260921-015-grok-luna-qwen-bakeoff — public-stream-parallel-20260921

Partition: `public_selection`; matched records: `648`.

| Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `grok` | `grok-4.6` | `grok-4.6-build` | 643/648 | 0.9923 | 0.37169517884914466 | `{'lower': 0.33520780375866616, 'upper': 0.40970650599998176}` | `{'ok': 643, 'provider_error': 5}` |
| `luna` | `gpt-5.6-luna` | `(none surfaced)` | 648/648 | 1.0000 | 0.9722222222222222 | `{'lower': 0.9565203816272095, 'upper': 0.9823582240804193}` | `{'ok': 648}` |
| `qwen_flash` | `qwen3.8-flash` | `qwen3.8-flash` | 647/648 | 0.9985 | 0.9706336939721792 | `{'lower': 0.954591076017282, 'upper': 0.9811206733594253}` | `{'ok': 647, 'parse_error': 1}` |

Provider failures, rate limits, parse errors, and skipped records remain unresolved and receive no fallback label.
Native probability and risk/coverage metrics are reported only when a valid probability map is returned.

Same-record agreement: `{"grok__vs__luna": {"agreement_count": 242, "agreement_rate": 0.37636080870917576, "comparable_count": 643}, "grok__vs__qwen_flash": {"agreement_count": 243, "agreement_rate": 0.37850467289719625, "comparable_count": 642}, "luna__vs__qwen_flash": {"agreement_count": 627, "agreement_rate": 0.9690880989180835, "comparable_count": 647}}`.
