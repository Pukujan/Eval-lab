# TASK-0008 — Verified Teacher-Assisted Hard Negatives

- Status: queued
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

## Handoff

TASK-0009 trains controlled student ablations on the verified corpus.
