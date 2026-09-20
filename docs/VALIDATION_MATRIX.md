# Validation Matrix

| Gate | Required evidence | Blocks next task? |
| --- | --- | --- |
| TASK-0002 schema | contract + unit tests + deterministic fixture fingerprint | yes |
| TASK-0003 Jev code | mocked response tests | yes for Jev experiments; no for metrics/local work |
| TASK-0003 live provider | successful call OR checkpointed 429/provider block | no |
| TASK-0004 metrics | known-value tests + calibration split guard | yes |
| TASK-0005 ARC | pinned source metadata + stable fingerprint + adapter tests | yes |
| TASK-0006 local | 20-record feasibility + full chosen slice + comparison report | final v0 gate |

## Required evidence in every task checkpoint

- branch/worktree path
- parent commit
- OS/Python/runtime versions
- files changed
- exact validation commands
- pass/fail/skip counts
- external blockers
- decisions
- next atomic action

## Provider-block policy

External rate limits, quota exhaustion, model download outages, or missing GitHub runners are not converted into code failures.

An agent must:
1. capture the external status;
2. prove local/mock contract behavior;
3. checkpoint the blocked integration;
4. continue only where the dependency graph permits.

## Scientific stop conditions

Stop and checkpoint before proceeding if:
- a source problem appears in multiple splits;
- a test label is used during calibration fitting;
- a gold label lacks provenance;
- public dataset revision cannot be identified;
- different systems are being compared on different record IDs without an explicitly named missingness analysis;
- secrets appear in logs/artifacts.

## TASK-0010 research-release gate

| Gate | Required evidence | Blocks completion? |
| --- | --- | --- |
| Routing core | unit + leakage + deterministic routing tests | yes |
| Metamorphic/differential | all offline M/D invariants green | yes |
| Jev pinned arm | pinned model identity + normalized live/mock evidence | yes unless provider externally unavailable and explicitly scoped |
| Statistical adequacy | counts + uncertainty for low-error claims | yes for confidence-supported claims |
| Benchmark | deterministic rebuild + source manifest + SHA-256 | yes |
| Provenance | RO-Crate + PROV graph + SHACL validation | yes |
| Paper | generated result tables + reproducibility/limitations sections | yes |
| Citation metadata | valid CFF; DataCite-compatible metadata captured | yes |

TASK-0010 cannot complete with a paper whose headline numbers are not traceable to committed result artifacts.
