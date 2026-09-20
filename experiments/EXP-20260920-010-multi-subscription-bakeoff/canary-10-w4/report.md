# EXP-20260920-010 — Multi-subscription judge bakeoff

Benchmark fingerprint: `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`.
Matched final-evaluation records: 10.

| Arm | Model | OK | Provider error | Parse error | Other |
| --- | --- | ---: | ---: | ---: | ---: |
| grok | `opencode/grok-4.6` | 10 | 0 | 0 | 0 |
| luna | `opencode/gpt-5.6-luna` | 10 | 0 | 0 | 0 |
| sol | `opencode/gpt-5.6-sol` | 10 | 0 | 0 | 0 |

Provider failures remain unresolved and receive no local fallback label.
Deferred Qwen and local-weight arms are recorded in `provider-status.json`.
