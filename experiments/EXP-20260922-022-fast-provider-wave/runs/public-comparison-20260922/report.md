# Fast provider wave — public_selection

| Arm | Requested | Surfaced | Resolved | Coverage | Accuracy | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `grok_46` | `grok-4.6` | `grok-4.6-build` | 643/648 | 0.9923 | 0.3701399688958009 | `{'ok': 643, 'provider_error': 3, 'rate_limited': 2}` |
| `grok_47` | `grok-4.7` | `grok-4.7-build` | 617/648 | 0.9522 | 0.3679092382495948 | `{'ok': 617, 'provider_error': 31}` |
| `qwen_flash` | `qwen3.8-flash` | `qwen3.8-flash` | 645/648 | 0.9954 | 0.9674418604651163 | `{'ok': 645, 'parse_error': 3}` |
| `jev` | `None` | `(none)` | 648/648 | 1.0000 | 0.8796296296296297 | `{'ok': 648}` |

Provider failures and malformed outputs remain unresolved and are excluded from accuracy.
Same-record agreement: `{"grok_46__vs__grok_47": {"agreement_count": 588, "agreement_rate": 0.9607843137254902, "comparable_count": 612}, "grok_46__vs__jev": {"agreement_count": 234, "agreement_rate": 0.36391912908242613, "comparable_count": 643}, "grok_46__vs__qwen_flash": {"agreement_count": 245, "agreement_rate": 0.3828125, "comparable_count": 640}, "grok_47__vs__jev": {"agreement_count": 217, "agreement_rate": 0.35170178282009723, "comparable_count": 617}, "grok_47__vs__qwen_flash": {"agreement_count": 233, "agreement_rate": 0.3794788273615635, "comparable_count": 614}, "jev__vs__qwen_flash": {"agreement_count": 578, "agreement_rate": 0.896124031007752, "comparable_count": 645}}`.
