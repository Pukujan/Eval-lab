# TASK-0012 — README Story and Supporting Visual System

- Status: completed and merged into `main`
- Owner: Codex/documentation and visual-design agent
- Priority: P1
- Branch: task/TASK-0012-readme-story-assets
- Depends on: TASK-0011 (merged hero asset)

## Goal

Rewrite the repository README as a human-relatable, technically accurate introduction to Eval Lab, and extend the hero’s visual language into a small set of supporting illustrations and reusable SVG icons.

## Research framing

The README should explain the project in layers: why judging agent output is difficult, what Eval Lab is trying to measure, how objective labels/calibration/selective escalation fit together, how the repository is organized, and how a researcher can reproduce the work. It must distinguish current implemented artifacts from planned or experimental work.

GitHub presentation decisions: keep one primary hero at the top, use relative paths for repository images, use clear headings for the rendered outline, and put detailed technical material in skimmable sections rather than inside images.

## Outputs

- `README.md` — narrative, technical, skimmable project introduction.
- `assets/eval-lab-problem.png` — supporting illustration for the “why this exists” section.
- `assets/eval-lab-system-square.png` — restrained square system-flow illustration for tablet/mobile layouts.
- `assets/eval-lab-evidence-portrait.png` — portrait evidence/calibration illustration for narrow layouts.
- `assets/icons/*.svg` — small reusable icons matching the hero palette and line style.
- remove the unused alternative hero-banner files from TASK-0011.

## Allowed files

- `README.md`
- `assets/eval-lab-problem.png`
- `assets/eval-lab-system-square.png`
- `assets/eval-lab-evidence-portrait.png`
- `assets/icons/*.svg`
- `assets/eval-lab-banner-alt-routing.png` (removal)
- `assets/eval-lab-banner-alt-calibration.png` (removal)
- this task file

## Acceptance criteria

- [x] README begins with one hero banner and a clear human-readable promise.
- [x] README tells a coherent story: agent-output problem, Eval Lab purpose, technical approach, evidence boundaries, getting started, and roadmap.
- [x] Technical claims are grounded in `PROJECT.md`, `docs/PDD.md`, `docs/SDD.md`, and active task context; planned work is labeled as planned.
- [x] README uses headings, short paragraphs, tables/lists, and links for easy skimming.
- [x] Supporting images use the hero’s visual language, preserve subject visibility, and contain little or no embedded text.
- [x] SVG icons are simple, readable, repository-native assets rather than noisy generated text.
- [x] README uses repository-relative image paths and does not render the former alternative-hero gallery.
- [x] `git diff --check` and the repository contract pass.

## Commands

- `git diff --check`
- `python scripts/check_repo_contract.py`
- `git status --short --branch`

## Checkpoint log

### 2026-09-20 — planning and research

Status: active. Created the isolated worktree from `origin/main` after TASK-0011 merged.

Completed: read the project contract, current checkpoint, TASK-0011 handoff, product design, system design, and GitHub README/image guidance. Defined a story-first README structure with one hero and three supporting visual moments.

Exact files changed: `tasks/TASK-0012-readme-story-assets.md`.

Commands run: `git fetch origin`; `git worktree add D:\\claude\\eval-lab-TASK-0012 -b task/TASK-0012-readme-story-assets origin/main`.

Test results: not run yet.

Decision: remove the unused alternative hero gallery and replace it with focused, low-text supporting visuals plus SVG concept icons.

Unresolved questions: none; proceed with asset generation and README authoring.

Next atomic action: run local validation, inspect the README diff and image dimensions, then commit and push the branch for review.

### 2026-09-20 — visual feedback iteration

Status: active. The user approved the restrained portrait evidence image and the original hero, rejected the first square system illustration as too busy and contrasty, and requested more human, less agent-like README language plus responsive image dimensions.

Completed: generated a replacement square system illustration with one calm glass-panel decision path, kept the portrait evidence illustration, removed the unused alternative hero files, authored the story-first README, and added four matching SVG concept icons.

