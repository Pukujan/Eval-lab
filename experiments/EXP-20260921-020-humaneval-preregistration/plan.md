# HumanEval source audit and executable-test plan (2026-09-21)

## Source, revision, license, access

- Official repository: https://github.com/openai/human-eval ; `git ls-remote`
  resolved `refs/heads/master` to
  `6d43fb980f9fee3c892a914eda09951f772ad10d`. Use this full commit,
  never floating `master` or an unpinned package.
- GitHub's read-only tree API for that commit returned `truncated=false` and
  `data/HumanEval.jsonl.gz` as a 44,877-byte blob with Git object ID
  `998d25196e17af24daf9b6cb3a975fe752528e46`. A HEAD request to the
  pinned raw URL returned HTTP 200 and Content-Length 44,877. Neither check
  fetched archive bytes or verified its content SHA-256.
- The sole license file in the full tree is root `LICENSE`, Git blob
  `4f14854c3243516f3de1487a60f14882874d7e3a` (1,083 bytes), with MIT
  text and OpenAI copyright. Its raw bytes hash to SHA-256
  `bcba3de214851cce46ed5af42d6698044616eeace887c3231bc7a20474ab639e`.
  No separate data-directory license/notice was listed. The repository-level
  terms support a local research-access plan; no data redistribution is
  planned. At retrieval, recheck the pinned license and source terms; stop on
  conflicting terms or unexpected separate restrictions. This is a source
  audit, not a legal opinion.
- Official README describes completion-only samples and explicitly warns
  against running untrusted code outside a robust security sandbox. The
  upstream `execution.py` builds `prompt + completion + "\n" + test + "\n" +
  check(entry_point)`; its own guard says it is **not** a security sandbox,
  and its `exec(check_program, exec_globals)` is commented out. These are
  design references, not permission to execute on the host.
- After separately authorized retrieval, cache the pinned archive locally
  outside Git, record retrieval UTC, source URL, license digest, archive
  SHA-256, decompressed canonical-row SHA-256 and row count; verify required
  fields, unique `task_id`, UTF-8 and expected 164 rows. Any mismatch blocks
  further use. Keep raw data and candidate code out of this repository.

## Frozen policy; unfilled execution parameters

Each distinct upstream task is one source family. Sort IDs by
`SHA-256("humaneval-v1|20260921|" + task_id)` (task-ID tie-break), then assign
floor(20%) dev, floor(20%) calibration, remainder test. Expected 164 rows
would yield 32/32/100; no actual membership or fingerprint is claimed yet.
All candidates for one task inherit its split. Canonical UTF-8 JSON uses sorted
keys, compact separators and LF; freeze archive, rows, ordered task-ID lists,
candidate pool, canonical records and packet hashes before final test.

One exact UTF-8 completion is a single-candidate `PASS`/`FAIL` prediction.
The versioned packet contains task type `python_function_correctness`, Python
language, task ID, exact prompt and completion, allowed labels and protocol/
rubric versions. It excludes tests, canonical solution, gold, split and
verifier diagnostics. Stable record IDs include revision, task ID, candidate
source/index and digest, and adapter version; no fence stripping, whitespace
repair or implicit imports. Model output must have one legal label and either
a finite two-label probability distribution summing to one or an explicit
probability-unavailable marker. Preserve raw scores, surfaced model ID, route,
latency, token usage and provider execution status separately.

Gold is issued only from the pinned test suite and exact upstream composition
inside a proven isolated Linux container or VM, with test/completion digests,
runtime identity, outcome and bounded diagnostics. Healthy-sandbox assertion,
syntax and runtime failures and candidate timeouts are `FAIL`; `passed` is
`PASS`. Invalid payloads have no gold. Sandbox crash, missing tests, image
mismatch or verifier error are indeterminate and excluded from correctness.
Provider timeout, rate limit, parse error and provider error are attempted
coverage/status only, not ordinary wrong predictions. Retain first attempts;
retry only preregistered infrastructure-indeterminate outcomes with a fixed
limit, never tune timeouts from final labels.

Isolation gate: a disposable sandbox per candidate, pinned image digest and
Python version, non-root identity, read-only inputs, ephemeral writable
scratch, network disabled, no host workspace/secret mounts, dropped Linux
capabilities, seccomp and no privilege escalation. Freeze exact CPU, wall,
memory, PID, file and output limits before running. Offline fixtures must
prove pass, assertion failure, syntax error, infinite loop, filesystem and
egress denial, sandbox error, and deterministic replay/evidence digest. Do not
run upstream `unsafe_execute` on the host. `docker version` could not reach
the Docker Desktop Linux engine (missing named pipe); WSL2 Ubuntu being
configured does **not** establish an isolated runnable sandbox. No candidate
execution is allowed until this gate is demonstrated.

Development IDs may guide packet choices; calibration IDs alone fit the
prespecified calibrator and abstention/error threshold; final test is used
once for evaluation, never selection. The primary unit is a candidate
decision; uncertainty intervals cluster by source task. Report per-arm
attempted/valid/invalid/indeterminate counts, verifier and provider statuses,
class prevalence, accuracy, balanced accuracy, macro F1, Brier, NLL, ECE,
selective risk/coverage, latency and cost. Probability metrics are unavailable
for label-only arms. Generation pass@k, if ever included, is a distinct metric
and never judge accuracy. Public-data contamination and incomplete coverage
must be explicit; no blended cross-domain score.

Provider policy is frozen: no OpenCode; OpenRouter only for an explicitly
selected Jev arm; Grok only via direct authenticated xAI `grok` Build CLI;
no silent fallbacks. Exact arms/routes/models, candidate generator and count,
seeds, prompt text, image digest, limits, calibration estimator, primary
comparison, retry cap and stopping rule are **not** frozen. They must be
selected and committed before provider calls or final test. A code/packet/
source/protocol change after execution requires a new experiment ID.

## Gate and handoff

This checkpoint is planning-only, blocked for execution by unavailable Docker
isolation and missing source/candidate fingerprints and experiment parameters.
No final-label artifact may be created. The next implementation checkpoint
must prove isolation without untrusted benchmark execution, implement and test
the adapter/verifier with hand-written fixtures, retrieve and fingerprint the
official source only after authorization, fill all nulls in the manifest,
freeze a complete preregistration in a commit, and only then consider an
offline smoke or provider execution. EXP-014 through EXP-019 stay immutable.
