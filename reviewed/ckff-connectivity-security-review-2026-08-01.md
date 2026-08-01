# Agent 2 — Independent Security Review

**Target:** PR #1 "Add safe CKFF gateway connectivity layer" (Pukujan/Eval-lab)
**Head:** bb9cb6f731378723ba7c7753cf6400b3b2d13c41 (verified)
**Base:** 89e43c9d267d4f42fa90a32adc77e80ffc8d4941 (verified = merge-base)
**Method:** read-only via `git show` / `git diff` / `git grep` against fetched refs.
**Diff size:** 5 files, +329 / -0.

## Compliance statement

- No live CKFF request, no model request, no gateway call of any kind.
- No GitHub Actions workflow triggered or dispatched.
- No repository file created, modified, or deleted. Only file written is this report,
  outside the repo.
- `Pukujan/Eval-lab-verifier` never accessed, cloned, or searched.
- No secret value read, printed, echoed, or searched for. Only secret *names* discussed.
- One outbound network call was made: `git ls-remote --tags https://github.com/actions/checkout`,
  to authoritatively resolve the pinned action SHA (item: unpinned actions). Read-only,
  public repo, unrelated to CKFF.

---

## Numbered items

### 1. Manual-dispatch only — CONFIRMED

`.github/workflows/ckff-connectivity.yml:3-10` — the entire `on:` block is:

```
on:
  workflow_dispatch:
    inputs:
      model: ...
```

No `push`, `pull_request`, `schedule`, `workflow_run`, `repository_dispatch`, or
`issue_comment` key. Verified by reading the whole file (40 lines) and by
`git grep -E "issue_comment|repository_dispatch|pull_request_review"` over the whole
tree — zero hits.

`workflow_dispatch` cannot be invoked by a fork or by an unauthenticated party; it
requires write access to the base repository.

**Verdict: fine. Does not block.**

### 2. No `pull_request_target` anywhere — CONFIRMED

`git grep -n -i "pull_request_target" origin/task-2b/ckff-connectivity` → **zero hits**,
whole tree, not just workflows. The repo contains exactly three workflow files
(`git ls-tree` on `.github/`):

- `.github/workflows/ci.yml` — `on: push / pull_request / workflow_dispatch` (lines 6-10)
- `.github/workflows/durable-stack-verification.yml` — `on: push / pull_request / workflow_dispatch` (lines 14-18)
- `.github/workflows/ckff-connectivity.yml` — `workflow_dispatch` only (lines 3-4)

`workflow_run` also has zero hits as a trigger; the 16 grep matches for that string are
Temporal `workflow_run_id` identifiers in `app/`, `scripts/`, `tests/` — unrelated.

**Verdict: fine. Does not block.**

### 3. Fork-PR access to the secret — CONFIRMED: no path found

Evidence, each leg:

- **Trigger.** The only workflow that references `secrets.CKFF_API_KEY` is
  `ckff-connectivity.yml` (lines 27 and 39), and it is `workflow_dispatch`-only
  (line 4). GitHub does not expose secrets to `pull_request`-triggered runs from a
  fork, and neither `ci.yml` nor `durable-stack-verification.yml` references
  `secrets.CKFF_API_KEY` at all (grep confirms only those two lines in the tree).
- **`pull_request_target` / `workflow_run`.** Absent (item 2).
- **Permissions.** `ckff-connectivity.yml:12-13` sets `permissions: contents: read`
  workflow-wide; no `id-token`, no write scope (item 4).
- **Composite action from an untrusted context.** `.github/actions/ckff-smoke/action.yml`
  holds **no** `secrets.*` reference. It takes `api-key` as an input
  (`action.yml:8-10`, consumed at `action.yml:22`). A fork PR that edits
  `ckff_smoke.py` cannot make anything supply the secret to it, because the only
  supplier is the dispatch-only workflow.
- **Environment protection.** *Not used* — `git grep "^\s*environment:"` over `.github/`
  returns nothing. See Finding B; this is a hardening gap, not a fork-PR hole.

**Verdict: fine — no fork-PR path to the secret. Does not block.**

