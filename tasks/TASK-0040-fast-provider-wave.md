# TASK-0040 — Fast provider benchmark wave

## Status

Active. This task runs a new, append-only provider wave; it must not modify
EXP-014 through EXP-021 or start new Qwen4B inference.

## Objective

Compare the directly authenticated Grok Build CLI at the exact discovered
models `grok-4.6` and `grok-4.7`, retain Qwen3.8 Flash through YOLO-Auto, and
run the current Jev OpenRouter Decisions route with bounded concurrency. Keep
Bonsai 2 27B on the Mac serial because its two-slot canary reduced throughput.
Use the Gravebuster Tailscale host only for isolated verifier/harness work;
provider credentials remain on the Windows host.

## Scope

- New experiment: `experiments/EXP-20260922-022-fast-provider-wave/`.
- Frozen source pool: EXP-015 records and typed specification, referenced by
  fingerprint and never edited.
- Arms: direct Grok 4.6, direct Grok 4.7, YOLO-Auto Qwen3.8 Flash, and
  OpenRouter pinned `typesafe/jev-1.13`.
- Safe starting limits: Grok 4.6/4.7 four isolated CLI workers each, Qwen
  Flash two workers, Jev eight workers, Bonsai one request at a time.
- Public-selection canary precedes any blind-holdout run. Provider errors,
  rate limits, skips, and parse failures remain unresolved statuses.

## Required files

- `scripts/run_grok_luna_qwen_bakeoff.py`
- `scripts/run_fast_jev_arm.py`
- `scripts/report_fast_provider_wave.py`
- `tests/test_grok_luna_qwen_bakeoff.py`
- `docs/GROK_BUILD_CLI_AUTOMATION.md`
- `experiments/EXP-20260922-022-fast-provider-wave/`
- this task file and `checkpoints/CURRENT.md`

## Checkpoint

Initial implementation is committed at `85e79c0`. The runner now recognizes a
separate `grok_47` arm while preserving the existing direct CLI adapter and
isolated leader sockets. The checkpointed Jev runner is also committed. No
provider was called by this code change. Targeted tests (`6 passed`), Ruff,
compile, and diff checks are green.

The one-record canaries completed concurrently in fresh directories:

- Grok 4.6: `ok`, surfaced `grok-4.6-build`, approximately 13.57 seconds.
- Grok 4.7: `ok`, surfaced `grok-4.7-build`, approximately 12.98 seconds.
- Qwen Flash: `ok`, surfaced `qwen3.8-flash`, approximately 4.35 seconds.
- Jev pinned: `ok`, surfaced `typesafe/jev-1.13-20260917`, approximately
  0.47 seconds.

Canary artifacts are retained under EXP-022 `runs/` and summarized in
`canary-summary.md`. These results authorize the bounded public-selection wave.

During the public run, the installed Grok Build CLI was rechecked against the
official headless-mode guidance. The direct adapter already used NDJSON
`streaming-json`, native JSON Schema, one turn, no web search, and no
subagents. The runner now also disables background auto-update checks and
assigns every request a unique UUID session in addition to its isolated leader
socket. The installed `grok 1.0.40` accepted `--no-auto-update`; targeted
tests are now `7 passed` and Ruff is clean.

The durable CLI guide is now in `docs/GROK_BUILD_CLI_AUTOMATION.md`, covering
authentication, exact model discovery, structured streaming, per-process
session isolation, bounded concurrency, checkpoint/resume, and the CLI/API
boundary.

Public selection is complete and compared offline in
`runs/public-comparison-20260922-v2/`:

- Grok 4.6: `643/648 ok`, `3 provider_error`, `2 rate_limited`, resolved
  accuracy `0.3701`; surfaced `grok-4.6-build`.
- Grok 4.7: `617/648 ok`, `31 provider_error`, resolved accuracy `0.3679`;
  surfaced `grok-4.7-build`.
- Qwen Flash: `645/648 ok`, `3 parse_error`, resolved accuracy `0.9674`;
  surfaced `qwen3.8-flash`.
- Jev pinned: `648/648 ok`, resolved accuracy `0.8796`; surfaced
  `typesafe/jev-1.13-20260917`.

The 4.6/4.7 same-record agreement was `588/612` (`0.9608`). The public
comparison uses gold only offline; unresolved provider statuses remain outside
accuracy. The public arm outputs and comparison are ready for the frozen blind
holdout pass.

## Next atomic action

Launch the blind-holdout execution concurrently as four isolated processes:
Grok 4.6 with four workers, Grok 4.7 with four hardened workers, Qwen Flash
with two workers, and pinned Jev with eight workers. Preserve per-record
checkpoints and stop an arm if provider status indicates a route failure or
rate limit.

## Decisions and unresolved questions

- Direct `grok models` discovery exposed `grok-4.7` as the CLI default and
  `grok-4.6` as an available model, but the current shell was not authenticated
  at discovery time. A canary must establish whether execution is available.
- OpenCode is not an allowed substitute for the Grok arms.
- Qwen4B is explicitly excluded from this wave.
- The existing EXP-015 result remains immutable; any retry or new model is a
  new run and experiment identity.
