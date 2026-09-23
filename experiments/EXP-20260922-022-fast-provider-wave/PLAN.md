# Plan

## Hypothesis

Independent remote judge arms can be evaluated faster through bounded
per-record concurrency, while preserving one normalized checkpoint per
record and exact provider/model identity.

## Primary comparison

Compare resolved accuracy and coverage on the frozen blind holdout for direct
Grok 4.6 versus direct Grok 4.7, with Qwen Flash and pinned Jev as contextual
arms. Provider failures, rate limits, skips, and parse failures are not
ordinary wrong answers.

## Frozen inputs

- Source pool: `experiments/EXP-20260921-015-grok-luna-qwen-bakeoff`.
- Records fingerprint: `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`.
- Blind ID fingerprint: `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.
- Typed spec: `eval-lab-system-one` v0.1.0.
- Gold provenance: answer key and deterministic verifier from the source pool.

## Arms and execution limits

| Arm | Route | Workers |
| --- | --- | ---: |
| Grok 4.6 | direct authenticated `grok` Build CLI | 4 |
| Grok 4.7 | direct authenticated `grok` Build CLI | 4 |
| Qwen3.8 Flash | YOLO-Auto OpenAI-compatible endpoint | 2 initially |
| Jev 1.13 | OpenRouter Decisions endpoint | 8 |

Each arm receives a separate output directory. Grok arms use isolated leader
sockets. No OpenCode or paid fallback route is allowed. Bonsai is not part of
this remote wave and remains one-at-a-time on the Mac.

## Stopping and exclusion rules

Run a one-record public-selection canary for every available route first. If
the direct Grok CLI is unauthenticated or an exact requested model is not
surfaced, record the provider status and stop that arm. Do not substitute
OpenCode or another Grok model. If Qwen rate-limits, preserve the status and
reduce or stop concurrency. A blind run is allowed only after the canaries
are recorded and the new run directories are non-empty-safe.

No new Qwen4B inference, no retries inside a one-pass artifact, no fabricated
labels, no mutation of EXP-014 through EXP-021, and no use of provider gold
labels in requests.
