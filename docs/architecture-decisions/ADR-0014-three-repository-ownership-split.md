# ADR-0014 — Three repositories, three owners, one human authority

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Milestone 2 spans three different jobs: producing work, evaluating work, and
holding the ground truth that evaluation is measured against. Putting any two of
them in the same repository makes the third meaningless.

This is not a hypothetical concern here. Task 2A's own security review found that
the party producing the evidence was also the party grading it. That finding is
why `app/evidence/bundle.py` refuses to write `verified: true` in anything it
authors, and why `docs/verification-baseline.md` already states that an
independent verifier holds its own holdouts and mutants which deliberately do not
exist in this repository — "building them here would make the verification
circular, which is the failure mode the whole lab exists to avoid."

The frozen statement of who owns what is `docs/END-STATE-CONTRACT.md`. This ADR
records the reasoning behind it.

## Decision

Three repositories with disjoint ownership, plus a human who is the only party
that can accept anything.

| Repository | Owns | Never receives |
|---|---|---|
| **Agent-workbench** | The real JobSpec and its format; the coding agent's isolated execution; worktree, container and session lifecycle; *visible* tests, initial and final results; candidate artifacts; the versioned evidence bundle; attempt lineage, retries, redaction, provenance and operational failures | Private verifier tests, oracle information, holdouts, mutation suites, thresholds, private reports |
| **Eval-lab** | The public evidence-intake schema; validation of schema version, required fields, hashes, provenance, JobSpec correspondence and artifact completeness; rejection of incomplete, inconsistent, malformed or tampered evidence; public deterministic checks; versioned calibrated rubric scorers; the controlled provider boundary; the narrow verifier-invocation protocol; the deterministic decision policy; the four outcomes | Anything in the verifier repository |
| **Eval-lab-verifier** | Hidden tests, hard-gold references, protected holdouts, private mutations, evaluator mutation suites, private oracle logic, private threshold material, detailed private reports | — it returns only a minimal versioned result (ADR-0016) |
| **A human** | Accepting work; authorising repository writes; approving deployment; production release; changing security boundaries; changing frozen contracts; accepting risk | — |

Two consequences of that table are rules rather than implications:

1. **Agent-workbench reviewer output is untrusted evidence, never an acceptance
   decision.** A reviewer's "this looks correct" has exactly the standing of a
   model completion: recorded, and with no authority over control flow
   (ADR-0018, ADR-0019).
2. **Eval-lab must never automatically merge, deploy, or declare production
   readiness.** No outcome it can emit authorises any of those. Its only positive
   outcome is `accepted_for_review`, which means a human should look.

## Why the verifier must be a repository and not a directory

This is the load-bearing argument, and it is about **read** access, not write
access.

A system that can see its own hidden tests is measuring itself. That failure does
not require anyone to cheat. It requires only that the hidden tests are reachable
from a process that is also producing or evaluating candidates — and the
implementation side here is a coding agent with a shell. A directory exclusion is
a rule about intent, enforced against something that does not have intent.

This repository already knows how thin that boundary is. Threat model T-1 (solver
reaches the answer key) is mitigated with an **allowlist**,
`app/domain/fixtures.py::solver_visible_paths()`, precisely because "the failure
mode of a denylist is that a new secret file leaks by default". And T-1's own
stated residual is the problem in one sentence: "a solver role executing
arbitrary code inside the working copy could walk the filesystem", bounded only
by T-4, which is *accepted, mitigated-not-closed* because isolation here is
process-level rather than kernel-level (ADR-0007).

An allowlist plus process isolation is an adequate answer for a fixture we wrote
ourselves. It is not an adequate answer for the one artifact whose secrecy is the
sole reason any number this lab produces is worth reading. Physical separation
into a repository nobody on the implementation side can clone is the only control
that survives an agent with filesystem access.

## Alternatives rejected

- **One repository, hidden tests in an excluded directory.** Defeated by read
  access, by `git grep`, by a new file the allowlist has not been taught about,
  and by T-1's own residual. The repository already argues this case against
  itself.
- **Two repositories, Agent-workbench folded into Eval-lab.** The producer would
  grade its own output. That is the exact Task 2A finding, repeated with a nicer
  directory layout.
- **The verifier as a private branch, a submodule, or a private package
  dependency.** All three grant read access to whoever can build. A submodule is
  a directory with extra steps.
- **A trusted debug mode in Eval-lab that reads verifier internals when a
  disagreement needs explaining.** A path that reads hidden tests is the leak;
  being rare only makes it unaudited. The debugging cost is accepted instead
  (ADR-0016).
- **Auto-merge when every gate passes, with the human as a notified observer.**
  Every gate passing is exactly what `accepted_for_review` means, and that is
  deliberately not a claim of correctness. Making it authorise a write converts a
  measurement into a decision.

## Consequences

- **Coordination cost becomes structural.** Any change to a shared shape is a
  three-party negotiation with a version attached (ADR-0015). That is slower than
  editing a schema in place, and the slowness is the point.
- **Eval-lab cannot explain a verifier disagreement.** It receives a minimal
  result and can report it; it cannot inspect the reasoning. The detailed private
  report exists and is a human's to read.
- **Nothing here is enforced cryptographically.** The split is repository access
  control plus a protocol. A human holding access to two of the three
  repositories can carry information across and nothing would detect it. This is
  an organisational boundary described honestly, not a technical guarantee.
- **The verifier's own correctness is not established.** Nothing attests that the
  hidden tests are right or that the private oracle is right. If the verifier is
  wrong, Eval-lab has no instrument that would notice — by construction, because
  the instrument that would notice is the one it is forbidden to have.
- **Enforced in code today:** `_reject_self_attestation` in
  `app/evidence/bundle.py` refuses to author `verified`, `verdict`, `passed`,
  `approved`, `certified` or `production_ready`, covered by
  `tests/unit/test_evidence_bundle_export.py`;
  `tests/acceptance/test_no_merge_capability.py` asserts no merge or deploy path
  exists; `tests/unit/test_outcome_vocabulary.py` keeps `approved`, `correct`,
  `safe` and `production_ready` out of the outcome vocabulary. The
  three-repository split itself is enforced by repository access, which no test
  in this repository can assert.