### 4. Least-privilege token permissions — CONFIRMED, all three workflows

| file | line | value | job-level override |
|---|---|---|---|
| `ckff-connectivity.yml` | 12-13 | `permissions: contents: read` | none |
| `ci.yml` | 20-21 | `permissions: contents: read` | none |
| `durable-stack-verification.yml` | 33-34 | `permissions: contents: read` | none |

No workflow is missing a `permissions:` block, and none grants more than
`contents: read`. `contents: read` is genuinely required by `ckff-connectivity.yml`
because the composite action is referenced locally (`ckff-connectivity.yml:36`) and so
the repo must be checked out (line 21-22). This is the minimum that still works.

**Verdict: fine, correctly minimal. Does not block.**

### 5. Secret printing / leakage — CONFIRMED clean on the primary paths, with two
qualified caveats

Clean:
- No `echo`/`print` of the key. `ckff_smoke.py:79` prints only the `summary` dict built
  at lines 68-78, which contains no credential field.
- No `set -x` anywhere. `ckff-connectivity.yml:29` uses `set -euo pipefail` — `-x` is
  deliberately absent. `action.yml:24` is a bare `python3 "$GITHUB_ACTION_PATH/..."`.
- No `env` dump. (`ci.yml:75` greps `env` but only for provider-key *names*, and it is
  pre-existing, not in this diff.)
- The secret-presence check at `ckff-connectivity.yml:30` uses `test -n "$CKFF_API_KEY"`
  — the value is passed via `env:` (line 27) and referenced as a quoted shell variable,
  never interpolated into the script text and never printed. On failure it prints only
  the literal string at line 31.
- No artifact upload in this workflow at all (no `upload-artifact` step in
  `ckff-connectivity.yml`), so no path writes the key to an artifact.
- No `>> $GITHUB_OUTPUT` / `::set-output` in `action.yml` — no step output carries it.
- Request headers (`ckff_smoke.py:40-44`, which do contain the bearer token) are never
  logged; only the *response* header `x-request-id` is read (line 53).

Caveat 5a — **error body is echoed raw**: `ckff_smoke.py:55-56` reads up to 500 bytes of
the gateway's error response and interpolates it into the exception message, which is
printed to stderr at line 87. GitHub masks the *exact literal* value of a registered
secret in logs, so a verbatim echo of `CKFF_API_KEY` by LiteLLM would be masked — but a
**truncated or transformed** form (LiteLLM auth errors historically include a shortened
`Received API Key=sk-...` form) would **not** be masked, and an *upstream provider* key
surfaced in a proxied error body is not a registered secret and would not be masked at
all. See Finding C (LOW).

Caveat 5b — **traceback analysis**: I checked whether an exception could print headers.
It cannot. `raise SystemExit(1) from exc` (`ckff_smoke.py:88`) does not print a
traceback — CPython handles `SystemExit` with an int code by exiting silently. And for
genuinely uncaught exceptions (see Finding D), CPython tracebacks print source lines
only, never local-variable reprs, so neither `request.headers` nor `api_key` can appear.
No `PYTHONFAULTHANDLER`, rich-traceback, or custom excepthook is configured.

**Verdict: no direct secret printing (fine). One indirect, conditional leak channel
(5a) — LOW, does not block.**

### 6. No master key / no direct provider credential — CONFIRMED for what the code
requires; UNVERIFIABLE for what is actually configured

- `ckff_smoke.py` reads exactly three env vars: `CKFF_BASE_URL`, `CKFF_API_KEY`,
  `CKFF_MODEL` (lines 20-22). No `LITELLM_MASTER_KEY`, no `OPENAI_API_KEY`, no
  `ANTHROPIC_API_KEY`, no provider SDK. One `Authorization: Bearer` header (line 42).
- `action.yml:9` documents "Never pass the master key."
- `.env.example:46-52` adds only `CKFF_BASE_URL` / `CKFF_API_KEY=REDACTED` /
  `CKFF_MODEL`, with a comment at lines 46-47 saying to use a restricted key and never
  `LITELLM_MASTER_KEY`.
