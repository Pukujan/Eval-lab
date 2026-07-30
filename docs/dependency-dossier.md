# Dependency dossier

Every external platform this walking skeleton depends on, with the exact version
selected, what we use it for, the surface we integrate through, what we know is
broken or limited, what custom code we still had to write, and — most importantly —
**what we are explicitly not reimplementing** because the platform already owns it.

Compiled 2026-07-30. Nothing here is a guess: every version was resolved from the
package index at pin time, and every API claim was checked against the shipped
source of that exact pinned version (see "Documentation access" below).

---

## Task 2A addendum — what is now executed rather than declared

Task 1 shipped this stack with Temporal and Compose **unrun**: the build sandbox
denied `temporal.download` and every container registry. Task 2A moved that proof
onto a clean GitHub-hosted runner, where those hosts are reachable.

Capabilities exercised for the first time, with the surface each one uses:

| Capability | Owner | Surface used | Evidence artifact |
|---|---|---|---|
| Durable execution across worker loss | Temporal | `Client.start_workflow`, `handle.signal`, `handle.fetch_history` | `durability-recovery.json` + `.history.json` |
| Activity retry policy | Temporal | `RetryPolicy` on `execute_activity`; read back from `ActivityTaskScheduled.retryPolicy` | `retry-behaviour.json` |
| Activity timeout | Temporal | `start_to_close_timeout`; `ActivityTaskTimedOut` in history | `timeout-behaviour.json` |
| Replay / determinism | Temporal | **`temporalio.worker.Replayer`** + `WorkflowHistory.from_json` | `replay-determinism.json` |
| Trace completeness | Phoenix | GraphQL query (its supported surface, not its database) | `phoenix-trace.json` |
| Container health, DNS, dependencies, volumes | Docker Compose | `compose config/ps/exec`, `docker inspect .State.Health` | `compose-verification-*.json` |

Two additions worth noting because they are *not* new dependencies:

* **`WorkflowHistory.to_json_dict()`** is used for every history artifact and every
  history assertion. We deliberately did not write a history parser — the SDK
  ships the serialisation and the replayer, so both are used as given.
* **The Temporal CLI inside `temporalio/temporal:1.8.1`** provides the health check
  (`temporal operator cluster health`) and the worker-registration check
  (`temporal task-queue describe`). No custom health protocol was invented.

### Correction to the Temporal service definition

The Task 1 compose file passed `--ui-ip` and `--namespace=default` to
`temporal server start-dev`. On a clean runner the container exited during startup
and Compose reported it unhealthy within ~31 seconds — far too fast to have
exhausted a 12-retry budget, which is the signature of a process dying rather than
being slow (CI run `30569302260`). `--ui-ip` defaults to `--ip`, and `start-dev`
always creates the `default` namespace, so neither flag was buying anything. Both
were removed and the health budget widened. Recorded here because the dossier's
"known limitation" column is where a reader would look for it.

---

## Documentation access — read this before trusting the "docs consulted" column

This build ran inside a sandbox whose egress policy **denies all documentation
domains**. Verified blocked at pin time (HTTP 403 at the egress proxy):

| Host | Status |
|---|---|
| `docs.temporal.io` | 403 CONNECT denied |
| `docs.litellm.ai` | 403 CONNECT denied |
| `inspect.aisi.org.uk` | 403 CONNECT denied |
| `www.promptfoo.dev` | 403 CONNECT denied |
| `arize.com` | 403 CONNECT denied |
| `docs.langchain.com` | 403 CONNECT denied |
| `opentelemetry.io` | 403 CONNECT denied |

Reachable: `pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org`,
`hub.docker.com` (metadata API), `registry-1.docker.io` + `ghcr.io` (manifest API
only — blob download denied), and web *search* (snippets, not pages).

Operating rule 2 says not to rely on remembered APIs *when official documentation is
accessible*. It was not accessible. So rather than work from memory, every API claim
below was verified against a **stronger** authority than the website: the shipped
source, docstrings, and bundled README of the exact pinned artifact, read from the
installed venv. Those paths are cited in the "Documentation consulted" column as
`[shipped]`, and they describe the precise version we pin — which a docs site,
tracking `main`, does not.

