# Task 2B sequential evaluation scaffold — BLOCKED

**Status: blocked from merge and from execution. Never run. No gateway request
has been made from any of this code.**

This document describes a scaffold: a sequential, one-model-at-a-time evaluation
harness aimed at the CKFF gateway. It is written, tested offline, and deliberately
inert. Nothing here claims that any model is calibrated, reliable, or ready for
anything, and nothing here has produced a measurement of any kind.

## The two blocking preconditions

Neither is satisfied at the time of writing, and both are recorded in code as
`app.models.sequential_plan.BLOCKING_PRECONDITIONS`:

1. **PR #1 is green and merged.** This scaffold sits on top of the CKFF
   connectivity work and must not land ahead of it.
2. **A confirmed CKFF route with zero hidden proxy retries exists** for every
   alias under evaluation. `docs/ckff-gateway-setup.md` records that CKFF
   currently performs five same-model retries. That is a reasonable availability
   posture for an ordinary application and a disqualifying one here: a latency
   figure that silently contains a second attempt, a failure rate that has already
   been repaired upstream, and a cost figure covering requests nobody counted are
   all unattributable. Unattributable numbers are worse than no numbers, because
   they look like evidence.

Until both hold, the `execution-gate` job in
`.github/workflows/task-2b-sequential-evaluation.yml` **fails on purpose**. A gate
that goes green before its preconditions are met is not a gate.

## The evaluation set is deliberately unchosen

The gateway exposes many aliases and keeps gaining more. Aliases confirmed at the
time of writing are recorded in `OBSERVED_GATEWAY_ALIASES`:

```
[aws]glm-5   [aws]kimi-k2-thinking   [aws]minimax-m2.5   [ds2] deepseek-v4-pro
[grok] grok-4.5   claude-opus-4-7   gemini-3.5-flash   gpt-5.6-luna
gpt-5.6-sol   gpt-5.6-terra   qwen-3.6-max
```

**That tuple is what has been seen, not what will be run.** Which models Task 2B
evaluates — how many, chosen how, and to answer what question — is an open
research decision that nobody has taken. Writing a seven-model list into the code
would freeze an unmade decision and make it look settled, so the scaffold refuses
to run without an explicit selection: the workflow input `models` is required and
has no default, and `SequentialRunPlan` raises when handed an empty set.

The observed list is used only to catch a typo before a run rather than after
one. An alias outside it is refused unless the operator passes
`--allow-unconfirmed-aliases`, and the plan then records which aliases were
unconfirmed.

Several aliases contain spaces and square brackets. They are treated as opaque
strings throughout: never split, never globbed, never lower-cased, never handed
to a shell. The selection input is therefore a **JSON array and nothing else** —
`[aws]glm-5` starts with a bracket and `[ds2] deepseek-v4-pro` contains a space,
so any delimiter-sniffing parser would have to guess, and a guess here selects a
different model than the operator intended.

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
- **Aborting on the first refusal loses the remaining models' data.** A run that
  stops early raises `SequentialRunAborted` carrying the partial result rather
  than returning a short result that reads as a whole one.
- **The limits are conservative bounds, not calibrated values.** The only prior
  art in this repository is `DEFAULT_TIMEOUT_SECONDS = 30.0` in
  `app/models/gateway.py` and the 120-second bound in the CKFF smoke action.
  Defaults are one request per model, 60 s per request, 900 s per run, 512
  completion tokens, 256 KiB per response. No evidence supports any of them as
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
| `app/models/sequential_plan.py` | plan, alias validation, limits, prompt catalogue, blocked-state guard |
| `app/models/ckff_client.py` | the bounded non-retrying client and the sequential runner |
| `scripts/prepare_task_2b_run.py` | offline preparation and the execution gate |
| `.github/workflows/task-2b-sequential-evaluation.yml` | manual-dispatch scaffold, blocked |
| `tests/unit/test_task_2b_scaffold.py` | the constraints above, asserted |

## Unblocking checklist

1. PR #1 green and merged.
2. A CKFF virtual key or route with proxy-side retries set to zero, for each alias
   in the selected set, with that configuration evidenced rather than asserted.
3. A human decision on the evaluation set, recorded — the `selection_source`
   input exists so the plan artifact names where that decision is written down.
4. Only then: flip `EXECUTION_BLOCKED`, add the request-issuing steps, and expect
   the first run to be a single alias with `max_requests_per_model = 1`.
