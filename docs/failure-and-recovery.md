# Failure and recovery

What breaks, what each break is classified as, and what the system does about it.

The organising rule: **a problem with the harness must never be reported as a
problem with the patch.** Conflating the two is how an evaluation lab quietly
manufactures false negatives, and it is the failure mode this document exists to
prevent.

## Classification

| Condition | Outcome | Meaning |
|---|---|---|
| Build fails, a test regresses, hidden tests fail, the primary invariant is violated, a prohibited file changed, duplicate output was suppressed without preventing duplicate processing, the diagnosis is not supported by evidence | `rejected` | The system measured something concrete about the patch and it was wrong |
| No hypothesis survives its probes, evidence remains materially contradictory, the causal mechanism cannot be tied to the repair | `abstained` | The system could not establish whether the patch is right. **Not** a claim that it is wrong |
| Temporal unavailable, Phoenix unavailable, missing mandatory trace, worker failure without recovery, corrupt evaluation artifact, activity timeout, harness error | `infrastructure_failure` | The harness could not complete the evaluation. **No patch verdict was reached** |
| Everything above passes | `accepted_for_review` | A human should look. Not "approved", "correct", "safe", or "production_ready" |

Checked in that order — infrastructure first (ADR-0012). Patch-level gate results
are still attached to an `infrastructure_failure` decision so nothing is hidden,
but the rationale states plainly that no verdict was reached.

`classify_infrastructure_incident()` **raises** on any condition not in the
`InfrastructureIncident` enum, so `hidden_tests_failed` cannot be re-labelled as
an infrastructure excuse. The bucket is closed on purpose.

## Worker interruption

**What Temporal guarantees.** Activity results are written to workflow history.
When a worker dies, another worker picks the workflow up and **replays** the
recorded results rather than re-executing the work.

**How it is proved** (`scripts/verify_durability.py`):

1. Worker A starts and polls.
2. `DurableCheckpointWorkflow` starts. Its first activity records a durable
   checkpoint — an append-only row in an effect ledger.
3. The workflow blocks on `workflow.wait_condition`. No workflow task is in
   flight, so the interruption is genuinely mid-execution.
4. Worker A is **SIGKILLed**. Not SIGTERM: a graceful drain would prove much less.
5. The workflow is confirmed still `RUNNING` with nothing polling.
6. Worker B starts; a `resume` signal is sent; the workflow completes.
7. **The checkpoint ledger still reads 1.**

That last number is the claim. If Temporal had lost the result, worker B would
have re-run the checkpoint activity and the ledger would read 2. The evidence
artifact records the full history, both worker identities, the SIGKILL exit
status, and the ledger contents.

## Retries

Configured on the activity, not implemented by us:

```python
RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=4),
    maximum_attempts=5,
)
```

`scripts/verify_retry.py` runs an activity that fails 3 times then succeeds, and
asserts from **real history**: the recorded `retryPolicy` matches what was
configured, the final `ActivityTaskStarted.attempt` is 4, and the consequential
side effect happened exactly once.

One detail worth knowing: **Temporal does not write a history event per failed
attempt.** Intermediate failures are not recorded; the attempt number lives on the
`ActivityTaskStarted` event. So the verification cross-checks history against the
activity's own durable ledger — two independent witnesses, because one of them
alone would be easy to misread.

There is exactly one retry layer. LiteLLM's `num_retries` is set to `0` in
`config/litellm-config.yaml` precisely so two independently-configured layers
cannot multiply into N×M attempts.

## Timeouts

`scripts/verify_timeout.py` runs an activity that sleeps 30s against a 5s
`start_to_close_timeout`, and asserts:

- history contains `ActivityTaskTimedOut`;
- the workflow catches `ActivityError` and returns
  `classification: infrastructure_failure`;
- the reliability layer independently agrees via
  `classify_infrastructure_incident("activity_timeout")`;
- the incident is recorded in a span;
- it is **not** `rejected`.

A slow or overloaded activity is a statement about the harness. Reporting it as a
defective patch would invent a coding verdict from a platform problem.

## Replay and determinism

`scripts/verify_replay.py` uses `temporalio.worker.Replayer` — the SDK's supported
facility — against a preserved real history:

1. **Positive:** replay `DurableCheckpointWorkflow` against the history it wrote.
   Must pass.
2. **Negative:** replay `IncompatibleDurableCheckpointWorkflow` — registered under
   the same workflow name, but commits the terminal effect *before* the checkpoint
   and never waits — against the same history. Must **fail**.

The negative half is the point. A replay check that can only pass proves nothing
about its ability to detect nondeterministic workflow evolution, which is the only
reason to run one. If the incompatible variant ever replays cleanly, the
verification fails loudly and says the check is worthless.

Histories are preserved as CI artifacts (`artifacts/histories/*.history.json`) so
a future change can be replayed against a real recorded execution.

## Service unavailability

| Service | Detection | Consequence |
|---|---|---|
| Temporal | `Client.connect` fails | `EXECUTION_MODE=temporal` → `temporal_unavailable` incident. `auto` → documented degraded fallback with a `NON_DURABLE_EXECUTION` caveat |
| Phoenix | `/healthz` not 200 | `phoenix_unavailable` incident; the run lacks mandatory artifacts |
| LiteLLM | `/health/readiness` not 200 | Gateway falls back to in-process LiteLLM dispatch, recorded on the invocation (ADR-0011) |

The asymmetry between "explicitly requested Temporal" and "auto" is deliberate.
Asking for durability and not getting it must not look like getting it; not asking
for it is not a failure.

## Persistence

Temporal and Phoenix both write to SQLite on named volumes.
`scripts/verify_persistence.py` runs **after** a `docker compose stop && up` cycle
and reads back the workflow histories and Phoenix traces recorded before the
restart. Persistence checked against data written after the restart would prove
nothing.

## What is still not defended

- The audit store is append-only **by convention** in application code, not by the
  engine (threat model T-7).
- Fixture isolation is process-level, not kernel-level, wherever the Inspect
  Docker sandbox is unavailable (ADR-0007, T-4).
- `temporal server start-dev` is a development server. Right for a walking
  skeleton, wrong for production.
- Recovery is proved for **worker** loss. Loss of the Temporal server itself, or
  of its volume, is not exercised.
