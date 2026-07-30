# ADR-0007 — Fixture execution isolation: what we actually get

- **Status:** Accepted
- **Date:** 2026-07-30

## Context

The skeleton applies a patch and runs the fixture's tests. That is untrusted-ish
code execution. The brief requires restricted sandbox access and no arbitrary host
filesystem access. Inspect AI owns "sandboxed coding evaluation execution" and
supports `sandbox="docker"`.

## Decision

Layered, with the boundary named honestly at each layer:

1. **Working-copy isolation (always).** Every patch application copies the fixture
   into a fresh `tempfile.mkdtemp()` working copy. The pristine fixture is never
   mutated; a run cannot see another run's copy.
2. **Subprocess execution (always).** Build and test run via `subprocess.run` with
   an explicit `cwd`, a **scrubbed environment** (allowlist, not the parent env), a
   hard `timeout`, and `PYTHONDONTWRITEBYTECODE=1`.
3. **Path confinement (always).** `app/activities/patching.py` refuses any patch
   whose target path escapes the working copy — `..`, absolute paths, and symlinks
   that resolve outside the root are rejected before any write.
4. **Container sandbox (when available).** `sandbox="docker"` for the Inspect
   evaluation, which is the strongest boundary and the one Inspect owns.

## The honest part

Layer 4 could not run in the build sandbox — container image pulls are denied by
egress policy. What was actually exercised here is layers 1-3, which give
**process-level isolation, not kernel-level isolation**. A hostile patch that
executes code inside the fixture's own test run is contained by path confinement
and the env scrub, but it is *not* contained by a namespace boundary.

That gap is real and is recorded in `docs/threat-model.md` as **T-4 (accepted,
mitigated-not-closed)**. It is acceptable for a walking skeleton whose fixture is a
repository we wrote ourselves; it would not be acceptable for third-party patches.

## Consequences

- The `local` Inspect sandbox is the default so the eval runs everywhere; the
  Docker sandbox is opt-in via `INSPECT_SANDBOX=docker`.
- No test asserts kernel-level isolation, because we do not have it. Claiming it
  would be the kind of unverified reliability claim this whole project exists to
  prevent.