Where a canonical URL is given without `[shipped]`, it is recorded as the page a
reader with unrestricted egress should consult; it was **not** fetched by this build
and must not be read as "verified by fetch". `[search]` marks a claim corroborated
only by a search-result snippet.

---

## Runtime

### Python

| Field | Value |
|---|---|
| **Exact version** | CPython **3.12.3** (`requires-python = ">=3.12,<3.13"`) |
| **Docs consulted** | PyPI `requires_python` metadata for every dependency below (fetched) |
| **Capability used** | Language runtime |
| **Integration surface** | `pyproject.toml` |
| **Known limitation** | 3.13 is out, but `arize-phoenix` and `litellm` both declare `<3.15`, and `temporalio[langgraph]` warns below 3.11 — 3.12 is the intersection with the widest wheel coverage. Not on 3.13 because no dependency needed it and each bump costs a re-verify. |
| **Custom code** | None |
| **Not reimplemented** | — |

**Compatibility verified**, not assumed: `temporalio` `>=3.10`, `langgraph` (via
extra) `>=3.11` for the Functional API, `inspect-ai` `>=3.10`, `arize-phoenix`
`>=3.10,<3.15`, `litellm` `>=3.10,<3.15`. 3.12.3 satisfies all.

---

## Orchestration

### Temporal Python SDK

| Field | Value |
|---|---|
| **Exact version** | `temporalio==1.31.0` with extras `[langgraph, opentelemetry, pydantic]` |
| **Docs consulted** | `[shipped]` `temporalio/contrib/langgraph/README.md`; `[shipped]` `temporalio/contrib/langgraph/_plugin.py` (`LangGraphPlugin.__init__` docstring); PyPI `requires_dist` (fetched — confirms `langgraph>=1.1.0; extra == "langgraph"`). Canonical: `https://docs.temporal.io/develop/python/integrations/langgraph` |
| **Capability used** | Durable workflow execution, activity retries, timeouts, cancellation, parallel activity coordination, workflow history/replay |
| **Integration surface** | `@workflow.defn` / `@workflow.run`; `@activity.defn`; `Worker(client, task_queue=..., workflows=[...], activities=[...], plugins=[LangGraphPlugin(...)])`; `workflow.execute_activity(...)`; `RetryPolicy`; `temporalio.contrib.pydantic.pydantic_data_converter` |
| **Known limitation** | The LangGraph plugin is **marked experimental** in its own README ("⚠️ This package is currently at an experimental release stage"). LangGraph `Store` is unsupported inside activity-wrapped nodes (`runtime.store` is `None`). The dev server binary is fetched from `temporal.download`, which this sandbox blocks — see ADR-0006. |
| **Custom code** | Workflow/activity definitions, the state model, and payload schemas — i.e. *what* to orchestrate. |
| **Not reimplemented** | Retry loops, backoff, timeout timers, cancellation propagation, run history, crash recovery, replay determinism. We never wrote a scheduler or a retry helper. |

### Temporal ↔ LangGraph integration (official plugin)

| Field | Value |
|---|---|
| **Exact version** | Ships inside `temporalio==1.31.0` as `temporalio.contrib.langgraph` (installed via the `langgraph` extra) |
| **Docs consulted** | `[shipped]` `temporalio/contrib/langgraph/README.md` (full text read); `[shipped]` `_plugin.py`. `[search]` Temporal's launch post describes the plugin as **Public Preview**. |
| **Capability used** | Runs LangGraph `StateGraph` nodes as Temporal Activities, so each node gets Temporal's retries/timeouts without LangGraph knowing about Temporal |
| **Integration surface** | `LangGraphPlugin(graphs={"name": state_graph}, default_activity_options={...})` passed to both `Client.connect(plugins=[...])` and `Worker(plugins=[...])`; inside the workflow, `temporalio.contrib.langgraph.graph("name").compile()`. Per-node `metadata={"execute_in": "activity"|"workflow", "start_to_close_timeout": ..., "retry_policy": ...}`. |
| **Known limitation** | Experimental. `execute_in` is **mandatory per node** and cannot be defaulted. Checkpointers other than `InMemorySaver` are pointless (Temporal owns durability). Stores unsupported. |
| **Custom code** | The investigation graph itself and the `execute_in` policy per node. |
| **Not reimplemented** | The node→activity bridge. This is the single most important "do not rebuild" in the project: we did **not** write our own adapter to run graph nodes durably. |

