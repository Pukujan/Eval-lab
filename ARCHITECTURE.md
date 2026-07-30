# Architecture

A local-first laboratory for evaluating AI coding *correctness*. It runs one
end-to-end vertical slice: take a structured bug report about a fixture repository
with a known duplicate-processing defect, investigate it under a bounded protocol,
propose repairs, apply one in isolation, verify it against deterministic checks, and
emit a reliability decision.

**This is a walking skeleton.** Every layer is present and connected; almost none of
it is deep. It is not an MVP and not a platform. Nothing here is calibrated, and no
claim is made about general reliability.

## The one thing it proves

An incorrect patch that makes the symptom disappear is **deterministically
rejected**, and the correct patch earns only `accepted_for_review` — never
"approved", "correct", "safe", or "production_ready".

## Platform ownership

Custom code exists only where no pinned platform already owns the capability
(`docs/build-vs-integrate.md`).

```
┌──────────────────────────────────────────────────────────────────────┐
│ Temporal  — durable execution, retries, timeouts, cancellation,      │
│             parallel activities, history, recovery                   │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ temporalio.contrib.langgraph.LangGraphPlugin                   │  │
│  │   (official; runs graph nodes as Temporal Activities)          │  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │ LangGraph — the bounded investigation graph:              │  │  │
│  │  │   state transitions · hypothesis flow · probe selection   │  │  │
│  │  │   · repair-candidate comparison                           │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
        │ model calls              │ spans                │ eval / compare
        ▼                          ▼                      ▼
┌────────────────┐    ┌────────────────────┐   ┌──────────────────────────┐
│ LiteLLM Proxy  │    │ OpenTelemetry SDK  │   │ Inspect AI · Promptfoo   │
│ cross-vendor   │    │  → Phoenix (OTLP)  │   │ eval runner · scorers ·  │
│ API, adapters, │    │  traces, datasets, │   │ sandbox · prompt matrix  │
│ normalisation  │    │  experiment records│   │ · comparison report      │
└────────────────┘    └────────────────────┘   └──────────────────────────┘
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Custom: domain schemas · hypotheses/evidence · reliability gates ·   │
│ model pseudonymisation · fixtures · coding workflow · audit records  │
└──────────────────────────────────────────────────────────────────────┘
```

## Workflow states

```
intake → specification → repository_inspection → hypothesis_generation
      → probe_design → probe_execution → diagnosis → repair_design
      → implementation → verification → accepted_for_review
                                      ↘ rejected
                                      ↘ abstained
                                      ↘ infrastructure_failure
```

Terminal: `accepted_for_review`, `rejected`, `abstained`, `infrastructure_failure`.
Legal transitions live in `app/domain/states.py` and are enforced — an illegal
transition raises rather than being logged and ignored.

`infrastructure_failure` is deliberately separate from `rejected`: a harness that
breaks must never be reported as a patch that failed. Conflating them is how an eval
harness quietly manufactures false negatives.

**Tool gating.** `app/tools/broker.py` derives the available toolset from the
current state. Editing and patch-application tools do not exist in the toolset
before `implementation`; asking for one raises `ToolNotAvailableError`. This is
enforced at *acquisition*, not by instructing a model to behave — a tool that was
never handed over cannot be argued into use.

## Investigation graph (LangGraph)

```
START → validate_specification → inspect_repository → generate_hypotheses
      → design_probes → execute_probes → establish_diagnosis
      → ┬─ (diagnosis supported) → generate_repair_candidates → END
        └─ (no hypothesis survives / contradictory) → abstain → END
```

Bounded: fixed node set, no unbounded loops, a hard cap on hypotheses and probes.
Every node carries `metadata={"execute_in": ...}` — `"activity"` for anything doing
real work (model calls, filesystem, subprocesses), `"workflow"` for pure decisions.
Temporal supplies the retry policy and timeout for each activity node; LangGraph
supplies none of that (ADR-0002).

## Span tree