- `docs/ckff-gateway-setup.md:31-33` states the master key must never enter a repo or a
  public-repo Actions secret; lines 37-54 mandate one restricted key per project with a
  model allowlist and a budget.

**Explicit non-verification:** whether the *actual value* stored in the `CKFF_API_KEY`
repository secret is a restricted virtual key rather than the master key is a
gateway/GitHub-settings fact that is **not determinable from this diff**, and I did not
(and must not) read it. The only programmatic check is
`ckff_smoke.py:28-29` (`len(api_key) < 16`), which does **not** distinguish a master key
from a virtual key. See Finding G (INFO).

**Verdict: the code neither uses nor requires a master key or any provider credential —
fine. The configured value is unverifiable from the diff. Does not block.**

### 7. Zero client-side retries — CONFIRMED in code; library defaults checked; two
honest qualifications

Verified in code, not prose:
- `ckff_smoke.py:50` is a single `urllib.request.urlopen(...)`. Reading the full 88-line
  file: there is no loop, no `while`, no `for`, no `except ... : retry`, no backoff, no
  recursion. The only `except` clauses (lines 54, 57) raise immediately.
- No `requests`, `httpx`, `urllib3`, or `openai` SDK is imported (lines 1-9 are the
  complete import list: `hashlib, json, os, sys, time, urllib.error, urllib.request`).
  So none of those libraries' retry defaults apply — notably `urllib3.Retry(3)`, which
  `requests` inherits, is **not** in play.
- Library default check, executed locally: `urllib.request.build_opener()` yields
  `[ProxyHandler, UnknownHandler, HTTPHandler, HTTPDefaultErrorHandler,
  HTTPRedirectHandler, FTPHandler, FileHandler, DataHandler, HTTPSHandler,
  HTTPErrorProcessor]`. **No retry handler**, and no auth handler (so no
  challenge-response re-send). `http.client` performs no retries.

Qualification 7a — **redirects are followed, up to 10 extra requests.**
`HTTPRedirectHandler` *is* in the default chain (`max_redirections = 10`,
`max_repeats = 4`). For a POST it follows 301/302/303 (converting to GET). These are not
retries, but the claim "exactly one HTTP round trip" is not guaranteed. This also has a
security consequence — see Finding A (MEDIUM).

Qualification 7b — **connection-level.** `socket.create_connection` iterates every
address returned by `getaddrinfo`, so one logical request can produce multiple TCP
connect attempts across A/AAAA records. Standard, not an HTTP retry, noted for
completeness because it was asked about.

Qualification 7c — **`"client_retry_count": 0` (`ckff_smoke.py:77`) is a hardcoded
literal**, not a measurement. It can never report anything else and therefore proves
nothing. See Finding F (INFO).

Qualification 7d — **server-side retries are out of scope of the client and are not
zero.** `docs/ckff-gateway-setup.md:143-146` honestly states CKFF currently does five
same-model retries and that this is unacceptable for Task 2B evidence until a
zero-retry alias exists. Credit: this is disclosed rather than glossed.

**Verdict: zero client-side retries — CONFIRMED. Does not block.**

### 8. Bounded timeout — CONFIRMED, with a precise caveat

- `ckff_smoke.py:50` — `urlopen(request, timeout=120)`.
- `.github/workflows/ckff-connectivity.yml:19` — `timeout-minutes: 5` on the job.

Caveat: urllib's `timeout` is a **per-socket-operation** timeout, not a total deadline.
A server dribbling bytes resets the 120 s timer on each read, so `response.read()`
(line 51) is not bounded by 120 s in the adversarial case. However the job-level
`timeout-minutes: 5` is a hard ceiling that GitHub enforces regardless, so the overall
answer to "can it hang indefinitely" is **no**.

**Verdict: fine — bounded, and cannot hang indefinitely. Does not block.**

### 9. Only safe metadata emitted — CONFIRMED on the success path

`ckff_smoke.py:68-78` emits exactly: `status`, `requested_model`, `resolved_model`,
`elapsed_seconds`, `prompt_tokens`, `completion_tokens`, `content_sha256`, `request_id`,
`client_retry_count`.

