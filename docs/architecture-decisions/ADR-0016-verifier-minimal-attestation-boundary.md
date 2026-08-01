# ADR-0016 — The verifier returns a minimal, digest-bound attestation

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

ADR-0014 puts hidden tests, holdouts, private mutations, oracle logic and
threshold material in a repository nobody on the implementation side can read.
That settles the *storage* question and leaves the harder one: the verifier still
has to answer, and every answer is a channel back out.

The temptation at this boundary is strong and entirely reasonable-sounding. A
verifier that returned per-test results, failing assertion text, diffs, or a
fine-grained score would make Eval-lab dramatically more useful to a developer.
Each of those is also a way to reconstruct what the hidden tests check.

The operational half of this boundary — how it is invoked, what is logged, what
the error paths are — is `docs/VERIFIER-BOUNDARY.md`. This ADR records why the
result is shaped the way it is.

## The inference channel

The sharp point, because it is the one that survives a per-response redaction
policy:

**Even a rich pass/fail stream leaks hidden-test structure over repeated runs.**

Suppose the verifier returned a vector of N booleans, one per hidden test, with
no names and no text. That looks minimal. It is not. A party that can submit
candidates and vary one behaviour at a time reads the vector as an oracle: change
one thing, see which bit flips, and you have learned what that test exercises.
Nothing in any single response is revealing. The information lives in the
*sequence*, and the sequence is free.

Two things follow, and both are decisions rather than observations:

1. Redaction on the receiving side is not a control. The bandwidth has to be
   removed from the **shape** of the result, not filtered out of instances of it.
2. **Eval-lab must not attempt to infer hidden-test detail from what it gets
   back.** This is a rule about Eval-lab's own code, not only about what the
   verifier sends: no heuristic mapping a reason code to a guess about which
   test, no accumulating results across runs into a matrix, no bisection loop
   over candidate variants. That last one is the attack, performed by the
   defender, with good intentions.

## Decision

`verifier-envelope/1.0.0`, jointly frozen as a public boundary while internals
stay private (ADR-0015).

**The request carries** the envelope version, the digest of the evidence being
verified, the `jobspec-reference` digest, and a run-scoped request identity.

**The response carries** the envelope version, the request digest echoed back, an
outcome value, a reason code drawn from a **closed enumeration**, and the
verifier's own identity and version. It carries no free text, no per-test
structure, no thresholds, and no counts that vary with hidden-test content.

Three properties make that shape load-bearing rather than decorative:

- **Digest binding.** The response names the digest of exactly what it answered.
  An attestation that does not name what it verified is an attestation about
  nothing, and a response that names a digest Eval-lab did not send is refused
  rather than reconciled.
- **Replay and duplicate protection.** A response is accepted **once**, for one
  (run, request digest) pair. A second response for the same pair is not a second
  opinion — it is an infrastructure incident (ADR-0012), because two answers to
  one question mean the record cannot say which one the decision used. Request
  identity is run-scoped so a response recorded in an earlier run cannot be
  replayed into a later one that happens to submit identical evidence.
- **A closed reason-code enumeration**, following the `InfrastructureIncident`
  pattern in `app/reliability/gates.py`: an unrecognised code raises rather than
  passing through. Free text at this boundary is both the leak channel and the
  laundering channel, and the existing guard already demonstrates the shape —
  `classify_infrastructure_incident()` refuses any kind not on the list rather
  than quietly accepting it.

## Alternatives rejected

- **Return the full private report; Eval-lab redacts it.** Redaction on the
  receiving side means the secret crossed the boundary. A redaction bug is then a
  disclosure, and a disclosure of hidden tests is permanent. The boundary has to
  be that the data never leaves.
- **Return per-hidden-test pass/fail.** The inference channel above. It also
  makes the hidden-test set effectively public after enough runs, which destroys
  the only property that makes it worth having.
- **Return a fine-grained numeric score.** A float is a high-bandwidth channel. A
  score that moves when one test's outcome changes *is* that test's outcome, with
  extra steps.
- **Let Eval-lab query the verifier repeatedly to narrow down a failure.** That
  is a bisection attack against the hidden test set, and calling it debugging
  does not change what it extracts.
- **Have the verifier explain itself in prose, "just for humans".** Prose in the
  envelope is prose in Eval-lab's logs, reports and traces, and prose is
  unbounded. The detailed private report is the right place for it, on the
  private side of the boundary.
- **No verifier; trust Agent-workbench's reviewer output.** That is the Task 2A
  finding — the producer grading itself (ADR-0014).

## Consequences

- **Debugging is genuinely worse and that is the price.** When the verifier says
  `rejected` with reason code X, nobody on the Eval-lab side can see further than
  X. The private report exists; reading it is a human's job, on the other side of
  the boundary.
- **The reason-code enumeration is itself a channel and has to be designed
  conservatively.** Codes name *categories* of failure, not tests. Every code
  added is bandwidth added, so adding one is a protocol change and gets a new
  version (ADR-0015).
- **Query volume needs a run-scoped budget**, because the inference channel is a
  function of how many times you may ask. Stated here as policy; it is not yet
  enforcement, and calling it enforcement would be the kind of unverified claim
  this repository exists to avoid.
- **Not established: that the envelope is leak-free.** It reduces bandwidth. No
  formal information-flow analysis was performed and none is claimed. What is
  enforceable on Eval-lab's side is envelope *shape* — unknown fields and unknown
  reason codes are refused rather than recorded — which constrains a
  well-behaved verifier and a misconfigured one, and does not constrain a
  determined one.
- **Not established: that the verifier's answer is correct.** ADR-0014 already
  admits Eval-lab has no instrument that could tell. A minimal attestation makes
  that admission structural rather than incidental.
