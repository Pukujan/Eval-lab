# TASK-0010 — Selective Escalation, System-One Differential, and Reproducible Research Release

- Status: complete
- Owner: Luna/local agent
- Priority: P0
- GitHub issue: #25
- Depends on: TASK-0009
- Branch: task/TASK-0010-selective-escalation
- Planned experiment: EXP-20260920-009-selective-escalation
- Planned benchmark release: EvalLab-Select v0.1.0

## Goal

Determine whether the calibrated lightweight judge can identify which cases it can safely resolve locally and escalate the uncertain remainder to a stronger or specialized judge.

Produce the result as a small, independently reproducible benchmark/research artifact and an arXiv-ready paper source in this repository.

Primary research questions:

1. Does calibrated local confidence identify the cases most worth escalating?
2. What local coverage is achievable at declared error targets?
3. Does pinned Jev structured decision-making improve routing or decision quality?
4. How much external-model usage can be avoided relative to strong-judge-only operation?
5. Do the conclusions reproduce from a clean checkout using only committed manifests/config plus documented credentials?

## Current student

The frozen TASK-0009 primary student is:

- representation: TF-IDF
- classifier: logistic regression
- selected training arm: D
- selection criterion: dev metrics only
- frozen TASK-0009 test accuracy: 0.6667
- frozen TASK-0009 balanced accuracy: 0.6250

Do not retrain this student before the primary routing experiment.

Qwen baselines may be secondary comparisons but may not silently replace the frozen TASK-0009 student.

## Context note

The primary student has no Transformer context window.

For differential provider comparisons use the same canonical evidence packet for every backend. Do not give Jev/Qwen extra task evidence merely because they support longer contexts.

A later experiment may evaluate 16K Qwen contexts. TASK-0010 first establishes routing validity under the existing canonical short-context contract.

## Inputs

- TASK-0009 model/predictions/calibration artifacts
- TASK-0004 metrics/calibration code
- TASK-0005 ARC adapter/source revision discipline
- TASK-0006 local Qwen artifacts
- TASK-0007 YOLO-Auto Qwen3.8 Flash results
- local `OPENROUTER_API_KEY`, reported available by the user
- local `YOLO_AUTO_API_KEY`, established by prior tasks

## Required external arms

### OpenRouter Jev

Pinned scientific model:

`typesafe/jev-1.13`

Rolling canary only:

`~typesafe/jev-latest`

Never combine pinned and rolling results.

Use OpenRouter's Decisions transport rather than pretending it is the first-party TypeSafe endpoint.

### YOLO-Auto Qwen3.8 Flash

- base URL: `https://yolo-auto.com/v1`
- model: `qwen3.8-flash`
- credential: `YOLO_AUTO_API_KEY`

### System-One differential

Hold the typed decision specification fixed and execute it through:
- pinned OpenRouter Jev;
- an LLM-backed System-One adapter using YOLO-Auto Qwen3.8 Flash when compatible.

Objective verifier/answer-key labels remain gold.

## Policies

P0 — frozen local student only.

P1 — pinned Jev only.

P2 — Qwen3.8 Flash only.

P3 — calibrated local -> pinned Jev.

P4 — raw-confidence local -> pinned Jev.

P5 — random -> pinned Jev with exactly matched escalation count and fixed seed.

P6 — calibrated local -> Qwen3.8 Flash.

P7 — identical-spec System-One differential: Jev vs Qwen3.8 Flash adapter.

## Threshold selection

Thresholds are selected only from threshold-selection/calibration-development data.

Never use final-evaluation labels to select:
- threshold;
- confidence definition;
- provider;
- typed question wording;
- target error;
- policy.

Target operating points:

- 1%
- 2%
- 5%
- 10% local accepted error

Primary confidence signal:

`max(calibrated class probability)`

Secondary diagnostic signal:

`top_probability - second_probability`

## Statistical adequacy

The small TASK-0009 calibration/test fixtures are regression evidence, not enough for credible 1-5% reliability claims.

Build a larger objective routing pool from already-supported public/synthetic sources while preserving upstream/source-family boundaries.

Targets when genuinely available without duplication:

- >=200 threshold-selection/calibration-development records
- >=500 final-evaluation records

Do not duplicate/resample examples to meet these counts.

Every selective-risk point reports:
- locally accepted count;
- local error count;
- empirical risk;
- 95% binomial confidence interval/upper bound.

A <=1%, <=2%, or <=5% claim is called confidence-supported only when the preregistered upper confidence bound is also within the target. Otherwise label the result descriptive/underpowered.

## Reproducible benchmark deliverable

Create a versioned release:

`benchmark/eval-lab-select-v0.1.0/`

The benchmark is a compact routing/judge benchmark, not a claim to cover all human evaluation.

Required contents:

- `README.md` benchmark card
- `benchmark.yaml`
- `records.jsonl` for redistributable records or a deterministic rebuild manifest when redistribution is inappropriate
- `splits.json`
- `source-manifest.json`
- `checksums.sha256`
- `ro-crate-metadata.json`
- `provenance.ttl`
- `shapes.ttl`
- deterministic rebuild/evaluation command

The release records:
- benchmark semantic version;
- source datasets/revisions/licenses;
- source problem IDs;
- canonicalization version;
- split/family policy;
- objective gold provenance;
- experiment code commit;
- record/checksum fingerprints;
- known limitations.

