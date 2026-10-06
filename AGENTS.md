# Agent Operating Contract

This repository is designed to be usable by multiple independent agents without shared chat history.

## Read order

Before doing work, read only:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. the assigned `tasks/TASK-*.md`
4. the minimum design document needed for the task:
   - product scope: `docs/PDD.md`
   - system design: `docs/SDD.md`
   - testing: `docs/TDD.md`
   - experiment rules: `docs/EXPERIMENT_PROTOCOL.md`
5. for README, marketing, UX writing, image-generation, or HTML-demo work, read the relevant `.content-system/` adapter files and the pinned helper version before producing output.

Do not scan unrelated historical files or experiments unless the task explicitly requires them.

## One canonical checkout; no worktrees or sibling clones

`D:\development\eval-lab` is the single local Eval Lab checkout. `D:\development`
holds only the main checkout of each repository: never create a Git worktree,
a second clone, a copied project directory, or a task-named sibling folder
under `D:\development`. Scratch files, helper-repository clones (for example
the pinned PCM, CGM, OIO and ACS checkouts) and temporary output live outside
`D:\development`, for example under `C:\work` or `%TEMP%`.

Branch format:

```
task/TASK-0001-short-name
```

Tasks are serialized in the one checkout. Before switching task branches,
finish a coherent checkpoint, commit it, push it to GitHub, and confirm the
working tree is clean; do not stash work to make parallel tasks appear safe.
When idle on `main`, fetch and fast-forward the checkout to `origin/main`; do
not create a second directory to preserve an old branch.

If GitHub or the checkout is unavailable, stop and report the blocker rather
than creating another local copy.

When a task is complete, verify its branch and all tracked, untracked, and
ignored state. Push the checkpoint and open or update its PR; wait for required
CI and merge the PR before closing the task. Preserve any unique state that is
not in Git, then confirm `git worktree list` shows only the one checkout and
that it is synchronized with `origin/main`.

A task may modify only the files declared in its task file unless the task file is updated first.

## One canonical dependency environment

Use the one canonical repository-root `.venv`, managed by the single `uv`
executable available on `PATH`. Resolve and synchronize from the root
`pyproject.toml` and `uv.lock` with `uv sync --extra dev`; run Python tools
through `.venv\Scripts\python.exe` on Windows. Do not make task-specific
virtual environments or copy `.venv`.

This project is Python-only. Do not create `node_modules` here. If a future,
approved change adds a Node package, its single `node_modules` must live at the
repository root and be managed from the root lockfile. If the task
changes dependency requirements incompatibly, serialize and synchronize the
canonical environment in place. Use package-manager caches for download reuse,
not duplicate project installs.

Tasks are serialized because `.venv` is mutable. If a branch changes dependency
requirements, update the single lockfile and synchronize the same `.venv`
before running the task. Never create another environment as a workaround; if
the change cannot be handled safely in the canonical environment, stop and ask.

### TASK-0053 remote model-runtime exception

For TASK-0053 only, an upstream model runtime that requires incompatible
dependencies may use an isolated runtime environment on the user's Apple
Silicon Mac. Keep that environment and downloaded weights outside every Eval
Lab checkout; do not clone or copy the repository to the Mac. Pin the runtime
and model revisions in the experiment artifacts, run one model at a time, and
retain or remove runtime state only as documented in the task checkpoint. This
exception is for model inference only and does not create another project
dependency environment.

### TASK-0065 free-tier Colab compute exception

For TASK-0065 only, model inference may run on a free-tier Google Colab T4 VM
driven by the official `colab` CLI from WSL, because the MoE judge arms are too
large for the canonical machine. The repository is never cloned or copied to
the VM; only gold-free request files are served there, and scoring happens
offline in the repo. This is a compute path, not a dependency environment: the
canonical `.venv` stays the only project environment. Bound the path to the
free tier and the official CLI — no ssh, console, repl, auth, or Drive mount,
one session at a time, always `colab stop` when done, and no tunnels, proxies,
or long-running services. Never upload, commit, or print a gold label, a token,
or a credential. See `docs/compute/colab-cli.md` and the TASK-0065 checkpoint
for the exact invocation and revisions.

### TASK-0068 gravebuster pod reconnaissance exception

For TASK-0068 only, dataset reconnaissance may run in a Podman pod on the owner's
Linux box `gravebuster`, because the patent-law release is large and Linux-native
to inspect while the canonical `.venv` is Windows-only. The pod holds only the
frozen public dataset and derived artifacts; it is never given a clone of this
repository, and **the scored experiment runs in the canonical `.venv`**, so this
exception authorises reconnaissance and substrate building only — not a second
project environment. The pod is ephemeral by construction: a systemd user timer
archives its workspace and then removes the container, pod and volume, and the
archive step aborts rather than deleting if it fails, so no unique state is lost.
It publishes no ports and is reached only by `podman exec`. Never upload, commit,
or print a token or a credential. See the TASK-0068 checkpoint for the exact pod
name, image, resource caps and the timer's `OnCalendar` value.

Run `python scripts/check_workspace_policy.py --canonical-root D:\development\eval-lab`
before task work and after cleanup. The repository contract check also enforces
the canonical path, the no-linked-worktree rule, and the one-environment rule.

## GitHub issue and checkpoint policy

