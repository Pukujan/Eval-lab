# TASK-0014 — Adopt the reusable content-generation system

<!-- eval-lab:task {"id":"TASK-0014","status":"awaiting_review","goal":"Dogfood the versioned content-generation-modules helper in Eval Lab and produce reviewable README, visual, and responsive HTML artifacts without changing research behavior.","branch":"task/TASK-0014-content-system-adoption","allowed_files":[".gitignore","AGENTS.md","checkpoints/CURRENT.md","tasks/TASK-0014-content-system-adoption.md","README.md",".content-system/**","assets/eval-lab-banner.png","assets/eval-lab-problem.png","assets/eval-lab-system-square.png","assets/eval-lab-evidence-portrait.png","docs/content-system-preview.md","docs/content-system-preview.html"],"helper_repository":"https://github.com/Pukujan/content-generation-modules","helper_version":"0.1.2","helper_commit":"cb8c18fa7789e4b651e1f963892bf056b0d3276d","next_action":"Review the updated README and rendered artifacts in PR #30 before merging the preview branch."} -->

- Status: README updated on the preview branch; awaiting user review before merge
- Owner: Codex current implementation session
- Branch: `task/TASK-0014-content-system-adoption`
- Helper: `Pukujan/content-generation-modules@v0.1.2` (`cb8c18fa7789e4b651e1f963892bf056b0d3276d`)
- Scope: project adapter plus reviewable content/visual/HTML preview only

## Goal

Use the reusable content-generation contract in Eval Lab so a fresh agent can produce human-oriented documentation and visuals from repository evidence without relying on prior conversation history.

## Allowed files

- `AGENTS.md`;
- `checkpoints/CURRENT.md`;
- `tasks/TASK-0014-content-system-adoption.md`;
- `.content-system/**`;
- `docs/content-system-preview.md`;
- `docs/content-system-preview.html`;
- the four named narrative raster assets under `assets/` when the title/subtitle contract requires regeneration.

Do not change research code, experiment artifacts, existing README copy, CI, or runtime behavior in this preview task. SVG icons and tiny helper graphics remain unchanged and text-free.

## Acceptance criteria

- [x] adapter pins the helper repository, version, and commit;
- [x] project brief identifies audience, problem, solution, mechanism, evidence, and boundaries;
- [x] brand language defines human-facing tone, preferred terms, and anti-patterns;
- [x] visual style defines the accepted hero pattern and responsive supporting roles;
- [x] asset manifest records existing image/icon roles and review decisions;
- [x] review rubric separates deterministic checks, model-assisted advice, and human acceptance;
- [x] rendered Markdown preview tells the story and displays the existing assets;
- [x] responsive HTML preview works at wide, tablet, and mobile widths;
- [x] repository contract, adapter validation, local tests, and preview render checks pass;
- [x] no target changes are merged without explicit user review.
- [x] every narrative raster asset carries a short title and subtitle; SVG/helper assets remain text-free.

## Review evidence to record

- helper commit and tag;
- target branch and PR URL;
- validator/test commands and results;
- HTML screenshot/PDF paths or URLs;
- human review decisions and required revisions;
- one exact next action for the next Luna/Codex session.

## Checkpoint log

### 2026-09-20 — Codex activation

Completed:

- created the dedicated Eval Lab preview branch from merged `main` at `345e731`;
- selected `content-generation-modules` version `0.1.0` as the pinned helper;
- limited this task to a non-destructive adapter and review previews.

Evidence:

- helper tag resolves to commit `78393825635850442822dd00e0e84aff665814a4`;
- working tree started clean on `task/TASK-0014-content-system-adoption`.

Decisions:

- keep existing README and assets unchanged until the user reviews the generated preview;
- store project-specific facts in `.content-system/`, not in the generic helper repository;
- use existing accepted Eval Lab images as the first visual regression set.

Blocked/uncertain:

- none.

Next:

- add and validate the project adapter and rendered previews.

### 2026-09-20 — Codex preview completion

Completed:

- added the pinned `.content-system/` adapter;
- added a story-first Markdown preview and responsive HTML preview using the existing accepted asset set;
- added a local ignore rule for generated review output;
- rendered desktop, tablet, and mobile screenshots plus a four-page A4 PDF review packet.

Evidence:

