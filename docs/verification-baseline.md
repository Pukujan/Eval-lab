# Task 2A verification baseline — document version 1

**Status: frozen.** This document records what Task 2A demonstrated, on which
execution, and what that does and does not mean. It is the public half of an
external verification arrangement: an independent verifier holds its own holdouts
and mutants, which are deliberately **not** in this repository and are not known to
anyone who worked on it. Building them here would make the verification circular,
which is the failure mode the whole lab exists to avoid.

Nothing in this document claims the system is calibrated, production-ready, or
generally reliable.

A later verification run does not edit this baseline. It produces version 2.

The machine-readable twin of this document is
[`verification/task-2a-baseline.json`](../verification/task-2a-baseline.json), which
the evidence exporter embeds verbatim in every bundle it writes.

## Frozen acceptance contract

| Field | Value |
|---|---|
| Task | 2A — prove durable execution and reproducible packaging |
| Commit | `a1017b24de9738dc576da3ded2d2d82d23bef47c` |
| Branch | `claude/reliability-walking-skeleton-31b6a2` |
| Workflow | `.github/workflows/durable-stack-verification.yml` |
| GitHub Actions run | `30580082420` |
| Artifact | `8774421809` (`durable-stack-verification`) |
| Artifact digest | `sha256:001bc6d8e14c5f45743130e68a5024da38bbfecf627f3a9edb44a852ec1c0e3b` |
| Runner | GitHub-hosted `ubuntu-24.04` |
| Criteria | 15 of 15 demonstrated |

The digest is the identity of the evidence. A verifier that fetches the artifact
and computes a different digest is not looking at this baseline, whatever the run
ID says.

## What each of the 15 criteria publicly means

Each entry states what was observed and, separately, what it does **not** establish.
The second column is the load-bearing one: a criterion name read on its own
reliably over-promises.

### Packaging and services

**`clean_runner_starts_full_compose_stack`** — on a hosted `ubuntu-24.04` runner
with volumes pruned first, `docker compose up -d --wait` brought every declared
service to a running state from images pulled during that run.
*Not established:* behaviour on any other host, orchestrator, or base image, or with
warm caches. An unreachable registry fails this criterion — there is no
static-validation fallback.

**`all_service_health_checks_pass`** — every declared service reported `healthy`
against its own Compose healthcheck, and `scripts/health.py` independently reached
each service's documented health endpoint over the network.
*Not established:* that any service is correct beyond answering that endpoint.

**`state_persists_across_restart`** — after `docker compose stop` then `up` against
the existing volumes, previously created workflow executions were still describable
with unchanged history event counts, and Phoenix still returned traces.
*Not established:* survival of volume deletion, host loss, or a service upgrade.

**`dependencies_and_images_pinned`** — every Python dependency is pinned with `==`,
every Compose image carries an `@sha256:` digest, installed versions matched the
declarations, zero problems recorded.
*Not established:* that those versions are free of vulnerabilities, or that a digest
still resolves at a registry today.

**`state_initialisation`** — the audit store and the privileged identity store exist
as separate database files and the Temporal namespace is registered.
*Not established:* that the separation is enforced by the operating system. It is
structural; code with filesystem access can open either file (threat model T-2).

### Durable execution

**`real_temporal_workflow_appears_and_completes`** — a workflow execution was
created on the Temporal server at `TEMPORAL_ADDRESS`, was retrievable by workflow
ID, reached `WorkflowExecutionStatus.COMPLETED`, and its history was fetched back
from the server.
*Not established:* anything about a production Temporal deployment. This is
`temporal server start-dev`.

**`coding_workflow_executes_under_temporal`** — `CodingEvaluationWorkflow`
specifically, not only the purpose-built probe workflows, executed on the real
server: it crossed the validation conditional edge into the activity branch,
produced at least one `ACTIVITY_TASK_COMPLETED` event, crossed the diagnosis
conditional edge, and completed with a non-empty history inside a bounded timeout.
*Not established:* anything about patch quality, or about graph paths not taken —
the abstention branch is not exercised here.

**`worker_interruption_recovery`** — the first worker was `SIGKILL`ed after its
checkpoint activity completed; the execution stayed `RUNNING` with nothing polling;
a second worker resumed it; it completed; and the append-only effect ledger held
exactly one checkpoint row.
*Not established:* recovery from loss of the server or of its volume.

**`retry_behaviour_from_real_history`** — an activity induced to fail a fixed number
of times was retried under the declared `RetryPolicy`; the attempt count read from
`ActivityTaskStarted.attempt` in server-fetched history matched both the expected
count and the durable ledger; exactly one consequential effect was committed.
*Not established:* that history holds one event per failed attempt. Temporal does
not write those, and claiming otherwise would misrepresent what the platform stores.

**`timeout_behaviour`** — an activity that exceeded its `start_to_close_timeout`
produced an `ActivityTaskTimedOut` event in real history and was surfaced as an
infrastructure failure.
*Not established:* coverage of other timeout classes. Only activity start-to-close
is exercised.

**`replay_determinism_verification`** — `temporalio.worker.Replayer`, the SDK's
supported facility rather than a hand-written history parser, replayed a real
recorded history against the workflow definition that produced it without error, and
raised a nondeterminism error for a deliberately incompatible variant.
*Not established:* determinism of any other workflow, or of that workflow under
inputs it has not seen.

### Observability