Exact files changed: `README.md`, `assets/eval-lab-problem.png`, `assets/eval-lab-system-square.png`, `assets/eval-lab-evidence-portrait.png`, `assets/icons/objective-truth.svg`, `assets/icons/calibrated-confidence.svg`, `assets/icons/selective-routing.svg`, `assets/icons/reproducible-evidence.svg`, removed `assets/eval-lab-banner-alt-routing.png`, removed `assets/eval-lab-banner-alt-calibration.png`, and this task file.

Commands run: built-in image generation with the existing hero as a visual reference; PNG copy and dimension inspection; SVG creation; README authoring.

Test results: image inspection passed visually; final repository validation pending.

Decision: use one wide hero only; use wide, square, and portrait supporting art for responsive reading; keep explanatory text in the README rather than inside generated images.

Unresolved questions: none.

### 2026-09-20 — implementation checkpoint

Status: implementation complete and merged into `main` via PR #28.

Completed: rewrote `README.md` around a human story and a skimmable technical explanation; kept only the original wide hero; added wide, square, and portrait supporting PNGs; replaced the rejected busy square illustration with a calmer subject-first version; added four matching SVG icons; removed unused alternative hero files.

Exact files changed: `README.md`, `assets/eval-lab-problem.png`, `assets/eval-lab-system-square.png`, `assets/eval-lab-evidence-portrait.png`, `assets/icons/objective-truth.svg`, `assets/icons/calibrated-confidence.svg`, `assets/icons/selective-routing.svg`, `assets/icons/reproducible-evidence.svg`, removed `assets/eval-lab-banner-alt-routing.png`, removed `assets/eval-lab-banner-alt-calibration.png`, and this task file.

Commands run: `git diff --check`; `python scripts/check_repo_contract.py`; `ruff check .`; `PYTHONPATH=<repo>;<repo>\\src pytest -q`; image dimension inspection.

Test results: repository contract OK; Ruff clean; `64 passed in 6.90s`; PNGs validated at 1672×941, 1254×1254, 1024×1536, plus the retained 1672×941 hero. GitHub Actions for PR #28 failed before checkout with empty step lists, consistent with the account runner-budget condition; no repository test step ran in CI.

Decision: use concrete, human-scale examples and active voice in the README; keep the technical boundaries explicit; use responsive visual dimensions rather than repeating horizontal banners.

Unresolved questions: none.

Next atomic action: none for TASK-0012; the README and visual system are available on `main`.

## Review handoff

PR: https://github.com/Pukujan/Eval-lab/pull/28

Branch: `task/TASK-0012-readme-story-assets`

Commit: `52ebd17`

The primary hero remains `assets/eval-lab-banner.png`. The rejected busy square concept was replaced with `assets/eval-lab-system-square.png`; the README also uses `assets/eval-lab-problem.png`, `assets/eval-lab-evidence-portrait.png`, and four repository-native SVG icons. The old alternative hero files were removed. PR #28 merged at `c9411fb33e5d242cd90c333e552b30f82b6882fb`.

## Handoff

Read, in order:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. this task
4. `docs/PDD.md`
5. `docs/SDD.md`

The existing primary hero `assets/eval-lab-banner.png` is retained. The README should use it once at the top and use the new supporting assets throughout the body.

### 2026-09-20 — merge checkpoint

Status: completed and merged into `main`.

Completed work: confirmed PR #28 had no file-level merge conflict, diagnosed its red GitHub checks as pre-step runner-budget failures with empty job step lists, merged the PR normally, and fast-forwarded the original local `main` checkout.

Exact files changed: `README.md`, `assets/eval-lab-problem.png`, `assets/eval-lab-system-square.png`, `assets/eval-lab-evidence-portrait.png`, `assets/icons/*.svg`, removed the two unused alternative hero PNGs, and this task file.

Commands run: `gh pr view 28`; `gh pr merge 28 --merge --delete-branch=false`; `git fetch origin refs/heads/main:refs/remotes/origin/main`; `git merge --ff-only origin/main`.

Test results: local contract, Ruff, diff check, and `64 passed` were recorded before merge. GitHub Actions still failed before checkout with empty job steps because the account runner budget was unavailable; no repository test step ran in CI.

Decision: merge was appropriate because the branch was conflict-free and the local gate passed; the CI failure was external to the repository changes.

Unresolved questions: GitHub Actions runner-budget availability remains an external repository condition.

Next atomic action: none for TASK-0012; continue the active research task in its dedicated worktree.
