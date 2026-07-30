# Known limitations and unfinished work

What this walking skeleton does **not** establish. Written plainly, because a
reliability lab that overstates its own reliability has failed at the first hurdle.

## What is not claimed

This system is **not calibrated**, **not production-ready**, and **not generally
reliable**. It has been exercised on exactly one fixture repository containing one
deliberately planted bug, with deterministic mock models. Two data points from a
fixture we wrote ourselves say nothing about performance on real defects.

`accepted_for_review` means every deterministic gate passed and a human should
look. It is not a claim that a patch is correct, safe, or ready to ship.

## Verified in this environment vs. not verified here

The build environment's egress policy denied several hosts. Everything below is
stated as it actually is — "not verified here" and "verified passing" are kept
strictly apart.

| Capability | Status |
|---|---|
| Fixture reproduces the bug deterministically | **Verified** — 5/5 identical probe runs |
| Duct-tape patch rejected | **Verified** — rejected on 3 gates, incl. effect counter = 2 |
| Known-good patch accepted for review only | **Verified** |
| Full test suite, no credentials, no services | **Verified** — 333 passed, 2 skipped (both Temporal) |
| LiteLLM Proxy serving mocks over HTTP via `custom_provider_map` | **Verified** — proxy 1.94.0 run locally; `transport=http`, resolved model read back |
| Phoenix trace collection, SQLite-backed | **Verified** — 2 traces, all 14 required spans, server 19.10.0 run locally |
| Inspect AI evaluation, both outcomes | **Verified** — `matches_expected_outcome` accuracy 1.000 |
| Promptfoo comparison across 3 mock identities | **Verified** — report generated, diversity failure correctly attributed |
| **Temporal workflow execution** | **NOT verified here** — see below |
| **Docker Compose stack startup** | **NOT verified here** — see below |
| Inspect AI Docker sandbox | **NOT verified here** — same registry block |

### Temporal was not executed in this environment

The Python SDK downloads its dev-server binary from `https://temporal.download/...`,
and every container registry is blocked. Both were denied with HTTP 403 at the
egress proxy:

```
temporal.download            403 (CONNECT denied)
production.cloudfront.docker.com  403   (Docker Hub blobs)
pkg-containers.githubusercontent.com  403   (GHCR blobs)
quay.io                      403
```

So the Temporal path is **written and statically verified** — the workflow is a
registered `@workflow.defn`, the plugin is the official
`temporalio.contrib.langgraph.LangGraphPlugin`, every graph node declares
`execute_in` with a `RetryPolicy` and a timeout, and the workflow body is asserted
to contain no reimplemented retry/sleep logic — but **no workflow was executed**,
no history was produced, and the Temporal UI was never populated here.

The two integration tests that would prove it **skip**, naming the unreachable
host. In an environment with normal egress, `make up && make demo` exercises it.

Consequence: **every run recorded in this environment is `execution_mode=local`**
and carries the `NON_DURABLE_EXECUTION` caveat. Those runs demonstrate the
investigation, the gates and the decision; they demonstrate **nothing** about
retries, timeouts, cancellation, crash recovery, or durability.

### Compose was config-validated, not run

`docker-compose.yml` is digest-pinned and structurally tested (health checks on
every service, `service_healthy` dependencies, no prohibited images). Images could
not be pulled, so the stack was never started here. Phoenix and LiteLLM were
instead run as local processes at the **same pinned versions**, which verifies the
integration but not the container packaging.

## Design limitations that are real, not environmental

### Patch bodies come from the fixture, not from a model

`materialise_candidate_patch` resolves a named repair strategy to file content
drawn from the fixture's own candidate library. The mock models choose and describe
a strategy; they do not author patch text.

This does not weaken the experiment — the gates read observable behaviour and never
consult `source_label` — but **nothing here demonstrates that a model can write a
correct fix.** Real patch generation is Task 2.

### Mock models are deterministic stand-ins

They return fixed, request-keyed structures. They exercise the plumbing, the
schema, the blinding and the gates. They do not exercise ambiguity, refusal,
malformed output under pressure, or any real reasoning.

### Isolation is process-level, not kernel-level

Working-copy isolation, path confinement and an environment allowlist are real and
tested. A container or VM boundary is not present in environments without a
container runtime. Acceptable for a fixture we wrote; **not** acceptable for
third-party patches (ADR-0007, threat model T-4).

### The privileged-identity boundary is structural, not enforced by the OS

Separate database files plus a capability object mean a leak requires deliberately
opening another database rather than forgetting a `WHERE` clause. But code with
filesystem access can still open `privileged.db`. A real boundary needs a separate
uid or an RPC (ADR-0008, T-2).

### The audit store is append-only by convention

No `UPDATE` or `DELETE` exists in the writer, and evidence is content-addressed.
The engine does not enforce it; direct SQLite access can rewrite history (T-7).

### One fixture, one bug class

Everything here concerns a check-then-write race under at-least-once delivery.
No claim extends to other bug classes.

### Cross-process span nesting is unverified

In `local` mode the span tree was confirmed end to end in Phoenix. Under Temporal,
activity nodes run in the worker process and correct parent/child nesting depends
on Temporal's OpenTelemetry interceptor. The `opentelemetry` extra is installed and
the spans are emitted, but the nesting was **not** observed here.

### The graph is bounded but shallow

Fixed node set, no cycles, caps on hypotheses and probes. There is no iterative
deepening, no re-planning after a failed probe, and no critic loop — a real
investigation would revise its hypotheses after seeing probe results.

## Failures encountered during the build

Recorded because a clean narrative would be less useful than an honest one.

1. **The artifact gate required a span that cannot exist yet.** The first end-to-end
   run rejected the *known-good* patch because `required_artifacts_present` demanded
   a `produce-report` span, which by definition completes after the decision.
   Fixed by splitting `GATE_REQUIRED_SPAN_NAMES` from the full tree, with the
   reasoning recorded in code rather than silently dropping the span.
2. **The duct-tape patch initially abstained instead of being rejected.** Abstention
   was checked before the gates, so a candidate whose hypothesis did not match the
   diagnosis abstained even though its effect counter read 2. That understated a
   finding the system had genuinely made. Fixed by ordering observational rejection
   ahead of abstention (`OBSERVATIONAL_GATE_NAMES`).
3. **Three of my own tests were wrong**, not the code: a `zip(strict=True)` over
   sequences of intentionally different lengths, a substring check that flagged the
   word "correct" inside the sentence denying correctness, and a raw-text scan that
   flagged the comment explaining why majority vote is not used. All three were
   fixed in the tests.
4. **`docs.temporal.io`, `docs.litellm.ai`, `inspect.aisi.org.uk`, `promptfoo.dev`,
   `arize.com`, `docs.langchain.com` and `opentelemetry.io` were all unreachable.**
   API facts were taken from the shipped source of each pinned version instead —
   which is a stronger authority for a pinned artifact than a docs site tracking
   `main`. Recorded in the dossier's "Documentation access" section.

## Explicitly deferred to Task 2

Out of scope here, by instruction:

- integrating all eight live frontier models;
- confidence calibration;
- autonomous patch selection;
- historical benchmark ingestion;
- reputation-based routing;
- real patch generation by a model;
- scaling beyond one fixture and one bug class;
- an OS-level boundary for the privileged identity store;
- an external human-approval console for acceptance.
