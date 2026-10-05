# EXP-20261004-030-grok-harness-correction — Grok Build harness correction

This is an append-only correction. EXP-022 and EXP-025 are not modified. The only
change from EXP-022 is the provider invocation: the two-line prompt is delivered
through a per-record `--prompt-file` instead of an inline `--single=<prompt>` argv
element, which the Windows `grok.CMD` shim truncates at the embedded newline.

Pool fingerprint: `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`; blind record-ID fingerprint: `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.

| Partition | Arm | Requested model | Surfaced IDs | Resolved | Coverage | Accuracy | Wilson 95% | Statuses |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `public_selection` | `grok` | `grok-4.6` | `grok-4.6-build` | 648/648 | 1.0000 | 0.9861 | `0.9738–0.9927` | `{'ok': 648}` |
| `public_selection` | `grok_47` | `grok-4.7` | `Qwen/Qwen3-4B, grok-4.7-build, qwen3.8-flash, typesafe/jev-1.13, typesafe/jev-1.13-20260917` | 645/648 | 0.9954 | 0.9798 | `0.9658–0.9882` | `{'ok': 645, 'provider_error': 2, 'rate_limited': 1}` |
| `blind_holdout` | `grok` | `grok-4.6` | `grok-4.6-build` | 760/760 | 1.0000 | 0.9908 | `0.9811–0.9955` | `{'ok': 760}` |
| `blind_holdout` | `grok_47` | `grok-4.7` | `grok-4.7-build` | 758/760 | 0.9974 | 0.9855 | `0.9742–0.9919` | `{'ok': 758, 'provider_error': 2}` |

Provider failures, rate limits, timeouts, and parse ambiguity remain unresolved and
receive no fallback label. The blind holdout was not used to select anything.

See `README.md` for the root cause and the pre-run canary evidence.
