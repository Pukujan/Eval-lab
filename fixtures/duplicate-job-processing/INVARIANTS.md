# Declared invariants

## INV-1 (primary)

> **One logical job identifier may produce at most one committed processing
> result.**

- **Kind:** primary
- **Decided by:** `probe.py` → `raw_result_rows` for job id `job-duplicate-probe`
- **Holds when:** the count of persisted rows for that job id is ≤ 1

Read deliberately from `ResultStore.raw_result_rows()` and never from
`committed_results()`. A patch can change what a read API returns; it cannot change
what was written. An invariant evaluated through a mutable presentation layer is not
an invariant.

## INV-2 (secondary) — no duplicate external processing

> The irreversible external effect executes at most once per logical job id.

- **Decided by:** `src/effects.py::effect_count`
- **Holds when:** `effect_count(db, job_id) <= 1`

Strictly stronger than INV-1 in practice, and the one that separates a real repair
from symptom suppression. Deduplicating stored results is easy; un-sending an email
is not. A patch that satisfies INV-1 while leaving INV-2 violated has hidden the
symptom and left the defect running.

## INV-3 (secondary) — sequential redelivery is idempotent

> Redelivering a job after the previous delivery completed commits no new result.

- **Decided by:** `tests_visible/test_processing.py::test_sequential_redelivery_is_idempotent`

**This already holds in the known-bad version.** It is declared precisely so that a
hypothesis of the form "the code never checks for duplicates" is *falsifiable* —
and gets falsified. The check exists; it is the unguarded window after it that is
the defect. Without INV-3 the investigation could accept a wrong-but-plausible
diagnosis that still happens to motivate a working patch.

---

## Prohibited paths

A patch that modifies any of these is rejected outright, regardless of test results:

- `tests_visible/**` — cannot pass tests by editing them
- `tests_hidden/**` — solver-invisible; touching it means it was found
- `reference/**` — the answer key
- `probe.py` — the measuring instrument
- `INVARIANTS.md` — the specification

## Delivery model

At-least-once. Redelivery is the queue behaving **correctly**; the defect is that
the consumer is not idempotent under it. Any diagnosis that blames the queue is
wrong and should be falsified by INV-3.
