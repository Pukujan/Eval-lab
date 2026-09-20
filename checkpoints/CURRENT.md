# Current Repository Checkpoint

## Program state

Phase: 1 — lab bootstrap and reproducibility.

Current P0 task: `TASK-0001-bootstrap-lab` / GitHub issue #5.

## Main objective

Establish a clean, reproducible local environment before creating benchmark adapters or running research experiments.

## Completed

- repository reset to clean project
- initial Jev adapter and smoke script
- project/product/system/test contracts
- Git-native multi-agent handoff protocol
- CI contract and experiment protocol
- repository contract validator and unit-test skeleton
- task/experiment GitHub issue templates
- TASK-0001 local bootstrap completed on Windows with editable install, contract check, Ruff, and pytest passing
- CI pre-step failure classified as account/runner infrastructure from live job metadata

## Active

- TASK-0001 is complete for local acceptance; Jev provider retry remains an external follow-up
- no TASK-0002 work has started

## Queued after TASK-0001

1. TASK-0002: canonical schema + synthetic fixture dataset
2. TASK-0003: Jev objective baseline runner
3. TASK-0004: calibration/metrics implementation
4. TASK-0005: first public benchmark adapter
5. TASK-0006: lightweight local baseline

## Blockers

- OpenCode Zen Jev free usage returned HTTP 429 `FreeUsageLimitError` with `Retry-After: 28021` seconds during the smoke test.
- GitHub Actions run `35521127126` created matrix jobs but ended before any workflow step was reported; both jobs had no assigned runner (`runner_id: 0`) and no steps. Treat this as account/runner infrastructure.

## Next atomic action

Keep TASK-0001 closed with its exact local evidence. Retry the Jev smoke only after the provider rate-limit window if needed; do not start TASK-0002 in this checkpoint.
