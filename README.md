# Reliability walking skeleton

A local-first laboratory for evaluating AI coding **correctness**. This repository
is one verified vertical slice: mature platforms wired together end to end, proving
that an incorrect AI-generated patch is **deterministically rejected**.

It is not an MVP and not a platform. Nothing here is calibrated, and no claim is
made about general reliability.

## The one thing it demonstrates

A fixture repository has a deliberate duplicate-processing bug: a check-then-write
race under at-least-once delivery. Two repair candidates are offered.

| Candidate | What it does | Visible tests | Outcome |
|---|---|---|---|
| **Duct tape** — de-duplicate results on read | Hides the symptom; both workers still process the job and the external effect still fires twice | **all green** | `rejected` |
| **Known-good** — atomic claim before irreversible work | Establishes the invariant | all green | `accepted_for_review` |

The duct-tape patch passes every visible test. It is caught anyway, by a gate that
reads the **external effect counter** rather than the output: you can de-duplicate a
result list, but you cannot un-send an email.

The only positive outcome this system can produce is **`accepted_for_review`** —
a recommendation that a human look at the patch. Not "approved", not "correct", not
"safe", not "production_ready". Nothing is ever merged or deployed.

## Quick start

```bash
make setup        # install pinned dependencies
make up           # start Temporal, Phoenix, LiteLLM (digest-pinned images)
make health       # verify every service
make demo         # the complete walking-skeleton scenario
make test         # deterministic tests, mock models, no credentials
make eval         # Inspect AI + Promptfoo evaluations
make traces       # Phoenix URL and recent trace identifiers
make down         # stop services
```

`make test`, `make eval` and `make demo` need **no credentials and no running
services**. Without services the gateway falls back to in-process LiteLLM dispatch
and the runner to the degraded local executor; results are labelled
`NON_DURABLE_EXECUTION` so a weaker run can never be mistaken for a durable one
(ADR-0006, ADR-0011).

## Architecture in one picture

```
Temporal ──── durable execution, retries, timeouts, cancellation, history
  └── temporalio.contrib.langgraph.LangGraphPlugin   (official)
        └── LangGraph ──── the bounded investigation graph
LiteLLM Proxy ─── one cross-vendor model API, provider adapters, normalisation
Phoenix + OTel ── trace collection, storage, visualisation
Inspect AI ────── eval samples, runner, deterministic scorers, logs
Promptfoo ─────── cross-provider prompt matrix and comparison report
custom code ───── domain schemas, evidence, reliability gates, blinding, fixtures
```

Full detail in [`ARCHITECTURE.md`](ARCHITECTURE.md); who owns what and why in
[`docs/build-vs-integrate.md`](docs/build-vs-integrate.md).

## How it works

1. A structured bug report enters the Temporal workflow, which runs a **bounded
   LangGraph investigation**: validate → inspect → hypothesise → design probes →
   execute probes → diagnose → propose repairs.
2. Three **causally distinct** hypotheses are generated, each with assumptions,
   predicted observations, a falsification condition, and a discriminating probe.
3. Deterministic probes run. Two hypotheses are **falsified**: sequential
   redelivery commits exactly once (so "there is no duplicate check" is wrong), and
   delivery is declared at-least-once (so "the queue is broken" is wrong). The race
   hypothesis survives, supported by a probe.
4. One repair candidate is applied in an isolated working copy; the repository is
   built and the visible, hidden and property tests run.
5. **Eight deterministic gates** decide. No model output is in any verdict path.

## Documentation

| Document | What it covers |
|---|---|
| [`docs/dependency-dossier.md`](docs/dependency-dossier.md) | Every dependency: exact version, docs consulted, capability, integration surface, known limitation, custom code, and what is *not* reimplemented |
| [`docs/architecture-decisions/`](docs/architecture-decisions/) | 11 ADRs |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | States, graph, span tree, data stores, file tree |
| [`AGENTS.md`](AGENTS.md) | Rules for anyone working in this repository |
| [`docs/acceptance-tests.md`](docs/acceptance-tests.md) | What must be true, and which test decides it |
| [`docs/build-vs-integrate.md`](docs/build-vs-integrate.md) | Integrate by default; every piece of custom code justified |
| [`docs/threat-model.md`](docs/threat-model.md) | Assets, boundaries, eight threats, accepted residuals |
| [`docs/implementation-plan.md`](docs/implementation-plan.md) | The staged build |
| [`docs/local-operation.md`](docs/local-operation.md) | Running the stack, service roles, troubleshooting |
| [`docs/failure-and-recovery.md`](docs/failure-and-recovery.md) | Classification, worker interruption, retries, timeouts, replay |
| [`docs/limitations.md`](docs/limitations.md) | **What this does not establish** |

