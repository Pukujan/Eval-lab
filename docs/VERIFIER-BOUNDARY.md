# Verifier boundary — FROZEN

**Contract version 1.0.0. Frozen 2026-08-01.** Companion to
[`END-STATE-CONTRACT.md`](END-STATE-CONTRACT.md). See ADR-0016.

Eval-lab-verifier is sealed. This document describes the **public client boundary
only**. It contains no verifier internals, and producing any is out of scope for
every workstream in this milestone.

## What the verifier exclusively owns

hidden tests · hard-gold references · protected holdouts · private mutations ·
evaluator mutation suites · private oracle logic · private threshold material ·
detailed private reports.

**Eval-lab and Agent-workbench must not access its repository or internals.** No
cloning, no reading, no importing, no documenting, no testing against it. This is
enforced by the GitHub App scope, and stated here so that a future agent asked to
"just check what the verifier does" recognises the request as out of bounds.

## Why the result must be minimal

The obvious design — return per-test results so Eval-lab can produce a useful
report — leaks the hidden tests. Not in one call, but across many: a candidate
that fails test 7 and passes 1–6, submitted repeatedly with variations, maps the
hidden suite precisely. A rich pass/fail stream is a side channel, and a side
channel that is read by an automated loop is a training signal.

So the result is **minimal and digest-bound**, and Eval-lab must not attempt to
infer hidden-test detail from it. That is a real cost: Eval-lab's reports are less
informative than they could be. The cost is accepted, because an informative
report that quietly destroys the instrument is worth less than a terse one.

## The envelope — `verifier-envelope/1.0.0`

Jointly frozen as a public boundary. Internals stay private.

**Request** carries only: the envelope version; the evaluation run id; the JobSpec
digest; the candidate-artifact digest(s); and a request id used as a nonce. It
carries nothing describing what Eval-lab hopes to find, because a request that
expresses intent invites a response shaped to it.

**Result / attestation** carries only: the envelope version; the request id it
answers; the digests it was bound to; a minimal verdict; and an attestation
digest. The schema is deliberately tight enough that there is nowhere to put
per-test output, thresholds, gold data, or a private report.

## What Eval-lab enforces on the boundary

| Property | Why |
|---|---|
| **Digest binding** | An attestation is accepted only when the digests it names match the run's JobSpec and candidate artifacts. An attestation for a different artifact is a mismatch, not a pass. |
| **Run binding** | The result must answer the request id it was issued for. |
| **Replay / duplicate protection** | A replayed attestation for a stale request is refused, so a previously favourable result cannot be re-presented. |
| **Timeout** | Bounded. An unbounded verifier call is an unbounded evaluation. |
| **Infrastructure-failure classification** | A verifier that is unreachable, times out, or returns an unparseable envelope produces `infrastructure_failure` — **never** `rejected`. A boundary fault says nothing about the work, and misclassifying it as a rejection would report a defect that was never observed. This follows the classification already established in `app/reliability/gates.py` and ADR-0012. |
| **No leakage into artifacts** | Private verifier details must never reach logs, evidence bundles, reports or CI output. Asserted by acceptance test. |

## Deterministic mock verifier

Public CI uses a deterministic mock. It implements the envelope and nothing else:
it has no hidden tests, no gold data and no oracle, because a mock that
approximated those would be a reimplementation of the thing this boundary exists
to keep out.

The mock is what makes the terminal demonstration runnable with **no paid
credentials, no CKFF secret and no private repository access**. It also means the
public acceptance suite proves the *boundary* behaves correctly — binding,
replay, timeout, classification — and proves nothing about the verifier's own
judgements, which is the correct division.

## What this boundary does not establish

- Nothing about the quality of the verifier's hidden tests. Eval-lab cannot see
  them and must not try.
- Nothing about whether a `pass` attestation means the work is correct.
  `accepted_for_review` remains "a human should look".
- The mock proves the protocol, not the verdict. A green public CI run says the
  boundary is sound, not that anything was verified.
