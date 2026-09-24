# TASK-0060: Live Eval Lab app on gravebuster (architecture)

## Status

Architecture complete (plan only). Tracked by GitHub issue #71. Build phases get
their own issues once Alex settles the open decisions.

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

The next phase is the `live/` backend (phase 2), after #69 lands the schema and
Alex settles the decisions. The design-bakery route is tracked in design-bakery#50.

## Next atomic action

Alex answers decisions 1 to 5 in `docs/architecture/live-app.md` section 14.