### LangGraph

| Field | Value |
|---|---|
| **Exact version** | `langgraph==1.2.10` |
| **Docs consulted** | `[shipped]` `langgraph/graph/state.py` (`StateGraph`, `add_node`, `add_edge`, `add_conditional_edges`, `compile`); `[shipped]` `langgraph.graph.START/END`. Canonical: `https://docs.langchain.com/oss/python/langgraph/graph-api` |
| **Capability used** | The bounded investigation graph: state container, node transitions, conditional edges |
| **Integration surface** | `StateGraph(InvestigationState)`, `add_node(name, fn, metadata=...)`, `add_edge`, `add_conditional_edges`, `compile()`, `ainvoke()` |
| **Known limitation** | Reducer semantics on `Annotated[list, operator.add]` mean node returns *append*; returning a full list double-appends. Bit us once, covered by a transition test now. |
| **Custom code** | Node bodies (hypothesis generation, probe selection, repair comparison) and the state schema. |
| **Not reimplemented** | Graph traversal, edge resolution, state merging/reducers, conditional routing. Also: **LangGraph is not used for persistence, retries, timers, or recovery** — Temporal owns those (ADR-0002). |

---

## Model access

### LiteLLM Proxy

| Field | Value |
|---|---|
| **Exact version** | `litellm==1.94.0` (Python, `[proxy]` extra); image `ghcr.io/berriai/litellm:v1.94.0` @ `sha256:65d84a2282137b4dc73bbe184650a7c807177c533e4223b3bfbc87963fe3fabe` |
| **Docs consulted** | `[shipped]` `litellm/proxy/proxy_server.py` L4478-4490 (`custom_provider_map` config loading via `get_instance_fn`); `[shipped]` `litellm/proxy/health_endpoints/_health_endpoints.py` L1552/L1652/L1656 (`/health/readiness`, `/health/liveliness`, `/health/liveness` unauthenticated; `/health` L901 requires `user_api_key_auth`); `[shipped]` `litellm.CustomLLM` class definition. Canonical: `https://docs.litellm.ai/docs/proxy/configs` |
| **Capability used** | One OpenAI-shaped API across every provider; provider adapters; request/response normalisation; named-model routing; retry bounding |
| **Integration surface** | `config.yaml` → `model_list[].litellm_params`; `litellm_settings.custom_provider_map` for our mock provider; HTTP `POST /v1/chat/completions`; `GET /health/readiness` for the healthcheck |
| **Known limitation** | `/health` requires a virtual key, so container healthchecks must target `/health/readiness`. Router fallbacks are on by default and **had to be explicitly disabled** for benchmark determinism (ADR-0004). The proxy resolves an alias to a concrete model, so the *resolved* id must be read back from the response rather than assumed. |
| **Custom code** | The `config.yaml`, a `CustomLLM` subclass implementing three deterministic mock models, and a thin registry that records the resolved model id. |
| **Not reimplemented** | **No custom provider SDKs.** No per-vendor auth, no request translation, no response normalisation, no streaming parser. The mock provider is registered *through LiteLLM's own documented extension point* (`custom_provider_map`), not alongside it. |

---

## Evaluation

### Inspect AI

