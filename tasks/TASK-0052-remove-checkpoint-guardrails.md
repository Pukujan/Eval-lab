# TASK-0052 — Remove optional approval and publish scanning

## Status

Active — tracked by GitHub issue #43 on `task/TASK-0052-remove-checkpoint-guardrails`. The scanner, approval language, CODEOWNERS file, and checkout token-persistence override are removed; focused tests pass.

## Goal

Remove the optional credential/private-data publish scanner and manual code-owner approval policy from Eval Lab's checkpoint automation. Required GitHub CI checks remain the merge gate.

## Decisions

- Keep GitHub Issues, explicit checkpoint paths, task branches, PRs, asynchronous auto-merge, merge recording, and finalization.
- Remove publishing-time credential/private-data scans and optional human/code-owner approval messaging from Eval Lab policy and templates.
- Keep the existing Python 3.11 and 3.12 branch-protection checks and required PR workflow.
- Correct stale TASK-0051 checkpoint text: issue #40 is closed, PRs #41 and #42 merged.
- Do not change global `D:\claude` policies or other repositories.

## Files in scope

- `tasks/TASK-0052-remove-checkpoint-guardrails.md`
- `tasks/TASK-0051-github-checkpoint-automation.md`
- `checkpoints/CURRENT.md`
- `AGENTS.md`
- `docs/CI_CD.md`
- `docs/WORKSPACE_POLICY.md`
- `.github/ISSUE_TEMPLATE/task.yml`
- `.github/pull_request_template.md`
- `.github/workflows/ci.yml`
- `.github/CODEOWNERS` (delete)
- `scripts/publish_checkpoint.py`
- `tests/test_checkpoint_automation.py`

Update this list before editing any additional file.

## Acceptance criteria

- The publisher has no credential/private-data path or content scanner.
- CI checkout uses the default GitHub token persistence behavior.
- CODEOWNERS and manual-approval instructions are removed from Eval Lab policy and templates.
- Task issue, explicit-file publication, CI, async auto-merge, merge recording, and finalization remain functional.
- Main still requires a PR and both Python matrix checks; no changes to global branch protection are needed.
- TASK-0051 status in `checkpoints/CURRENT.md` is accurate.
- Obsolete approval/scanning notes are removed from the active project checkpoint/task documentation.
- Full local gates and GitHub CI pass; PR merges and issue #43 closes after finalization.

## Handoff

The task remains active until issue #43 reflects the merged PR and finalization.

## Checkpoint log

- 2026-09-24: Created issue #43 before implementation. Main is clean at `80df0fa`, synchronized with `origin/main`.
- 2026-09-24: Removed the publisher scanner, CODEOWNERS file, manual-approval language, task-form approval field, and checkout token-persistence override. Kept the required CI checks unchanged. Focused automation tests pass (11 passed).

## Exact files changed

- `.github/CODEOWNERS` (deleted)
- `.github/ISSUE_TEMPLATE/task.yml`
- `.github/pull_request_template.md`
- `.github/workflows/ci.yml`
- `AGENTS.md`
- `checkpoints/CURRENT.md`
- `docs/CI_CD.md`
- `docs/WORKSPACE_POLICY.md`
- `scripts/publish_checkpoint.py`
- `tasks/TASK-0051-github-checkpoint-automation.md`
- `tasks/TASK-0052-remove-checkpoint-guardrails.md`
- `tests/test_checkpoint_automation.py`

## Next atomic action

Run the full local gates, update issue #43 with the results, and publish this branch for required CI and auto-merge.
