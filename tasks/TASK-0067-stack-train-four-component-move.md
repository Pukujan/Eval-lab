# TASK-0067 - Move the ACS hotloader and all stack components to the current train

## Status

Implementation complete, local gates green. GitHub issue #90. Branch
`task/TASK-0067-stack-train-four-component-move`. Awaiting publish and merge.

## Goal

Finish the four-component stack move that TASK-0066 deferred. The current
certified train names PCM 0.7.0 `851bcf72`, CGM 0.5.12 `62340f3d`, ACS 0.2.0
and OIO 0.1.0 `a4bba77b`; eval-lab still fetches PCM 0.6.0 `4e23854` and CGM
`6831f91e`. Move all four together so eval-lab follows the mesh.

## Scope

- `.github/workflows/ci.yml`: `PCM_COMMIT` -> `851bcf72`, `CGM_COMMIT` ->
  `62340f3d`, `ACS_COMMIT` -> `25be219b`.
- `.github/workflows/boss-watchdog.yml`: `ACS_COMMIT` and its comment -> `25be219b`.
- `.coord/assignment.json`: `pins.acs.revision` -> `25be219b`, `pins.pcm.revision`
  -> `851bcf72` with `cli_version` 0.7.0, `pins.cgm.revision` -> `62340f3d`, a new
  `pins.oio` block at `a4bba77b`, plus `notes` and `revision_note`.
- `.content-system/system-version.json`: `helper_commit` -> `62340f3d`.
- `.coord/PROMPT_INJECT.md`: the three CGM commit references -> `62340f3d`.
- `checkpoints/CURRENT.md`: new top entry (repository-wide next action changed).
- `tasks/TASK-0067-stack-train-four-component-move.md`: this file.
- Out of scope: OIO content (already equivalent to `a4bba77b`), repository
  settings, the canonical checkout layout.

## Acceptance criteria

- CI `quality`, `stack` and `gates` are green on the PR head.
- `hotload_check.py` (ACS `25be219b`) prints `hotload_check: OK` against the new
  `.coord/assignment.json` and the new PCM/CGM checkouts.
- `check_manifest.py` prints `OK: eval-lab agrees with release train current
  (4 components)`.
- Local gates: repo contract, workspace policy, Ruff, mypy, pytest, telemetry
  `--check`.

## Upstream note (recorded, not worked around)

The train's ACS entry is `589b0a97`, but that commit's own `stack-mesh.json`
still requires PCM `197f7ba8` / CGM `b487b48c`, so an install at `589b0a97`
refuses the train's own PCM/CGM. ACS `25be219b` (#78, "Route adopters through
the train and gate every install path") carries the mesh that matches the live
train, so it is the mesh-consistent commit to pin. `mesh.py --check` fails on
`589b0a97` and passes on `25be219b`. Filing that upstream is the sibling
repository owner's call; it is recorded here only.

## Decisions

- Pin ACS at `25be219b` (mesh-consistent) rather than the train's stale
  `589b0a97`, because `589b0a97` cannot accept the train's PCM/CGM.
- Record OIO as a pin in `.coord/assignment.json` for traceability even though
  its managed content is unchanged; `hotload_check.py` does not require it.
- Do not run `acs_install.py --force`: it would replace eval-lab-specific
  `project`, `notes`, `role_fill` and `ticket_links` with defaults.

## Checkpoint log

### 2026-10-05 - four-component move

- Verified the live train (`agent-stack-train` main, recorded
  `2026-10-05T19:19:07Z`): PCM 0.7.0 `851bcf72`, CGM 0.5.12 `62340f3d`,
  ACS 0.2.0 `589b0a97`, OIO 0.1.0 `a4bba77b`.
- Confirmed the new ACS `hotload_check.py` refuses the old pins and passes once
  PCM/CGM are moved; confirmed `mesh.py --check` passes on `25be219b`.
- Confirmed OIO managed content is byte-identical (LF-normalized) to `a4bba77b`.
- Confirmed `check_manifest.py` -> `OK: eval-lab agrees with release train
  current (4 components)`.

### 2026-10-05 - edits and local gates

Files changed: `.github/workflows/ci.yml`, `.github/workflows/boss-watchdog.yml`,
`.coord/assignment.json` (pins acs/pcm/cgm + new oio, notes, revision_note,
recorded_at), `.content-system/system-version.json`, `.coord/PROMPT_INJECT.md`,
`checkpoints/CURRENT.md`, this task file.

Commands run (all green):

- `check_manifest.py` -> `OK: eval-lab agrees with release train current (4 components)`.
- `mesh.py --check --root <acs 25be219b>` -> `OK: this repo requires the mesh versions`.
- `hotload_check.py` (ACS `25be219b`) -> `hotload_check: OK`, `install_surface=FULL
  PCM + FULL CGM 0.5.12 + this runtime`, `cgm_validate=VALID`.
- PCM `continuity validate` -> `VALID`; `continuity preflight` -> `VALID`.
- `scripts/check_repo_contract.py` -> `Repository contract OK`.
- `scripts/check_workspace_policy.py --canonical-root D:/development/eval-lab` ->
  `Workspace policy OK`.
- `ruff check .` -> `All checks passed!`; `mypy src/eval_lab` -> `Success`.
- `pytest tests -q` -> `209 passed`.
- `export_chart_data.py --check` -> exit 0; `run_telemetry.py --check` -> `155
  records ... current`; `validate_research_artifacts.py` -> all ok.

Note: `hotload_check.py` emitted dev-root WARNs about `D:\development\colab-cli`
and `D:\development\grok` (plain folders with no `.git`). Pre-existing and
unrelated to this task; CI runs on Linux where that root does not exist.

## Handoff

Next atomic action: publish the checkpoint with `scripts/publish_checkpoint.py`
against issue #90 and merge after required CI (`quality`, `stack`, `gates`).
