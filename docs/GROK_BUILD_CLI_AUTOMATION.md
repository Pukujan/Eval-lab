# Grok Build CLI automation

This is the Eval Lab operating guide for the `grok` command-line client. It
covers the subscription-backed Grok Build CLI route used by the benchmark
runner. It is not a license to replace that route with the separately metered
xAI API.

Official references:

- [Grok Build overview](https://docs.x.ai/build/overview)
- [Headless and scripting](https://docs.x.ai/build/cli/headless-scripting)
- [CLI reference](https://docs.x.ai/build/cli/reference)
- [Official Grok Build source: headless mode](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/14-headless-mode.md)

## Install and authenticate

On Windows PowerShell, use the official installer only when the local CLI is
missing:

```powershell
irm https://x.ai/cli/install.ps1 | iex
grok --version
```

The normal interactive route is `grok login`, which opens the browser OAuth
flow. In a headless environment the official documentation also describes
`XAI_API_KEY`; never print the value or commit it. Eval Lab's Grok benchmark
policy uses the already-authenticated direct CLI subscription route and does
not silently switch to an API-key endpoint.

Before a run, discover the exact model catalog and record it as metadata:

```powershell
grok models
```

The requested model and the model surfaced in the response are separate facts.
For example, the current benchmark discovery exposes requested `grok-4.6` and
`grok-4.7`, while the Build route has surfaced `grok-4.6-build` and
`grok-4.7-build`. Do not assume that an alias or default model is equivalent to
the requested ID.

## One headless structured-output request

`--single`/`-p` makes one non-interactive request. `streaming-json` is the
CLI's newline-delimited JSON event format. `--json-schema` constrains the
model's structured result. Use a very small schema for label-only judging:

```powershell
$sessionId = [guid]::NewGuid().ToString()
$socket = Join-Path $env:TEMP ("eval-lab-grok-$sessionId.sock")
$schema = '{"type":"object","properties":{"label":{"type":"string","enum":["fail","pass"]}},"required":["label"],"additionalProperties":false}'

grok `
  --no-auto-update `
  --model grok-4.7 `
  --session-id $sessionId `
  --output-format streaming-json `
  --json-schema $schema `
  --max-turns 1 `
  --disable-web-search `
  --verbatim `
  --no-subagents `
  --no-plan `
  --permission-mode dontAsk `
  --leader-socket $socket `
  --single 'Return exactly one JSON object with a legal label.'
```

The installed Eval Lab binary (`grok 1.0.40`) accepts `--no-auto-update`; this
prevents background update checks from competing with a scripted request. The
current runner passes both `--output-format streaming-json` and
`--json-schema`; verify this combination after a CLI upgrade because local help
describes JSON Schema as implying JSON output. If an upgraded client changes
that precedence, either consume its documented `json` output or use its
documented structured-streaming mode, but keep strict schema validation.

For automation, consume stdout and stderr concurrently. A streaming client
must not read stdout to completion while leaving stderr unread, because either
pipe can fill and stall the child process. Parse each complete NDJSON line,
retain only normalized metadata, and wait for both streams to close.

## Safe concurrency

The CLI is a session-oriented agent, not a shared stateless socket. To run
independent requests concurrently:

1. Start one CLI process per record/request.
2. Generate a fresh UUID `--session-id` for every process.
3. Generate a fresh `--leader-socket` for every process; never share the default
   leader socket between workers.
4. Use `--max-turns 1`, `--no-subagents`, `--no-plan`, and disable tools that
   are outside the benchmark contract.
5. Give every arm its own output directory and append-only checkpoint file.
6. Bound workers per provider and preserve `provider_error`, `rate_limited`,
   timeout, and parse statuses without assigning a fallback label.

Eval Lab's observed starting limit is four Grok workers per arm. If process
errors rise, lower the worker count for the remaining records. A continuation
must use `--resume` against the same validated checkpoint and must not rewrite
completed predictions. A change in model, prompt, schema, or benchmark pool
requires a new run/experiment identity.

The runner's current command construction is in
[`scripts/run_grok_luna_qwen_bakeoff.py`](../scripts/run_grok_luna_qwen_bakeoff.py).
It uses streaming JSON, native schema constraints, unique UUID sessions,
isolated leader sockets, and per-record fsynced checkpoints.

## Benchmark parsing contract

- Treat the requested model ID, surfaced model IDs, CLI version, and route as
  separate metadata fields.
- Accept only a legal schema-validated label for the current judgment mode.
- Do not search arbitrary stderr or an error message for `pass`/`fail` and call
  that a prediction.
- Do not include gold labels, answer keys, or verifier outputs in the provider
  prompt.
- Keep raw provider transcripts out of committed artifacts unless a separate
  experiment explicitly authorizes their retention and redaction.
- Provider failures are execution/coverage evidence, not ordinary wrong labels.

## CLI versus xAI API

The official xAI API also documents streaming and structured outputs, but that
is a different access path with different credentials, quotas, and accounting.
Use it only in an explicitly preregistered API experiment. For the current
Eval Lab Grok arms, call the authenticated `grok` CLI directly and do not
replace it with OpenCode, OpenRouter, or a direct API fallback.
