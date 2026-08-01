# Task 2B sequential evaluation scaffold — BLOCKED

**Status: blocked from merge and from execution. Never run. No gateway request
has been made from any of this code.**

This document describes a scaffold: a sequential, one-model-at-a-time evaluation
harness aimed at the CKFF gateway. It is written, tested offline, and deliberately
inert. Nothing here claims that any model is calibrated, reliable, or ready for
anything, and nothing here has produced a measurement of any kind.

## The blocking preconditions

None is satisfied at the time of writing, and all are recorded in code as
`app.models.sequential_plan.BLOCKING_PRECONDITIONS`:

1. **A current sanitized validator artifact** from the evaluation service is on
   record, with its timestamp and the deployment identifier it describes.
2. **The `__canary_invalid` route failed fast** in that artifact rather than
   returning 200. A 200 means something silently fell back, and then no number
   from the service is attributable.
3. **All five documented hidden-retry sources are closed** on the evaluation
   service: `litellm_settings.num_retries`, `router_settings.num_retries`,
   multi-route pooling of an alias, cooldowns parking a failing route, and client
   SDK defaults. The last is outside the proxy entirely and is the easiest to
   miss — the OpenAI and Anthropic SDKs both default to `max_retries=2`.
4. **`drop_params` is false**, so a parameter the harness believes it sent was
   actually sent. Silent stripping produces a run that measures something other
   than what it recorded.
5. **A frozen ordered alias snapshot exists**, hashed, with its retrieval
   timestamp, source, method and deployment identifier.

Until all hold, the `execution-gate` job in
`.github/workflows/task-2b-sequential-evaluation.yml` **fails on purpose**. A gate
that goes green before its preconditions are met is not a gate.

Production is not an acceptable substitute for any of this. The production gateway
retries at two layers, pools some aliases across up to three upstream routes,
cools failing routes down, drops parameters silently, and queues requests so a 429
never surfaces. Every one of those turns a failure into a slow success.

## The evaluation set comes from a frozen snapshot, not from code

An earlier version of this scaffold carried eleven aliases "observed on the
gateway", plus a flag to opt into anything outside them. **Both are gone.**

The hardcoded list was wrong three ways: it went stale as soon as the gateway
grew, it described *production* rather than the evaluation service, and — worst —
it read as authoritative. The opt-in flag was worse still, because it converted
"this alias is not in the frozen set" from a hard stop into a checkbox someone
ticks at 2am.

What replaces them is `app/models/alias_snapshot.py`. A benchmark run requires a
snapshot file recording:

| Field | Why |
|---|---|
| `aliases` | the exact ordered list, byte for byte |
| `sha256` | over the normalised list; recomputed on load and refused on mismatch |
| `retrieved_at` | UTC, explicit timezone — a naive timestamp cannot be tied to a deployment |
| `source` | what was read |
| `method` | how, in enough detail to repeat |
| `evaluation_service_url` | must be the evaluation service; a production URL is refused |
| `evaluation_service_identifier` | which deployment served that list, so a redeploy is visible |
| `excluded` | aliases deliberately left out, each with a stated reason |

Order is preserved exactly. The list is never sorted, trimmed, case-folded or
de-duplicated on load: each of those would silently produce a different experiment
from the one that was frozen. After the freeze, a plan may not add, remove,
rename, substitute or reorder an alias — a changed list is a new campaign with a
new snapshot, not a mutation of this one.

`__canary_invalid` is refused if it appears in the alias list. It routes at a
nonexistent upstream so a validator can prove failures surface fast; evaluating it
as a model would record a fabricated failure for a model that does not exist.

## The connectivity canary is not the benchmark

Two run kinds, and they produce different evidence:

| | `canary` | `benchmark` |
|---|---|---|
| Aliases | exactly `gpt-5.6-luna` | exactly the frozen snapshot |
| Snapshot | must be absent | required |
| Question answered | does the endpoint reply | the campaign |
| `is_benchmark_evidence` | `false` | `true` |

The canary runs *before* the freeze, so it cannot require a snapshot — and
precisely because it cannot, its artifact is stamped `is_benchmark_evidence:
false`. Conflating the two is how a smoke test ends up quoted as a model result.

One thing the canary cannot establish, stated plainly: **a single clean request
looks identical on a zero-retry gateway and on a five-retry one.** It proves
reachability, not the retry contract. Proving that needs an induced failure.

## Failures are results, and are never skipped

Every attempt is recorded with an outcome — `completed`, `rate_limited`,
`service_unavailable`, `http_error`, `timeout`, `transport_error`,
`protocol_error`, `output_limit_exceeded`, `model_mismatch`,
`concurrency_violation` — and every one is written into that model's evidence
beside its successes.

