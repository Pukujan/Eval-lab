# Experiment 1 execution plan — one model, one fixture, one patch

**Status:** Frozen for implementation under Project Contract Amendment 1.  
**Authorized:** 2026-08-01.  
**Execution mode:** Continue automatically phase by phase after required checks pass. Report every phase result. Stop only on a mandatory stop condition.

## Objective

Demonstrate the central missing experiment:

> one live frontier coding model in Agent-workbench → one original model-authored patch → one versioned evidence bundle → Eval-lab evaluation → human review

The first run omits private-verifier execution. The already-frozen verifier envelope remains unchanged and may be exercised later only through its public boundary. This keeps the first experiment focused on model authorship, evidence provenance, and deterministic public evaluation without expanding private-verifier work.

## Frozen fixture

Use the existing Eval-lab duplicate-processing race fixture as the source problem.

Agent-workbench receives only the public problem material needed to work:

- buggy source files;
- public description and invariants appropriate for the JobSpec;
- visible tests;
- build and visible-test commands.

Agent-workbench must not receive or copy:

- `fixtures/duplicate-job-processing/patches/**`;
- hidden tests;
- reference-patch contents;
- verifier tests, holdouts, thresholds, mutations, or reports.

A fixture-origin manifest records the exact Eval-lab source commit and every copied public file digest. Tests fail if a forbidden path or known reference-patch digest appears in Agent-workbench.

## Model selection

Exactly one frontier coding-model alias will be selected from the validated, ordered evaluation-service alias inventory at the live gate.

The plan does not guess the alias before that inventory is evidenced. The live run records:

- exact proxy endpoint;
- requested alias;
- resolved model identifier;
- validator source version and artifact digest;
- evaluation deployment/config identifier;
- zero client retries and redirects;
- one route, no fallback or substitution.

If the requested and resolved identities do not satisfy the frozen selection, the run is an infrastructure failure and no substitute model is tried.

## Protocols

- Agent-workbench JobSpec: its existing versioned schema, extended only through a new explicit version if required for a live model configuration.
- Cross-repository submission: Eval-lab `evidence-intake/1.0.0` exactly.
- Eval-lab outcome: `evallab-outcome/1.0.0` exactly.
- Verifier: omitted from the first live run; no private repository access.

No existing protocol version is silently reinterpreted.

## Phase E1 — freeze and import the public fixture

**Repository:** Agent-workbench.

Deliverables:

- `fixtures/duplicate-job-processing/` public template and JobSpec;
- fixture-origin manifest with source commit and SHA-256 values;
- explicit forbidden-source list covering patches, hidden tests, and reference material;
- visible baseline reproducing duplicate processing;
- no candidate patch content.

Required checks:

- fixture baseline fails the intended visible behavior before editing;
- template can be materialized into an isolated worktree;
- repository search and digest tests prove no forbidden reference-patch or hidden-test content was imported;
- existing Agent-workbench suite remains green.

Automatic advance condition: all checks pass.

## Phase E2 — strict shared-proxy model adapter

**Repository:** Agent-workbench.

Deliverables:

- narrow OpenAI-compatible adapter for the shared LiteLLM proxy;
- no client retry loop;
- redirect refusal;
- bounded request bytes, response bytes, tokens, and timeout;
- requested and resolved model recording;
- no fallback or model substitution;
- redaction before persistence;
- deterministic fake-server tests with no credential or external network.

Required checks:

- one request per attempt;
- invalid or redirected responses fail closed;
- oversized input/output and timeout paths classify as infrastructure failures;
- requested/resolved mismatch fails closed;
- secret-shaped values do not survive in artifacts;
- existing suite remains green.

Automatic advance condition: all checks pass.

## Phase E3 — model-authored patch execution

**Repository:** Agent-workbench.

Deliverables:

- live-agent implementation using a fresh session and isolated worktree;
- model receives JobSpec, permitted source, and visible-test feedback only;
- model cannot read forbidden fixture paths or Eval-lab/private-verifier material;
- model output becomes a candidate-authored patch proposal, never a verdict;
- initial and final visible tests recorded;
- one attempt for the first live experiment; no automatic model rerun;
- complete lineage, provenance, redaction, and cleanup evidence.

Required checks:

- fake model can author a novel patch not present in the fixture library;
- prohibited paths are refused;
- candidate-authored tests are marked untrusted and do not replace declared tests;
- fresh-session and no-conversation-state guarantees remain enforced;
- worktree cleanup passes on success and failure;
- existing suite remains green.

Automatic advance condition: all checks pass.

