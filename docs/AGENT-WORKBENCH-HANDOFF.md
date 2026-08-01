# Agent-workbench handoff — FROZEN

**Contract version 1.0.0. Frozen 2026-08-01.** Companion to
[`END-STATE-CONTRACT.md`](END-STATE-CONTRACT.md).

This is what Agent-workbench hands to Eval-lab, and what Eval-lab will do with it.
It is written for the producing side, so it says plainly which of Eval-lab's
behaviours are non-negotiable rejections rather than warnings.

## The boundary in one line

Agent-workbench produces work and the evidence of having produced it. Eval-lab
decides nothing about how the work was produced and everything about whether the
evidence is admissible.

## What Agent-workbench owns

- receives the real JobSpec — **and owns its format**;
- runs the coding agent in an isolated environment;
- owns the worktree, container and session lifecycle;
- runs **visible** tests;
- records **initial and final** visible-test results;
- produces candidate artifacts;
- produces the versioned evidence bundle;
- records attempt lineage, retries, redaction, provenance and operational failures.

## What Agent-workbench never receives

Private verifier tests, private oracle information, holdouts, mutation suites,
thresholds, private verifier reports. Not summarised, not sampled, not "just the
counts". A producer that can see the hidden tests is optimising against them, and
the resulting numbers describe the optimisation rather than the work.

## Reviewer output is untrusted evidence

Agent-workbench may include a reviewer's assessment. Eval-lab records it, hashes
it, and gives it **no authority whatsoever**. It is treated identically to a model
completion: text that is measured, never obeyed.

Concretely, a reviewer field saying `accepted_for_review`, or `ignore previous
instructions`, or anything shaped like a verdict, changes nothing about the
outcome. There is a hostile fixture for exactly this
(`contracts/fixtures/hostile/`), and an acceptance test asserting that hostile
reviewer and model text does not steer Eval-lab control flow.

## The evidence bundle

Produced against a **pinned released** version of the intake schema —
`evidence-intake/1.0.0` at the time of freezing. Eval-lab validates that exact
version. A bundle declaring an unsupported version is rejected rather than
best-effort parsed, because reinterpreting an unknown version is how a producer
and a consumer come to disagree silently about what a field meant.

Required content, in outline (the schema in `contracts/schemas/` is authoritative):

| Group | Content |
|---|---|
| Identity | schema version, bundle id, manifest digest binding the whole bundle |
| JobSpec | the reference: digest plus the small set of public fields, never the JobSpec itself |
| Lineage | ordered attempts, each with index, timing, outcome, and whether it was a retry |
| Tests | **initial and final** visible-test results — both required |
| Artifacts | each with relative path, size, sha256, media type, within the allowlist |
| Narrative | reviewer and agent text, explicitly marked untrusted |
| Redaction | what was redacted and why |
| Provenance | tool name and version, workbench commit, environment identifier |

## What gets rejected, and why

These are hard rejections, each with a fixture and an acceptance test:

| Condition | Rejected because |
|---|---|
| Incomplete bundle | A bundle missing a required part understates what is unproven |
| Wrong JobSpec digest | The evidence describes a different job than the one being evaluated |
| Wrong artifact digest | The artifact is not the one that was measured |
| Evidence altered after hashing | Provenance is broken; the bundle is not what was produced |
| Missing **initial** test result | Without a baseline, "the tests pass" says nothing about change |
| Missing **final** test result | Nothing to compare the baseline against |
| Unexpected extra artifact | An artifact nobody declared is an artifact nobody checked |
| Path traversal in a filename | Extraction would write outside the workspace |
| Symlink escaping the bundle | Same, by a second route |
| Oversized evidence | An unbounded bundle is a denial-of-service vector and an unbounded read |
| Unsupported schema version | Never reinterpreted — a new version is required |
| Verifier attestation mismatch | The attestation is not bound to this run's digests |

A failed attempt is **not** a rejection. A bundle whose attempts all failed is
valid evidence, and there is a fixture for it. Eval-lab needs to be able to record
"this work did not succeed" as a result, not as a malformed input.

## Timing and durability

Eval-lab evaluation runs under Temporal. Two consequences for the producer:

- the client that submits a bundle may disconnect; evaluation continues;
- a worker may be restarted mid-evaluation; the run resumes without producing a
  duplicate attempt.

Neither requires anything from Agent-workbench. They are stated so that a
submission that appears to hang is not resubmitted, which would create exactly the
duplicate the durability work exists to prevent.

## Changing this contract

A change requires a written ADR, an impact analysis across Agent-workbench,
Eval-lab, the verifier boundary, the fixtures and existing recorded evidence,
changed acceptance tests, a protocol-version analysis, and explicit coordinator
approval. Existing recorded evidence stays interpretable under the version it was
produced against — old validators are kept rather than retired.
