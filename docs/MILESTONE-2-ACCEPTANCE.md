# Milestone 2 acceptance — FROZEN

**Contract version 1.0.0. Frozen 2026-08-01.**

Milestone 2 is *Durable Evidence Evaluation Pipeline*. It is accepted when every
demonstration below is automated and passing, and a human approves the milestone.
Not before, and not by partial credit.

Baseline commits: merged CKFF connectivity base `a4001ef4`, Task 2B scaffold
`0588f484`.

## The terminal demonstration

```
Agent-workbench-compatible evidence fixture or real evidence bundle
  → durable Eval-lab Temporal workflow
  → evidence intake and schema validation
  → hash and JobSpec correspondence verification
  → isolated public deterministic checks
  → versioned rubric-scoring boundary
  → optional controlled CKFF scorer invocation
  → protected verifier request boundary
  → minimal verifier attestation returned
  → deterministic Eval-lab decision policy
  → versioned evaluation report and evidence manifest
  → human review required
```

The mandatory public CI run of this uses **deterministic Agent-workbench evidence
fixtures, a deterministic rubric adapter and a deterministic mock verifier**, with
**no paid credentials, no CKFF secret and no private repository access**. The live
CKFF path is separately gated and manual-only.

## Acceptance inventory

Each row is an automated demonstration. `WS` is the owning workstream (see
[`MILESTONE-2-STATUS.md`](MILESTONE-2-STATUS.md)).

### A. Evidence intake

| # | Demonstration | WS |
|---|---|---|
| A1 | Valid Agent-workbench-compatible evidence is accepted into evaluation | 3 |
| A2 | Tampered evidence is rejected | 3 |
| A3 | Wrong JobSpec digest is rejected | 3 |
| A4 | Wrong artifact digest is rejected | 3 |
| A5 | Incomplete evidence is rejected | 3 |
| A6 | Unsupported protocol version is rejected — **not** reinterpreted | 3 |
| A7 | Missing initial visible-test result is rejected | 3 |
| A8 | Missing final visible-test result is rejected | 3 |
| A9 | Unexpected extra artifact is rejected | 3 |
| A10 | A valid bundle whose attempts all failed is **accepted as evidence** | 3 |

### B. Containment of untrusted input

| # | Demonstration | WS |
|---|---|---|
| B1 | Hostile filenames are contained | 3 |
| B2 | Symlink escape is contained | 3 |
| B3 | Path traversal is contained | 3 |
| B4 | Hostile archives are contained (entry count, depth, expansion ratio) | 3 |
| B5 | Oversized inputs are contained | 3 |
| B6 | Hostile reviewer and model output does not steer Eval-lab control flow | 3, 4 |
| B7 | Temporary workspace is cleaned up on **every** terminal path | 3 |
| B8 | Intake diagnostics are redacted | 3 |

### C. Public evaluation

| # | Demonstration | WS |
|---|---|---|
| C1 | Deterministic public checks produce reproducible results | 4 |
| C2 | Scorer version, prompt version, configuration and model resolution are recorded | 4, 5 |
| C3 | Rubric scorer output cannot choose control flow or bypass deterministic policy | 4 |
| C4 | Abstention conditions are reachable and produce `abstained` | 4 |

### D. Durability

| # | Demonstration | WS |
|---|---|---|
| D1 | Worker termination followed by workflow resumption | 2 |
| D2 | Initiating client disconnection does not cancel durable evaluation | 2 |
| D3 | Cancellation of an active evaluation | 2 |
| D4 | Timeout enforcement (workflow and activity) | 2 |
| D5 | Evidence and reports survive worker restart | 2 |
| D6 | **No duplicate attempt** after Temporal resumption | 2 |
| D7 | Durable approval wait — a human approval is a signal, not a poll | 2 |
| D8 | Infrastructure failure is classified as such, never as a rejection | 2 |

### E. Verifier boundary

| # | Demonstration | WS |
|---|---|---|
| E1 | The boundary receives only approved candidate information | 6 |
| E2 | A verifier result is rejected when its digest/run binding does not match | 6 |
| E3 | A replayed or duplicate attestation is refused | 6 |
| E4 | Private verifier details never enter logs or artifacts | 6 |
| E5 | Verifier timeout produces `infrastructure_failure` | 6 |

### F. Outcome discipline

| # | Demonstration | WS |
|---|---|---|
| F1 | Exactly the four supported terminal outcomes are emitted, and no others | 4, 7 |
| F2 | Human review remains required | 7 |
| F3 | No automatic merge | 7 |
| F4 | No automatic deployment | 7 |
| F5 | No claim of correctness or production safety appears in any report | 4, 7 |

### G. Regression

| # | Demonstration | WS |
|---|---|---|
| G1 | All existing Phase 1 tests remain green | 7 |
| G2 | All Task 2A tests remain green, and the Task 2A baseline stays frozen | 7 |
| G3 | All PR #1 tests remain green (promptfoo gate, redirect refusal) | 7 |
| G4 | All Task 2B scaffold tests remain green, and it stays blocked | 7 |

## Live CKFF gate

Live execution stays blocked until a **sanitized infrastructure artifact**
confirms every one of:

- evaluation URL is exactly `https://litellm-eval-production.up.railway.app`;
- current deployment/config identifier;
- current validator source version;
- all static validator checks pass;
- live `__canary_invalid` **fails** rather than returning 200 or falling back;
- zero SDK/client retries;
- zero router retries;
- exactly one route per alias;
- no fallback;
- no cooldown;
- no request queue;
- no silent parameter dropping;
- current ordered evaluation alias inventory;
- image-only, test and canary aliases identified;
- `CKFF_API_KEY` is valid for the evaluation service and is **not** the production
  master/admin login credential.

**Credential values are never revealed, printed, compared, requested or rotated as
part of this milestone.** The classification above is a statement about which key
was issued, established by whoever issued it — not by inspecting a value.

### The Luna canary

- exactly one `gpt-5.6-luna` request;
- connectivity evidence only;
- **never** benchmark evidence;
- **cannot unblock or validate the full benchmark by itself** — a single clean
  request looks identical on a zero-retry gateway and on a five-retry one;
- must not run until the validator artifact, deployment identifier, endpoint and
  credential classification are confirmed.

### The full benchmark

- requires one **frozen ordered evaluation-service alias snapshot**;
- records its SHA-256, retrieval timestamp, source, method, deployment/config
  identifier, exclusions and classifications;
- **cannot** accept an arbitrary model list entered at dispatch time;
- **cannot** use the production gateway;
- **cannot** bypass snapshot membership;
- runs one model at a time;
- records failures, rate limits, timeouts and unavailable models **as results**;
- performs no silent retry, rerun, fallback, substitution or skipping.

## Not accepted as evidence

- A green public CI run is not evidence about any model. It exercises fixtures and
  mocks.
- A passing mock verifier is not a verification. It proves the boundary, not the
  verdict.
- A clean canary is not a retry-contract proof.
- `accepted_for_review` is not approval, correctness, safety or production
  readiness. It means a human should look.

## Changing this document

Same policy as the end-state contract: written ADR, impact analysis across
Agent-workbench / Eval-lab / verifier boundary / fixtures / existing evidence,
changed acceptance tests, protocol-version analysis, explicit coordinator
approval. An acceptance item is not removed because it turned out to be hard.
