# TASK-0008 — Verified Teacher-Assisted Hard Negatives

- Status: ready-for-review
- Owner: Luna/local agent
- Priority: P0
- GitHub issue: #13
- Depends on: TASK-0007
- Branch: task/TASK-0008-teacher-hard-negatives

## Goal

Use the user's available subscriptions/models to generate high-information training examples while preserving objective truth.

## Inputs

- TASK-0007 access/model census
- frozen objective source problems
- verifier/answer-key infrastructure

## Teacher utilization

- YOLO-Auto `qwen3.8-flash`: bulk structured generation, rubric decomposition, concise critique, paraphrases.
- SuperGrok: adversarial generation and failure-cluster analysis.
- Luna: larger audit/triage batches.
- Sol: hardest disagreement/research-audit subset.
- selected OpenCode free models: diversity generation/independent critique.

## Objective re-verification

No generated record enters objective training data until independently verified by deterministic verifier, answer key, structured constraint, or executable test.

Teacher identity is never stored as objective gold provenance.

## Outputs

- teacher request manifests
- teacher metadata
- verified hard-negative corpus
- rejected-generation log
- failure-mode taxonomy
- rubric-paraphrase set
- teacher disagreement summary

## Acceptance criteria

- [x] YOLO-Auto Qwen3.8 Flash actively used
- [x] SuperGrok actively used if TASK-0007 integration succeeded
- [x] Luna audit completed
- [x] Sol hardest-case audit completed
- [x] every accepted objective example independently re-verified
- [x] rejected unverifiable items excluded from objective corpus
- [x] source-family split discipline preserved
- [x] full local merge gate passes

## Validation

Sample accepted/rejected examples from every teacher path and assert independent verification evidence for every accepted objective record.

## Stop conditions

Stop a generation family when objective re-verification cannot reliably establish intended truth.

## Checkpoint log

Append evidence here.

### 2026-09-20 — TASK-0008 start and pre-registration

Created dedicated worktree D:\\claude\\eval-lab-TASK-0008 on branch task/TASK-0008-teacher-hard-negatives from accepted main 00baf7c7bb5c8b237f1b4f3f699e61dc74ad4b68. Read PROJECT.md, AGENTS.md, checkpoints/CURRENT.md, this task file, docs/EXPERIMENT_PROTOCOL.md, docs/TDD.md, and docs/ACCESS_MODEL_MATRIX.md.

The synthetic fixture contains 24 source families across arithmetic, multiple_choice, structured, and code_output: 11 train, 7 dev, 2 calibration, and 4 test. The generation corpus will use the 20 non-test sources and preserve each source split. The ignored task .env contains only the YOLO/OpenCode aliases needed locally; secret values are not printed or committed.

Pre-registration: experiments/EXP-20260920-004-teacher-hard-negatives/README.md and experiment.yaml freeze the hypothesis, source fingerprint, split exclusion, verifier acceptance rule, provider order, artifacts, and stopping conditions before teacher generation.

Next atomic action: implement the bounded structured-teacher runner, verifier routing, rejection taxonomy, and audit metadata without admitting model output as objective gold.

### 2026-09-20 — EXP-004 bounded generation checkpoint

The first preregistered run generated 20 non-test source families with YOLO-Auto qwen3.8-flash. It produced 18 candidates independently rejected by deterministic verifiers and 2 rejected generations (one structured parse failure and one verifier-correct proposal). Luna completed its 10-record audit batch. Sol returned an incomplete batch, so its result is preserved as parse_error in EXP-20260920-004 and is not treated as completed audit evidence.

Decision: create the append-only follow-up EXP-20260920-005 with the same source/prompt contract and one-record Sol audit requests. No EXP-004 result is overwritten.

Next atomic action: commit EXP-004 evidence and EXP-005 pre-registration, then rerun the bounded generation with complete Luna/Sol audit coverage.

## Handoff

TASK-0009 trains controlled student ablations on the verified corpus.


### 2026-09-20 — EXP-006 audit protocol follow-up

The first EXP-004 run was preserved with 18 verified hard negatives and a completed Luna audit. A follow-up attempt using one-record Sol requests still returned an incomplete batch, so those uncommitted outputs were discarded rather than presented as complete. EXP-20260920-006 now freezes an explicit object-shaped single-record Sol request contract before the next run.

Next atomic action: commit the EXP-006 pre-registration and run the final append-only teacher/audit experiment.

### 2026-09-20 — EXP-007 final teacher and audit run

Final artifacts are in experiments/EXP-20260920-007-teacher-hard-negatives. YOLO-Auto qwen3.8-flash attempted all 20 non-test synthetic source families; 5 candidates were accepted after independent verifier rejection, 2 were rejected as verifier-correct or malformed, and 11 provider timeouts were retained as rejected execution states. The accepted corpus contains arithmetic and code-output hard negatives with train, dev, and calibration source splits; no test source entered the corpus.

Luna completed 10/10 audit records through opencode/gpt-5.6-luna. Sol completed 10/10 hardest-case records through opencode/gpt-5.6-sol using one-record requests. SuperGrok remains unavailable/provider-blocked from TASK-0007, so no substitute path was used.

Files changed: scripts/generate_hard_negatives.py, tests/test_hard_negatives.py, experiments/EXP-20260920-004-teacher-hard-negatives/ (initial append-only run), experiments/EXP-20260920-007-teacher-hard-negatives/ (final run), and this task log.

Decisions: accept only candidates with deterministic verifier evidence showing incorrectness; preserve teacher output as weak supervision metadata; exclude test sources and all verifier-correct, malformed, or timed-out proposals; retain both audit batches and explicit provider statuses.

Blockers: provider slowdown caused 11 YOLO timeouts in the final run, reducing accepted coverage to 5; this is recorded and does not invalidate the verified examples. SuperGrok remains blocked by the TASK-0007 timeout. GitHub Actions remains blocked by the external account budget/no-runner condition.

Next atomic action: run the full repository contract, Ruff, and pytest gates, commit the final EXP-007 artifacts and checkpoint, push the branch, and open the review PR.


### 2026-09-20 — EXP-007 final audit protocol

The EXP-006 attempt still received an empty or incomplete Sol object under the first structured prompt. A direct single-record probe succeeded when the expected JSON object was included verbatim with the case context. EXP-20260920-007 freezes that exact prompt shape and one-record request policy before the final run; no EXP-006 outputs are retained.

Next atomic action: commit the EXP-007 pre-registration and run the final append-only teacher/audit experiment.


### 2026-09-20 — TASK-0008 review handoff

TASK-0008 is locally complete. Final experiment EXP-20260920-007 records 5 verified hard negatives, 10 Luna audits, 10 Sol audits, explicit rejected generation reasons, and SuperGrok unavailable status. Local gate: contract OK, Ruff clean, 60 passed in 1.60s.

Next atomic action: push the task branch, open the review PR, and update this log with its URL before merge.