- Model content is hashed, never printed: line 66 assigns `content`, line 75 emits only
  `hashlib.sha256(content.encode("utf-8")).hexdigest()`. `content` appears nowhere else.
- No request headers are emitted. The single response header read is `x-request-id`
  (line 53) — a correlation id, explicitly in the allowed set.
- The prompt is a fixed literal, `"Reply with exactly OK."` (line 33) — no repository
  content, no user data, no file contents. `max_tokens: 8` and `temperature: 0`
  (lines 34-35) bound the response.
- No raw response body is emitted on success; `raw` (line 51) is only `json.loads`'d.

Exception: the **error** path prints up to 500 raw bytes of the gateway response
(lines 55-56). That is raw server output, though for this fixed trivial prompt the
sensitive-content risk is minimal; the credential aspect is Finding C.

**Verdict: fine on the success path; one raw-body echo on the failure path (LOW).
Does not block.**

### 10. No verifier / holdout / mutant material — CONFIRMED

Grepping the complete diff for `holdout|mutant|verifier|secret_key|sk-[A-Za-z0-9]{10,}`
returns exactly two hits, both prose policy statements, no material:

- `.env.example:48` — "does not start Task 2B or grant the model access to the private
  verifier."
- `docs/ckff-gateway-setup.md:138` — "keep the private verifier inaccessible to the
  implementation agent".

No test cases, no mutants, no holdout data, no verifier code, no key-shaped strings.
The whole diff is 5 files and I read every added line of all 5.

**Verdict: fine. Does not block.**

### 11. No live CKFF request without explicit human dispatch — CONFIRMED

- The only invocation of `ckff_smoke.py` in the entire tree is `action.yml:24`, and the
  only reference to that composite action is `ckff-connectivity.yml:36`, in a
  `workflow_dispatch`-only workflow (line 4). Verified by `git grep` for all `uses:`
  refs across `.github/`.
- Merging the PR runs nothing. `ci.yml` and `durable-stack-verification.yml` do not
  reference the action, the script, or `secrets.CKFF_API_KEY`.
- CI cannot even accidentally execute it: `ci.yml:40,43,46,49` scope ruff/mypy/bandit to
  `app evals scripts tests`, and pytest runs explicit paths (`ci.yml:81,84`).
  `.github/actions/` is outside all of them.
- Both other workflows run the deterministic mock model path (`ci.yml:3-4,136`;
  `durable-stack-verification.yml:12,230`).

**Verdict: fine. Does not block.**

---

## Additional adversarial findings

### Finding A — MEDIUM — `Authorization` header is forwarded across redirects, including an HTTPS→HTTP downgrade

**Where:** `ckff_smoke.py:24-25` (scheme check), `:37-46` (headers), `:50` (default opener).

The script validates `base_url.startswith("https://")` at line 24 — but that validates
only the **initial** URL. `urlopen` uses the default opener, which includes
`HTTPRedirectHandler`. I read the CPython source to confirm the two behaviours rather
than assume them:

1. `HTTPRedirectHandler.redirect_request` copies **all** request headers except
   `content-length` / `content-type` into the redirected request. `Authorization` is
   **not** stripped, and it is **not** stripped on a cross-host redirect. (This differs
   from `requests`, which does strip auth on cross-host redirects — a reader who assumes
   `requests` semantics would get this wrong.)
2. `HTTPRedirectHandler.http_error_302` permits redirect targets with scheme
   `http`, `https`, `ftp`, or empty. So a `302 Location: http://attacker/` is followed
   and the bearer token is sent **in cleartext**.
3. For a POST, 301/302/303 are followed (converted to GET), up to `max_redirections=10`.

**Exploitability:** requires control of the gateway response, its DNS, or its TLS path —
e.g. a compromised LiteLLM instance, or a `*.up.railway.app` subdomain takeover if the
Railway project is ever deleted while the URL stays pinned in
`ckff-connectivity.yml:38`, `.env.example:50`, and `docs/ckff-gateway-setup.md:12,61,71,83`.
Not remotely triggerable by an outsider today. It is a genuine defence-in-depth defect
with a two-line fix (build an opener without `HTTPRedirectHandler`, or assert the final
`response.url` host matches the configured host).

