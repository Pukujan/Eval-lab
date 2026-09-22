# TASK-0040 — Fast provider benchmark wave

## Status

Complete — recommendation wave finished. This task ran a new, append-only provider wave; it did not modify
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
- InferHub is an append-only follow-on experiment. The historical
  `EXP-20260922-023-inferhub-wave` remains immutable, and the refreshed
  recommendation-policy wave is `EXP-20260922-024-inferhub-recommendation-wave`;
  neither may alter EXP-022 outputs.
- Frozen source pool: EXP-015 records and typed specification, referenced by
  fingerprint and never edited.
- Arms: direct Grok 4.6, direct Grok 4.7, YOLO-Auto Qwen3.8 Flash, and
  OpenRouter pinned `typesafe/jev-1.13`.
- Safe starting limits: Grok 4.6/4.7 four isolated CLI workers each, Qwen
  Flash two workers, Jev eight workers, Bonsai one request at a time.
- Public-selection canary precedes any blind-holdout run. Provider errors,
  rate limits, skips, and parse failures remain unresolved statuses.
- InferHub model IDs are provider-qualified and captured exactly; aliases and
  ChatGPT/Codex model IDs are excluded from the new arm set.

## Required files

- `scripts/run_grok_luna_qwen_bakeoff.py`
- `scripts/run_fast_jev_arm.py`
- `scripts/report_fast_provider_wave.py`
- `tests/test_grok_luna_qwen_bakeoff.py`
- `docs/GROK_BUILD_CLI_AUTOMATION.md`
- `docs/INFERHUB_AUTOMATION.md`
- `scripts/run_inferhub_arm.py`
- `tests/test_inferhub_arm.py`
- `experiments/EXP-20260922-023-inferhub-wave/`
- `experiments/EXP-20260922-024-inferhub-recommendation-wave/`
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

## Pause checkpoint — 2026-09-22

The InferHub follow-on `EXP-20260922-023` was release-researched and
preregistered against the immutable EXP-015 pool. Live discovery returned `251`
models. The selected non-ChatGPT routes include both DeepSeek V4.1 Flash arms
(`cb/deepseek-v4.1-flash` and `cbcn/deepseek-v4.1-flash`), as well as the
cheapest and newest verified route choices on the other active rails. Claude is
present only as the `cc/` rail choices: `cc/claude-haiku-4-5` and
`cc/claude-fable-5-1`.

The runner was corrected to allow reasoning routes up to `1024` output tokens;
the earlier `32`-token canary parse failures were retained and not promoted.
Successful retries validated the selected routes except
`cp/cline-pass/qwen3.8-max`, which returned repeat `503` provider errors and
is excluded from bulk execution. The user then requested a pause, so all
InferHub runner processes were stopped cleanly with no remaining runner
processes.

Partial public checkpoints are preserved in new append-only run directories.
The valid DeepSeek checkpoints currently contain `206` rows on `cb` (`177 ok`,
`26 parse_error`, `3 provider_error`) and `272` rows on `cbcn` (`248 ok`, `22
parse_error`, `2 provider_error`). Claude checkpoints contain `224` Haiku rows
(`179 ok`, `45 provider_error`) and `195` Fable rows (`162 ok`, `33
provider_error`). Gemini High has `90 ok` rows; the incorrectly named
`ag/gemini-3.8-flash` diagnostic run is excluded. No checkpoint has duplicate
record IDs. The completed EXP-022 blind comparison is retained separately.

Files changed: `docs/INFERHUB_AUTOMATION.md`,
`scripts/run_inferhub_arm.py`, `tests/test_inferhub_arm.py`,
`experiments/EXP-20260922-023-inferhub-wave/`,
`experiments/EXP-20260922-022-fast-provider-wave/`, this task file, and
`checkpoints/CURRENT.md`. Validation before pause: InferHub tests `3 passed`,
Ruff clean, live catalog check `251` models with no key leakage, and duplicate
ID audit clean for all partial public checkpoints.

Decision: DeepSeek V4.1 Flash remains a primary selected family; it was not
dropped. This pause checkpoint is superseded for future execution by the
deduplicated recommendation policy below. EXP-023 remains immutable, and its
partial routes are historical evidence only.

## InferHub recommendation-policy refresh — 2026-09-22

The updated InferHub policy uses `routing_eligible_only`, one model per family,
at most two models per vendor, minimum tier order `2`, minimum capability score
`25`, at least two priced providers, at least `55` catalog availability, at
least `90%` public seven-day availability, and a maximum supply-weighted or
median cost of `0.5` USDC per million tokens. The top-20 view is explanatory;
the operational shortlist is the nine-family `daily-shortlist.json` result.
Runtime reliability is only claimed after `30` observations, and probes must
stream SSE with a content type and `[DONE]` marker.

For the next append-only experiment, deduplicate each operational family to the
cheapest currently listed exact route, without including GPT/ChatGPT/Codex:

