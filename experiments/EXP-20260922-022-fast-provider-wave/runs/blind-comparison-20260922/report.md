# Fast provider wave — blind_holdout

| Arm | Requested | Surfaced | Resolved | Coverage | Accuracy | Statuses |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `grok_46` | `grok-4.6` | `grok-4.6-build` | 757/760 | 0.9961 | 0.4346103038309115 | `{'ok': 757, 'provider_error': 1, 'rate_limited': 2}` |
| `grok_47` | `grok-4.7` | `grok-4.7-build` | 726/760 | 0.9553 | 0.43526170798898073 | `{'ok': 726, 'provider_error': 33, 'rate_limited': 1}` |
| `qwen_flash` | `qwen3.8-flash` | `qwen3.8-flash` | 759/760 | 0.9987 | 0.9736495388669302 | `{'ok': 759, 'parse_error': 1}` |
| `jev` | `typesafe/jev-1.13` | `typesafe/jev-1.13-20260917` | 760/760 | 1.0000 | 0.8986842105263158 | `{'ok': 760}` |

Provider failures and malformed outputs remain unresolved and are excluded from accuracy.
Same-record agreement: `{"grok_46__vs__grok_47": {"agreement_count": 689, "agreement_rate": 0.9529737206085753, "comparable_count": 723}, "grok_46__vs__jev": {"agreement_count": 314, "agreement_rate": 0.4147952443857332, "comparable_count": 757}, "grok_46__vs__qwen_flash": {"agreement_count": 338, "agreement_rate": 0.4470899470899471, "comparable_count": 756}, "grok_47__vs__jev": {"agreement_count": 303, "agreement_rate": 0.41735537190082644, "comparable_count": 726}, "grok_47__vs__qwen_flash": {"agreement_count": 325, "agreement_rate": 0.4482758620689655, "comparable_count": 725}, "jev__vs__qwen_flash": {"agreement_count": 682, "agreement_rate": 0.8985507246376812, "comparable_count": 759}}`.