**`phoenix_contains_required_spans`** — a query to the running Phoenix instance
returned at least one trace for the project, and the observed span-name set
contained every required name.
*Not established:* that spans are correctly nested. See limitation L-5.

### Evaluation outcomes, unchanged from Task 1

**`ducttape_remains_rejected`** — under `execution_mode=temporal` the duct-tape
candidate recorded `rejected`, its failing gate set included
`not_symptom_suppression`, and its observed effect invocation count was 2. This is
the Task 1 expectation, unrelaxed.
*Not established:* that symptom suppression is detected in general. One candidate,
one fixture, one bug class.

**`known_good_remains_accepted_for_review`** — under `execution_mode=temporal` the
known-good candidate recorded `accepted_for_review` with no failing gate, an effect
invocation count of 1, and `merged_or_deployed=false`.
*Not established:* correctness. `accepted_for_review` is the only positive outcome
this system has, and it means a human should look. It is never `approved`,
`correct`, `safe`, or `production_ready`, and nothing was merged, pushed, or
deployed.

**`infrastructure_failures_classified_separately`** — the induced activity timeout
was classified as `infrastructure_failure` by both the workflow and the reliability
layer, and was not reported as a defective patch.
*Not established:* correct classification of every infrastructure fault class. One
induced fault is exercised.

## Known limitations

1. **One hosted run, not a standing guarantee.** The contract above is a single
   execution on a single day. The completion manifest is regenerated per run from
   evidence files; a later run can report fewer criteria.
2. **Development Temporal server.** All durability evidence comes from
   `temporal server start-dev` with SQLite persistence, running as root in its
   container so it can create that database in a fresh named volume (T-9).
3. **Worker-loss recovery only.** An abrupt `SIGKILL` of the worker process, with
   the server up throughout.
4. **No server-loss or volume-loss recovery.** Neither is exercised. The restart
   test stops and starts services against volumes that remain intact.
5. **Cross-process trace parentage not asserted.** The Phoenix evidence asserts
   span *presence*, not nesting. Activity-side nodes run in another process and
   correct parentage there depends on Temporal's OpenTelemetry interceptor, which is
   installed but unverified.
6. **Fixture candidates and mock models.** Patch bodies come from the fixture's own
   candidate library, not from a model; the models are deterministic mocks behind
   LiteLLM. No model wrote a patch and no live provider was contacted.
7. **No calibration and no benchmark generalization.** One fixture, one planted bug
   (a check-then-write race under at-least-once delivery), two candidates. Nothing
   here is calibrated and nothing extrapolates to other defects.

## The public interface for an external verifier

### `scripts/export_evidence_bundle.py`

Collects **raw evidence only** from a verification run's artifact directory into a
self-describing bundle, and hashes every file it exports.

```
python scripts/export_evidence_bundle.py --source artifacts --destination bundle
```

What it collects: Temporal histories; the workflow and run IDs observed in them;
candidate reliability reports; the Phoenix trace query result; retry, timeout,
replay and recovery evidence; the Promptfoo JSON report; Inspect AI logs; container
logs; dependency and image pins; and the completion manifest.

Three things it deliberately does not do:

- **It does not decide whether any criterion passed.** It copies and hashes. A
  verifier that wants a verdict computes one from the bundle with its own
  instruments.
- **It never writes a self-attesting field.** No `verified: true`, no `passed`, no
  `verdict` in anything the exporter authors. This is enforced in code
  (`_reject_self_attestation`), not by convention, because a bundle that certifies
  itself is worth nothing to the party it is being handed to.
- **It does not rewrite evidence.** Files are copied byte-for-byte, so the recorded
  SHA-256 is verifiable against the source artifact. Producer-written fields
  therefore survive inside copied evidence — `phoenix-trace.json` really does
  contain `"verified": true`, because the script that produced it wrote that. Those
  are **claims by the producer, not attestations by the bundle**, and a verifier
  should treat them as data to check rather than as findings.

### `evidence-index.json`

The machine-readable map at the root of every bundle. Each entry names one exported
file and records its `source_system`, `category`, path within the bundle, path in
the source artifact, byte length, SHA-256, and — where the evidence records them —
the Temporal `workflow_id` and `run_id` it belongs to. The index also carries the
frozen baseline above, the repository commit, and the CI run identifiers.

The export is **deterministic**: the same source tree produces a byte-identical
index. There is deliberately no generation timestamp, because a wall-clock field
would break that property for no benefit — the run's own timing is already recorded
in the evidence.

### What fails an export

An export that cannot be trusted must fail, not warn. Four conditions abort it:

| Condition | Why it is fatal |
|---|---|
| A required file is missing | A bundle that silently omits evidence understates what is unproven |
| A checksum does not match | The copy is not the file that was hashed; provenance is broken |
| A workflow ID maps to two different run IDs | The bundle cannot say which execution a piece of evidence describes |
| Evidence is malformed | Unparseable JSON, a history with no events, or a history whose recorded run ID contradicts its paired evidence |

Optional evidence that is absent is recorded in `missing_optional` rather than
dropped — an absence has to be visible.

### Traceability of candidate reports

Each candidate reliability report records the Temporal `workflow_id` **and** the
Temporal `run_id` of the execution that produced it, so a report can be tied to
exactly one history file. The run ID had not previously been captured:
`client.execute_workflow` returns only the result, so the runner now starts the
workflow and reads the identity off the handle. This is a linkage fix; no gate,
threshold, or expectation changed with it.