- helper validator: `python scripts/validate_content_system.py --root .` -> `VALID: content-generation-modules contract`;
- target adapter validator: helper validator with `--adapter D:\\claude\\eval-lab-TASK-0014\\.content-system --project-root D:\\claude\\eval-lab-TASK-0014` -> `VALID: content-generation-modules contract and target adapter`;
- repository contract: `python scripts/check_repo_contract.py` -> `Repository contract OK`;
- Ruff: `ruff check .` -> `All checks passed!`;
- tests: `PYTHONPATH=.;src python -m pytest -q` -> `64 passed`;
- render check: no horizontal overflow at 1440px, 900px, or 390px; all four preview images loaded at each viewport;
- PDF: `review-output/content-system-preview.pdf` -> 4 A4 pages; rendered page images inspected with no clipped content.

Decisions:

- keep the existing README unchanged until user review;
- use one hero plus supporting wide, square, and portrait assets rather than alternate hero banners;
- make PDF pages intentionally section-based so the packet can be reviewed without a browser;
- keep generated review output local and ignored while source previews remain in Git.

Blocked/uncertain:

- whether the user wants the preview story promoted into the canonical README after inspection;
- additional target repositories for cross-repository dogfooding have not yet been supplied.

Next:

- commit and push this preview branch, open a PR, attach the helper/continuity references, and wait for user review before changing README.md.

### 2026-09-20 — Codex CI correction

Completed:

- diagnosed and corrected the first preview-branch CI failure;
- merged current Eval Lab `main` into the preview branch so it contains the accepted `PYTHONPATH=.:src` workflow fix from TASK-0013;
- reran the GitHub Actions matrix successfully.

Evidence:

- initial push run `35545998206` failed during collection with `ModuleNotFoundError: No module named 'scripts'` because the branch was created from stale local `origin/main` at `345e731`;
- current `main` is `82047d9` and contains the workflow environment fix;
- corrected push run `35546113184` passed `contract-and-tests (3.11)` and `contract-and-tests (3.12)`;
- PR #30 is open and clean with all required checks passing.

Decisions:

- treat the initial failure as a branch-base synchronization defect, not a content-system or research-test defect;
- keep historical failed runs visible for audit rather than deleting them;
- require future worktrees to verify their base ref against current `main` before pushing.

Blocked/uncertain:

- none; PR #30 remains intentionally unmerged pending user review.

Next:

- review the rendered Markdown/HTML/PDF artifacts and decide whether to promote the content system into the canonical README.

### 2026-09-20 — Narrative image text contract update

Completed:

- advanced the adapter pin to `content-generation-modules` v0.1.2 at `cb8c18fa7789e4b651e1f963892bf056b0d3276d`;
- regenerated the problem, square system, and portrait evidence raster assets with restrained exact title/subtitle copy while preserving the accepted hero and text-free SVG icons;
- recorded the exact image copy and visual rule in the manifest and visual style contract.

Evidence:

- problem title/subtitle: `Plausible is not proven` / `A confident answer still needs evidence before it becomes a judgment.`;
- system title/subtitle: `Judge the uncertainty` / `Compare evidence, measure confidence, and route the hard cases.`;
- evidence title/subtitle: `Keep the trail` / `Every verdict should point back to data, rules, and review.`;
- generated assets visually inspected for subject visibility, low noise, and readable copy.

Decisions:

- keep one hero only; supporting assets use wide, square, and portrait roles for device coverage;
- retain SVG icons without embedded words because they are helper visuals rather than narrative illustrations;
- keep README promotion and merge gated on user review.

Blocked/uncertain:

- none for the adapter or asset update; final human acceptance remains open.

Next:

- rerun adapter, repository, and responsive render validation, push the updated preview branch, and update PR #30 for review.

### 2026-09-20 — README promotion staged

Completed:

- updated the canonical README on the preview branch with the reviewed story, bold/italic skim cues, the CGM contract reference, and the approved wide, square, and portrait assets;
- kept the existing technical explanation and SVG helper-icon system intact;
- updated the preview footer and checkpoint text so they describe README promotion as staged rather than merely proposed.

Evidence:

- README image paths resolve to the committed assets;
- local contract, Ruff, and 64-test gates remain green;
- GitHub Actions push and pull-request runs `35549659966` and `35549662574` pass on Python 3.11 and 3.12.

Decisions:

- keep the README update in PR #30 until the user reviews the rendered result;
- do not change research code, experiment artifacts, or runtime behavior.

Blocked/uncertain:

- none; merge is waiting only on explicit human review.

Next:

- review the updated README in PR #30 and merge only after acceptance.

## Handoff

Fresh session: read `PROJECT.md`, `checkpoints/CURRENT.md`, this task, and the relevant content-system adapter files. Validate the adapter from the pinned helper commit before editing the preview or requesting review. Do not change research code or merge this preview without user approval.
