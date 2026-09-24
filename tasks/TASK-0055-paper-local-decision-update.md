# TASK-0055 — Update the benchmark paper with local decision-model results

## Status

Complete pending PR/CI/merge — tracked by GitHub issue #61.

## Objective

Bring `paper/benchmark_comparison_study.md` up to date with the completed
TASK-0053 local decision-model experiments: EXP-027 (frozen EXP-015 pool,
public and blind partitions) and EXP-028 (LegalBench Hearsay). Every new number
must trace to committed EXP-027/EXP-028 artifacts; the figure must be generated
by `scripts/generate_benchmark_figures.py`, not hand-entered.

## Goal

Publish a paper revision and a data-first figure that report the EXP-027 and
EXP-028 results with blind/public separation, coverage and abstention status,
and the not-run Nimble-9B and Kev-9B arms stated explicitly.

## Scope

- `tasks/TASK-0055-paper-local-decision-update.md`
- `checkpoints/CURRENT.md`
- `paper/benchmark_comparison_study.md`
- `scripts/generate_benchmark_figures.py`
- `paper/figures/benchmark/*.png`
- `paper/figures/benchmark/*.svg`
- `paper/figures/benchmark/manifest.json`
- `pyproject.toml`
- `uv.lock`

## Scientific decisions

- EXP-027 blind is primary; public-selection numbers are reported as
  descriptive only.
- EXP-027 and EXP-028 are separate benchmarks and separate figure panels; they
  are never pooled with each other or with the provider waves.
- The EXP-022 Jev/Qwen Flash numbers are cited as same-record context only; the
  local arms use native label scoring, not the provider typed-output harness.
- Unresolved Verdict abstentions and Verdict 1.4/Laya context-limit skips are
  reported as statuses, not wrong answers.
- Nimble-9B and Kev-9B are reported as not run (pinned configurations exceed
  the 16 GiB M1 host), not as failures or zeros.
- The Hearsay majority-class rate is derived by the figure script from
  `canonical-records.jsonl` gold labels and recorded in the manifest.

## Acceptance criteria

- The paper status, abstract, results (Sections 3.4 and 3.5), calibration,
  conclusions, limitations, and reproducibility map cover EXP-027 and EXP-028.
- `local_decision_models.png/.svg` is generated from EXP-027/EXP-028 results
  files, with SHA-256 source fingerprints in the manifest.
- Regenerating the figures is byte-stable (fixed SVG hash salt, no SVG date).
- Required local and GitHub gates pass and the PR merges.

## Checkpoint log

### 2026-09-24 — paper and figure updated

Status: complete pending PR/CI/merge; GitHub issue #61 created.

Completed work: added Sections 3.4 (EXP-027 blind table, public descriptive
numbers, by-mode interpretation) and 3.5 (EXP-028 Hearsay table with the
majority-class baseline); extended Section 5 with raw native-probability
metrics; added a sixth conclusion, local-run limitations, and EXP-027/EXP-028
reproducibility links. Extended the figure script with a three-panel local
decision-model figure (blind accuracy with Wilson intervals, blind coverage,
Hearsay accuracy) and made SVG output deterministic. `matplotlib` was not
declared anywhere, so the figure script could not run in the canonical
`.venv`; it is now declared as the optional `figures` extra and locked.

Files changed: the files listed in Scope. Existing SVGs changed only in
metadata/ids from the determinism fix; existing PNGs are byte-identical.

Commands run:

- `uv lock` and `uv sync --locked --extra dev --extra figures`
- `.venv\\Scripts\\python.exe scripts\\generate_benchmark_figures.py` (run twice;
  all 11 outputs hash-identical between runs)
- `ruff format` / `ruff check` on the figure script
- the publisher's local gate list, run manually: `uv lock --check`,
  `uv sync --locked --extra dev`, `check_repo_contract.py`,
  `check_workspace_policy.py`, `ruff check .`, `ruff format --check` on the
  changed script, `mypy src/eval_lab`, `pytest -q tests`, and `uv build`

Test results: all gates passed; pytest 167 passed. A bare `pytest -q` also
collects the untracked TASK-0054 linked worktree's duplicate tests and fails at
collection, so pytest was scoped to `tests` (CI has no linked worktree).
`scripts/publish_checkpoint.py` was not used because it refuses to publish while
the untracked TASK-0054 worktree folder exists; the commit, push, and PR body
follow its format manually.

Decisions: a new task and issue were used because the paper update is a
separate deliverable from TASK-0053's model runs, which remain open under
issue #47.

Observed inconsistencies (not changed here): the EXP-027 `README.md` still says
no inference has run; the root `RESULTS.md` holds only EXP-025 results; the
paper's Bonsai 2 27B limitation predates the TASK-0053 Mac cleanup that
removed that model.

Unresolved questions: none for this checkpoint.

## Handoff

The paper reflects all completed TASK-0053 arms. If Nimble-9B or Kev-9B is run
later on adequate hardware, add it to `LOCAL_LABELS` in the figure script,
regenerate the figures, and update Sections 3.4/3.5; never hand-edit figure
numbers.

## Next atomic action

After merge, run `scripts/finalize_checkpoint.py` for issue #61 and fast-forward
the canonical checkout to `origin/main`.