| Field | Value |
|---|---|
| **Exact version** | `inspect-ai==0.3.251` |
| **Docs consulted** | `[shipped]` `inspect_ai/__init__.py` exports; `[shipped]` signatures of `Task`, `Sample`, `@scorer`, `@solver`, `Score`, `Target`, `MemoryDataset`, `eval()`. Canonical: `https://inspect.aisi.org.uk/` |
| **Capability used** | Evaluation task/sample model, the eval runner, scorers, and the `.eval` log format |
| **Integration surface** | `@task def ...() -> Task`, `Task(dataset=[Sample(...)], solver=..., scorer=[...])`, `@scorer(metrics=[accuracy()])`, `inspect eval` CLI, logs under `evals/logs/` |
| **Known limitation** | Inspect's own sandboxing (`sandbox="docker"`) needs a container runtime, which this sandbox denies; we run the `local` sandbox plus our own per-run temp-directory isolation and document the weaker boundary honestly (ADR-0007, threat model T-4). |
| **Custom code** | The coding-problem samples, the deterministic scorers (build / visible / hidden / invariant / prohibited-files), and the solver that drives our workflow. |
| **Not reimplemented** | The eval runner, sample iteration, scoring/metric aggregation, log format, or a results viewer. |

### Promptfoo

| Field | Value |
|---|---|
| **Exact version** | `promptfoo@0.121.19` (npm, installed and version-verified) |
| **Docs consulted** | `[shipped]` installed CLI (`promptfoo --version`, `promptfoo validate`); bundled JSON schema. Canonical: `https://www.promptfoo.dev/docs/configuration/guide/` |
| **Capability used** | Repeatable cross-provider prompt matrices; provider comparison reports; deterministic assertions |
| **Integration surface** | `promptfooconfig.yaml` (`providers`, `prompts`, `tests`, `defaultTest.assert`), `exec:` provider shelling to our pinned venv, `is-json` + `javascript` assertions, `promptfoo eval -o report.json` |
| **Known limitation** | Node's built-in fetch ignores `HTTPS_PROXY` unless `NODE_USE_ENV_PROXY=1`; irrelevant for the mock path (no egress) but it will bite the optional live-provider path. |
| **Custom code** | The config, the `exec:` bridge to the mock gateway, and the JSON-schema/diversity assertions. |
| **Not reimplemented** | The matrix runner, assertion engine, or comparison report. Notably we do **not** score correctness by majority vote (task rule); assertions are schema- and field-level. |

---

## Observability

### Arize Phoenix

| Field | Value |
|---|---|
| **Exact version** | server `arize-phoenix==19.10.0`, image `arizephoenix/phoenix:version-19.10.0` @ `sha256:3092f5543a3ddd35db7390cf971027c33be6be1f171274d57f3c8658c2193d67`; client `arize-phoenix-otel==0.16.1` |
| **Docs consulted** | `[shipped]` `phoenix/config.py` env-var constants — `PHOENIX_WORKING_DIR`, `PHOENIX_SQL_DATABASE_URL`, `PHOENIX_PORT`, `PHOENIX_GRPC_PORT`, `PHOENIX_ENABLE_PROMETHEUS`; `[shipped]` `phoenix.otel.register`. Canonical: `https://arize.com/docs/phoenix/self-hosting` |
| **Capability used** | OTLP trace collection, trace UI, SQLite-backed persistence, projects |
| **Integration surface** | OTLP/HTTP into `:6006/v1/traces`; `phoenix.otel.register(project_name=..., endpoint=...)`; persistence via `PHOENIX_SQL_DATABASE_URL=sqlite:////data/phoenix.db` |
| **Known limitation** | Phoenix's dependency closure conflicts with the app's, so the **server lives in its own venv/container** and only the light `arize-phoenix-otel` client is in the app environment. Image blobs are unpullable in this sandbox (registry egress denied), so the containerised path is config-validated but unrun here. |
| **Custom code** | Span names, the artifact attributes we choose to record, and redaction. |
| **Not reimplemented** | **No custom trace database and no custom trace viewer** — the explicit prohibition. We emit OTLP and stop. |

### OpenTelemetry (Python)

