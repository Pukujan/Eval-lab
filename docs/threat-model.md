# Threat model

Scope: the reliability walking skeleton — a **local-first** lab that applies
AI-proposed patches to a fixture repository and decides whether to accept them for
human review. Single trust domain, single operator, no multi-tenancy.

The point of writing this down is to be precise about which boundaries are real and
which are conventions, because the project's whole claim is about not overstating
what has been established.

## Assets

| # | Asset | Why it matters |
|---|---|---|
| A-1 | Real vendor/model identity mapping | Blinding is void if it leaks; comparison results become biased |
| A-2 | Hidden acceptance tests | A solver that sees them can target them instead of fixing the bug |
| A-3 | The known-good reference patch | Same — it is the answer key |
| A-4 | Provider credentials (optional live path) | Ordinary secret |
| A-5 | Audit records, traces, reliability decisions | The evidence base; worthless if forgeable |
| A-6 | The host filesystem and network | Patch/test execution is code execution |

## Trust boundaries

```
operator shell
  └── application process ── HTTP ──> LiteLLM Proxy ──> mock provider (in-proc)
        │                                          └──> live providers (opt-in)
        ├── OTLP ──> Phoenix (separate process/container, own venv)
        ├── gRPC ──> Temporal dev server (separate container)
        ├── privileged.db   [capability-gated, separate file]   ← A-1
        ├── audit.db        [agent-accessible]                  ← A-5
        └── subprocess ──> fixture working copy (temp dir)      ← A-6
```

## Threats

### T-1 — Solver reaches the answer key (A-2, A-3) · **Mitigated**

The known-good patch and hidden tests must never be inside a solver's reachable
context.

- `fixtures/duplicate-job-processing/reference/` and `tests_hidden/` are excluded
  from every path handed to a solver role.
- `app/domain/fixtures.py::solver_visible_paths()` is an **allowlist**, not a
  denylist. New files are invisible until explicitly published — the failure mode
  of a denylist is that a new secret file leaks by default.
- Both directories are in the prohibited-file manifest, so touching them fails the
  patch outright.
- `tests/acceptance/test_solver_isolation.py` asserts the reference patch body and
  hidden-test content appear in no solver-visible surface.

**Residual:** a solver role executing arbitrary code inside the working copy could
walk the filesystem. Bounded by T-4.

### T-2 — Model identity leak (A-1) · **Mitigated, not closed**

- Separate database files; the mapping table is absent from `audit.db`.
- `PrivilegedIdentityStore` requires an explicit `PrivilegedAccess` capability that
  workflow code cannot construct.
- `assert_blinded()` scans outbound prompts and span attributes for vendor tokens
  and raises `IdentityLeakError` before egress.

**Residual (accepted):** this is a code-structure boundary inside one OS user. Code
with filesystem access can open `privileged.db`. A real boundary needs a separate
uid or an RPC; deferred to Task 2. Stated in ADR-0008 rather than papered over.

### T-3 — Patch escapes the working copy (A-6) · **Mitigated**

- Patches apply only to a fresh `mkdtemp()` copy; the pristine fixture is read-only
  in practice and never mutated.
- Path confinement rejects absolute paths, `..` traversal, and symlinks resolving
  outside the root — checked after `realpath`, before any write.
- The prohibited-file gate rejects changes to tests, reference, or CI config.

### T-4 — Hostile code executes during build/test (A-6) · **Accepted, mitigated-not-closed**

Running the fixture's tests is arbitrary code execution by construction.

- Subprocess with explicit `cwd`, hard timeout, and an **environment allowlist**
  (no inherited secrets — provider keys are not in the child env).
- Inspect AI's Docker sandbox is supported (`INSPECT_SANDBOX=docker`) and is the
  strongest available boundary.

**Residual (accepted):** in the sandbox this was built in, container pulls are
denied by egress policy, so what was actually exercised is **process-level, not
kernel-level, isolation**. Acceptable because the fixture is a repository we wrote;
**not** acceptable for third-party patches. See ADR-0007.

### T-5 — Credential leakage into traces or logs (A-4) · **Mitigated**

- `.env` is gitignored; only `.env.example` is committed, with no real values.
- `app/telemetry/redaction.py` scrubs a key-name denylist (`*_KEY`, `*_TOKEN`,
  `*_SECRET`, `authorization`, `api_key`) plus value-shaped patterns (`sk-…`)
  from every span attribute before export.
- Prompts and responses are recorded as **content hashes plus lengths**, not raw
  text, so a prompt carrying a pasted secret cannot land in the trace store.
- The mock path needs no credentials at all, so CI holds none.

### T-6 — Unauthorised write to an external repository (A-6) · **Mitigated by omission**

The brief forbids merging, deploying, or modifying external repositories.

- The application imports no VCS-write client. There is no push, no merge, no PR
  creation anywhere in `app/`.
- The only positive outcome is `accepted_for_review` — a **recommendation**, not an
  action.
- `tests/acceptance/test_no_merge_capability.py` greps the application tree for
  `git push`, `merge_pull_request`, and similar, and fails if any appears.

### T-7 — Forged or missing evidence (A-5) · **Mitigated**

- The `required_artifacts_present` gate rejects a run whose spans or audit rows are
  missing — a run that loses its evidence cannot be accepted.
- Evidence records are content-addressed (`sha256` over the canonical payload) and
  the audit store is append-only (no `UPDATE`/`DELETE` in the writer).

**Residual:** append-only is enforced in application code, not by the engine. A
process with direct SQLite access can rewrite history. Same trust domain as T-2.

### T-8 — Tool misuse before diagnosis · **Mitigated**

Editing before evidence exists is exactly the failure the lab studies.

- `app/tools/broker.py` resolves tools **from the workflow state**. Editing and
  patch-application tools are absent from the returned toolset until the state
  reaches `implementation`; requesting one earlier raises `ToolNotAvailableError`.
- Enforcement is on *acquisition*, not on a prompt instruction. A model cannot be
  talked out of a tool it was never handed.
- `tests/acceptance/test_tool_gating.py` asserts unavailability across every
  pre-implementation state.

## Explicitly out of scope

Multi-tenant isolation, network egress filtering for live providers, supply-chain
verification beyond digest pinning, and DoS/resource-exhaustion defence. Named here
so their absence is a recorded decision rather than an oversight.
