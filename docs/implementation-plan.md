# Staged implementation plan

Small, independently testable steps. Each stage lands with its own tests green
before the next begins; nothing downstream is started on a stage that is still red.

| Stage | Deliverable | Independently verifiable by |
|---|---|---|
| **S0** | Design artifacts: dossier, 10 ADRs, `ARCHITECTURE.md`, `AGENTS.md`, acceptance tests, build-vs-integrate, threat model, file tree, this plan | Documents exist and pin exact versions; no implementation started before this |
| **S1** | Project skeleton: `pyproject.toml` with exact pins, tree, `.env.example`, `.gitignore`, Makefile targets | `make setup`; `ruff`/`mypy` run clean on an empty tree |
| **S2** | Domain layer: 15 versioned Pydantic schemas + the 14-state model with a legal-transition table | `tests/unit/test_domain_schemas.py`, `test_workflow_states.py` |
| **S3** | Fixture repository: known-bad, known-good reference (solver-inaccessible), visible + hidden tests, invariants, duplication probe, duct-tape patch | `tests/acceptance/test_fixture_reproduces_bug.py`; fixture's own visible + hidden suites |
| **S4** | Storage + blinding: `audit.db` / `privileged.db` split, pseudonym generation, capability-gated privileged store, `assert_blinded` | `tests/unit/test_model_identity_access.py` |
| **S5** | Model gateway: LiteLLM `config.yaml`, three deterministic mocks via `custom_provider_map`, registry recording the resolved id, no fallback | `tests/unit/test_model_adapter_contract.py`; `scripts/health.py` |
| **S6** | Tool broker: state-gated availability of editing/patch tools | `tests/acceptance/test_tool_gating.py` |
| **S7** | LangGraph investigation graph: nodes, conditional edges, `execute_in` on every node, bounded hypotheses/probes | `tests/unit/test_langgraph_transitions.py` |
| **S8** | Activities: repository inspection, probe execution, patch application with path confinement, build, test, property-test run | `tests/unit/test_activities.py` |
| **S9** | Reliability gates + report: 8 rejection conditions, 3 abstention conditions, `accepted_for_review` as the sole positive | `tests/unit/test_reliability_gates.py`, `test_abstention.py` |
| **S10** | Temporal workflow + worker: `LangGraphPlugin` wiring, retry policies, timeouts; degraded local runner behind the same entry point | `tests/integration/test_temporal_workflow.py` (skips when no server) |
| **S11** | Telemetry: OTel spans matching the required tree, redaction, Phoenix export, span ledger | `tests/integration/test_phoenix_instrumentation.py` |
| **S12** | Inspect AI evaluation: known-good task + deliberately-incorrect-patch task, deterministic scorers, agent-vs-infrastructure failure split | `tests/integration/test_inspect_eval_smoke.py`; `make eval` |
| **S13** | Promptfoo: ≥3 mock identities, identical structured tasks, JSON-schema assertions, diversity + required-evidence-field checks, latency/usage reporting | `tests/integration/test_promptfoo_config.py`; `make eval` |
| **S14** | Docker Compose: digest-pinned services, health checks, startup dependencies; `make up`/`health`/`down` | `docker compose config`; `tests/integration/test_service_healthchecks.py` |
| **S15** | CI: install pinned deps, format, lint, type-check, security scan, unit + property tests, containers, integration, mock Inspect + Promptfoo evals, artifact upload | Workflow file validity; job graph review |
| **S16** | End-to-end demo + honest limitations write-up | `make demo`; `docs/limitations.md` |

## Ordering constraints

- S2 precedes everything: schemas are the vocabulary.
- S3 precedes S8-S9: gates need something real to judge.
- S4 precedes S5: the gateway records pseudonyms, so blinding must already exist.
- S7 precedes S10: the plugin needs the graph at plugin-construction time.
- S9 precedes S12: Inspect scorers reuse the gate predicates rather than restating
  them — one definition, or they drift.

## Stop conditions

If a stage cannot be verified in this environment (blocked registry, unreachable
host), it is recorded as **not verified here**, with the blocking host named, and
the build continues. It is never marked passing on the strength of the code looking
correct.