GitHub Issues are the authoritative change log. Create or update an issue
before implementation, and put its number in the task file. Use a GitHub
sub-issue only when a parent task has independently deliverable child tasks;
do not maintain a second issue register in the repository.

GitHub is the durable record for committed task progress; local folders are
working state, not backup. At each meaningful stopping point, update the task
file and, when the repository-wide next action changes, `checkpoints/CURRENT.md`.
Use `scripts/publish_checkpoint.py` with explicit paths to run local gates, make
the checkpoint commit, push only the task branch, create or update its PR, and
request GitHub auto-merge. The publisher returns while required CI runs; agents
may continue or hand off asynchronously. The PR must reference its issue;
close it only after finalization. A merged-PR workflow records the exact PR
head and merge SHA. Task PRs auto-merge after the required CI checks. Never
push directly to `main` or bypass a failed or missing required check.

A checkpoint is complete only after GitHub confirms its PR merged with required
CI successful. Do not leave completed work or handoff state only in chat or a
local branch. After merge, run
`scripts/finalize_checkpoint.py` to confirm the merge, audit tracked,
untracked, and ignored state, and fast-forward the canonical checkout to
`origin/main`. Never discard unique state.

## Required checkpoint behavior

At every meaningful stopping point, update the task file with:

- status
- completed work
- exact files changed
- commands run
- test results
- decisions made
- unresolved questions
- next atomic action

If the task becomes blocked, write the blocker before stopping.

When the repository-wide next action changes, update `checkpoints/CURRENT.md`.

## Commit rule

A commit should represent one coherent checkpoint. Commit message:

```
TASK-0001: concise checkpoint description
```

Never leave important state only in a chat transcript.

## Experiment rule

Every experiment must have a directory under `experiments/` and follow `docs/EXPERIMENT_PROTOCOL.md`.

Never overwrite completed experiment results. Create a new experiment ID for a changed dataset, rubric, model, prompt, seed, calibration method, or evaluation protocol.

## Run telemetry rule

Every eval run appears in the committed telemetry ledger at `telemetry/runs.v1.jsonl`, one record per run unit keyed by `run_path`, with findings in `telemetry/FINDINGS.md`. Both are derived from the `experiments/` artifacts by `scripts/run_telemetry.py` and checked in CI with `--check`.

When a change adds, removes, or alters a `results.json` under `experiments/`, regenerate with `uv run --locked python scripts/run_telemetry.py rebuild` in the same checkpoint. Never hand-edit the ledger or findings. A run directory without a `results.json` is still recorded (`partial`/`quarantined`), never dropped.

## Ground-truth rule

Model judgments are never promoted to objective gold merely because the model is strong.

Gold labels must identify their provenance:

- deterministic verifier
- benchmark answer key
- executable test
- human adjudication
- explicitly marked weak/model supervision

<!-- pcm:issue-log-format:start -->
## Issue log format (issue-log-format 1.2.0)

<!-- pcm:policy {"id":"issue-log-format","policy_version":"1.2.0","protocol_version":"0.1.0-draft"} -->

Write issue logs, progress updates, and pull requests in one plain-language shape a newcomer can follow. Pick the tier by the kind of issue, not by preference. **Core tier (every issue log):** title states the problem and intended direction; a 1-3 paragraph summary naming who/what is affected, the consequence, and what this proposes; identity and lineage (leaf owning issue, parent ancestry or none, task ID, primary writer, branch); observed facts vs interpretation, with inferences labelled *inferred*; acceptance criteria with numeric thresholds marked *(proposed)* when untested; boundaries/non-goals and one next action. **Investigation tier (incidents, failures, research, design issues):** numbered symptoms; hypotheses with Status, confirm/refute, and experiment; evidence with provenance; a **Counter-signal** entry when one exists; honest caveat; problems-vs-gaps; a **Proposal** labelled *(proposal)* stating none of it exists unless named as existing. **Pull requests open reader-first:** problem and consequence, what changes, how to verify, and what stays unchanged; lineage links; evidence and one next action; long logs collapsed or linked; reference issues with "Refs #<number>" and use closing keywords only when closing at merge is intended. **Diagrams (mermaid):** when a record describes a flow with 4+ ordered steps or 2+ branches, add a fenced mermaid diagram *and* keep an adjacent text list or table so the record survives render failure; default to `graph TD` (vertical) because wide `LR` flows shrink to illegible strips on phones — reserve `LR` for 4 or fewer short nodes; cap 8 nodes and 6-word labels; wrap diagrams that may exceed the container width inside `<details>` (GitHub mounts the renderer lazily on expand); preview the rendered diagram before publishing (broken syntax shows a visible parse error) and never cite renderer URLs as standalone sources. No private absolute paths or secrets; link rather than paste long logs. See `docs/ISSUE_LOG_FORMAT.md` for the full format, exemplar, and examples.
<!-- pcm:issue-log-format:end -->

<!-- oio:issue-log-guidance:start -->
Before filing an observational or operational issue log, read `.oio/ontology/ISSUE_LOG_ONTOLOGY.md`, `.oio/ontology/project.json`, and `.oio/ontology/AGENT_GUIDE.md`. Confirm the exact destination and filing action are authorized. On OIO, ACS, CGM, and PCM, do not submit an issue or write files without explicit human direction for that destination and action. A proposal can remain a local draft until directed. Never treat adoption as permission to write to an adopter or sibling repository.
<!-- oio:issue-log-guidance:end -->