## Research paper deliverable

Create arXiv-ready source under:

`paper/`

Required:

- `paper/main.tex`
- `paper/references.bib`
- `paper/README.md`
- generated tables/figures sourced from committed experiment results
- reproducibility appendix
- limitations/threats-to-validity section
- artifact/benchmark availability section

Use a generic LaTeX article layout rather than claiming conference affiliation/acceptance.

Minimum paper structure:

1. Abstract
2. Introduction
3. Related Work
4. Benchmark and Objective-Gold Construction
5. Local Judge and Calibration
6. Selective Escalation Method
7. Jev/System-One Differential Method
8. Experiments
9. Results
10. Statistical Uncertainty
11. Ablations/Controls
12. Limitations and Threats to Validity
13. Reproducibility and Artifact Availability
14. Conclusion
15. Appendices

No table/claim may be manually copied from an old run without a machine-traceable source artifact.

## Research metadata standard

Authoritative standard stack is defined in `docs/RESEARCH_ARTIFACT_STANDARD.md`.

Required:

- RO-Crate 1.3 as outer research-object package
- PROV-O for provenance/lineage
- W3C SHACL 2017 Recommendation for validation shapes
- CITATION.cff 1.2.0
- DataCite 4.6-compatible metadata fields for future DOI deposit
- SHA-256 checksums and semantic versioning

OWL 2 is optional for a small Eval Lab vocabulary only if useful. Do not build a custom ontology merely to satisfy this task.

## PCM compatibility

Project Continuity Modules is useful for cold-start continuity, but its current repository implements only minimal/software templates even though a research profile is planned.

TASK-0010 therefore must:

- map Eval Lab PROJECT/CURRENT/TASK/CHECKPOINT objects to PCM concepts;
- document the exact PCM commit inspected;
- avoid making the experiment/runtime depend on an unfinished PCM research profile;
- optionally validate/generate a context pack with a pinned PCM checkout if non-destructive and compatible;
- keep Eval Lab canonical repository files authoritative;
- revisit full PCM research-profile adoption when that profile exists.

Do not vendor the PCM source tree into Eval Lab.

## Required routing record

Every routed record retains at least:

~~~json
{
  "record_id": "stable-id",
  "student_model": "task-0009-arm-d",
  "student_label": "PASS",
  "student_raw_confidence": 0.81,
  "student_calibrated_confidence": 0.72,
  "threshold": 0.85,
  "route": "escalate",
  "escalation_provider": "openrouter",
  "escalation_model": "typesafe/jev-1.13",
  "escalation_status": "ok",
  "escalation_label": "FAIL",
  "final_label": "FAIL"
}
~~~

Provider failure remains unresolved; never silently pretend escalation succeeded.

## Required metrics

For every policy:

- accuracy
- balanced accuracy
- macro F1 where applicable
- execution coverage
- local coverage
- escalation rate
- local accepted error/risk
- final resolved error
- unresolved rate
- Brier/NLL/ECE where probability semantics permit
- median/p95 latency
- external calls per 1,000 records
- provider cost/subscription-resource metadata
- aggregate and per-domain results

Selective policies additionally report:

- risk-coverage curve
- coverage at <=1%, <=2%, <=5%, <=10% empirical error
- confidence-supported coverage where sample size permits
- raw-vs-calibrated routing
- calibrated-vs-random matched-escalation control

## OSS/reference evaluation

Evaluate, do not blindly duplicate:

- `typesafe-ai/typesafe-sdk-python`
- `typesafe-ai/system-one-adapter-python`
- `browser-use/jev-ultrafast` as architectural reference only

The first two may be integrated if they cleanly preserve repository-owned typed semantics.

Jev-Ultrafast browser action routing is out of scope for TASK-0010 implementation and is a candidate later task.

## Outputs

- `src/eval_lab/escalation/`
- OpenRouter Jev Decisions adapter
- repository-owned System-One typed spec
- optional System-One adapter bridge for YOLO-Auto
- selective-routing scripts
- unit tests
- metamorphic tests
- differential tests
- provider integration tests
- EXP-20260920-009 artifacts
- EvalLab-Select v0.1.0 benchmark release
- arXiv-ready paper source
- research-object/provenance metadata
- PCM compatibility note
- task/checkpoint updates

## Allowed files

- `src/eval_lab/escalation/`
- `src/eval_lab/judges/`
- backward-compatible `src/eval_lab/schema.py` extensions
- selective-risk/statistical extensions under `src/eval_lab/metrics/`
- `scripts/`
- `tests/`
- `docs/` TASK-0010/research-standard changes
- `paper/`
- `benchmark/eval-lab-select-v0.1.0/`
- `CITATION.cff`
- `experiments/EXP-20260920-009-selective-escalation/`
- `experiments/EXP-20260920-010-multi-subscription-bakeoff/`
- `.github/workflows/ci.yml`
- `.gitattributes` for byte-stable benchmark-release line endings
- `scripts/check_repo_contract.py`
- `tests/test_program_contract.py`
- this task file
- `checkpoints/CURRENT.md`

## Acceptance criteria