| Field | Value |
|---|---|
| **Exact version** | `opentelemetry-sdk==1.44.0`, `opentelemetry-exporter-otlp-proto-http==1.44.0`, `openinference-instrumentation-langchain==0.1.68` |
| **Docs consulted** | `[shipped]` `opentelemetry.sdk.trace` / `.export` / `BatchSpanProcessor`; `[shipped]` OTLP HTTP exporter. Canonical: `https://opentelemetry.io/docs/languages/python/` |
| **Capability used** | Span creation, context propagation, batching, OTLP export |
| **Integration surface** | `TracerProvider(resource=...)` + `BatchSpanProcessor(OTLPSpanExporter(endpoint=...))`; `tracer.start_as_current_span(...)`; `LangChainInstrumentor().instrument()` for graph-level spans |
| **Known limitation** | Export is fire-and-forget; a dropped span is invisible unless you force-flush, so the reliability gate that requires trace artifacts checks our own span ledger rather than trusting the exporter. |
| **Custom code** | The span tree shape and attribute redaction. |
| **Not reimplemented** | Span plumbing, batching, retry, or the wire protocol. |

---

## Application-side libraries

| Package | Exact version | Capability used | Integration surface | Known limitation | Custom code | Not reimplemented |
|---|---|---|---|---|---|---|
| `pydantic` | **2.13.4** | Runtime-validated versioned domain schemas | `BaseModel`, `Field`, `field_validator`, `model_config=ConfigDict(extra="forbid", frozen=True)` | v2 `frozen=True` gives shallow immutability only — a `list` field is still mutable in place; we use tuples where it matters | The 15 domain schemas | Validation, coercion, JSON Schema generation, serialisation |
| `pytest` | **9.1.1** | Test runner | `pytest.ini` options in `pyproject.toml`, markers | — | Tests | Test discovery/reporting |
| `pytest-asyncio` | **1.4.0** | Async test support | `asyncio_mode = "auto"` | Mode must be set explicitly or async tests silently skip | — | Event-loop management |
| `hypothesis` | **6.164.0** | Property-based testing of the invariant | `@given`, `strategies`, `@settings` | Default deadline flakes on slow subprocess work; disabled per-test with justification | Strategies + properties | Shrinking, generation, replay database |
| `ruff` | **0.16.0** | Format + lint | `ruff format --check`, `ruff check` | — | Config | Linting |
| `mypy` | **2.3.0** | Type checking | `mypy app` | Temporal's sandbox re-imports confuse some inference; `temporalio.contrib` is untyped in places | Annotations | Type inference |
| `bandit` | **1.9.4** | Security scan of our own code | `bandit -r app` | AST-only; finds no logic flaws | Config + justified suppressions | Rule set |
| SQLite | stdlib `sqlite3` on CPython 3.12.3 | Privileged identity store + application audit records | `sqlite3` module, WAL, `PRAGMA foreign_keys` | Single-writer; fine at walking-skeleton scale | Schema + access boundary | The database engine |

---

## Container images (all digest-pinned)

| Service | Image | Digest |
|---|---|---|
| Temporal dev server + Web UI | `temporalio/temporal:1.8.1` | `sha256:59561b9ef060eaeb1f46cb6a1842d6cbdd8a393eb3b6d315ecef5fe2f0b1d7a6` |
| Phoenix | `arizephoenix/phoenix:version-19.10.0` | `sha256:3092f5543a3ddd35db7390cf971027c33be6be1f171274d57f3c8658c2193d67` |
| LiteLLM Proxy | `ghcr.io/berriai/litellm:v1.94.0` | `sha256:65d84a2282137b4dc73bbe184650a7c807177c533e4223b3bfbc87963fe3fabe` |
| Worker base | `python:3.12.11-slim` | `sha256:47ae396f09c1303b8653019811a8498470603d7ffefc29cb07c88f1f8cb3d19f` |

Digests were read from the registry manifest API at pin time. Tags are kept
alongside for readability; the digest is what Compose actually resolves.

`temporalio/temporal:1.8.1` runs `temporal server start-dev`, which bundles the
frontend, history, matching and worker services **plus the Web UI** and persists to
a SQLite file. That is why this stack has no PostgreSQL and no separate UI
container — see ADR-0005.

---

## Explicitly not added

Per the task's constraints, and because nothing in the walking skeleton requires
them: **Kubernetes, Redis, PostgreSQL, Prometheus, Grafana**, and any cloud service.
`PHOENIX_ENABLE_PROMETHEUS` is left at its default (off).
