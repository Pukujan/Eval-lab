# Project contract — authoritative roadmap

**Status:** proposed governance reset. This file becomes the authoritative project
roadmap when this pull request is merged.

**Initial version:** 2026-08-01.

This document controls phase, scope and sequencing. It does not replace frozen
technical contracts or recorded historical evidence. When roadmap language in an
older planning or status document conflicts with this file, this file controls what
work may start next.

## Authority and precedence

The documents have different jobs:

1. This file controls the current objective, phase, next experiment, deferred work
   and phase-change process.
2. `docs/END-STATE-CONTRACT.md` and the versioned schemas control the frozen public
   repository and protocol boundaries.
3. `docs/acceptance-tests.md` preserves the durable Task 1 acceptance contract.
4. `docs/verification-baseline.md` and
   `verification/task-2a-baseline.json` preserve the frozen Task 2A result.
5. `docs/MILESTONE-2-ACCEPTANCE.md` defines the broader Milestone 2 design target,
   but does not itself authorize all listed workstreams to start.
6. `docs/MILESTONE-2-STATUS.md` records implementation status under this roadmap.
7. `docs/implementation-plan.md` is the historical Task 1 S0–S16 plan, not the
   roadmap for later phases.

A chat instruction, agent report, branch name or commit message does not amend this
contract.

## Original objective

The project tests whether several frontier coding models, assigned different roles
and compared through executable evidence, can improve reliability on long-running
coding tasks.

The intended eventual flow is:

> coding task → independent investigation → competing diagnoses → adversarial
> review → model-authored patches → executable checks → protected verification →
> human review

Model opinions, reviewer prose, rankings and voting never directly decide
correctness. Tests, invariants, provenance, versioned evidence and deterministic
gates control the Eval-lab outcome. A human remains the final authority.

## Historical baselines

These are frozen demonstrations. Later work must preserve their stated limits.

### Task 1 — reliability walking skeleton

- Frozen commit: `8d1d416de94b398fb05d91b8e3090a7cb36ebdcf`.
- One duplicate-processing race fixture.
- A duct-tape candidate passed visible tests but still triggered the external
  effect twice.
- A known-good atomic-claim candidate triggered the effect once.
- Deterministic gates rejected the duct-tape candidate.
- `accepted_for_review` was and remains the strongest positive outcome.
- No automatic merge, deployment, production-readiness claim or model-controlled
  verdict.
- Patch bodies were fixture candidates. No real model authored original code.

The durable Task 1 acceptance contract remains in `docs/acceptance-tests.md`.

### Task 2A — durable execution

- Frozen commit: `a1017b24de9738dc576da3ded2d2d82d23bef47c`.
- Frozen GitHub Actions run: `30580082420`.
- Machine-readable baseline: 15 of 15 demonstrated criteria.
- Demonstrated real Temporal execution, worker-loss recovery, retries, timeout
  handling, replay checking, Phoenix evidence, Compose persistence and separate
  infrastructure-failure classification.
- Patch bodies still came from the fixture candidate library.
- Models were deterministic mocks; no model wrote a patch and no live provider was
  contacted.

The precise claims and limitations are frozen in
`docs/verification-baseline.md` and `verification/task-2a-baseline.json`.

### Public evidence exporter

- Commit: `89e43c9d267d4f42fa90a32adc77e80ffc8d4941`.
- Copies, hashes, indexes and validates export completeness.
- Does not independently verify correctness.
- Writes no self-attestation and reaches no verdict.

### Task 2B-0 — CKFF connectivity classification

- Merged connectivity base:
  `a4001ef48079ec8105b702f4750224ef4792d926`.
- Task 2B scaffold:
  `0588f48437fbe1723ed6189787dad404658de2ae`.
- The scaffold remains blocked for live use until every live-request prerequisite
  below is evidenced.

## Permanent ownership boundaries

### Agent-workbench