A 429 or a 503 is a *result*. ckff caps at 100 requests per minute account-wide,
and an entire flat-rate lane has been observed returning `503 No available
channel`. Neither is retried until it disappears: that would fabricate a success
out of a real failure, and `attempt_repeated: false` is recorded to say so. A
model quietly dropped because its channel was down would leave a comparison that
reads as complete and is not.

Two outcomes stop the whole campaign instead: `model_mismatch`, because a run that
cannot say which model answered is not evidence, and `concurrency_violation`,
because overlapping requests make the latency figures describe contention rather
than the models.

## Pacing is the harness's job

ckff enforces **100 requests per minute account-wide**, counted across every
model, and the evaluation service deliberately has no request queue — queueing
would hide a 429 that is itself evidence. The plan therefore carries a global
`requests_per_minute` (default 30) and refuses anything at or above the account
limit. A self-inflicted 429 is indistinguishable in the record from a genuine one.

Related, and recorded as `MIN_TOOL_CALL_MAX_TOKENS`: **never test tool calling
below 256 completion tokens.** Reasoning models emit reasoning content before the
tool call, so a smaller cap truncates the response before the call appears and
produces a false negative that looks exactly like a model lacking support.

Several aliases contain spaces and square brackets. They are treated as opaque
strings throughout: never split, never globbed, never lower-cased, never handed
to a shell. The snapshot's alias list is therefore **JSON and nothing else** —
`[aws]glm-5` starts with a bracket and `[ds2] deepseek-v4-pro` contains a space,
so any delimiter-sniffing parser would have to guess, and a guess here selects a
different model than the one that was frozen.

## What is enforced, and where

| # | Constraint | Where it is enforced |
|---|---|---|
| 1 | Manual dispatch only | workflow `on:` has only `workflow_dispatch`; asserted by `test_the_workflow_is_manual_dispatch_only` |
| 2 | Exactly one model at a time | explicit nested `for` loop in `SequentialRunner.run`, plus `_InFlightGuard`, which raises if a second request starts while one is in flight; no job matrix exists |
| 3 | Requested vs resolved model | `verify_resolved_model` — byte-for-byte equality; missing, empty, or non-string is a mismatch, not a pass |
| 4 | Zero client retries | `httpx.HTTPTransport(retries=0)`, then `assert_no_client_retry` reads the value back off the constructed transport |
| 5 | No cross-model substitution | no such code path exists; an AST test refuses any identifier naming one, and LiteLLM's router is deliberately not imported |
| 6 | Bounded timeouts | per-request `httpx.Timeout`; whole-run wall clock in `SequentialRunner.run`; `timeout-minutes` on both jobs |
| 7 | Request/token/output caps | `prepare_payload` before the call, `interpret_response` after it, `RunLimits` ceilings on both |
| 8 | Output is untrusted | `CallRecord` has no field carrying model text; only a SHA-256 and a length survive |
| 9 | No secrets in prompts or evidence | prompts come only from `PROMPT_CATALOGUE`; `assert_no_secret_material` scans outbound text and evidence; response headers are allowlisted |
| 10 | Separate evidence per model | `SequentialRunResult.evidence_documents` keys by `alias_slug`, one alias per document, no aggregates |
| 11 | Temporal owns visible retries | `CLIENT_RETRIES = 0`; `retry_owner: "temporal"` recorded in every plan and evidence document |
| 12 | Fail closed | every unrecognised state raises; execution is refused outright by `assert_execution_allowed` |

### Why raw `httpx` rather than LiteLLM

`app/models/gateway.py` goes through LiteLLM because, for the deterministic mock
provider, LiteLLM's dispatch and response normalisation are the feature. On this
path they are the hazard: the LiteLLM client and router own `num_retries`,
cooldowns, and model-group failover, and any of them would silently repair the
exact condition Task 2B exists to measure.

The retry count is **asserted, not assumed**. `httpx` is not pinned in
`pyproject.toml` — it arrives transitively through LiteLLM — so its defaults can
change under us, and a keyword argument that a future version renames would pass
silently. `assert_no_client_retry` therefore reads `httpcore`'s `_retries` off the
object that was actually constructed, and treats an internal shape it does not
recognise as an error rather than a pass. Redirect following is refused for the
same reason: a followed 3xx is an unrecorded second request that can land on a
different upstream. `trust_env=False` keeps an ambient `HTTPS_PROXY` from
inserting a hop the evidence would not mention.

Verified in the installed environment: `httpx` 0.28.1 with `httpcore` 1.0.9,
`HTTPTransport()._pool._retries == 0` by default; the scaffold sets it explicitly
anyway.

### Why the record carries no model text

`CallRecord` stores a SHA-256, a character count, a byte count, token counts,
latency, status, and an allowlisted set of response headers. It has no field for
the completion itself. A caller cannot act on content it never receives, which
makes "output cannot steer control flow" a property of the type rather than a rule
someone has to remember.