## Phase E4 — evidence-intake 1.0.0 export

**Repository:** Agent-workbench.

Deliverables:

- deterministic exporter/translator producing `evidence-intake/1.0.0`;
- JobSpec reference by digest, not body;
- complete attempt lineage;
- initial/final visible-test reports;
- candidate patch and required metadata as declared regular files;
- canonical manifest digest;
- artifact hash, byte-size, path, media-type, redaction, and provenance records.

Required checks:

- output validates against Eval-lab's exact released schema fixture copy or pinned schema digest;
- every declared artifact exists and hashes correctly;
- no undeclared entry, symlink, archive, credential, or self-attestation;
- changing any byte makes validation fail;
- existing Agent-workbench suite remains green.

Automatic advance condition: all checks pass.

## Phase E5 — minimal Eval-lab intake and public evaluation

**Repository:** Eval-lab.

Deliverables:

- bounded intake for the versioned bundle;
- schema, manifest, file, JobSpec-reference, count, lineage, and provenance checks;
- isolated public execution against the duplicate-processing fixture;
- deterministic decision policy emitting only the four allowed outcomes;
- infrastructure failures kept separate from patch rejection;
- no private-verifier call in this experiment.

Minimum public gates:

- intake complete and untampered;
- submitted patch applies only to permitted source paths;
- declared visible tests reconcile with their reports;
- build and public deterministic tests execute successfully;
- duplicate-processing probe observes exactly one consequential effect;
- no symptom-suppression or prohibited-path evidence;
- requested/resolved model provenance is complete;
- no model or reviewer text controls the outcome.

Required checks:

- valid fixture bundle can reach `accepted_for_review` only when every deterministic gate passes;
- duct-tape behavior is rejected even if visible tests pass;
- malformed or altered evidence is rejected before execution;
- harness faults become `infrastructure_failure`;
- unsupported or ambiguous cases can abstain;
- historical Task 1 and Task 2A regression checks remain green.

Automatic advance condition: all checks pass.

## Phase E6 — credential-free end-to-end rehearsal

**Repositories:** Agent-workbench and Eval-lab.

Deliverables:

- deterministic fake proxy produces an original patch through the same live-agent path;
- Agent-workbench exports the exact submission format;
- Eval-lab consumes and evaluates it;
- one report links all source commits, digests, fixture identity, model identity, attempts, artifacts, and outcome.

Required checks:

- complete end-to-end run from JobSpec through Eval-lab outcome;
- no real provider, credential, private verifier, merge, or deployment;
- replaying the same recorded fake response yields the same deterministic evaluation evidence;
- all repository suites and contract checks remain green.

Automatic advance condition: all checks pass.

## Phase E7 — live readiness gate and one live run

All offline work continues to this gate without further approval.

Before the one live request, verify every prerequisite from `docs/PROJECT-CONTRACT.md`:

- current sanitized validator artifact;
- exact evaluation deployment/config identifier;
- current validator source version;
- exact ordered evaluation-service alias inventory;
- `__canary_invalid` failure;
- zero client and router retries;
- one route per alias;
- no fallback, cooldown, queue, silent parameter dropping, redirect, or substitution;
- human confirmation that the configured key is the restricted evaluation-service key and not a production master/admin credential, without inspecting its value.

Then run exactly one model attempt against the frozen fixture. No automatic live rerun occurs.

Required result record:

- requested and resolved model;
- request/response metadata within allowed bounds;
- original patch digest and changed paths;
- initial and final visible-test evidence;
- versioned evidence bundle digest;
- Eval-lab outcome and gate results;
- infrastructure or blocker classification when applicable.

If readiness evidence is missing, stop at this gate and report the missing items. Do not weaken the gate or choose a different endpoint/model.

## Phase E8 — completion report and human review

Present one consolidated report containing:

- result of every phase and every required check;
- exact repository commits and PRs;
- fixture provenance and forbidden-content proof;
- model provenance;
- evidence-bundle digest;
- Eval-lab outcome and caveats;
- whether the live run happened or stopped at the readiness gate;
- remaining risks and deferred work.

No automatic merge of the candidate patch into a target product repository and no deployment occur. `accepted_for_review` means only that the human should review it.

## Explicit non-goals

- no eight-model rollout;
- no debate, voting, tournament, or model-controlled verdict;
- no new fixture or benchmark category;
- no calibration, leaderboard, dashboard, or generalized operations UI;
- no second provider adapter;
- no general LiteLLM infrastructure redesign;
- no private-verifier expansion or internal access;
- no automatic live retry, candidate merge, deployment, or production-readiness claim.