**Blocks merge: NO** for this repo as-is. **Recommend fixing before**
`docs/ckff-gateway-setup.md:113-126` invites other repositories to consume the action,
since that multiplies the number of distinct keys exposed to the same defect.

### Finding B — LOW — the secret is a plain repository secret with no environment protection; any dispatchable branch gets it

**Where:** `ckff-connectivity.yml:15-19` (no `environment:` key — confirmed by grep over
all of `.github/`), `:36` (`uses: ./.github/actions/ckff-smoke`).

`workflow_dispatch` lets a maintainer pick **any** branch, and the workflow resolves the
composite action **ref-relatively** (`./`) — so the code that receives the key is
whatever `ckff_smoke.py` says on the dispatched ref, not what was reviewed here. This
is the TOCTOU/local-action question asked about: the answer is that the trust boundary
collapses to "who can push a branch and dispatch", both of which require write access.

That is the standard GitHub model and **not** a fork-PR hole (item 3 stands). But for a
repo with more than one write-access collaborator, or for an automated agent with push
rights, a protected Environment holding `CKFF_API_KEY` with a required reviewer would
make every dispatch — from any branch — need explicit approval. Cheap hardening.

**Blocks merge: NO.** Recommendation.

### Finding C — LOW — gateway error body echoed unmasked (up to 500 bytes)

**Where:** `ckff_smoke.py:55-56`, surfaced at `:87`.

GitHub masks the exact literal value of `CKFF_API_KEY`. It does not mask a truncated or
transformed rendering of it, and it does not mask an upstream **provider** key that
LiteLLM might surface while proxying a 401/403 from the origin. Auth-failure paths are
precisely the ones most likely to echo key material, and they are also the most likely
runs in a first connectivity test. Suggest redacting anything matching `sk-[A-Za-z0-9_-]{8,}`
in `body` before interpolation, or emitting only `exc.code` plus a hash of the body.

**Blocks merge: NO.**

### Finding D — LOW — read-phase exceptions escape both handlers and produce a raw traceback

**Where:** `ckff_smoke.py:51` inside the `with` block; handlers at `:54,57` and `:86`.

`urlopen` wraps connect/request-phase `OSError` into `URLError` (in
`AbstractHTTPHandler.do_open`), but `response.read()` at line 51 runs **after** that
wrapper. A read timeout raises `TimeoutError`, and a truncated response raises
`http.client.IncompleteRead` — neither is a `URLError`, and neither is a `RuntimeError`
or `ValueError`, so both escape line 54, line 57, **and** line 86, producing an
unhandled traceback instead of the intended `CKFF smoke check failed: ...` message.

The exit code is still non-zero, and **no secret leaks** (CPython tracebacks print source
lines only, never local reprs — so `api_key` and `request.headers` cannot appear). This
is a robustness/diagnostics defect, not a disclosure one.

**Blocks merge: NO.**

### Finding E — LOW — the secret's destination is governed by a repository *variable*

**Where:** `ckff-connectivity.yml:38` — `base-url: ${{ vars.CKFF_BASE_URL || 'https://...' }}`,
consumed at `ckff_smoke.py:20,38`.

Repository *variables* are a lower-integrity control than secrets: changing
`CKFF_BASE_URL` to any attacker-controlled HTTPS host passes the only check
(`ckff_smoke.py:24`) and sends the bearer token there on the next dispatch.

**Honest scoping:** changing a repository variable already requires write/admin access,
and someone with that access could equally edit the workflow — so this does **not**
cross a privilege boundary and I am deliberately not inflating it. It is still worth an
explicit host allowlist in `ckff_smoke.py` (assert the parsed host equals the known
gateway host), because that also closes Finding A's redirect target and turns a
misconfiguration into a fast, loud failure.

**Blocks merge: NO.**

### Finding F — INFO — `client_retry_count: 0` is an assertion, not a measurement