This is a real limitation, not a free win: **this path can establish reachability
and attribution, and cannot say anything about answer quality.** A future
evaluation that needs the text has to add a deliberate, reviewed channel for it,
with its own containment story.

## Known costs of these choices

- **Exact-equality model comparison will false-alarm** if the gateway ever
  reformats the `model` field it echoes — for example, returning
  `openai/gpt-5.6-luna` for an alias registered as `gpt-5.6-luna`. That is the
  intended direction of error: an unexplained difference stops the run rather than
  being normalised away. If it happens, the fix is to establish what the gateway
  actually echoes and record it, not to loosen the comparison.
- **A fatal outcome still ends the campaign early.** `model_mismatch` and
  `concurrency_violation` raise `SequentialRunAborted` carrying the partial result
  rather than returning a short result that reads as a whole one. Every other
  failure — 429, 503, timeout, transport, protocol — is recorded and the run
  continues, so a single bad channel no longer costs the remaining models' data.
- **The limits are conservative bounds, not calibrated values.** The only prior
  art in this repository is `DEFAULT_TIMEOUT_SECONDS = 30.0` in
  `app/models/gateway.py` and the 120-second bound in the CKFF smoke action.
  Defaults are one request per model, 120 s per request, 900 s per run, 512
  completion tokens, 256 KiB per response, 30 requests per minute globally. No evidence supports any of them as
  correct; they are chosen so that an unattended mistake stays small.
- **`trust_env=False` will break a runner that genuinely needs a proxy.** That is
  a decision to revisit deliberately, by configuring the proxy explicitly and
  recording it, not by re-enabling environment discovery.

## What has and has not been verified

**Verified, offline:** 89 unit tests covering resolution mismatch (including
missing and empty), the constructed transport's retry count, the absence of any
substitution path, sequential ordering with a concurrency guard exercised from a
second thread, every limit on both sides of the call, hostile-output handling,
per-model evidence separation, alias round-tripping for every observed alias
including the bracketed and space-containing ones, and the workflow's trigger,
permissions, input requirements and shell-interpolation hygiene.

**Not verified, and cannot be from here:**

- that the gateway echoes the alias in the form this client expects;
- that CKFF's proxy-side retry count is what any document says it is;
- anything about latency, cost, availability, or answer quality;
- that the workflow runs, since it has never been dispatched.

Nothing in this scaffold is calibrated, production-ready, or generally reliable.
The lab's only positive outcome remains `accepted_for_review`, and this path does
not produce even that — it produces records of what was asked and what answered.

## Not wired into CI

This workflow is referenced by no other workflow, and no other workflow is
modified by it. It runs only when a human dispatches it, and in its current form
the run stops at the execution gate. The steps that would issue requests are
deliberately **absent** rather than present-and-disabled: an unreachable egress
path in the repository is the kind of thing that stops being unreachable during a
hurried edit.

The CKFF credential is not referenced anywhere in the workflow. A workflow that
makes no request needs no key, and a secret pulled into an environment that does
not need it is a secret that can end up in a log.

## Files

| Path | Role |
|---|---|
| `app/models/alias_snapshot.py` | the frozen, hashed evaluation-service alias list |
| `app/models/sequential_plan.py` | plan, run kinds, alias validation, limits, prompt catalogue, blocked-state guard |
| `app/models/ckff_client.py` | the bounded non-retrying client and the sequential runner |
| `scripts/prepare_task_2b_run.py` | offline preparation and the execution gate |
| `.github/workflows/task-2b-sequential-evaluation.yml` | manual-dispatch scaffold, blocked |
| `tests/unit/test_task_2b_scaffold.py` | the constraints above, asserted |

## Unblocking checklist

1. A current sanitized validator artifact from the evaluation service, with its
   timestamp and deployment identifier, showing `__canary_invalid` failing fast
   rather than returning 200.
2. Evidence — not assertion — that all five hidden-retry sources are closed and
   that `drop_params` is false.
3. One `gpt-5.6-luna` connectivity canary, reviewed. Its artifact says
   `is_benchmark_evidence: false`; it does not become the benchmark.
4. The exact current alias list read off the evaluation service and frozen, with
   every real chat alias classified as frontier, non-frontier or ambiguous, and
   the ambiguous ones resolved with the user rather than by this scaffold.
5. Only then: flip `EXECUTION_BLOCKED`, add the request-issuing steps, and expect
   the first benchmark run to be `max_requests_per_model = 1`.

Nothing in steps 1-4 is machine-checkable from inside this repository, which is
why `BLOCKING_PRECONDITIONS` is prose. A flag that claimed to verify them would be
a fake gate.
