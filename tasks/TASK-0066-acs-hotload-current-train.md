# TASK-0066 - ACS hotloader to the current certified train (ACS 0.2.0)

## Status

In progress. GitHub issue #88. Branch
`task/TASK-0066-acs-hotload-current-train`.

## Goal

Bring the eval-lab ACS multi-agent-hotload runtime up to the ACS version the
current certified train names. The train moved from the frozen `2026-10-01`
snapshot to `current` (agent-stack-train #9, #10); eval-lab's `stack-manifest.json`
now follows it (PR #86). The CI fetch pins and `.coord/` install were left on the
old train, so they are refreshed here.

Scope is deliberately ACS-only. A full move of PCM and CGM to the train's
certified commits is blocked upstream: the certified ACS 0.2.0 pack still
requires PCM `4e23854` (0.6.0) and CGM `6831f91e`, so `hotload_check.py` fails
against the newer checkouts. That blocker is recorded, not worked around.

## Scope

- `.github/workflows/ci.yml`: `ACS_COMMIT` -> `c15e53fc17e8158e9182709d5d3b6f255bcc11f2`
  (agent-custom-setup 0.2.0). `PCM_COMMIT` and `CGM_COMMIT` unchanged.
- `.github/workflows/boss-watchdog.yml`: `ACS_COMMIT` and its comment -> `c15e53f`.
- `.coord/assignment.json`: `pins.acs.revision` -> `c15e53f`, with a `revision_note`;
  top-level `notes` updated to name the current train.
- `checkpoints/CURRENT.md`: new top entry for this checkpoint (the repository-wide
  next action changed), naming the ACS 0.2.0 adoption, the verified blocker, and
  the follow-up re-certification dependency.
- Out of scope: PCM/CGM/OIO version moves (blocked, see below); the CGM
  `.content-system/` adapter; repository settings.

## Acceptance criteria

- CI `quality`, `stack` and `gates` are green on the PR head.
- `hotload_check.py` (ACS 0.2.0) prints `hotload_check: OK` against
  `.coord/assignment.json` with the pinned PCM/CGM checkouts.
- `check_pins.py` (ACS 0.2.0) prints `OK (15 projections agree)`.
- `check_manifest.py` -> `OK: eval-lab agrees with release train current`.

## Checkpoint log

### 2026-10-05 - ACS runtime bump

- Verified the live train (`agent-stack-train` main): `release_train: current`,
  `status: certified`, PCM 0.7.0 `197f7ba8`, CGM 0.5.12 `b487b48c`,
  ACS 0.2.0 `c15e53f`, OIO 0.1.0 `469adf1e`.
- Confirmed main's `stack` job was latently red before PR #86: the manifest
  pinned `2026-10-01` while the train reads `current`; `check_manifest.py`
  failed with a `release_train` mismatch plus three component mismatches. PR #86
  (the owner's) fixed the manifest and is merged.
- `ACS_COMMIT` -> `c15e53f` in `ci.yml` and `boss-watchdog.yml`;
  `.coord/assignment.json` `pins.acs.revision` -> `c15e53f`.
- Verified against ACS 0.2.0 `c15e53f`: `check_pins.py` -> `OK (15 projections
  agree)`; `hotload_check.py` -> `hotload_check: OK`; `check_manifest.py` ->
  `OK: eval-lab agrees with release train current (4 components)`.
- Added the top `checkpoints/CURRENT.md` entry (repository-wide next action
  changed) and recorded the upstream blocker there.

## Blocker (upstream, agent-custom-setup)

The current train's adoption rule says the four components move together, and
`scripts/mesh.py` fails a repository that still requires an older one. But the
certified ACS 0.2.0 pack contradicts this:

- `modules/coordination/multi-agent-hotload/v0.1.0/pins.json` certifies
  `pcm.commit = 4e23854` (0.6.0) and `cgm.commit = 6831f91e`.
- `scripts/hotload_check.py` hard-codes `PCM_PIN_REVISION_PREFIX = "4e23854"` and
  `CGM_PIN_REVISION = "6831f91e..."`.

So eval-lab cannot fetch PCM 0.7.0 / CGM `b487b48c` without failing
`hotload_check.py`. PCM and CGM therefore stay at their 2026-10-01 pins until
agent-custom-setup re-certifies ACS against the new train. Filing that upstream
issue is the owner's call (sibling repository).

## Decisions

- Bump ACS only; keep PCM/CGM/OIO pins. A partial move keeps `hotload_check.py`
  green and still adopts the certified ACS 0.2.0 runtime (installer, dev-root
  checks).
- Do not regenerate `.coord/assignment.json` with `acs_install.py --force`: the
  existing file carries eval-lab-specific `project`, `notes`, `role_fill` and
  `ticket_links` that the generator would replace with defaults.

## Handoff

Next atomic action: run local gates and publish the checkpoint.
