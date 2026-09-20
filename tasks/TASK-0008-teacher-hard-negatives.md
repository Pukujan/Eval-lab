# TASK-0008 — Verified Teacher-Assisted Hard Negatives

- Status: active
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

- [ ] YOLO-Auto Qwen3.8 Flash actively used
- [ ] SuperGrok actively used if TASK-0007 integration succeeded
- [ ] Luna audit completed
- [ ] Sol hardest-case audit completed
- [ ] every accepted objective example independently re-verified
- [ ] rejected unverifiable items excluded from objective corpus
- [ ] source-family split discipline preserved
- [ ] full local merge gate passes

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
