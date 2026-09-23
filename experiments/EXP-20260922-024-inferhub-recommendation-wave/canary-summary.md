# EXP-20260922-024 canary summary

All canaries used `public_selection`, one record, streaming OpenAI SSE, one
worker, and `max_tokens=1024`. Every run used a fresh output directory.

| Arm | Route | Result | Evidence |
|---|---|---|---|
| DeepSeek V4.1 Flash | `cb/deepseek-v4.1-flash` | `ok` on retry | initial canary `parse_error`; retry2 `ok` |
| GLM 5.3 Flash | `cbcn/glm-5.3-flash` | `ok` | canary |
| DeepSeek V4 Flash | `cbcn/deepseek-v4-flash` | `ok` | canary |
| Qwen3.8 Flash | `ali/qwen3.8-flash` | `ok` | canary |
| MiniMax M3 | `cbcn/minimax-m3` | `ok` | canary |
| GLM 5.2 | `ali/glm-5.2` | `ok` | canary |
| Qwen 3.8 Max | `ali/qwen3.8-max` | `ok` | canary |
| Kimi K2.7 Code | `ali/kimi-k2.7-code` | `ok` | canary |
| MiMo V2.5 | `cp/cline-pass/mimo-v2.5` | `provider_error` | HTTP 402 on canary and retry2 |

The MiMo failure is retained under both canary directories. The benchmark does
not substitute `ocg/mimo-v2.5` or any other provider route because the
experiment selection is one exact cheapest route per family.

Live catalog refresh: 254 authenticated models; 498 rate-limit units reported.
The live checker was run without `--compare` because the current local catalog
snapshot is a list while that optional comparison path expects an object.