Agent-workbench produces work. It receives the real JobSpec, runs the coding model
in isolation, owns the worktree/container/session, records initial and final
visible tests, produces the candidate patch and artifacts, emits the evidence
bundle, and records lineage, retries, failures, provenance and redaction.

It never receives private verifier tests, holdouts, mutation suites, private
thresholds, reference answers or private reports.

### Eval-lab

Eval-lab evaluates submitted evidence. It validates schema versions, hashes,
JobSpec correspondence, provenance and completeness; runs deterministic public
checks; invokes controlled rubric scorers; optionally uses models through the
shared proxy; and invokes the verifier only through the narrow public protocol.

It emits exactly:

- `accepted_for_review`
- `rejected`
- `abstained`
- `infrastructure_failure`

Eval-lab does not run the coding agent, automatically merge, deploy or declare
production readiness.

### Eval-lab-verifier

The private verifier exclusively owns hidden tests, hard-gold references,
protected holdouts, private mutations, private evaluator checks, thresholds and
oracle logic. It returns only the minimal digest-bound public attestation.

Eval-lab and Agent-workbench must not access, clone, search, inspect or describe
verifier internals.

### Human

A human is the final authority for repository writes, acceptance, deployment,
security-boundary changes, risk exceptions, contract amendments and phase changes.

## LiteLLM boundary

LiteLLM is a reusable shared model proxy serving multiple projects. Eval-lab is
not a LiteLLM infrastructure repository and must not rebuild general routing,
provider normalization, deployment management or cross-project gateway operations.

Eval-lab and Agent-workbench consume the proxy only through a narrow adapter that
records the exact endpoint, requested and resolved model, uses a restricted
project-appropriate credential, performs no client retries or redirects, permits
no fallback or substitution, and bounds request bytes, tokens, timeout and response
bytes.

Moving the laptop-only LiteLLM validator/operations workflow to a cloud-accessible
location is a separate infrastructure migration. First preserve the source that
actually exists. When it is unavailable, rebuild only the minimum validator and
operations workflow documented by the sanitized material, without expanding proxy
scope.

## Live-request prerequisites

No live CKFF request is authorized until all of the following are evidenced without
reading or exposing credential values:

- current sanitized CKFF validator artifact;
- exact evaluation deployment/config identifier;
- current validator source version;
- exact ordered evaluation-service alias inventory;
- proof that invalid alias `__canary_invalid` fails;
- zero client retries and zero router retries;
- exactly one route per alias;
- no fallback, cooldown, queue or silent parameter dropping;
- human confirmation that `CKFF_API_KEY` is appropriate for the evaluation service
  and is not a production master/admin credential.

Credential values must never be requested, printed, compared, exposed or rotated by
this project.

## Verified repository state at reset

Verified on 2026-08-01 before authoring this reset:

- Repository: `Pukujan/Eval-lab`.
- Default branch: `claude/reliability-walking-skeleton-31b6a2`.
- Default-branch head: `a4001ef48079ec8105b702f4750224ef4792d926`.
- `milestone-2/integration` head:
  `0235b31fd980b21855b11d8633f4b5ca60513573`.
- The integration branch was six commits ahead of the Task 2B scaffold and five
  commits ahead of planning commit
  `7a1358531029d5a6750b9e45977aa3b8e834c054`.
- Workstream 1 artifacts were integrated: ADR-0014 through ADR-0020, four public
  `1.0.0` schemas, three valid fixtures, thirteen hostile fixtures, a fixture
  manifest and contract-fixture tests.
- Only `milestone-2/integration` was visible under remote `milestone-2/*` branches.
- No open pull request was returned by the repository PR audit.
- No Milestone 2 work was merged from the integration branch to the default branch.
- The status record reported no live workflow dispatch and no private-verifier
  access.
- `docs/PROJECT-CONTRACT.md` did not yet exist.
- Workstreams 2 through 7 had not started.

Repository state must be reverified before every phase change. This snapshot is not
a standing claim about later branch or Actions state.

## Current phase

**Phase: governance reset and experiment definition.**

