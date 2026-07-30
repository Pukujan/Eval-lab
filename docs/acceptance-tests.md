# Acceptance tests

What must be demonstrably true for this walking skeleton to be considered working.
Each row names the automated check that decides it. "Demonstrated" below means a
named test asserts it — not that it looked right in a log.

Vocabulary note: the only positive outcome anywhere in this system is
**`accepted_for_review`**. Not `approved`, not `correct`, not `safe`, not
`production_ready`. AT-14 enforces that by grep.

## Core behavioural acceptance

| ID | Statement | Deciding check |
|---|---|---|
| **AT-1** | The known-bad fixture reproduces the duplicate-processing bug deterministically | `tests/acceptance/test_fixture_reproduces_bug.py` — the invariant probe observes 2 committed results for one logical job id |
| **AT-2** | The duct-tape patch is **rejected** | `tests/acceptance/test_ducttape_rejected.py` — visible tests go green, output dedupes, and the run is still `rejected` on `not_symptom_suppression` (effect counter still 2) |
| **AT-3** | The known-good patch reaches **`accepted_for_review`** and nothing stronger | `tests/acceptance/test_known_good_accepted_for_review.py` — asserts the decision equals `accepted_for_review`, and that no field claims correctness, safety, or production-readiness |
| **AT-4** | Editing/patch tools are unavailable before `implementation` | `tests/acceptance/test_tool_gating.py` — every pre-implementation state raises `ToolNotAvailableError` on tool acquisition |
| **AT-5** | Solver roles cannot reach hidden tests or the reference patch | `tests/acceptance/test_solver_isolation.py` — allowlist contains neither; their content appears in no solver-visible surface |
| **AT-6** | Ordinary workflow components cannot resolve real model identities | `tests/unit/test_model_identity_access.py` — the agent-accessible connection cannot resolve a pseudonym; `PrivilegedIdentityStore` refuses construction without a capability |
| **AT-7** | The application cannot merge, push, or deploy | `tests/acceptance/test_no_merge_capability.py` — static scan of `app/` for VCS-write calls |

## Platform integration acceptance

| ID | Statement | Deciding check |
|---|---|---|
| **AT-8** | The Temporal workflow runs the LangGraph investigation end to end | `tests/integration/test_temporal_workflow.py` (skips, with the blocked host named, when no server is reachable) |
| **AT-9** | Every graph node declares `execute_in` and the transitions are legal | `tests/unit/test_langgraph_transitions.py` |
| **AT-10** | The mock gateway is deterministic and credential-free | `tests/unit/test_model_adapter_contract.py` — same request ⇒ byte-identical response; no env key read |
| **AT-11** | The span tree matches the required shape | `tests/integration/test_phoenix_instrumentation.py` — span ledger contains the 13 required span names under `coding-evaluation` |
| **AT-12** | Inspect records both a known-good and an incorrect-patch outcome | `tests/integration/test_inspect_eval_smoke.py` |
| **AT-13** | The Promptfoo config is valid and drives ≥3 mock identities | `tests/integration/test_promptfoo_config.py` |
| **AT-14** | Prohibited outcome vocabulary appears nowhere | `tests/unit/test_outcome_vocabulary.py` |
| **AT-15** | Every declared service has a health check | `tests/integration/test_service_healthchecks.py` — parses `docker-compose.yml`, asserts each service defines one |

## Gate-level acceptance

Each of the eight rejection conditions gets its own test in
`tests/unit/test_reliability_gates.py`, driven from synthetic artifacts (no model,
no network):

| Gate | Rejects when |
|---|---|
| `build_succeeds` | the repository does not build |
| `no_test_regression` | a previously passing visible test fails |
| `hidden_tests_pass` | any hidden test fails |
| `primary_invariant_holds` | one job id yields >1 committed result |
| `evidence_supports_diagnosis` | the diagnosis cites evidence that does not support it |
| `no_prohibited_file_changes` | a prohibited path is modified |
| `not_symptom_suppression` | duplicate output is hidden but the effect counter is still >1 |
| `required_artifacts_present` | spans or audit rows are missing |

And the three abstention conditions in `tests/unit/test_abstention.py`:
no hypothesis survives its probes; evidence remains materially contradictory; the
causal mechanism cannot be tied to the patch.

## Property-based acceptance

| ID | Property | Check |
|---|---|---|
| **AT-16** | For any interleaving of at-least-once deliveries, the fixed processor commits at most one result per job id, and the known-bad one does not | `tests/property/test_invariant_property.py` (Hypothesis) |

## Task 2A — infrastructure acceptance (CI-only)

These cannot be demonstrated on a machine without a container runtime. They are
decided by `.github/workflows/durable-stack-verification.yml` on a clean hosted
runner, and each writes an evidence artifact.

| ID | Statement | Deciding check | Evidence |
|---|---|---|---|
| **AT-17** | The full Compose stack starts from empty volumes and every service reports healthy | `docker compose up --wait` + `scripts/verify_compose.py --phase clean` | `compose-verification-clean.json` |
| **AT-18** | Containers resolve and reach each other by service name | `scripts/verify_compose.py` DNS probes (resolve **and** connect) | same |
| **AT-19** | A real Temporal workflow executes and its history is persisted on the server | `scripts/verify_durability.py` | `durability-recovery.history.json` |
| **AT-20** | A workflow survives an abrupt worker loss and resumes under a new worker | `scripts/verify_durability.py` — SIGKILL, then resume | `durability-recovery.json` |
| **AT-21** | The recovered workflow does **not** repeat a committed external effect | effect ledger reads 1 after recovery | same |
| **AT-22** | Activity retries follow the configured policy, bounded | `scripts/verify_retry.py` — history `retryPolicy` + `ActivityTaskStarted.attempt`, cross-checked against a durable ledger | `retry-behaviour.json` |
| **AT-23** | An activity timeout is recorded and classified as infrastructure, not as a bad patch | `scripts/verify_timeout.py` — `ActivityTaskTimedOut` present, classification `infrastructure_failure` | `timeout-behaviour.json` |
| **AT-24** | Replay accepts the genuine workflow **and rejects** a deliberately incompatible variant | `scripts/verify_replay.py` using `temporalio.worker.Replayer` | `replay-determinism.json` |
| **AT-25** | Phoenix holds every required span | `scripts/verify_phoenix_trace.py` (GraphQL) | `phoenix-trace.json` |
| **AT-26** | Outcomes are unchanged under durable execution | `scripts/verify_outcomes.py --require-durable` | `evaluation-outcomes.json` |
| **AT-27** | Temporal and Phoenix state survive a stack restart | `scripts/verify_persistence.py` after `stop` + `up` | `persistence-across-restart.json` |
| **AT-28** | Every dependency and image is exactly pinned | `scripts/verify_pins.py` | `pin-verification.json` |

Classification is additionally tested deterministically, with no services, in
`tests/unit/test_failure_classification.py`: a missing mandatory trace yields
`infrastructure_failure` rather than `rejected`, and
`classify_infrastructure_incident` refuses to launder an unknown condition
(e.g. `hidden_tests_failed`) into an infrastructure excuse.

## Non-goals for this task

Not claimed, not tested, deferred to Task 2: calibration, live frontier models,
autonomous patch selection, historical benchmark ingestion, and any statement about
general reliability. See `docs/limitations.md`.
