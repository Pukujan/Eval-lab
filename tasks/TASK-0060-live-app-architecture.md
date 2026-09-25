# TASK-0060: Live Eval Lab app on gravebuster (architecture)

## Status

Architecture complete (plan only); Alex settled decisions 1-4 on 2026-09-24
(recorded in `docs/architecture/live-app.md` §14). Decision 5 (offsite backup
target) stays open until phase 4. Tracked by GitHub issue #71. Build phases get
their own issues as they become actionable; phase 2 (`live/` backend) is next
because its dependency, the #69 chart-data schema, is merged.

## Goal

Design a live Eval Lab app: a frontend, a backend and a database of every eval run,
self-hosted on gravebuster. Public reads go through a Cloudflare Tunnel and are
surfaced at design-bakery.com/eval-lab. The runner pushes results as runs finish.
Papers keep embedding frozen, commit-pinned snapshots.

## Scope

- `docs/architecture/live-app.md`: stack, code location, data model, ingest and
  read APIs (the same chart-data schema as #69 and design-bakery#49), snapshot
  freezing, deployment, security, CI, phases, decisions and risks.
- Docs only. No deploys, tunnels, secrets or application code.

## Acceptance criteria

- The architecture doc is merged and posted on issue #71.
- design-bakery#50 (TASK-DB-0055) is open and cross-linked with #69,
  design-bakery#48 and design-bakery#49.
- Open decisions are listed for Alex.

## Checkpoint log

### 2026-09-24 (late): Alex settled decisions 1-4

Recorded in `docs/architecture/live-app.md` §14:
- Decision 1: host on gravebuster; register the node (or allow Tailscale SSH) so
  specs/Docker/disk can be checked directly. Registration is an admin-console
  action on Alex's side.
- Decision 2: option (b) — keep the existing public blind set as-is with a
  disclosure note; all future blind sets stay private (out of git).
- Decision 3: hostnames `evallab-api.design-bakery.com` and
  `evallab-admin.design-bakery.com` approved.
- Decision 4: uncommitted runs shown live badged "provisional"; paper snapshots
  still require committed runs.
- Decision 5 (offsite backup target): still open; needed before phase 4.

Same session: design-bakery PR #54 (TASK-DB-0055 self-host deploy files,
container verified on loopback, no DNS/tunnel change) was merged at `24dbcab`
with Alex's approval; the cutover stays a separate authorized step tracked in
design-bakery#52.

### 2026-09-24: architecture

Status: doc written. The issue comment is posted and design-bakery#50 is open.

Read-only checks:
- gravebuster is not a registered machine; it is on the tailnet and
  owned by another Tailscale account.
- design-bakery.com DNS is on Cloudflare.
- The Vercel rewrite and Cloudflare Tunnel/Access documentation was checked.

Finding: the blind-holdout records, gold labels included, are committed in this
public repo (see decision 2 in the doc).

## Handoff

The next phase is the `live/` backend (phase 2): models, Alembic, read API
returning chart-data schema v1, backfill of all existing runs, tests. The
#69 schema/exporter is merged, so phase 2 is unblocked. Phase 4 (gravebuster
deploy) additionally needs decision 5 and the node registration/SSH access
from decision 1. The design-bakery route is tracked in design-bakery#50 and
the self-host cutover in design-bakery#52.

## Next atomic action

Open the phase-2 issue (TASK-0061 numbering: `live/` backend) and start its
implementation; ask Alex for decision 5 (offsite backup target) before phase 4.
