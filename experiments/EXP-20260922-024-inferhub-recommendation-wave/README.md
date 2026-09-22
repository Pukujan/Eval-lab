# EXP-20260922-024 — InferHub recommendation-policy wave

This append-only experiment evaluates one cheapest exact InferHub route for
each family selected by the refreshed daily recommendation policy. It uses the
immutable EXP-015 source pool and does not modify EXP-022 or the historical
EXP-023 release-first wave.

The InferHub artifacts were generated on 2026-09-22. The operational shortlist
contains nine families; the top-20 recommendation view is explanatory and is
not itself an execution list. Routes are deduplicated by model family, with no
GPT, ChatGPT, Codex, alias, or Qwen4B route.

All requests use the checkpointed OpenAI-compatible SSE adapter. Public
selection is descriptive and precedes the primary blind holdout. Provider
errors, rate limits, timeouts, skips, and parse failures remain explicit
unresolved statuses and are never converted to labels or silently rerouted.

The wave is run in bounded route batches with four workers per route. Each
canary, public partition, and blind partition has a fresh append-only output
directory and is resumable without duplicate record IDs.
