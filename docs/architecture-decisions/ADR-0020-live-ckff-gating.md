# ADR-0020 — The live CKFF path stays gated and manual-only

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Milestone 2's mandatory CI demonstration runs **without paid credentials**, using
deterministic provider and verifier test adapters. There is also a real gateway
with real models behind it, and a scaffold aimed at it
(`docs/task-2b-scaffold.md`) that has never been executed.

The pull toward wiring the real gateway into the normal CI path is strong, and
every argument for it is an argument about convenience: fresher evidence, fewer
manual steps, one fewer thing to remember. None of them is an argument that the
resulting numbers would mean anything.

## Decision

Four constraints, all of which already have code behind them.

**1. Manual dispatch only.** The live path is `workflow_dispatch` and nothing
else — no push, no pull request, no schedule, no `workflow_call` from another
workflow. `.github/workflows/task-2b-sequential-evaluation.yml` declares only
`workflow_dispatch`, and `test_the_workflow_is_manual_dispatch_only` in
`tests/unit/test_task_2b_scaffold.py` asserts the trigger set is exactly that.
The `execution-gate` job **fails on purpose** while
`app.models.sequential_plan.BLOCKING_PRECONDITIONS` are unmet, because a gate
that goes green before its preconditions are met is not a gate.

**2. The evaluation service, never production.** A production URL is *refused*,
not warned about. `EVALUATION_SERVICE_URL` in `app/models/alias_snapshot.py` is
the only base URL a snapshot may name, and `.github/workflows/ckff-connectivity.yml`
refuses a `CKFF_BASE_URL` that is not it — with no fallback default, since "a
default that silently pointed at the production gateway would produce a green
connectivity check against a service whose numbers are unusable as evidence — the
failure mode being that it *works*."

**3. The Luna canary is connectivity evidence and nothing else.** It runs exactly
`gpt-5.6-luna`, requires the snapshot to be **absent** (it runs before the
freeze, so it cannot require one), and its artifact is stamped
`is_benchmark_evidence: false`. It can never unblock the benchmark by itself.

**4. The benchmark requires the frozen snapshot.** No snapshot, no benchmark. The
snapshot is hashed over its normalised alias list, order-preserving, and refused
on hash mismatch — "the snapshot has been edited or is corrupt; it is not the
list that was frozen, so it is not the experiment that was agreed."

## Why a green canary proves almost nothing

Stated plainly, because it is the fact that makes constraint 3 non-negotiable:

**A single clean request looks identical on a zero-retry gateway and on a
five-retry one.** The success path is byte-for-byte the same. The client sends
one request, receives one 200, and records one latency, whether the gateway tried
once or five times behind it.

So the canary establishes that the endpoint answers and that the alias resolves.
It establishes **nothing** about the retry contract — and the retry contract is
what decides whether any later number is attributable to the model rather than to
the gateway. Proving it needs an **induced failure**: the `__canary_invalid`
route failing fast rather than returning 200. A 200 there means something
silently fell back, and then no number from the service is attributable at all.

Production is not an acceptable substitute for any of this. It retries at two
layers, pools some aliases across up to three upstream routes, cools failing
routes down, drops parameters silently, and queues requests so a 429 never
surfaces. Every one of those turns a failure into a slow success.

## Alternatives rejected

- **Run the live path on a schedule, for freshness.** Recurring cost, and worse:
  a schedule makes an unattended live run normal, so the first time a
  precondition regresses nobody is watching. Every scheduled green run is also
  one more artifact that can later be quoted as a model result.
- **Let a green canary unblock the benchmark.** That is the exact conflation the
  scaffold document exists to prevent — "how a smoke test ends up quoted as a
  model result". Different question, different artifact, different flag.
- **Point the benchmark at production because the evaluation service is smaller
  or occasionally unavailable.** A 503 `No available channel` from the evaluation
  service is a *result*, recorded with `attempt_repeated: false`. A production
  run that quietly succeeds on the fourth internal retry is not a result; it is a
  number with no owner.
- **Keep the request-issuing steps present but disabled behind a flag.** They are
  deliberately **absent** instead, because "an unreachable egress path in the
  repository is the kind of thing that stops being unreachable during a hurried
  edit". The same reasoning deleted the earlier opt-in alias flag: it converted
  "this alias is not in the frozen set" from a hard stop into a box someone ticks
  at 2am.
- **Reference the CKFF secret in the gated workflow so it is ready to go.** A
  workflow that makes no request needs no key, and a secret pulled into an
  environment that does not need it is a secret that can end up in a log.
- **A machine-checkable precondition flag instead of prose.**
  `BLOCKING_PRECONDITIONS` is prose because nothing in the first four unblocking
  steps is checkable from inside this repository. A flag claiming to verify them
  would be a fake gate, which is worse than no gate.

## Consequences

- **The mandatory demonstration needs no paid credentials**, so anyone can run
  the full Milestone 2 pipeline end to end against deterministic provider and
  verifier adapters. That is the property being protected here.
- **Live evidence arrives only when a human dispatches a run and reviews it.**
  Slow, on purpose, and consistent with the human being the final authority
  (ADR-0014).
- **Retries on the live path belong to Temporal** (ADR-0017). Client retries are
  zero and **asserted, not assumed** — `assert_no_client_retry` reads
  `httpcore`'s `_retries` off the transport that was actually constructed and
  treats an unrecognised internal shape as an error rather than a pass.
- **Not established, and cannot be from here:** that the gateway echoes the alias
  in the form this client expects; that CKFF's proxy-side retry count is what any
  document says it is; anything about latency, cost, availability or answer
  quality; or that the workflow runs at all, since it has never been dispatched.
- **Not established: any model's capability.** When this path does run, it
  produces records of what was asked and what answered. `CallRecord` carries no
  model text by construction (ADR-0018), so this path can establish reachability
  and attribution and cannot say anything about answer quality. Eval-lab's only
  positive outcome remains `accepted_for_review` (ADR-0019), and this path does
  not produce even that.
