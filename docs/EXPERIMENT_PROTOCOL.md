# Experiment Protocol

## Objective

Make every experiment independently auditable and reproducible.

## Directory

```
experiments/EXP-YYYYMMDD-NNN-short-name/
  README.md
  experiment.yaml
  results.json
  report.md
  artifacts/
```

During planning, `results.json` and `report.md` may be absent. Once status is `completed`, they are required.

## Required manifest fields

```yaml
id:
status:
hypothesis:
created_at:
code_commit:
seed:
context_limit:
dataset:
  name:
  version:
  fingerprint:
  split_policy:
judge:
  provider:
  model:
  adapter_version:
  prompt_version:
rubric:
  version:
gold:
  provenance_policy:
calibration:
  method:
  split:
metrics:
  - accuracy
  - brier
  - ece
artifacts:
notes:
```

## Pre-registration rule

Before running the final test split, commit:

- hypothesis
- metrics
- primary comparison
- split policy
- calibration method
- exclusion rules
- stopping rule if applicable

After test execution, changes require a new experiment ID.

## Data rule

All derived examples preserve `source_problem_id`. No family of variants may cross splits.

## Gold hierarchy

Preferred:

1. executable/deterministic verifier
2. trusted benchmark answer key
3. human expert adjudication
4. consensus/weak supervision, explicitly marked as non-objective

Model judgments alone are never silently upgraded to levels 1–3.

## Prompt/rubric variants

Changing prompt wording or rubric wording creates a new experiment or an explicitly declared within-experiment arm.

## Provider failures

Report provider errors separately. Do not count timeouts or malformed responses as ordinary wrong answers unless the experiment explicitly studies reliability.

## Completion

An experiment is completed only when:

- manifest is frozen
- raw normalized predictions are retained or fingerprinted
- results JSON exists
- report states limitations
- task file links the experiment