`ckff_smoke.py:77` hardcodes the literal `0`. It will read `0` even if a retry somehow
occurred (e.g. the redirect path in Finding A). As *evidence* it is circular. Either
derive it (count actual `urlopen` invocations / redirects observed) or rename it to
something that does not read as a measured value.

**Blocks merge: NO.**

### Finding G — INFO — nothing enforces "restricted virtual key, not master key"

`ckff_smoke.py:28-29` only checks `len(api_key) >= 16`, which both key types satisfy.
The restriction lives entirely in prose (`action.yml:9`, `.env.example:46-47`,
`docs/ckff-gateway-setup.md:31-33`). Not fixable client-side in general, but the model
allowlist + budget on the gateway (`docs:45-51`) is the real control and is documented.
Recorded so the residual risk is explicit rather than assumed away.

**Blocks merge: NO.**

### Finding H — INFO — the new script is excluded from every quality gate

`ci.yml:40,43,46,49` scope `ruff format`, `ruff check`, `mypy`, and `bandit` to
`app evals scripts tests`. `.github/actions/ckff-smoke/ckff_smoke.py` is in none of them,
so the `# noqa: S310` at `ckff_smoke.py:50` suppresses a rule that never runs, and the
file is unlinted, untyped and unscanned. Findings A and D are exactly the class bandit
(B310) and a type checker would have prompted questions about.

**Blocks merge: NO.**

### Finding I — INFO — gateway endpoint is hardcoded in three places

`ckff-connectivity.yml:38`, `.env.example:50`, `docs/ckff-gateway-setup.md:12,61,71,83`
all contain `https://litellm-production-8656.up.railway.app`. The docs explicitly and
correctly call this "public configuration" (`docs:15`), and a URL is not a credential.
If the repository is public this does publish the endpoint for unauthenticated probing
and cost/DoS attempts against Railway — I **could not verify repository visibility** from
the diff or from this environment (`gh` is not installed and I did not want to spend API
calls on it), so I am flagging it conditionally rather than asserting it. The hardcoded
fallback at `ckff-connectivity.yml:38` also means the workflow still runs if the
`CKFF_BASE_URL` variable is deleted — arguably a feature, but it defeats "disable access
by removing the variable" as a kill switch.

**Blocks merge: NO.**

---

## Things I checked adversarially and found genuinely FINE

State these plainly rather than manufacture findings:

- **Script injection via `${{ }}` into `run:`** — **not present, and correctly avoided.**
  `inputs.model` flows `ckff-connectivity.yml:40` → `action.yml:23` **into an `env:`
  block**, and the `run:` at `action.yml:24` is a bare
  `python3 "$GITHUB_ACTION_PATH/ckff_smoke.py"` with no interpolation at all. Values in
  `env:` are passed as environment variables by the runner and are never re-parsed by
  the shell, so a payload like `"; curl evil; #` in the model input cannot execute.
  Same for `secrets.CKFF_API_KEY` (`:27`) and `vars.CKFF_BASE_URL` (`:38`), and
  `$GITHUB_ACTION_PATH` is quoted. This is the correct pattern.
- **Command injection via workflow inputs** — none. The only user-controlled input is
  `model` (`:5-10`), which reaches only a JSON body field (`ckff_smoke.py:32`). JSON is
  serialised with `json.dumps` (line 39), so no injection into the request either.
- **Unpinned third-party actions in the new workflow** — **pinned by full SHA and the
  SHA is legitimate.** `ckff-connectivity.yml:22` uses
  `actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09`; I resolved this against
  the public `actions/checkout` repo and it is exactly `refs/tags/v5.1.0` (and current
  `v5`). This is *better* practice than the pre-existing `ci.yml` /
  `durable-stack-verification.yml`, which use mutable `@v5` / `@v6` / `@v4` tags — a
  pre-existing weakness, out of scope for this PR, worth a separate cleanup.
- **Artifact upload of sensitive paths** — `ckff-connectivity.yml` uploads **nothing**;
  it has no `upload-artifact` step. The pre-existing artifact uploads in the other two
  workflows (`ci.yml:88,165`; `durable-stack-verification.yml:309,317`) are untouched by
  this PR and never see `CKFF_API_KEY`.
