# Build vs integrate

One line per capability: who owns it, and — where we wrote code — why the platform
did not already cover it.

The bias is heavily toward integrate. Custom code here is a liability: it is the
part nobody else tests.

## Integrated (platform owns it — we wrote none of it)

| Capability | Owner | Our integration surface |
|---|---|---|
| Durable execution, retries, timeouts, cancellation | Temporal | `@workflow.defn`, `@activity.defn`, `RetryPolicy`, `Worker` |
| Workflow history, replay, recovery | Temporal | Server-side; we read it in the UI |
| Parallel activity coordination | Temporal | `asyncio.gather` over `workflow.execute_activity` |
| Running graph nodes as durable activities | Temporal LangGraph plugin | `LangGraphPlugin(graphs=...)`, `metadata={"execute_in": "activity"}` |
| Graph traversal, conditional edges, state reducers | LangGraph | `StateGraph`, `add_conditional_edges`, `compile()` |
| Cross-vendor model API, provider adapters, normalisation | LiteLLM Proxy | `config.yaml`, `POST /v1/chat/completions` |
| Provider retry/routing primitives | LiteLLM | `router_settings` (deliberately set to no-fallback) |
| Trace collection, storage, visualisation, datasets | Phoenix | OTLP/HTTP → `:6006/v1/traces` |
| Span creation, batching, context propagation, OTLP wire format | OpenTelemetry SDK | `TracerProvider`, `BatchSpanProcessor` |
| Eval task/sample model, runner, scoring, log format, viewer | Inspect AI | `@task`, `Task`, `Sample`, `@scorer`, `inspect eval` |
| Sandboxed eval execution | Inspect AI | `sandbox="docker"` (opt-in) |
| Cross-provider prompt matrix, comparison report, assertions | Promptfoo | `promptfooconfig.yaml`, `exec:` provider |
| Schema validation, coercion, JSON Schema emission | Pydantic | `BaseModel` |
| Property generation, shrinking, replay | Hypothesis | `@given`, strategies |
| Test discovery and reporting | pytest | — |
| Relational storage | SQLite (stdlib) | `sqlite3` |

## Built (custom application code)

| Component | Path | Why not integrated |
|---|---|---|
| Coding-problem + evidence schemas (15 models) | `app/domain/schemas.py` | Domain vocabulary. No platform defines `RootCauseHypothesis` or `FalsificationProbe`; these are the lab's subject matter. |
| Workflow state model + legal transitions | `app/domain/states.py` | The 14 states are a claim about how careful debugging proceeds. Temporal executes state machines; it does not opine on which states a diagnosis should have. |
| Tool broker (state-gated tool availability) | `app/tools/broker.py` | The rule "no editing before `implementation`" is a policy about *our* states. Nothing off-the-shelf knows them. Deliberately enforced at acquisition, not by prompt. |
| Reliability gates | `app/reliability/gates.py` | **The differentiator.** Every framework's "evaluation" is a model-graded scorer or a developer callback — the deterministic checker is always yours to write. No model call, ever (ADR-0009). |
| Model pseudonymisation + privileged store | `app/models/blinding.py`, `app/storage/privileged.py` | Blinding is an experimental-design requirement. LiteLLM deliberately does the opposite: it tells you which model answered. |
| Deterministic mock models | `app/models/mock_provider.py` | Content-addressed fake responses for a credential-free path. Written **as a `litellm.CustomLLM` through `custom_provider_map`** — LiteLLM's own extension point, not a parallel implementation (ADR-0004). |
| Fixture repository | `fixtures/duplicate-job-processing/` | The benchmark subject. Must be ours to hold the answer key. |
| Deterministic scorers | `evals/scorers/` | Inspect owns the runner; the *predicates* are domain logic. |
| Investigation node bodies | `app/graphs/investigation.py` | LangGraph owns traversal; what a node *thinks* is ours. |
| Reliability report | `app/reliability/report.py` | Composes platform artifacts into the required decision record. |
| Redaction | `app/telemetry/redaction.py` | Which fields are sensitive is application knowledge. |

## Things we were tempted to build and did not

Worth recording, because each was a real fork in the road:

| Temptation | Why we stopped |
|---|---|
| A node→activity adapter for LangGraph | The official plugin *is* that adapter. Writing it would have been the headline violation of "do not recreate". |
| A retry/backoff helper around model calls | Temporal's `RetryPolicy`. Two retry layers multiply into N×M attempts; LiteLLM's is set to 0 so exactly one layer exists. |
| A trace viewer for the reliability report | Phoenix. Explicitly prohibited, and it would have been worse. |
| A mock OpenAI HTTP server | That is a provider adapter. `custom_provider_map` covers it. |
| A SQLite checkpointer for LangGraph | Temporal's history is the durable record (ADR-0002). |
| A results leaderboard | Inspect's log format and viewer already do this. |

## Recurring test

Before any new module: *which pinned platform already owns this, and what exactly
does it fail to do for our case?* If that second answer is vague, the module does
not get written.
