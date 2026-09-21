# EXP-20260921-015 — Grok Build, Luna, and Qwen Flash Matched Bakeoff

This is a new experiment from the completed TASK-0012 independent benchmark state.
It does not modify EXP-014 or reuse its provider results as if they were this run.

The frozen source pool is copied from EXP-014: 648 public-selection records and 760
blind-holdout records, with source fingerprint
`b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`. Every selected
arm receives the same System-One typed prompt and record order.

The core comparison is Grok Build through the direct authenticated xAI `grok` CLI,
Luna through the direct authenticated Codex/ChatGPT subscription route, and YOLO-Auto
`qwen3.8-flash`. Sol is optional. Requested model IDs and exact surfaced IDs are kept
in every run's results and provider-status artifacts.

Provider failures, rate limits, malformed responses, and skipped records are explicit
execution outcomes. They are excluded from resolved accuracy and never assigned a
fallback label. See [PLAN.md](PLAN.md) and [experiment.yaml](experiment.yaml) for the
preregistered protocol.
