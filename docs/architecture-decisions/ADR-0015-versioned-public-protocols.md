# ADR-0015 — Public protocols are versioned, and a version is never silently reinterpreted

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Four shapes now cross a repository boundary, and three different owners can
change code on either side of them (ADR-0014). Evidence is recorded at one moment
and read later — sometimes much later, and sometimes by a party that was not
present when it was produced.

That combination has a specific failure mode that is worse than an incompatible
change: a **compatible-looking** change. If a validator quietly starts reading
`evidence-intake/1.0.0` differently, every bundle already on record changes
meaning retroactively, nothing errors, and no artifact says which reading applied
to it. The bundles are byte-identical and their conclusions are not.

## Decision

Four protocols, frozen at `1.0.0`, with named owners:

| Protocol | Version | Owner | What it is |
|---|---|---|---|
| JobSpec format | Agent-workbench's own | Agent-workbench | The real specification; Eval-lab never holds it |
| `jobspec-reference` | `1.0.0` | Eval-lab | How Eval-lab names a JobSpec without holding it — by digest |
| `evidence-intake` | `1.0.0` | Eval-lab | What Agent-workbench produces against |
| `evallab-outcome` | `1.0.0` | Eval-lab | What humans and downstream readers consume |
| `verifier-envelope` | `1.0.0` | **jointly frozen** | The public Eval-lab ↔ verifier boundary (ADR-0016) |

The rules, frozen with them:

1. Agent-workbench produces evidence against a **pinned released** schema
   version. Eval-lab validates **that exact version** — exact equality, not a
   compatible range.
2. **A protocol change requires a new version.** Not to fix a bug, not to add a
   field, not to relax a constraint.
3. **Existing recorded evidence stays interpretable under the version it was
   produced against.** Old validators are kept.
4. Verifier internals stay private even though the envelope is public. The
   envelope says what may cross, not what happens behind it.

An unknown or unsupported declared version is an intake **rejection**, not an
`infrastructure_failure`. The evidence is the input, and evidence Eval-lab cannot
interpret is evidence it must refuse (ADR-0019). Nothing about the harness has
gone wrong.

## What "silently reinterpreted" actually covers

Three cases, all of which feel harmless at the moment someone makes them.

- **Adding a field to an existing version.** A producer pinned at `1.0.0` does
  not send it. A validator that begins requiring it has retroactively made every
  previously valid bundle invalid, and one that begins *reading* it has made
  every previously recorded bundle one that was graded without a field the schema
  now says matters.
- **Relaxing a constraint in place.** Bundles that were correctly rejected under
  the stricter reading are now bundles the record says were rejected under a
  schema that would accept them. The rejection reason on file no longer follows
  from the schema it names.
- **Fixing a validator bug without a version bump.** This is the sharpest one,
  because it is the one that looks like a strict improvement. The bug is part of
  what `1.0.0` meant in practice. A bundle rejected by the buggy validator *was*
  rejected, and the record has to keep saying so under `1.0.0` while `1.1.0` says
  something different. Rewriting the meaning of `1.0.0` to be the correct one
  makes the archive describe a world that never happened.

## Alternatives rejected

- **Semver range acceptance ("any 1.x").** Turns adding a required field into a
  silent behavioural change, and lets a producer at `1.0.0` and a producer at
  `1.3.0` be graded by the same validator under different meanings with nothing
  in the record distinguishing them. Range matching optimises for not having to
  coordinate, which is precisely the coordination ADR-0014 made structural on
  purpose.
- **One current schema, migrating old evidence forward on read.** Migration
  rewrites evidence. `app/evidence/bundle.py` already refuses to rewrite
  evidence — files are copied byte-for-byte so the recorded SHA-256 stays
  checkable against the source artifact. A read-time migration destroys exactly
  that property, and it does so invisibly.
- **A single joint schema owned by all three repositories.** Owned by everyone
  means frozen by nobody. The `verifier-envelope` is jointly frozen because it is
  a genuine two-party boundary; making that the general case removes the ability
  to freeze anything.
- **Tolerant readers — accept what you can parse.** A tolerant reader that
  accepts a partially malformed bundle is the intake failure Eval-lab exists to
  prevent. Eval-lab's job description includes rejecting incomplete,
  inconsistent, malformed and tampered evidence; tolerance is the opposite of it.
- **Version as advisory metadata, with structural duck-typing for the real
  check.** Then the version records an intention and the validator records
  something else, and when they disagree there is no way to tell which one the
  run actually used.

## Consequences

- **Old validators are kept, and the set only grows.** Every version that
  produced recorded evidence needs a validator that still reads it, with its own
  tests, maintained through dependency upgrades and language-version moves. That
  is real, permanent, monotonically increasing cost, and it is accepted
  deliberately — a version can only be retired by a decision that the evidence
  produced against it is retired too.
- **Version churn for changes that feel trivial.** Clarifying a field
  description is free; changing what a field means is not, however small the
  diff.
- **Cross-repository release sequencing becomes a real activity.** A new intake
  version needs a producer that emits it, a validator that reads it, and a period
  where both old and new are live.
- **Not established: that a producer honoured the version it declares.**
  Validation checks shape, hashes and correspondence — not intent. A bundle can
  declare `1.0.0` and be wrong about it in ways no schema catches. Digest binding
  and JobSpec correspondence (ADR-0016, ADR-0018) narrow this; they do not close
  it.
- **Not established: that versioning prevents disagreement.** It makes
  disagreement *visible and attributable*. Two parties can still hold
  incompatible readings of the same version; the version tells you which document
  to argue about.
- **Precedent already in code.** `BUNDLE_INDEX_VERSION` in
  `app/evidence/bundle.py` is bumped when the index shape changes, and
  `SNAPSHOT_VERSION` in `app/models/alias_snapshot.py` shows the intended
  behaviour on an unknown version exactly: `snapshot_version is X, this harness
  reads Y` — refuse and say so, rather than guess. The same module is also the
  precedent for hash-checking a frozen artifact on load and refusing a mismatch
  instead of warning.
