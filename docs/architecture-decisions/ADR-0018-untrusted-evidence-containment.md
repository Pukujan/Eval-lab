# ADR-0018 — Everything in an evidence bundle is untrusted input

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Eval-lab's input is a bundle produced by a different repository (ADR-0014),
describing work done by a coding agent, containing filenames the agent chose,
reports the agent wrote, reviewer statements, and model responses.

The important framing is that **the producer does not have to be hostile for any
of this to go wrong**. An agent that writes an artifact path containing `..`
produces the same outcome as one that intended to. A model that emits a
gigabyte of repeated text fills the same disk as a decompression bomb. Treating
the bundle as untrusted is not an accusation against Agent-workbench; it is the
recognition that Agent-workbench's own input is a coding agent, and its output is
not its intent.

## Decision

Every field, filename, archive member, report body, reviewer statement and model
response in an evidence bundle is hostile data until a deterministic check says
otherwise, and no amount of checking grants it authority over control flow.

| Surface | Containment |
|---|---|
| Archive extraction | Ceilings on member count, per-member uncompressed size, total uncompressed size, and compression ratio. Refused **before** writing, not discovered during |
| Member paths | Reject absolute paths, `..` at any position, drive letters and UNC prefixes; resolve each member and require containment under the extraction root |
| Symlinks and hardlinks | **Refused outright**, not resolved. A link that resolves inside the root today resolves outside it after the next member is written |
| Device, FIFO and other special members | Refused |
| Filenames | Opaque bytes. Never globbed, never split on a delimiter, never handed to a shell |
| Artifact set | An **allowlist** of logical names, in the shape of `EVIDENCE_SPECS`. A file nobody published is invisible, not implicitly collected |
| Report and reviewer text | Never interpolated into a prompt, a log line, a shell command, or a rendered report without escaping. Never parsed for instructions |
| Model and reviewer output | No authority over control flow, ever (ADR-0019) |
| Workspace | One fresh directory per run, removed on **every** terminal path |

## Cleanup on every terminal path is the part people get wrong

The happy path always cleans up. The paths that do not are exactly the ones a
malformed bundle steers you into: the extraction that aborts on the fourth bad
member, the activity that exceeds its `start_to_close_timeout`, the workflow that
is cancelled, the run that ends in `infrastructure_failure`. Those are also the
runs whose unpacked contents you most want gone, because they are the runs where
something unexpected was on disk.

Under Temporal this needs deliberate structure rather than a trailing statement.
Cleanup written after a `try` body does not run when the activity is cancelled,
so cancellation and timeout have to reach it. And because worker loss is a
*demonstrated* event in this repository rather than a hypothetical one
(ADR-0017 — a `SIGKILL`ed worker whose workflow another worker resumed), there
also has to be a sweeper for the case where the worker died between extraction
and cleanup. No `finally` block survives `SIGKILL`.

## Precedent already in this repository

The pattern being extended here is not new; three pieces of it are already
enforced in code:

- **`CallRecord` in `app/models/ckff_client.py` carries no model text at all.**
  It stores a SHA-256, a character count, a byte count, token counts, latency,
  status, and an allowlisted set of response headers — and has no field for the
  completion. "A caller cannot act on content it never receives", which makes
  *output cannot steer control flow* a property of the type rather than a rule
  someone has to remember. That is enforcement, not a promise, and it is the
  model to copy at the intake boundary.
- **`app/activities/patching.py` refuses any path that escapes the working
  copy** — `..`, absolute paths, and symlinks resolving outside the root — before
  any write (ADR-0007, threat model T-3).
- **`app/domain/fixtures.py::solver_visible_paths()` is an allowlist**, because
  the failure mode of a denylist is that a new file leaks by default (T-1). The
  artifact allowlist above is the same argument at a different boundary.

And one that governs how producer claims are read: `app/evidence/bundle.py`
copies evidence byte-for-byte, so producer-written fields survive inside it —
`phoenix-trace.json` really does contain `"verified": true`. Those are **claims
by the producer, data for the verifier to check**, never findings. `_reject_self_attestation`
enforces the other half by refusing to let Eval-lab author such a field itself.

## Alternatives rejected

- **Trust bundles from a known producer, because the pipeline is ours.** The
  producer runs a coding agent against a task. Its output is not its intent, and
  a trusted-producer model has no answer for an agent that makes an ordinary
  mistake.
- **A denylist of dangerous filenames and paths.** The failure mode of a denylist
  is that the next dangerous thing is permitted by default. This repository
  already made and accepted that argument for solver-visible paths.
- **`tarfile.extractall(filter="data")` and nothing else.** The data filter is a
  genuine improvement and covers traversal, links and special files. It does
  **not** bound total uncompressed size or member count, so it does not address a
  decompression bomb. Use it *and* the ceilings. (Stated as a requirement for the
  intake path; it is not yet implemented, and saying otherwise would be exactly
  the unverified claim this repository exists to prevent.)
- **Sanitise hostile text into a safe form and then trust the result.**
  Sanitisation that succeeds still yields text that should have no authority;
  sanitisation that fails yields text that has it. Only the second case matters,
  so the answer is to never grant the authority.
- **Rely on the container boundary to contain extraction.** There is no
  kernel-level boundary in every environment this runs in (ADR-0007's honest
  part, threat model T-4). Containment is layered and the layer count is stated
  rather than assumed.
- **Resolve symlinks and allow the ones that land inside the root.** Correct at
  the moment of the check and wrong one member later. Time-of-check to
  time-of-use, in a loop, on attacker-ordered input.

## Consequences

- **The ceilings are conservative bounds, not calibrated values.** Same admission
  as the Task 2B limits: no evidence supports any of them as correct; they are
  chosen so an unattended mistake stays small. A legitimate large bundle will be
  refused, and the fix is to raise a recorded ceiling deliberately — not to
  remove it.
- **Refusing symlinks outright will refuse some legitimate bundles.** Accepted.
  The producer can flatten; the alternative is a resolution loop that is wrong on
  hostile input.
- **Rejections here are evidence rejections, not verdicts on the work**, and they
  are reported as `rejected` with a reason rather than as `infrastructure_failure`
  (ADR-0019). A malformed bundle is bad input; the harness worked.
- **Not established: kernel-level isolation.** No test asserts it, because we do
  not have it (ADR-0007). Unpacking a bundle executes nothing, which is the easy
  half; the public deterministic checks *do* execute repository code, and that is
  contained by ADR-0007's layers 1-3 and no further.
- **Not established: that a self-consistent bundle is a true bundle.** Hashes,
  provenance and JobSpec correspondence establish that the bundle describes one
  coherent job and has not been altered since it was assembled. They do not
  establish that the job happened as described. Detecting a wholly fabricated but
  internally consistent bundle is the verifier's problem (ADR-0016), and not a
  solved one.