Workstreams 2 through 7 are paused. Workstream 1 contracts remain available as
inputs, but their completion does not authorize broad parallel implementation.
No live CKFF workflow, private-verifier interaction, LiteLLM infrastructure change,
automatic merge or deployment is authorized.

The next permitted work after this governance-only pull request is documentation
and design needed to define the minimum cross-repository path for the central
experiment. Implementation begins only after a human approves that reduced path.

## Exact next product experiment

The next central experiment is:

> one live frontier coding model in Agent-workbench → one original model-authored
> patch → one versioned evidence bundle → Eval-lab evaluation → optional minimal
> verifier attestation → human review

Constraints:

- one existing fixture;
- one model;
- one original model-authored patch;
- no fixture-provided patch contents;
- no Agent-workbench access to hidden tests or a reference patch;
- no eight-model rollout;
- no new benchmark categories;
- no calibration or leaderboards;
- no dashboards;
- no additional private-verifier expansion;
- no automatic merge or deployment.

Milestone 2 implementation may supply only the minimum cross-repository path needed
for this experiment before any broader build-out.

## Required approval packet before implementation

Before code implementation is authorized, present one concise, reviewable proposal
that identifies:

1. the existing fixture and its public JobSpec boundary;
2. the single model alias and the live-request prerequisite evidence;
3. the minimal Agent-workbench output and exact evidence schema version;
4. the minimum Eval-lab intake, public checks and deterministic decision path;
5. whether the first run omits the verifier or uses only the already-frozen minimal
   attestation boundary;
6. the exact repositories, branches and files to change;
7. executable acceptance checks and failure classifications;
8. explicit non-goals and a stop condition after one completed experiment.

A human must approve this packet before implementation branches or workstreams are
started.

## Deferred work

Until the central experiment is completed and reviewed, defer:

- parallel WS2–WS7 rollout;
- multi-model investigation, debate, voting or tournament orchestration;
- new fixtures or benchmark categories;
- calibration, aggregate metrics and leaderboards;
- dashboards and generalized operations UI;
- additional provider adapters;
- private-verifier feature growth;
- general LiteLLM infrastructure or gateway redesign;
- automatic reruns, merging, deployment or production-readiness claims.

Deferred does not mean rejected. It means the work has no authorization in the
current phase.

## Phase-change and amendment rules

A phase changes only through a human-approved amendment to this file. Every
amendment must include:

- date and authorizing human decision;
- verified repository and workflow state;
- evidence that the current phase's exit criteria were met;
- exact newly authorized work;
- exact work that remains deferred;
- affected frozen contracts or protocol versions;
- rollback or stop conditions.

Frozen protocol changes additionally require the ADR and versioning process in
`docs/END-STATE-CONTRACT.md`.

## Phase-drift checklist

Before assigning an agent, opening an implementation branch, dispatching a live
workflow or changing scope, answer all of these:

- Does the work directly support the currently authorized experiment?
- Is it explicitly permitted in the current phase?
- Is the repository owner correct for the work?
- Does it preserve the Agent-workbench/Eval-lab/verifier separation?
- Does it avoid private-verifier access or inference?
- Does it keep general LiteLLM operations outside Eval-lab?
- Are any live-request prerequisites still unresolved?
- Does it avoid model-controlled correctness decisions?
- Does it preserve `accepted_for_review` as the strongest positive outcome?
- Does it avoid automatic merge, deployment or production claims?
- Are executable acceptance checks defined before implementation?
- Has current GitHub state been reverified rather than inferred from a handoff?
- Has a human approved the phase and exact scope?

Any `no`, `unknown` or unresolved item stops the work and returns it to human
review.

## Amendment history

| Version | Date | Change | Authorization |
|---|---|---|---|
| 1 | 2026-08-01 | Establish authoritative roadmap, pause broad Milestone 2 implementation and name the one-model/one-fixture experiment | Proposed in governance-reset draft PR; effective only when merged by a human |