- **`.env.example` containing a real value** — no. `.env.example:51` is
  `CKFF_API_KEY=REDACTED`; `:50` and `:52` are a public URL and a model alias.
  `.gitignore:1-2` ignores `.env` with the comment "only `.env.example` is committed".
  Scanned the full diff for `sk-`-shaped strings: zero.
- **TLS verification** — not disabled. No `PYTHONHTTPSVERIFY`, `verify=False`,
  `_create_unverified_context`, or `SSL*` env var anywhere in the diff.
  `HTTPSHandler` with `context=None` uses `ssl.create_default_context` (cert chain +
  hostname verification on).
- **Supply-chain risk of the action being callable by other repos** — the exposure runs
  *outward*, not inward: the action holds no secrets of its own, so a consumer risks
  *their* key if Eval-lab's action is later modified maliciously. The docs handle this
  correctly, instructing consumers to pin to a full commit SHA
  (`docs/ckff-gateway-setup.md:113-126`, "Pin it to the exact merge commit"), with
  `permissions: contents: read` in the sample. That is the right advice.
- **Would the documented rollout advice lead a user to leak a key?** No — the guidance is
  unusually good. `docs:92-98` forbids `NEXT_PUBLIC_` / `VITE_` / `EXPO_PUBLIC_`
  prefixes and mandates a backend-mediated call; `docs:31-33` keeps the master key in
  Railway only; `docs:37-54` mandates one restricted key per project/environment with
  allowlist, budget, rotation, and no key-management permission; `docs:163-168` gives a
  per-project rotation path that does not require rotating everything. All placeholders
  are `REDACTED*` (`docs:62,72,84`). The one thing I would add is an explicit "never
  paste a key into a chat message or agent prompt" — which `docs:31-33` does in fact
  already say.
- **Honesty of the docs** — `docs:143-146` volunteers that CKFF's current five-retry
  behaviour is unacceptable for Task 2B evidence. Disclosing a limitation that
  undercuts the PR's own headline is the right call and is worth noting positively.

---

## Final judgement

**DOES NOT BLOCK MERGE.**

Reasoning. All eleven required properties hold. The three that carry the real risk —
manual-dispatch-only (item 1), no fork-PR path to the secret (item 3), and no secret
printing (item 5) — are confirmed with direct file:line evidence, and item 2's
`pull_request_target` check was run over the entire tree rather than only the new file.
The workflow is least-privileged (`contents: read`, three for three), SHA-pins its one
third-party action to a SHA I independently resolved to `actions/checkout` v5.1.0, keeps
every `${{ }}` interpolation out of `run:` bodies, emits a content hash instead of
content, uploads no artifacts, and performs no client-side retries — verified against
`urllib`'s actual default handler chain, not against its documentation.

Nine findings, none HIGH. One MEDIUM (Finding A: `urllib` forwards `Authorization`
across redirects and permits an HTTPS→HTTP downgrade target, so the line-24 HTTPS check
is bypassable by a hostile or hijacked endpoint). It does not block because exploiting
it requires already controlling the gateway or its DNS, which is outside the threat
model this PR is defending against — but it is a two-line fix (an opener without
`HTTPRedirectHandler`, plus a host assertion that would also close Finding E), and I
would want it landed **before** other repositories are onboarded per
`docs/ckff-gateway-setup.md:113-126`, because that step replicates the defect across
every additional key.

The remaining findings (B, C, E LOW; D LOW; F, G, H, I INFO) are hardening and hygiene.
The highest-value follow-ups, in order: put `CKFF_API_KEY` behind a protected
Environment (B), redact key-shaped strings from the echoed error body (C), and add
`.github/actions/**` to the ruff/mypy/bandit scope (H).

Two things I could **not** verify from the diff and am flagging rather than guessing:
whether the value stored in the `CKFF_API_KEY` secret is genuinely a restricted virtual
key (item 6 / Finding G), and whether the repository is public (Finding I severity).
