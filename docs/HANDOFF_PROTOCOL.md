# Handoff and Checkpoint Protocol

## Purpose

Agents should be able to stop at any moment and allow another agent to resume without reconstructing context from conversation history.

## State hierarchy

### Repository state

`PROJECT.md` contains stable project goals.

### Current program state

`checkpoints/CURRENT.md` contains the single repository-wide current objective and task dependencies.

### Task state

Each `tasks/TASK-XXXX-*.md` contains the complete bounded context for that task.

### Experiment state

Each `experiments/EXP-*/` contains immutable configuration and output for one experiment.

## Task file format

Every task file must contain:

```
ID
status
owner/agent
goal
why
allowed files
dependencies
acceptance criteria
commands
checkpoint log
handoff
```

Statuses:

- queued
- active
- blocked
- review
- done
- abandoned

## Checkpoint log format

Append entries; do not rewrite history.

```
### YYYY-MM-DD HH:MM UTC — <agent>

Completed:
- ...

Evidence:
- command -> result

Decisions:
- ...

Changed:
- paths

Blocked:
- none | ...

Next:
- one atomic next action
```

## Handoff rule

Before another agent takes over, the current agent must ensure:

1. working tree is committed or explicitly documented as dirty;
2. task file contains the last known test results;
3. next action is unambiguous;
4. credentials/manual actions needed are named but never embedded;
5. relevant experiment IDs are linked;
6. `checkpoints/CURRENT.md` is updated if repository-level priority changed.

## Context minimization

A receiving agent should not need more than PROJECT + CURRENT + one task file + one domain design document to begin.

If more context is necessary, the task file must link it explicitly.

## Conflict avoidance

- one writable worktree per task
- do not let two agents edit the same task file concurrently
- shared design changes become their own task
- cross-cutting changes merge before dependent tasks begin