```
coding-evaluation
├── validate-specification
├── inspect-repository
├── generate-hypotheses
├── design-probes
├── execute-probes
├── establish-diagnosis
├── generate-repair-candidates
├── apply-patch
├── run-build
├── run-tests
├── run-property-tests
├── apply-reliability-gates
└── produce-report
```

Observable artifacts only: exit codes, counters, durations, content hashes, decision
records. No attempt is made to store or reconstruct private model chain-of-thought.
Prompts and responses are recorded as hash + length, which also keeps pasted secrets
out of the trace store (threat model T-5).

## Data stores

| Store | File | Contents | Reachable from |
|---|---|---|---|
| Agent-accessible audit | `var/audit.db` | Runs, hypotheses, evidence, probe results, decisions — **pseudonyms only** | Workflow, nodes, activities, scorers |
| Privileged identity | `var/privileged.db` | pseudonym → real vendor/model | `app/storage/privileged.py` only, behind a capability object |
| Phoenix | `var/phoenix/phoenix.db` | Traces | Phoenix server process |
| Temporal | `var/temporal/temporal.db` | Workflow history | Temporal server process |

Two files, not two tables. A convention is not a boundary (ADR-0008).

## Model access

The application never imports a vendor SDK. It speaks OpenAI-shaped HTTP to the
LiteLLM Proxy, which owns adapters and normalisation. Three deterministic mock
models are registered through LiteLLM's own `custom_provider_map` extension point;
each response is a pure function of `(model, sha256(messages))`. Fallback between
named models is disabled and LiteLLM's retry count is 0, so **Temporal is the only
retry layer** — two layers would multiply into N×M attempts (ADR-0004).

## Execution modes

`app/runner.py` exposes one entry point with two paths:

- **`temporal`** (primary) — the durable path; what Compose and CI run.
- **`local`** (degraded) — the same graph via `graph.ainvoke()`, used where no
  Temporal server is reachable. It adds no retries, timers, persistence, or
  recovery; those capabilities are simply absent, and the absence is stamped onto
  `EvaluationRun.execution_mode`, the root span, and the report as
  `NON_DURABLE_EXECUTION` (ADR-0006).

## File tree

```
.
├── app/
│   ├── domain/         schemas.py · states.py · fixtures.py
│   ├── workflows/      coding_evaluation.py (Temporal workflow)
│   ├── graphs/         investigation.py (LangGraph StateGraph)
│   ├── activities/     repository.py · probes.py · patching.py · verification.py
│   ├── models/         registry.py · gateway.py · mock_provider.py · blinding.py
│   ├── evidence/       store.py
│   ├── reliability/    gates.py · report.py
│   ├── telemetry/      tracing.py · redaction.py
│   ├── storage/        audit.py · privileged.py
│   ├── tools/          broker.py
│   ├── config.py
│   └── runner.py
├── evals/
│   ├── inspect/        coding_eval.py (known-good + incorrect-patch tasks)
│   ├── promptfoo/      promptfooconfig.yaml · provider_bridge.py
│   ├── datasets/       walking_skeleton.jsonl
│   └── scorers/        deterministic.py
├── fixtures/
│   └── duplicate-job-processing/
│       ├── src/                  known-bad implementation
│       ├── tests_visible/        solver-visible
│       ├── tests_hidden/         NOT solver-visible
│       ├── reference/            known-good patch — NOT solver-visible
│       ├── patches/              duct-tape candidate
│       ├── INVARIANTS.md
│       └── probe.py              reproducible duplication probe
├── tests/               unit/ · integration/ · property/ · acceptance/
├── docs/                dossier · ADRs · threat model · acceptance tests ·
│                        build-vs-integrate · implementation-plan · limitations
├── scripts/             health.py · serve_phoenix.sh · serve_litellm.sh · demo.py
├── docker-compose.yml   Makefile   pyproject.toml   .env.example   README.md
```

## Deliberately absent

Kubernetes, Redis, PostgreSQL, Prometheus, Grafana, cloud services, custom provider
SDKs, a custom trace store or viewer, reputation-based routing, and any auto-merge
or deploy path. Each omission is a decision, not an oversight.
