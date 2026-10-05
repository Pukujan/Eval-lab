# TASK-0063 - Fresh NTFS clone: dependency cleanup and ACS hotloader update

## Status

In review. GitHub issue #77. Branch `task/TASK-0063-ntfs-deps-acs-hotload`.

## Goal

Work from a fresh clone at `D:\development\eval-lab` now that `D:` is NTFS
(it was exFAT), remove leftover exFAT and pip-era setup, and bring the ACS
multi-agent hotloader install up to the current pins: PCM `4e23854` (CLI 0.6.0),
CGM 0.5.12 `6831f91e` (all eight modules), OIO 0.1.0 and ACS multi-agent-hotload
0.1.0 (`agent-custom-setup` `e1d7732`), via release train 2026-10-01.

## Scope

- Docs: uv-only setup in `README.md` and `docs/LOCAL_BOOTSTRAP_LUNA.md`;
  `D:\development\eval-lab` as the single checkout, with no worktrees or sibling
  clones under `D:\development` and scratch outside it, in `AGENTS.md`,
  `docs/WORKSPACE_POLICY.md`, `docs/architecture/live-app.md` and `tasks/README.md`.
- Workspace guard: `scripts/check_workspace_policy.py` rejects every linked
  worktree; `scripts/finalize_checkpoint.py` refuses worktree cleanup; tests updated.
- PCM overlay: `.continuity/config.json` (single-checkout), `.continuity/tasks/`,
  `schemas/v1/**` copied from the PCM pin, `continuity:project` /
  `continuity:current` markers, issue-log-format block in `AGENTS.md` and the PR
  template.
- CGM adapter: `.content-system/*` raised to 0.5.12 (project-brief v2, narrative
  asset provenance, eight modules); README drops the helper-promotion section;
  `assets/README-ASSET-MANIFEST.yaml` on-image text corrected to match the images.
- OIO: installer output (`.github/ISSUE_TEMPLATE/observational-issue.yml`,
  `.github/workflows/issue-triage.yml`, `.github/scripts/oio_*.py`, `.oio/**`,
  `AGENTS.md` block), `.gitattributes` LF rules for hash-checked files.
- ACS runtime: `.coord/assignment.json`, `.coord/boss_claim.json`,
  `.coord/PROMPT_INJECT.md`, `.github/workflows/boss-watchdog.yml`,
  `stack-manifest.json`; CI gains `stack` and aggregate `gates` jobs.
- Out of scope: repository settings (rulesets, required checks, auto-merge).

## Acceptance criteria

- No npm/yarn lockfiles or exFAT/copy-mode workarounds; docs describe uv only.
- `uv sync --extra dev` builds the single root `.venv`.
- `continuity validate` is VALID and `continuity preflight` reports
  `MODE: TARGET_VALID` on a single-worktree checkout (CI).
- `validate_content_system.py` prints `VALID`; `hotload_check.py` prints
  `hotload_check: OK`.
- CI `quality`, `stack` and `gates` are green on the PR head.

## Checkpoint log

### 2026-10-04 - install and local verification

- Clone of `main` `d16397d`. Hardlink test on `D:` succeeded (`fsutil hardlink`).
- pnpm store is user-wide on `C:` (`%LOCALAPPDATA%\pnpm\store\v10`); left alone
  because this repository has no JavaScript. uv cache is `C:\cache\uv`.
- `uv sync --extra dev` -> root `.venv`, Python 3.11.15; `uv lock --check` OK.
- `validate_content_system.py` -> `VALID: content-generation-modules contract and target adapter`.
- `hotload_check.py --assignment .coord/assignment.json` -> `hotload_check: OK`.
- `watchdog_check.py --dry-run` -> `vacant` (no boss has claimed the seat).
- `check_manifest.py` -> `OK: eval-lab agrees with release train 2026-10-01 (4 components)`.
- Owner rule (2026-10-04 20:01 ET): `D:\development` holds only main checkouts.
  The TASK-0062 linked worktree (`task/TASK-0062-run-telemetry`, clean, HEAD
  `56dd1dd` = PR #79 head) was removed with a normal `git worktree remove` and
  pruned; helper clones moved to `C:\work\_deps`.
- After that: `continuity validate` -> `VALID`; `continuity preflight` ->
  `MODE: TARGET_VALID`; repository contract OK; workspace guard OK; `186 passed`.
- OIO installer refuses to run on Windows (no descriptor-relative no-follow
  operations), so it was run on Linux against a scratch Git repo with the same
  `origin` and its output copied in; the managed files are byte-identical to
  OIO `main` `469adf1`.

## Decisions

- PCM workspace mode is `single-checkout`, matching the one-checkout rule.
- ACS ships no gates workflow stub at `e1d7732`; the `gates` aggregate follows
  PCM `docs/adopter-enforcement.md` instead.
- No auto-merge workflow is added (frontend-bakeoff has one); merging stays with
  the owner.

## Handoff

Next atomic action: owner reviews the PR, then applies the repository settings
listed in the PR (ruleset requiring `gates`, auto-merge) if wanted.
