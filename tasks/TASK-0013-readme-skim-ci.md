# TASK-0013 — README Skimmability, Content System, and CI Import Fix

- Status: active
- Owner: Codex/documentation and CI agent
- Priority: P1
- Branch: task/TASK-0013-readme-skim-ci
- Depends on: TASK-0012 (merged README story and visual assets)

## Goal

Make the README easier to scan without flattening its technical meaning, document a reusable human-first content and visual-generation system for future agents, and fix the now-reproducible CI import failure.

## Research and diagnosis

The README needs emphasis at the phrase level so readers can scan topic sentences and key decisions without reading every paragraph. The content system should preserve a concrete, human voice, distinguish evidence from aspiration, and make visual generation repeatable at the brief-and-review level.

The public GitHub Actions run now reaches the runner, checkout, installation, contract, and lint steps. Its unit-test step fails because `pytest` cannot import the repository’s top-level `scripts` namespace under the CI environment. Local tests pass when both the repository root and `src` are on `PYTHONPATH`.

## Outputs

- `README.md` — selective bold/italic emphasis and link to the reusable content/visual system.
- `docs/README_CONTENT_VISUAL_SYSTEM.md` — human-writing, UX, marketing, prompt, asset, and review playbook.
- `assets/README-ASSET-MANIFEST.yaml` — current asset roles, dimensions, style tokens, and reproduction metadata.
- `.github/workflows/ci.yml` — explicit repository-root plus `src` import path for unit tests.
- this task file.

## Allowed files

- `README.md`
- `docs/README_CONTENT_VISUAL_SYSTEM.md`
- `assets/README-ASSET-MANIFEST.yaml`
- `.github/workflows/ci.yml`
- this task file

## Acceptance criteria

- [x] Important phrases in long README paragraphs are selectively bolded or italicized for scanning.
- [x] README does not become visually noisy from over-formatting.
- [x] Future agents have a documented content voice, paragraph, marketing, image-prompt, responsive-dimension, and review recipe.
- [x] Current visual assets have a manifest with roles, dimensions, references, and honest reproducibility limits.
- [x] CI unit tests can import both `eval_lab` and the repository’s `scripts` namespace.
- [x] Local contract, lint, and tests pass.
- [ ] A fresh public GitHub Actions run passes on Python 3.11 and 3.12.

## Commands

- `python scripts/check_repo_contract.py`
- `ruff check .`
- `PYTHONPATH=<repo>;<repo>\\src pytest -q`
- `git diff --check`
- `gh workflow run CI --ref main`
- `gh run watch <run-id> --exit-status`

## Checkpoint log

### 2026-09-20 — planning and CI diagnosis

Status: active. Created the isolated worktree from `origin/main` after TASK-0012 merged.

Completed: inspected the public repository’s workflow and latest run; confirmed Actions is enabled, the runner now starts, and the actual failure is `ModuleNotFoundError: No module named 'scripts'` during `pytest` collection. Read the project contract, current checkpoint, TASK-0012 handoff, PDD, SDD, and existing README.

Exact files changed: `tasks/TASK-0013-readme-skim-ci.md`.

Commands run: `git fetch origin`; `git worktree add D:\\claude\\eval-lab-TASK-0013 -b task/TASK-0013-readme-skim-ci origin/main`; `gh workflow run CI --ref main`; `gh run watch 35541354152 --exit-status`; `gh run view 35541354152 --log-failed`.

Test results: the public workflow reached checkout/install/contract/lint; both matrix unit-test steps failed during collection because `scripts` was not importable. Local validation from the prior task was green with `64 passed` when the repository root and `src` were available.

Decision: fix CI at the workflow boundary with `PYTHONPATH: .:src`, then make README emphasis and reproducibility guidance durable in the repository.

Unresolved questions: none.

Next atomic action: apply the README emphasis, content/visual playbook, asset manifest, and CI import-path fix; then rerun the full local and public gates.

### 2026-09-20 — implementation checkpoint

Status: implementation complete locally; public CI rerun pending.

Completed: added selective phrase-level bold/italic emphasis throughout `README.md`; linked the reusable content/visual system and asset manifest; documented human-first paragraph structure, marketing-post structure, prompt recipes, responsive dimensions, palette tokens, iteration rules, and reproducibility limits; added `PYTHONPATH: .:src` to the CI unit-test step.

Exact files changed: `README.md`, `docs/README_CONTENT_VISUAL_SYSTEM.md`, `assets/README-ASSET-MANIFEST.yaml`, `.github/workflows/ci.yml`, and this task file.

Commands run: `git diff --check`; `python scripts/check_repo_contract.py`; `ruff check .`; `PYTHONPATH=.;src pytest -q`.

Test results: repository contract OK; Ruff clean; `64 passed in 7.86s`. The previous public run `35541354152` reached the runner but failed test collection with `ModuleNotFoundError: No module named 'scripts'`; the workflow now supplies the missing import path.

Decision: keep formatting selective—bold the sentence-level decision, promise, boundary, or result a scanner needs, not every technical noun. Treat image generation as reproducible intent and review metadata, not pixel-identical output.

Unresolved questions: public CI confirmation is pending.

Next atomic action: commit and push this branch, trigger or observe the public CI run, and open a review PR.

## Handoff

Read, in order:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. this task
4. `docs/PDD.md`
5. `docs/SDD.md`

The existing README story and responsive visual assets are intentionally preserved; this task improves scanning, reproducibility, and CI reliability without changing research claims or generated artwork.
