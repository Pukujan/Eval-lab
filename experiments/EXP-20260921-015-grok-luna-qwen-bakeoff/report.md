# EXP-20260921-015 — Grok Build, Luna, and Qwen Flash Matched Bakeoff

The preregistered experiment is complete with the frozen 1,408-record pool: 648
public-selection records and 760 blind-holdout records. The blind holdout is the
primary comparison; the public run is descriptive only.

## Primary blind holdout

| Arm | Route | Resolved | Coverage | Accuracy | Statuses |
| --- | --- | ---: | ---: | ---: | --- |
| Grok Build | direct authenticated xAI `grok` CLI | 756/760 | 0.9947 | 0.4378 | 756 ok, 4 provider_error |
| Luna | direct Codex ChatGPT subscription | 760/760 | 1.0000 | 0.9842 | 760 ok |
| Qwen Flash | YOLO-Auto `qwen3.8-flash` | 442/760 | 0.5816 | 0.9910 | 442 ok, 1 provider_error, 317 rate_limited |

Qwen's accuracy is conditional on its 442 resolved records and must not be compared
to full-coverage accuracy without the coverage qualification. Provider failures and
rate limits remain unresolved and receive no fallback label.

## Public-selection context

The public run resolved Grok at 643/648 with accuracy 0.3717, Luna at 648/648 with
accuracy 0.9722, and Qwen at 647/648 with accuracy 0.9706. These values are retained
as descriptive context and were not pooled into the blind score.

## Reproducibility and limitations

Each arm used its required direct route, four independent workers, and streaming:
Grok `streaming-json`, Luna Codex JSONL, and Qwen OpenAI-compatible SSE. The final
combined blind artifact was assembled offline from the completed per-arm normalized
checkpoints; no provider calls were made during assembly. OpenCode and OpenRouter
were not used. The exact per-run reports, provider-status files, differential files,
checksums, and normalized predictions are retained under `runs/`.

Native probability/risk metrics are reported only when a valid native probability map
exists. This experiment used one pass per selected record; any later provider retry
would be a separate timestamped experiment run and cannot overwrite this evidence.