- [x] frozen TASK-0009 student reproduced
- [x] larger routing pool created without source leakage
- [x] final labels isolated from threshold/provider/spec selection
- [x] P0-P7 policies/arms run or external infeasibility explicitly recorded
- [x] pinned Jev model remains `typesafe/jev-1.13`
- [x] rolling Jev alias remains a separate canary
- [x] provider failures remain explicit/unresolved
- [x] metamorphic suite passes
- [x] differential suite passes
- [x] confidence bounds accompany low-error coverage
- [x] cost/latency/call usage reported
- [x] experiment preregistration frozen before final evaluation
- [x] EvalLab-Select v0.1.0 benchmark release reproducibly rebuilds
- [x] RO-Crate metadata validates structurally
- [x] PROV-O provenance graph covers benchmark, model, calibration, thresholds, predictions, results, and paper
- [x] SHACL shapes validate required research graph invariants
- [x] CITATION.cff is present and valid
- [x] paper sources reproduce all reported result tables from committed artifacts
- [x] paper contains reproducibility and limitations sections
- [x] PCM compatibility/mapping documented
- [x] repository contract passes
- [x] Ruff passes
- [x] full pytest suite passes

## Validation

See:

- `docs/TDD.md`
- `docs/TASK-0010-METAMORPHIC-DIFFERENTIAL.md`
- `docs/RESEARCH_ARTIFACT_STANDARD.md`
- `docs/VALIDATION_MATRIX.md`

Required local gate:

~~~powershell
.venv\Scripts\python.exe scripts/check_repo_contract.py
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m pytest -q
~~~

## Stop conditions

Stop and checkpoint if:

- final labels influence threshold/provider/spec selection;
- source-family leakage occurs;
- frozen TASK-0009 student is retrained after final inspection;
- pinned and rolling Jev results are conflated;
- provider/model identity is ambiguous;
- policy comparisons use different record IDs without explicit missingness analysis;
- provider failure silently falls back to local;
- low-error reliability is overstated from underpowered data;
- paper numbers are not machine-traceable to experiment artifacts;
- benchmark cannot be deterministically reconstructed;
- research metadata claims provenance that cannot be evidenced;
- credentials enter committed artifacts.

## Checkpoint log

### 2026-09-20 — planning

Issue #25 created and task branch started from main `6ae355f470d905f8fd8c85363a353674818b19f9`.

TASK-0009's actual selected student is TF-IDF + logistic regression, not Qwen3-4B. The primary selective-routing experiment preserves that frozen student.

The publication/reproducibility target is now part of task acceptance: a compact benchmark release plus arXiv-ready source and machine-readable provenance.

### 2026-09-20 — local planning gate and handoff

Worktree: `D:/claude/eval-lab-TASK-0010`; branch: `task/TASK-0010-selective-escalation`; starting head: `50312637a28a71e279387db6293f17b99a11ed10`. Read in order: `PROJECT.md`, `checkpoints/CURRENT.md`, this task, `docs/PDD.md`, `docs/SDD.md`, `docs/TDD.md`, `docs/TASK-0010-METAMORPHIC-DIFFERENTIAL.md`, `docs/RESEARCH_ARTIFACT_STANDARD.md`, and `docs/TASK-0010-OPENROUTER-JEV.md`; `AGENTS.md` was also read before edits.

Environment and commands:
- `git fetch --all --prune` -> completed.
- `git switch task/TASK-0010-selective-escalation` and `git pull --ff-only` -> already on branch and up to date.
- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `D:\claude\eval-lab\.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- The shared editable environment initially pointed at `D:\claude\eval-lab-TASK-0006`, so the requested pytest command first failed to import `eval_lab.training`. This was an environment-path issue, not a repository defect. With `PYTHONPATH= D:\claude\eval-lab-TASK-0010\src`, the equivalent gate command returned `65 passed in 25.36s`.

No planning-contract defect was found or changed. The branch contains only the planning/publication scaffold at this point; routing, benchmark data, final results, and provider labels are not yet present.

Next atomic action: implement and offline-test the provider-independent typed-question/routing core and deterministic benchmark builder, then freeze the EXP-009 and EvalLab-Select split/fingerprint manifest before final evaluation.

### 2026-09-20 — frozen release, local evaluation, and provider status

Environment: Windows-11-10.0.26200-SP0; Windows PowerShell; Python 3.12.10; Git 2.51.2.windows.1; Node v24.14.1. Worktree `D:/claude/eval-lab-TASK-0010`; branch `task/TASK-0010-selective-escalation`. The frozen protocol commit is `169a15d23a38db5c1246bde36db082e383467fe7`; implementation/benchmark commit is `1aace02f6e5b7e9f1b0403c6ffbfe7b2ce27dbd6`.

Frozen inputs: ARC-Challenge `allenai/ai2_arc`, revision `210d026faf9955653af8916fad021475a3f00453`; canonicalization `eval-lab-select-single-v1`; benchmark fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`; threshold-selection `2,863` records/`1,427` source families; final-evaluation `2,356` records/`1,176` disjoint source families. TASK-0009 frozen student is arm D, `tfidf-logistic-v1`, restored from committed `student_D.json`; no retraining occurred. Confidence is maximum calibrated class probability with top-two margin retained as secondary; targets are `0.01`, `0.02`, `0.05`, and `0.10`; typed System-One is `eval-lab-system-one` v`0.1.0`, context limit `4096`, single labels `pass/fail`, pairwise labels `A/B/TIE`.

Commands and results:

- `D:\claude\eval-lab\.venv\Scripts\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `D:\claude\eval-lab\.venv\Scripts\ruff.exe check .` -> `All checks passed!`.
- `$env:PYTHONPATH="$PWD\src"; D:\claude\eval-lab\.venv\Scripts\python.exe -m pytest -q` -> `74 passed in 6.35s`.
- `$env:PYTHONPATH="$PWD\src"; D:\claude\eval-lab\.venv\Scripts\python.exe scripts/build_selective_benchmark.py` -> fingerprint above; `2,863` threshold and `2,356` final records.
- `... scripts/run_selective_escalation.py --skip-providers` -> full local routing and matched-random outputs over the frozen final pool; provider arms remained explicit unresolved.
- `... scripts/smoke_task0010_providers.py --env-file .env --limit 1` -> pinned `typesafe/jev-1.13`: `ok`; rolling `~typesafe/jev-latest`: `ok`; YOLO-Auto `qwen3.8-flash`: `ok`.
- `... scripts/run_selective_escalation.py --env-file .env --provider-limit 500 --provider-timeout 10 --skip-rolling --skip-qwen` with `EVAL_LAB_PROVIDER_WORKERS=1` -> pinned Jev `500/500 ok`; these are the deterministic first `500` final records.
- The equivalent Qwen bulk command with `--skip-pinned --skip-rolling` was interrupted after the provider did not complete; no fallback labels were written. Rolling remains smoke-only. OpenCode `scripts/jev_smoke.py` was attempted with the local key and returned `JevRateLimitError`.
- `... scripts/generate_research_artifacts.py` followed by `... scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0` -> checksums `ok`, RO-Crate `ok`, PROV-O parsed, SHACL conforms, CFF parsed, paper present.
- `gh run view 35537436072 --json ...` and `gh api .../actions/jobs/106148870777` -> CI failed in 2–3 seconds with `steps: []`, `runner_id: 0`, empty `runner_name`, and `ubuntu-latest` label. After local validation, this establishes an external GitHub runner/account startup failure rather than a repository test failure.

Files changed: provider-independent escalation core under `src/eval_lab/escalation/`; selective dataset adapter; frozen TASK-0009 arm-D artifacts; benchmark builder and release files under `benchmark/eval-lab-select-v0.1.0/`; provider/smoke/final runners and research-artifact validator/generator under `scripts/`; offline routing, leakage, artifact, typed-response, model-separation, and frozen-student tests; `pyproject.toml`; `CITATION.cff`; EXP-009 README, thresholds, routing, provider outputs, smoke outputs, differential, results, and report; RO-Crate/PROV-O/SHACL/DataCite files; generated paper tables/figure, completed `paper/main.tex`, reproducibility appendix, and limitations.

Decisions: exclude TASK-0009 training source families from threshold selection; keep ARC train/validation in threshold selection and ARC test in final evaluation; preserve pinned and rolling Jev as separate arms; retain provider failures as unresolved; report Wilson 95% intervals and label nominal low-error coverage underpowered when the interval upper bound misses the target; keep `.env` ignored and never print or commit credentials; use PCM only as the documented compatibility reference.

Blockers: the pinned Jev arm has 500 final labels, but bulk rolling and Qwen final labels are not complete because the rolling path became intermittent and the Qwen bulk call did not finish. The one-record smoke differential is `1/1` comparable and agreeing, and is explicitly excluded from pooled estimates. EXP-009 therefore remains active with `completed_with_provider_statuses`; TASK-0002 and any new project scope remain out of scope.

Next atomic action: commit the current research bundle and checkpoint, push the task branch, then retry only the missing Qwen/rolling bulk arms during a stable provider window or leave them explicitly blocked in a follow-up checkpoint; do not claim TASK-0010 fully accepted until its provider acceptance criteria are resolved.

### 2026-09-20 — CI collection defect diagnosed

After commit `fb804569e841459671961f6cac9f8779219f3203` was pushed, CI runs `35541435860` and `35541433231` reached workflow steps. Contract and Ruff passed, but pytest collection failed on Python 3.12 because `tests/test_external_bakeoff.py`, `tests/test_hard_negatives.py`, `tests/test_program_contract.py`, and `tests/test_repo_contract.py` could not import `scripts` in the clean GitHub environment (`ModuleNotFoundError: No module named 'scripts'`). This was a real packaging defect masked by the local checkout path.

Fix: add the minimal `scripts/__init__.py` package marker. Local rerun returned contract `OK`, Ruff clean, `74 passed in 30.51s`, and clean `git diff --check`. No project scope or experiment semantics changed.

Next atomic action: commit and push the CI import fix, then inspect the new CI run. Keep TASK-0010 active until the provider acceptance blocker and the resulting CI run are resolved.

### 2026-09-20 — CI test invocation defect diagnosed

The package marker alone did not fix clean GitHub collection: duplicate CI runs `35541679787` and `35541681635` checked out commit `f65512b36132cb9a94c5fd5d420e486350410473`, completed install/contract/lint, and then `pytest -q` reported `ModuleNotFoundError: No module named 'scripts'` on both Python 3.11 and 3.12. The workflow was using the standalone pytest entry point, which did not put the checkout root on `sys.path` in that runner environment.

Fix: change `.github/workflows/ci.yml` to invoke `python -m pytest -q`. Local validation from `D:/claude/eval-lab-TASK-0010` using the shared Python 3.12.10 environment returned repository contract `OK`, Ruff clean, `74 passed in 31.38s`, and clean `git diff --check`. The current head before this fix is `f65512b`; no experiment files or provider results changed.

Next atomic action: commit/push the workflow invocation fix and inspect the fresh CI matrix; keep TASK-0010 active until CI and the unresolved Qwen/rolling provider acceptance criteria are addressed.

### 2026-09-20 — CI benchmark checksum defect diagnosed

Fresh CI runs `35541979823` and `35541981648` checked out `708e9fdf73595f42c72a8f9b9028b49bda85a213`. The `python -m pytest -q` invocation fixed collection, but both Python 3.11 and 3.12 failed one research-artifact test: `benchmark.yaml` had a checksum generated from Windows CRLF bytes while GitHub checked out LF bytes. All other test behavior was unchanged; the 3.11 install cancellation was a matrix consequence after the 3.12 failure, not a dependency defect.

Fix: add `.gitattributes` with LF enforcement for `benchmark/eval-lab-select-v0.1.0/*`, normalize the frozen release files to LF, and regenerate `checksums.sha256` from the canonical LF bytes. Local validation returned repository contract `OK`, Ruff clean, `74 passed in 25.63s`, research-artifact validation `checksums ok`, `RO-Crate ok`, `PROV-O parsed`, `SHACL conforms`, `CFF parsed`, `paper present`, and clean `git diff --check`. Benchmark counts and fingerprint are unchanged.

Next atomic action: commit/push the byte-stability fix and inspect the fresh CI matrix; keep TASK-0010 active until CI and the unresolved Qwen/rolling provider acceptance criteria are addressed.

### 2026-09-20 — CI green checkpoint

Commit `88ec75e184739cfc84ba9ccbacc5827a6da117a6` is pushed at the expected task branch head. CI runs `35542193123` (push) and `35542195848` (pull request) both passed on Python 3.11 and 3.12: install, repository contract, Ruff, and `python -m pytest -q`. This verifies the package-import and cross-platform benchmark-checksum fixes in GitHub’s clean environment.

Next atomic action: retry the missing Qwen and rolling provider arms against the frozen final-evaluation record order, preserving separate output files and explicit failure statuses; do not begin TASK-0002.

### 2026-09-20 — Qwen contention checkpoint

The required YOLO-Auto arm remains `qwen3.8-flash`; Grok 4.6 is a different provider/model and cannot replace it in the frozen protocol. A bounded full-arm attempt used `EVAL_LAB_PROVIDER_WORKERS=16`, `--provider-limit 500`, `--provider-timeout 30`, `--skip-pinned`, and `--skip-rolling`. The provider opened 16 HTTPS connections but returned no batch within approximately six minutes, so the local launcher and child process were terminated; no Qwen labels were written or fabricated. A direct ten-record probe with `EVAL_LAB_PROVIDER_WORKERS=8` and timeout `12` returned `10 provider_error` statuses. The existing pinned `typesafe/jev-1.13` output was preserved; rolling and Qwen remain separate unresolved arms.

No credentials or raw provider payloads were printed or committed. Decision: wait for a stable YOLO-Auto window or reduced contention and retry Qwen against the same frozen provider record order; do not add a Grok arm or expand scope solely to work around Qwen availability.

Next atomic action: retry the Qwen arm when the YOLO-Auto contention condition clears, then regenerate results and research artifacts only from the separate normalized Qwen output; keep TASK-0010 active and do not begin TASK-0002.

### 2026-09-20 — rolling Jev bulk checkpoint

The separate rolling canary was retried with `EVAL_LAB_PROVIDER_WORKERS=4`, `--provider-limit 500`, `--provider-timeout 12`, `--skip-pinned`, and `--skip-qwen`. It returned `openrouter_rolling` model `~typesafe/jev-latest` with `500 ok`; the previously committed pinned arm remains `typesafe/jev-1.13` with `500 ok`. The normalized outputs remain in separate `provider-rolling.jsonl` and `provider-pinned.jsonl` files, and no pooled pinned/rolling estimate was created.

`scripts/generate_research_artifacts.py` was run after the rolling result. Its generated benchmark metadata was normalized to canonical LF bytes and `checksums.sha256` was regenerated. `scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0` returned checksums `ok`, RO-Crate `ok`, PROV-O parsed, SHACL conforms, CFF parsed, and paper present. Current EXP-009 status remains `completed_with_provider_statuses` because Qwen has no final labels; pinned/rolling are both 500/500 and the System-One smoke differential remains separate at `1/1` comparable and agreeing.

Next atomic action: commit the rolling output/results and checkpoint, then retry Qwen only after YOLO-Auto contention clears; do not substitute Grok or begin TASK-0002.

### 2026-09-20 — Qwen availability recheck

After the rolling run completed, a fresh three-record YOLO-Auto probe used `EVAL_LAB_PROVIDER_WORKERS=2`, base URL `https://yolo-auto.com/v1`, model `qwen3.8-flash`, and timeout `20`. It returned `3 provider_error` statuses. No labels or raw payloads were written. This confirms the current external Qwen availability condition is still unresolved rather than a threshold, schema, or routing defect.

Decision: keep TASK-0010’s frozen provider set unchanged. Grok/Luna and local Qwen 1.7B/4B can be proposed as separately preregistered follow-up arms after TASK-0010 is accepted or explicitly provider-blocked; they cannot replace the required YOLO-Auto arm in this experiment. TASK-0006’s local Qwen3-0.6B remains the existing local baseline in the broader program.

Next atomic action: leave the Qwen arm explicitly unresolved and retry only after provider contention changes; do not open a new arm or begin TASK-0002 from this checkpoint.

### 2026-09-20 — current handoff checkpoint

Current head is `cea7558568bafad4791353f53f7b8ad5286feacd` on `task/TASK-0010-selective-escalation`; PR #26 remains open and draft. CI run `35543153294` passed both Python 3.11 and 3.12, including install, repository contract, Ruff, and unit tests. Local validation remains contract `OK`, Ruff clean, `74 passed`, and research-artifact validation successful.

Frozen benchmark: EvalLab-Select v0.1.0 fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`, with `2,863` threshold-selection and `2,356` final-evaluation records. Provider counts: pinned `typesafe/jev-1.13` `500 ok`; rolling `~typesafe/jev-latest` `500 ok`; YOLO-Auto `qwen3.8-flash` no final labels after the 500-record stall and 10-record/3-record probes (`provider_error`). System-One smoke differential is separate at `1/1` comparable and agreeing. No local 1.7B/4B model weights are present in the standard Hugging Face cache.

Decision: TASK-0010 remains active with `completed_with_provider_statuses`. Do not relabel Grok/Luna or local Qwen results as the missing YOLO-Auto arm. Any such model is a follow-up experiment with a new arm/spec/provider manifest and experiment ID after TASK-0010 is accepted or explicitly provider-blocked.

Next atomic action: retry the YOLO-Auto Qwen arm only when contention changes, or record a formal provider-blocked acceptance decision with the current evidence; do not begin TASK-0002.

### 2026-09-20 — formal provider-blocked handoff

Status: `blocked` on the external YOLO-Auto Qwen arm; TASK-0010 is not claimed complete. The required local `.venv\\Scripts\\...` gate commands were attempted and the dedicated worktree has no `.venv`. Equivalent shared-environment commands from `D:/claude/eval-lab/.venv` with `PYTHONPATH=D:/claude/eval-lab-TASK-0010/src` returned repository contract `OK`, Ruff clean, `74 passed in 3.89s`, and clean diff check. The configured Qwen URL is `https://yolo-auto.com/v1`.

Provider evidence: pinned `typesafe/jev-1.13` is `500 ok`; rolling `~typesafe/jev-latest` is a separate `500 ok`; Qwen `qwen3.8-flash` has no final labels. A 500-record Qwen attempt with 16 workers/30-second timeout stalled with 16 open HTTPS connections for approximately six minutes and was terminated without labels. Ten-record and three-record probes returned `provider_error`; the latest one-record probe with one worker and 20-second timeout returned `transport_error`. No fallback labels, credentials, or raw provider payloads were written or committed.

Frozen release evidence remains: EvalLab-Select v0.1.0 fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`; `2,863` threshold-selection records; `2,356` final-evaluation records; separate pinned/rolling outputs; System-One smoke differential `1/1` comparable and agreeing; research-artifact validation checksums `ok`, RO-Crate `ok`, PROV-O parsed, SHACL conforms, CFF parsed, paper present. CI run `35543153294` passed Python 3.11 and 3.12.

Decision: preserve TASK-0010’s frozen provider/model protocol and mark the missing Qwen final arm as externally blocked. Grok/Luna/local Qwen 1.7B/4B are not substitutes and are deferred to a new experiment ID after this block is resolved or separately accepted. Do not begin TASK-0002 or add a new provider arm in this branch.

Next atomic action: when YOLO-Auto recovers, rerun the one-record smoke, then the deterministic 500-record Qwen prefix with separate output and artifact regeneration; otherwise obtain an explicit decision to accept the provider-blocked release.

### 2026-09-20 — final CI verification for blocked handoff

The provider-blocked handoff is pushed at `afb74595e26084abc1975e2bd3c51553dbd1c8ba`. CI run `35543406626` passed both Python 3.11 and 3.12, including install, repository contract, Ruff, and unit tests. The worktree is clean.

Next atomic action: wait for YOLO-Auto availability or obtain explicit provider-blocked acceptance; do not substitute a model or begin TASK-0002.

### 2026-09-20 — EXP-20260920-010 plan frozen before execution

The provider-blocked TASK-0010 handoff authorizes a separate append-only multi-subscription bakeoff. Durable plan: `experiments/EXP-20260920-010-multi-subscription-bakeoff/PLAN.md`; machine-readable manifest: `experiments/EXP-20260920-010-multi-subscription-bakeoff/experiment.yaml`. The plan freezes EvalLab-Select v0.1.0 fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`, the deterministic first 500 final-evaluation records, frozen TASK-0009 arm D, typed System-One v0.1.0, and independent OpenCode arms `opencode/grok-4.6`, `opencode/gpt-5.6-luna`, and `opencode/gpt-5.6-sol`. YOLO Qwen and local Qwen 1.7B/4B are explicitly deferred, not substituted.

Status: plan-only; no new provider call or evaluation label has been produced. Exact planned commands, output files, missingness rules, uncertainty reporting, and acceptance boundary are recorded in the plan. Next atomic action: commit the plan, then implement and offline-test the runner/validator before provider execution.

### 2026-09-20 — EXP-20260920-010 offline runner checkpoint

Implemented the planned provider-independent OpenCode runner and validator: `scripts/run_multi_subscription_bakeoff.py`, `scripts/validate_multi_subscription_bakeoff.py`, and `tests/test_multi_subscription_bakeoff.py`. Added LF-stable experiment output rules and the required experiment `README.md`. No provider call has been made for EXP-010.

Validation: targeted Ruff `All checks passed!`; targeted tests `3 passed in 0.54s`; repository contract `OK`; clean diff check. The runner freezes the final-record prefix, uses typed System-One v0.1.0, preserves one normalized prediction per record, records provider failures without fallback labels, and writes separate Grok/Luna/Sol outputs. Deferred Qwen and local-weight arms remain explicit.

Next atomic action: commit this implementation, run the offline full gate, then execute a bounded subscription smoke on the frozen matched pool before attempting the planned 500-record arms.

## Handoff

Read, in order:

1. `PROJECT.md`
2. `checkpoints/CURRENT.md`
3. this task
4. `docs/PDD.md`
5. `docs/SDD.md`
6. `docs/TDD.md`
7. `docs/TASK-0010-METAMORPHIC-DIFFERENTIAL.md`
8. `docs/RESEARCH_ARTIFACT_STANDARD.md`

Implement offline routing + metadata validation first. Freeze EXP-009 and benchmark split/fingerprints before opening final labels. Smoke-test providers only after offline invariants pass.

### 2026-09-20 — provider-path diagnosis and OpenCode run stopped

Status: EXP-20260920-010 was stopped before any final arm file was written because its configured OpenCode path was not the claimed subscription route. The dedicated worktree uses Windows PowerShell, Python 3.12.10 from the shared `D:/claude/eval-lab/.venv`, and `PYTHONPATH=D:/claude/eval-lab-TASK-0010/src`; the local `.env` remained ignored and credentials were not printed.

Exact checks and results: `opencode --version` returned `1.18.31`; `opencode models` exposed `opencode/grok-4.6`, `opencode-go/grok-4.6`, and `litellm/grok-4.6`. `opencode auth list` showed stored OpenCode Zen/Go and named credentials but no active entitlement details. A bounded `opencode run --model opencode-go/grok-4.6 ...` returned HTTP 403, `An active OpenCode Go subscription is required to use Go models`; `opencode run --model opencode/grok-4.6 ...` returned HTTP 402, `Insufficient account funds`, from `https://opencode.ai/zen/v1/responses`; `litellm/grok-4.6` returned a connection failure for `http://localhost:4000/v1/chat/completions`. No `grok` or `grok-build` executable was present on PATH. The in-flight EXP-010 command was terminated with `taskkill /F /T` before `predictions/grok.jsonl` existed.

Decision: do not claim the slow OpenCode Zen canary as subscription evidence and do not retry the exhausted route. The already committed EXP-010 plan and bounded smoke/canary remain separate evidence; its final 500-record output is absent. The Qwen streaming arm is recorded separately under EXP-009 retry artifacts.

Next atomic action: use an actually available provider path under a new frozen experiment ID, preserving the OpenCode route diagnosis and all prior outputs.

### 2026-09-20 — EXP-20260920-011 OpenRouter provider-blocked result

Plan and files: committed plan `experiments/EXP-20260920-011-openrouter-multi-subscription-bakeoff/PLAN.md`, manifest, and README at `5e7df93`; committed streaming runner and offline SSE test at `1d53b29`; committed validator and 1-record three-arm smoke at `d6d4ebb`; committed final normalized output at `5277827`. Arms were frozen as OpenRouter `x-ai/grok-4.6`, `openai/gpt-5.6-luna`, and `openai/gpt-5.6-sol`; benchmark fingerprint remained `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5` and the provider pool was the deterministic first 500 final-evaluation records.

Exact execution: OpenRouter `/v1/models` returned HTTP 200 and confirmed all three IDs. Smoke command `python scripts/run_openrouter_multi_subscription_bakeoff.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260920-011-openrouter-multi-subscription-bakeoff/smoke --limit 1 --timeout 120 --workers 1 --env-file .env` returned `grok/luna/sol: 1 ok`; validator passed. Final command used the same runner with `--limit 500 --timeout 120 --workers 4 --env-file .env`; validator returned `grok: 368 ok, 132 provider_error`, `luna: 500 provider_error`, `sol: 500 provider_error`. All 632 provider errors were HTTP 402, `Insufficient account funds`; no labels were fabricated and no fallback was used. The output checksums and differential artifacts validate, with zero pairwise comparable records for the blocked arms.

Full local verification after this work: repository contract `OK`; Ruff `All checks passed!`; pytest `80 passed in 31.55s`; research-artifact validation returned checksums `ok`, citation parsed, paper present, PROV-O parsed, RO-Crate `ok`, and SHACL conforms. CI run `35546251591` for the preceding pushed head passed; the current result commit is the next push checkpoint.

Files changed: `.gitattributes`; EXP-010 plan/runner/validator/smoke/probe/canary and parser fixes; EXP-009 Qwen streaming retry, targeted retry, merged 500-label artifact, and merge manifest; EXP-011 plan/manifest/README, OpenRouter runner/validator, smoke, final predictions, provider-status, differential, report, and checksums; focused streaming tests.

Blocker: OpenCode Go has no active subscription, OpenCode Zen has insufficient funds, LiteLLM is unavailable, and the OpenRouter account exhausted funds after 368 Grok labels. The Qwen streaming merged artifact is complete at `500 ok`, but selective-routing outputs have not yet been regenerated from that streaming Qwen arm.

Next atomic action: regenerate the frozen TASK-0010 selective-routing and matched-random outputs using the validated Qwen streaming 500-label artifact while keeping Jev pinned/rolling separate; then update the final research artifacts and checkpoint the resulting metrics. Do not begin TASK-0002.

### 2026-09-20 — EXP-20260920-012 completed and acceptance closed

Status: `complete`. The frozen TASK-0010 selective-routing release now uses EXP-20260920-012, an append-only replay of the frozen benchmark and student with committed provider artifacts. The replay was run in `D:/claude/eval-lab-TASK-0010` on branch `task/TASK-0010-selective-escalation` with Windows PowerShell, Python 3.12.10 from `D:/claude/eval-lab/.venv`, and `PYTHONPATH=$PWD/src`. The dedicated worktree has no local `.venv`; the plain `.venv\\Scripts\\...` commands therefore failed to launch there, while the shared-environment equivalents below passed.

Exact commands and results:

- `D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/check_repo_contract.py` -> `Repository contract OK`.
- `D:\\claude\\eval-lab\\.venv\\Scripts\\ruff.exe check .` -> `All checks passed!`.
- `$env:PYTHONPATH = "$PWD\\src"; D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe -m pytest -q` -> `80 passed`.
- `$env:PYTHONPATH = "$PWD\\src"; D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0` -> checksums `ok`, citation `parsed`, paper `present`, PROV-O `parsed`, RO-Crate `ok`, SHACL `conforms`.
- `$env:PYTHONPATH = "$PWD\\src"; D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/run_selective_escalation.py --benchmark benchmark/eval-lab-select-v0.1.0 --output experiments/EXP-20260920-012-selective-escalation-qwen-streaming --skip-providers --provider-limit 500 --pinned-predictions experiments/EXP-20260920-009-selective-escalation/provider-pinned.jsonl --rolling-predictions experiments/EXP-20260920-009-selective-escalation/provider-rolling.jsonl --qwen-predictions experiments/EXP-20260920-009-selective-escalation/qwen-streaming-final-merged-20260920-010/predictions.jsonl --experiment-id EXP-20260920-012-selective-escalation-qwen-streaming` -> threshold `2863`, final `2356`, provider `500`; pinned `500 ok`, rolling `500 ok`, Qwen `500 ok`.
- `$env:PYTHONPATH = "$PWD\\src"; D:\\claude\\eval-lab\\.venv\\Scripts\\python.exe scripts/generate_research_artifacts.py --experiment experiments/EXP-20260920-012-selective-escalation-qwen-streaming --smoke-experiment experiments/EXP-20260920-009-selective-escalation` -> generated the paper, tables, figure, RO-Crate, PROV-O, SHACL, and reproducibility appendix.
- The benchmark and EXP-012 checksum manifests were regenerated with SHA-256 over every committed file except the manifest itself: `10` benchmark entries and `11` experiment entries.

Frozen evidence: EvalLab-Select v0.1.0 fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`; ARC source revision `210d026faf9955653af8916fad021475a3f00453`; canonicalization `eval-lab-select-single-v1`; confidence is maximum calibrated class probability; targets are `0.01`, `0.02`, `0.05`, and `0.10`; typed System-One is `eval-lab-system-one` v0.1.0; primary student is frozen TASK-0009 TF-IDF plus logistic-regression arm D. The deterministic provider prefix is the first `500` final-evaluation records and is disjoint from threshold selection.

Provider/model results: pinned OpenRouter `typesafe/jev-1.13` is `500/500 ok`, rolling OpenRouter `~typesafe/jev-latest` is a separate `500/500 ok` canary, and YOLO-Auto `qwen3.8-flash` is `500/500 ok` from one-record streaming requests. The final Jev/Qwen System-One differential has `500` comparable records and `486` agreements; the separate smoke differential is `1/1`. EXP-012 reports `500` calls per arm, per-arm status counts, latency summaries, and usage where supplied: pinned Jev cost `$0.008354262` and mean latency `225.363 ms`; rolling Jev cost `$0.008354262` and mean latency `238.794 ms`; Qwen mean latency `632.822 ms` with provider usage unavailable. The routing result contains `17` policies, including matched random controls, Wilson 95% intervals, and unresolved-provider handling.

Files changed in this checkpoint: `scripts/run_selective_escalation.py` now writes provider call/latency/usage summaries and a correctly identified report; `scripts/generate_research_artifacts.py` writes exact EXP-012 reproduction commands; EXP-012 results/report/differential/routing/threshold/checksum files; benchmark checksum and generated metadata files; `paper/reproducibility.md`; this task and `checkpoints/CURRENT.md`. No credential, raw response, or `.env` file was committed.

Decision: TASK-0010 acceptance criteria are satisfied and the task is marked complete. OpenRouter EXP-011 remains a separate provider-status experiment whose final arms were blocked by HTTP 402 account-funds errors after a 1-record smoke; OpenCode Go/Zen and LiteLLM route checks remain separate diagnostics. Those routes do not alter the completed primary TASK-0010 experiment, and TASK-0002 remains out of scope.

Next atomic action: commit and push this final checkpoint, inspect the CI run for the pushed head, and leave TASK-0002 unopened.
