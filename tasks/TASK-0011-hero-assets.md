# TASK-0011 — Eval Lab README Hero Assets

- Status: active
- Owner: Codex/image-generation agent
- Priority: P1
- Branch: task/TASK-0011-hero-assets
- Depends on: TASK-0009 (content context only)

## Goal

Create polished, README-renderable hero banner artwork for the Eval Lab repository and add a small set of related variants without changing the research implementation owned by TASK-0010.

## Research framing

Eval Lab evaluates lightweight AI judges against objective labels and trusted answer keys, with emphasis on calibration, reliability, selective escalation, and explicit uncertainty. Jev is relevant as a structured decision and routing component, not as an unsupported benchmark claim.

## Outputs

- `assets/eval-lab-banner.png` — primary wide README hero.
- `assets/eval-lab-banner-alt-routing.png` — routing-focused visual variant.
- `assets/eval-lab-banner-alt-calibration.png` — calibration-focused visual variant.
- `README.md` — top-of-file hero embed and a compact note describing the variants.

## Allowed files

- `assets/eval-lab-banner.png`
- `assets/eval-lab-banner-alt-routing.png`
- `assets/eval-lab-banner-alt-calibration.png`
- `README.md`
- this task file

## Acceptance criteria

- [ ] Each image is a readable, wide PNG suitable for GitHub README rendering.
- [ ] Artwork depicts an adult anime-style researcher with a small robot assistant in a tasteful research-lab setting.
- [ ] On-image copy is minimal, human-readable, and includes a restrained Jev mention.
- [ ] No explicit sexualization, underage appearance, fake benchmark claims, or dense technical jargon.
- [ ] README embeds the primary banner using a repository-relative path and preserves existing research content.
- [ ] Image files are inspected after generation and the working tree passes `git diff --check`.

## Commands

- `git diff --check`
- `git status --short --branch`

## Checkpoint log

### 2026-09-20 — implementation checkpoint

Status: implementation complete; awaiting push and review. Created the isolated branch and worktree from `origin/main`. Read the project contract, current checkpoint, TASK-0010 context, product design brief, and image-generation instructions.

Completed: defined three README-ready image outputs, generated and visually inspected three wide PNG variants, copied them into `assets/`, and added a primary hero plus collapsible alternatives to `README.md`.

Exact files changed: `tasks/TASK-0011-hero-assets.md`, `assets/eval-lab-banner.png`, `assets/eval-lab-banner-alt-routing.png`, `assets/eval-lab-banner-alt-calibration.png`, `README.md`.

Commands run: `git fetch origin`; `git worktree add D:\\claude\\eval-lab-TASK-0011 -b task/TASK-0011-hero-assets origin/main`; image generation via built-in image-generation tool; PNG copy and local inspection.

Test results: image review passed; all three PNGs are 1672×941 (1.78:1); `git diff --check` passed; `python scripts/check_repo_contract.py` returned `Repository contract OK`.

Decision: keep this work isolated from the active TASK-0010 worktree and avoid touching experiment or source files.

Unresolved questions: none.

Next atomic action: commit the asset checkpoint, push the branch, and open a review PR.

## Handoff

Read, in order:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. this task
4. `docs/PDD.md`

The branch contains only README presentation changes, generated PNG assets, and this task checkpoint. The primary banner is `assets/eval-lab-banner.png`; the routing and calibration alternatives are in the same directory and are rendered in the README's collapsible alternatives section.
