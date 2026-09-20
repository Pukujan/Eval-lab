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

## Active

- local bootstrap via TASK-0001
- classify GitHub Actions pre-step runner failure after local validation

## Queued after TASK-0001

1. TASK-0002: canonical schema + synthetic fixture dataset
2. TASK-0003: Jev objective baseline runner
3. TASK-0004: calibration/metrics implementation
4. TASK-0005: first public benchmark adapter
5. TASK-0006: lightweight local baseline

## Blockers

This chat cannot execute commands on the user's local machine.

GitHub Actions currently creates jobs but terminates them before any workflow step is reported. Treat this as an infrastructure/account/runner question until local bootstrap proves otherwise.

## Next atomic action

Local Luna/agent executes TASK-0001 from `docs/LOCAL_BOOTSTRAP_LUNA.md`, records exact results, and commits the checkpoint.
