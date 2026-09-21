# EXP-20260921-016 — Qwen rate-limit retry

This append-only recovery study retried exactly the `317` Qwen blind-holdout records
that were `rate_limited` in EXP-20260921-015. The original EXP-015 primary result was
not overwritten or relabeled.

| Arm | Route | Resolved | Coverage | Accuracy | Statuses |
| --- | --- | ---: | ---: | ---: | --- |
| Qwen Flash | direct YOLO-Auto streaming | 317/317 | 1.0000 | 0.9527 | 317 ok |

The retry requested `qwen3.8-flash` and surfaced the same model ID. It used one worker,
streaming, the unchanged EXP-015 typed prompt and pool, and no fallback labels. The
Wilson 95% accuracy interval is `[0.9234, 0.9711]`.

This result is a separate recovery observation, not a replacement for EXP-015's
one-pass Qwen coverage result. Combining it with EXP-015 would require a separately
declared merge analysis. No OpenCode, OpenRouter, Grok, Luna, or Sol route was used.