## Pinned versions

Every Python package, npm tool and container image is pinned exactly; images are
**digest**-pinned. Python 3.12.

`temporalio` 1.31.0 · `langgraph` 1.2.10 · `litellm` 1.94.0 · `inspect-ai` 0.3.251 ·
`arize-phoenix` 19.10.0 · `opentelemetry-sdk` 1.44.0 · `pydantic` 2.13.4 ·
`hypothesis` 6.164.0 · `pytest` 9.1.1 · `promptfoo` 0.121.19

## Security

No secrets are committed; `.env` is gitignored and only `.env.example` is tracked.
Credentials are redacted from traces, and prompts are recorded as content hashes
rather than raw text. Patches apply only to temporary working copies with path
confinement, and subprocesses get an environment allowlist. The application has
**no VCS-write capability** — a test scans for one. Solver roles cannot reach the
hidden tests or the reference patch. Real model identities live in a separate,
capability-gated SQLite store.

Read [`docs/threat-model.md`](docs/threat-model.md) for what is *not* covered —
notably that fixture isolation is process-level, not kernel-level, in environments
without a container runtime.

## Durable execution

Task 1 shipped the Temporal and Compose paths **written but unrun** — the build
sandbox denied every container registry and `temporal.download`. Task 2A moved
that proof onto a clean GitHub-hosted runner:

```
.github/workflows/durable-stack-verification.yml
```

It starts the full Compose stack from empty volumes, waits for explicit health
checks, then proves against **real Temporal history** that a workflow survives a
`SIGKILL`ed worker and resumes under a new one without repeating a committed
effect; that retries follow the configured policy; that a timeout is recorded and
classified as infrastructure rather than as a bad patch; and that replay accepts
the genuine workflow while **rejecting a deliberately incompatible variant**. Every
step writes an evidence artifact, and the histories are uploaded so a future change
can be replayed against a real recorded execution.

If the runner cannot reach a registry, that workflow fails as an infrastructure
requirement. There is no static-validation fallback.

Latest green run: [`30580082420`](https://github.com/pukujan/eval-lab/actions/runs/30580082420)
on commit `a1017b2` — all steps passed and the completion manifest reported
**15/15 criteria demonstrated**. The manifest is generated from the evidence files
rather than from step exit codes, and it is per-run: a green badge is not a
standing guarantee, and the artifact from the run you care about is the answer.

See [`docs/failure-and-recovery.md`](docs/failure-and-recovery.md) for what each
failure mode is classified as and why, and
[`docs/limitations.md`](docs/limitations.md) for the four earlier runs that failed
first — three of them faults in the verification rather than in the system.

## Evidence for an external verifier

Task 2A's result is frozen in
[`docs/verification-baseline.md`](docs/verification-baseline.md) and its
machine-readable twin `verification/task-2a-baseline.json`: the commit, run,
artifact and digest it was demonstrated on, the public meaning of each of the 15
criteria, and what each one does **not** establish.

```
make evidence-bundle    # collect raw evidence + hash every file
make verify-bundle      # recompute every checksum in an exported bundle
```

The exporter copies and hashes. It reaches no verdict, writes no `verified: true`
of its own, and refuses to produce a bundle at all when evidence is missing, a
checksum does not match, a workflow ID maps to two run IDs, or evidence is
malformed. Grading is the verifier's job, and their holdouts are deliberately not
in this repository — if they were, the verification would be circular.

## Status

Task 1 (walking skeleton) and Task 2A (durable execution and reproducible
packaging) are complete, the latter evidenced by run `30580082420`. This remains a
walking skeleton: **not calibrated, not production-ready, not generally reliable**,
exercised on one fixture with one planted bug against deterministic mock models.
**Deferred:** live frontier models, confidence calibration, autonomous patch
selection, and historical benchmark ingestion. See
[`docs/limitations.md`](docs/limitations.md).
