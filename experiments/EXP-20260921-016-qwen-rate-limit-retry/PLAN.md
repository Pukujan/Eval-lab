# EXP-20260921-016 — Qwen rate-limit retry

Status: preregistered retry study; no new provider labels requested yet.

## Hypothesis

After the one-pass rate-limit event in EXP-20260921-015, a later YOLO-Auto request
window may recover some or all of the unresolved Qwen blind records without changing
the frozen prompt, pool, or gold labels.

## Frozen source and retry set

- Base experiment: `EXP-20260921-015-grok-luna-qwen-bakeoff`
- Base blind run: `runs/blind-stream-parallel-20260921`
- Source pool fingerprint: `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`
- Blind ID fingerprint: `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`
- Retry selection: exactly the `317` records whose EXP-015 Qwen status is `rate_limited`
- Exclusion: the one EXP-015 Qwen `provider_error` is not retried

## Provider protocol

Use only YOLO-Auto's OpenAI-compatible streaming route with requested model
`qwen3.8-flash`. Use the exact EXP-015 typed packet and record order. The retry is
append-only evidence and cannot overwrite or relabel EXP-015.

## Metrics and stopping rule

Report attempted count, resolved coverage, accuracy among resolved records, Wilson 95%
interval, latency p50/p95, surfaced model IDs, streaming metadata, and provider status
counts. Attempt each frozen retry ID once. Any later retry requires another experiment ID.

