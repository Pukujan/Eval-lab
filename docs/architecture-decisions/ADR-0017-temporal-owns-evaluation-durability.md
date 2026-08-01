# ADR-0017 — Temporal owns evaluation durability, including human approval waits

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

A Milestone 2 evaluation is no longer a function call. It is intake and schema
validation, hash and JobSpec correspondence, isolated public deterministic
checks, a versioned rubric-scoring boundary, an optional controlled model call, a
verifier round trip, a decision, a report — and, at the end, a wait for a human
who is the only party that can accept anything (ADR-0014).

Every one of those steps wants a timeout, a retry policy, and somewhere to be
resumed from after a crash. Building any of it here recreates a durable execution
engine badly, and worse, produces two competing sources of truth about what has
already happened. ADR-0002 settled that argument for the investigation graph; the
same argument applies unchanged, and this ADR extends it to the evaluation
pipeline and to approval.

## Decision

**Temporal owns durability. Eval-lab writes no scheduler, no queue, no retry
framework, no state machine, and no polling loop.**

- Retries, backoff, `start_to_close_timeout`, cancellation, recovery and replay
  are Temporal's. Activity code does the work and does not manage its own
  reattempts.
- Workflow code carries ordering and nothing else. Anything that touches a
  filesystem, a network, or a subprocess is an Activity.
- Temporal's history is *the* durable record. No parallel status table exists to
  disagree with it.
- Long-running artifacts cross the boundary by reference and digest, not as
  payloads (ADR-0002: node state crosses the activity boundary through Temporal's
  payload converter, so everything durable must stay serialisation-friendly).
- Run-scoped task queues remain in force for filesystem-bound activities
  (ADR-0013): the only worker that may be handed an activity referring to a
  working copy is the worker that created it.
- Platform failures are `infrastructure_failure`, never `rejected` (ADR-0012).

## Human approval is a signal, not a poll

An approval wait can last days, and there are two ways to build it.

A **polling loop** asks a table on a timer. It burns a worker's attention for the
entire wait, and it fails wrong by default: if the poller dies, the run is stuck
forever and *nothing in the durable record says so* — there is no history event
for "the thing that was supposed to check stopped checking". It also
reimplements a durable timer that Temporal already has, which is the specific
thing ADR-0002 forbids.

A **signal** blocks the workflow on a wait condition until the approval arrives.
Temporal holds the execution with no worker attention, and the signal itself
lands in history — so *who approved, and when* is recorded in the same durable
artifact as everything else. That matters more here than it would elsewhere,
because human authority is the boundary the whole design rests on; an approval
that is not in the record is an approval that cannot be audited.

The wait is bounded by a durable timer. An approval that never arrives must reach
a terminal state and say what happened. A run that sits `RUNNING` forever is
indistinguishable from a run that was lost, and Task 2A already produced the
lesson that a structurally broken workflow can present as a slow one.

## What Task 2A actually established, and what it did not

From `docs/verification-baseline.md`, on GitHub Actions run `30580082420`:

- **Worker-loss recovery.** The first worker was `SIGKILL`ed after its checkpoint
  activity completed; the execution stayed `RUNNING` with nothing polling; a
  second worker resumed it; the append-only effect ledger held exactly one
  checkpoint row. *Not established:* loss of the server or of its volume.
- **Replay determinism.** `temporalio.worker.Replayer` — the SDK's supported
  facility, not a hand-written history parser — replayed a real recorded history
  against the workflow that produced it, and raised a nondeterminism error for a
  deliberately incompatible variant. *Not established:* determinism of any other
  workflow, or of that one under inputs it has not seen.
- **Retry behaviour from real history.** Attempt count read from
  `ActivityTaskStarted.attempt` and cross-checked against our own durable ledger,
  with exactly one consequential effect committed. *Not established:* one history
  event per failed attempt. Temporal does not write those, and claiming otherwise
  would misrepresent what the platform stores.

And the failure that is worth carrying forward, because it is the platform's
sharpest edge rather than a bug in our code:

**The `run_in_executor` hang.** LangGraph ran a *synchronous* callable through
`run_in_executor()`, which Temporal's deterministic workflow event loop cannot
provide, raising `NotImplementedError`. The workflow task then failed, and
Temporal retried it forever — so a structurally broken workflow presented as a
ten-minute hang instead of an error. The fix was to make every workflow-context
callable `async def`, **including the conditional-edge routing callbacks**, which
carry no `execute_in` metadata and are therefore the easy ones to miss. Guarded
by `tests/unit/test_workflow_context_callables.py` and by a bounded smoke test
(`scripts/verify_workflow_smoke.py`) that fails in seconds rather than at the
execution timeout.

That is the honest cost of handing durability to a platform: its retry semantics
will convert some classes of programming error into a slow success rather than a
fast failure. The mitigation is a bounded smoke test, not a smaller platform.

## Alternatives rejected

- **A custom scheduler, queue or state machine for evaluations.** Explicitly out
  of scope, and ADR-0002's reasoning applies without modification — two sources
  of truth about what has already happened.
- **LangGraph checkpointers as the durable record.** Same objection. `InMemorySaver`
  only, and only where LangGraph structurally demands one.
- **Celery or RQ plus a status table.** Reimplements recovery, and a status table
  has no replay: you can see what a run's state was said to be, never re-execute
  the history that produced it.
- **Polling for human approval.** Above.
- **A cron job that reaps stuck runs.** A reaper is a state machine wearing a
  hat. It also cannot distinguish "stuck" from "legitimately waiting for a human"
  without consulting the durable record it was introduced to substitute for.
- **Custom retry wrappers around activity bodies "for better error messages".**
  Retries inside an activity are invisible to history, so the record understates
  how many times the work ran — the same class of error the Task 2B scaffold
  refuses when it records `retry_owner: "temporal"` and asserts
  `CLIENT_RETRIES = 0` rather than assuming it.

## Consequences

- Every durable value must survive the payload converter, so large evidence moves
  by digest and reference (ADR-0018 bounds what is unpacked, and where).
- Each inline run creates a short-lived run-scoped queue (ADR-0013). Queues are
  cheap; a queue listing shows one entry per run.
- **Not established: anything about a production Temporal deployment.** All
  durability evidence comes from `temporal server start-dev` with SQLite
  persistence (ADR-0005), running as root in its container so it can create that
  database in a fresh named volume (threat model T-9).
- **Not established: server-loss or volume-loss recovery.** Neither is exercised.
  The restart test stops and starts services against volumes that remain intact.
- **Not established: durable approval waits themselves.** No run in this
  repository has yet waited on a human approval signal. The mechanism is chosen;
  the evidence for it does not exist, and this ADR does not pretend otherwise.
- The Temporal LangGraph plugin remains **experimental** by its own README
  (ADR-0002). The mitigation is unchanged: the graph is also directly invocable,
  so a plugin regression degrades durability rather than destroying the pipeline.
