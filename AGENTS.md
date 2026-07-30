# AGENTS.md

Operating rules for any agent — human or model — working in this repository.

## What this repo is

A reliability walking skeleton: one verified vertical slice proving that mature
platforms integrate end to end and that an incorrect AI-generated patch is
deterministically rejected. Read `ARCHITECTURE.md` first, then
`docs/build-vs-integrate.md`.

## Non-negotiables

1. **Never claim calibration, production-readiness, or general reliability.** Not in
   code, comments, docs, commit messages, or reports. The system is uncalibrated and
   says so.
2. **The only positive outcome is `accepted_for_review`.** The strings `approved`,
   `correct`, `safe`, and `production_ready` must not appear as outcome values.
   `tests/unit/test_outcome_vocabulary.py` enforces this.
3. **No model output in any verdict path.** `app/reliability/gates.py` must never
   import a model client. Gates read artifacts — exit codes, counters, path sets,
   set relations — and nothing else.
4. **Never merge, push, deploy, or modify an external repository.** The application
   has no VCS-write capability and must not gain one.
5. **Do not hand solver roles the answer key.** `fixtures/**/reference/` and
   `fixtures/**/tests_hidden/` are off-limits to any solver-visible surface. The
   allowlist in `app/domain/fixtures.py` is an allowlist on purpose.
6. **Pin everything.** Exact versions for Python packages, npm tools, and container
   images (digest-pinned). No `latest`, no floating ranges, no `^`.
7. **Do not reimplement a platform.** Before writing a module, answer: which pinned
   platform already owns this, and what precisely does it fail to do here? If that
   answer is vague, don't write it.

## Before you add a dependency

1. Resolve the exact version from the index.
2. Verify Python compatibility against `requires-python` for the whole set.
3. Add a full row to `docs/dependency-dossier.md`: version, docs consulted,
   capability used, integration surface, known limitation, custom code required, and
   what you are explicitly not reimplementing.
4. If it replaces a required platform, write an ADR documenting a **confirmed
   incompatibility** — preference is not a reason.

## Verifying an API

Documentation domains may be unreachable (see the dossier's "Documentation access"
section). When they are, read the **shipped source of the pinned version** in the
venv. That is a stronger authority than a docs site tracking `main`, because it
describes the artifact you actually pin.

Do not work from memory. A remembered API that has moved produces confident,
wrong code and a debugging session that blames the wrong layer.

## Editing rules by area

| Area | Rule |
|---|---|
| `app/domain/schemas.py` | Every model is versioned (`schema_version`), `extra="forbid"`, `frozen=True`. Sequences are tuples — `frozen` is shallow. |
| `app/domain/states.py` | New states need a transition-table entry and a test. Illegal transitions raise. |
| `app/graphs/investigation.py` | Every node needs `metadata={"execute_in": ...}` — the plugin refuses to default it. Keep the graph bounded: no unbounded loops. |
| `app/workflows/` | Workflow code must be deterministic. No clock, no RNG, no I/O outside activities. |
| `app/reliability/gates.py` | Pure functions of artifacts. No I/O, no model, no network. |
| `app/models/` | No vendor SDK imports. Everything goes through the LiteLLM Proxy. |
| `app/storage/privileged.py` | The only module allowed to open `privileged.db`. |
| `fixtures/` | Changing the fixture invalidates recorded results. Say so in the commit. |

## Testing expectations

- `make test` must pass with **no credentials and no network**.
- New gates need both a passing and a failing case.
- New states need a tool-availability assertion.
- Property tests use Hypothesis; deadlines may be disabled only with a written
  reason (subprocess work is legitimately slow).

## Reporting results

Report what ran and what did not. If a step was skipped because a host was blocked
or a service was unreachable, say that explicitly and name the host — "skipped, not
verified" and "verified passing" must never look alike in a report.

Failures encountered during development belong in the final report too. A clean
narrative that omits the two hours spent on a blocked registry is a less useful
artifact than an honest one.
