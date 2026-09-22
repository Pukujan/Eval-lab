# Canary checkpoint — 2026-09-22

All four one-record public-selection canaries completed concurrently in fresh
run directories. No fallback route was used and no Qwen4B request was made.

| Run | Requested | Surfaced | Status | Latency |
| --- | --- | --- | --- | ---: |
| `canary-grok-46-20260922` | `grok-4.6` | `grok-4.6-build` | `ok` | 13.57s |
| `canary-grok-47-20260922` | `grok-4.7` | `grok-4.7-build` | `ok` | 12.98s |
| `canary-qwen-flash-20260922` | `qwen3.8-flash` | `qwen3.8-flash` | `ok` | 4.35s |
| `canary-jev-20260922` | `typesafe/jev-1.13` | `typesafe/jev-1.13-20260917` | `ok` | 0.47s |

The canary prediction files and checksums are retained under `runs/`. Jev
returned native probabilities; Grok and Qwen remained label-only. Gold was not
included in any provider request.