- DeepSeek V4.1 Flash → `cb/deepseek-v4.1-flash`
- GLM 5.3 Flash → `cbcn/glm-5.3-flash`
- DeepSeek V4 Flash → `cbcn/deepseek-v4-flash`
- Qwen3.8 Flash → `ali/qwen3.8-flash`
- MiniMax M3 → `cbcn/minimax-m3`
- GLM 5.2 → `ali/glm-5.2`
- Qwen 3.8 Max → `ali/qwen3.8-max`
- Kimi K2.7 Code → `ali/kimi-k2.7-code`
- MiMo V2.5 → `cp/cline-pass/mimo-v2.5`

This replaces the earlier 14-route bulk proposal for the next wave only. No
provider calls or EXP-023 mutations were made during this refresh.

## Recommendation-wave execution checkpoint — 2026-09-22

The user resumed execution after the pause. The new append-only experiment is
preregistered from InferHub's 2026-09-22 `daily-shortlist.json` and uses one
cheapest exact route per selected family: `cb/deepseek-v4.1-flash`,
`cbcn/glm-5.3-flash`, `cbcn/deepseek-v4-flash`, `ali/qwen3.8-flash`,
`cbcn/minimax-m3`, `ali/glm-5.2`, `ali/qwen3.8-max`,
`ali/kimi-k2.7-code`, and `cp/cline-pass/mimo-v2.5`. This replaces the old
14-route proposal for the new experiment only. Qwen4B and ChatGPT/Codex
models remain excluded.

The new run uses the immutable EXP-015 source pool, streaming SSE, fresh
checkpoint directories, one-record canaries, then public and blind partitions.
Routes run in bounded batches with four workers per route; unresolved provider,
rate-limit, timeout, and parse statuses remain explicit.

Canaries completed in fresh directories under EXP-024. Eight routes passed on
the retry-stable streaming contract: DeepSeek V4.1 Flash, GLM 5.3 Flash,
DeepSeek V4 Flash, Qwen3.8 Flash, MiniMax M3, GLM 5.2, Qwen 3.8 Max, and
Kimi K2.7 Code. The first DeepSeek V4.1 canary had one transient parse error;
its fresh retry returned `ok`. The selected MiMo V2.5 route returned HTTP 402
twice and is retained as an explicit unavailable arm; no alternate provider
route is substituted.

The live catalog check after refresh reported `254` models and `498` remaining
rate-limit units. The authenticated compare option in
`scripts/check_inferhub_catalog.py` is incompatible with the current list-form
catalog snapshot, so the no-compare live check was used and its output was not
treated as benchmark evidence.

The eight-arm public selection is complete in
`experiments/EXP-20260922-024-inferhub-recommendation-wave/runs/`. All arms
have 648 duplicate-free rows and are compared offline in
`runs/public-comparison-20260922/`. Resolved accuracy / coverage are: GLM 5.2
`0.9872 / 0.9660`, Kimi K2.7 Code `0.9753 / 0.9985`, Qwen3.8 Flash
`0.9846 / 1.0000`, Qwen 3.8 Max `0.9861 / 1.0000`, DeepSeek V4.1 Flash
`0.9890 / 0.8410`, DeepSeek V4 Flash `0.9891 / 0.8488`, GLM 5.3 Flash
`0.9799 / 0.9985`, and MiniMax M3 `0.9687 / 0.9861`. Parse errors remain
explicit unresolved statuses; DeepSeek had the highest public parse-error
rates (`103` and `98`).

The blind holdout is complete for all eight executable arms. Results are in
`runs/blind-comparison-20260922/` and summarized in `RESULTS.md`: Qwen3.8
Flash achieved full coverage with resolved accuracy `0.9921`; Qwen 3.8 Max
achieved `0.9908` at full coverage; DeepSeek V4 Flash reached conditional
accuracy `0.9984` at `0.8039` coverage; DeepSeek V4.1 Flash reached `0.9871`
at `0.8171`; GLM 5.2 `0.9917` at `0.9566`; Kimi K2.7 Code `0.9855` at
`0.9974`; GLM 5.3 Flash `0.9788` at `0.9947`; and MiniMax M3 `0.9798` at
`0.9789`. MiMo remains a documented HTTP 402 unavailable arm with no fallback.

All eight blind outputs contain exactly 760 duplicate-free records, all runner
processes have exited, and public/blind comparisons use gold only offline.

## Next atomic action

No provider execution remains for TASK-0040. Preserve MiMo's failed canaries
and all partial/failed statuses as historical evidence. Do not resume the old
14-route plan, change EXP-023, or treat the recommendation score as benchmark
gold.

## Decisions and unresolved questions

- Direct `grok models` discovery exposed `grok-4.7` as the CLI default and
  `grok-4.6` as an available model, but the current shell was not authenticated
  at discovery time. A canary must establish whether execution is available.
- OpenCode is not an allowed substitute for the Grok arms.
- Qwen4B is explicitly excluded from this wave.
- The existing EXP-015 result remains immutable; any retry or new model is a
  new run and experiment identity.
