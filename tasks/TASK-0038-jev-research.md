# TASK-0038 — Jev research and integration audit

- Status: complete
- Owner: Codex/local agent
- Priority: P1
- Branch: `task/TASK-0038-jev-research`
- Worktree: `D:/claude/eval-lab/.worktrees/TASK-0038-jev-research`
- Depends on: TASK-0019 and the completed EXP-014–EXP-019 artifacts

## Goal

Research Jev's actual typed-decision contract and inspect real open-source
integrations so that new Eval Lab Jev work follows the model's intended
semantics. Record the result durably and correct the active adapter if the audit
finds a concrete mismatch.

## Scope and constraints

- Use official TypeSafe and OpenRouter documentation as primary contract sources.
- Inspect multiple public repositories with real Jev code and record their
  actual patterns, not only their README claims.
- OpenRouter is authorized only for Jev in Eval Lab.
- Do not use OpenCode for new work.
- Do not modify or overwrite EXP-014 through EXP-019.
- Do not make live provider calls in this task.

## Acceptance criteria

- [x] Official state, primitive, response, probability, and confidence semantics
      are documented.
- [x] The OpenRouter Jev-only route and model IDs are documented.
- [x] At least four real OSS integrations are inspected, including code-level
      usage patterns and snapshot star counts.
- [x] Streaming, batching, deterministic control flow, and error-handling
      implications are recorded.
- [x] The active typed-spec builder no longer depends on the historical OpenCode
      adapter.
- [x] Descriptive criteria are sent for the closed label space.
- [x] Nested native Jev probabilities and confidence are preserved by the
      active response normalizer.
- [x] No completed experiment artifact is changed.

## Files changed

- `docs/JEV_RESEARCH_AND_USAGE_AUDIT.md`
- `docs/JEV_EVAL_LAB_INTEGRATION_CONTRACT.md`
- `src/eval_lab/escalation/spec.py`
- `src/eval_lab/escalation/providers.py`
- `tests/test_selective_escalation.py`
- `tasks/TASK-0038-jev-research.md`
- `checkpoints/CURRENT.md`

## Validation

Run the repository contract, Ruff, focused Jev/provider tests, full pytest, and
`git diff --check`. No live credentials or raw provider transcripts belong in
the task artifacts.

## Decisions and unresolved work

- The active Jev path remains OpenRouter-only and uses the dedicated Decisions
  endpoint. Direct TypeSafe was studied as the vendor reference contract but is
  not substituted into Eval Lab.
- The historical OpenCode adapter remains for historical reproducibility and is
  not imported by the active typed provider path.
- A multi-record Jev fan-out/batching implementation is a separate future task;
  it must receive its own contract tests and experiment ID.
- The calibrated-probability claim still requires independent objective-gold
  measurement; vendor or GitHub claims are not gold.

## Next atomic action

Return to TASK-0023's sandbox gate using the user's Gravebuster host through
Tailscale. Do not execute untrusted benchmark candidates locally until the
isolated Linux sandbox/resource policy is demonstrated.

## Checkpoint log

### 2026-09-21 — research and adapter correction complete

Audited the official TypeSafe System One/API/state/primitives/confidence
documentation and the OpenRouter Jev Decisions route. Inspected code-level Jev
usage in `browser-use/jev-ultrafast`, `awlevin/typesafe-computer-use`,
`wy-coliney/jev-browser-use`, `jkudish/jev-browser`, `supercorp-ai/supercov`,
and the TypeSafe router reference. The durable findings are in the two Jev
docs listed above.

The active typed-spec builder was decoupled from the historical OpenCode
adapter, descriptive criteria were added to the provider payload, and response
normalization now retains nested native probability maps and confidence. No
provider call or experiment artifact was changed.

Validation initially found the repository task-contract requirement for
`## Checkpoint log` and `## Handoff`; those headings were added before the final
gate. Final gate results are recorded after the task is committed.

Final validation: `python scripts/check_repo_contract.py` -> `Repository
contract OK`; `ruff check .` -> `All checks passed!`; `PYTHONPATH=src python -m
pytest -q` -> `123 passed`; `git diff --check` -> clean.

## Handoff

Worktree: `D:/claude/eval-lab/.worktrees/TASK-0038-jev-research`
Branch: `task/TASK-0038-jev-research`
Status: complete; ready to integrate as a durable Jev research checkpoint.
Next task: use the user's Gravebuster host through Tailscale for the TASK-0023
isolated Linux sandbox/resource-policy gate. Keep EXP-014 through EXP-019
immutable and do not use OpenCode.
