# TASK-0064 - Grok Build harness correction and Grok re-run

## Status

In progress. GitHub issue #81. Branch `task/TASK-0064-grok-harness-correction`.

## Goal

Correct a Windows invocation defect that invalidated every Grok Build result in
EXP-022 and EXP-025, then re-run the Grok arms on the frozen EXP-015 records as a
new append-only experiment.

## Root cause

`scripts/run_grok_luna_qwen_bakeoff.py::_run_grok_build_one` and
`scripts/run_grok_protocol_ablation.py::run_one` built the Grok command as
`--single=<prompt>`. The prompt is two lines (one instruction plus a JSON
payload). On Windows `shutil.which("grok")` resolves to the `grok.CMD` shim, and
`subprocess.Popen` runs a `.CMD` through `cmd.exe`, which truncates the command
line at the first embedded newline. The model received only the instruction line
with no record payload and collapsed to a constant answer: `fail` in single mode
and `TIE` in pairwise mode. This matches the recorded EXP-022/EXP-025 pattern
(single accuracy ~0.50, pairwise accuracy ~0.019, mode-balanced ~0.26).

## Scope

- Fix the prompt delivery in both Grok runners: write the prompt to a unique
  per-record temp file and pass `--prompt-file <path>`; remove it in `finally`.
- Focused unit test asserting the prompt never travels through argv.
- New experiment `experiments/EXP-20261004-030-grok-harness-correction/`
  (append-only; EXP-022 and EXP-025 are not modified) that re-runs Grok 4.6 and
  Grok 4.7 over the frozen EXP-015 public and blind partitions.
- `scripts/finalize_grok_harness_correction.py`: assemble the experiment-level
  `results.json` and `report.md` from the two partition runs (offline, no
  provider calls, no hand-typed numbers).
- `docs/GROK_BUILD_CLI_AUTOMATION.md`: document the argv/newline failure mode.
- Regenerate the run telemetry ledger and update the paper where Grok is cited.
- Out of scope: the Qwen, Luna/Sol, and Jev arms; they do not use this
  invocation and are unaffected.

## Acceptance criteria

- Both Grok runners deliver the prompt by file; no `--single=` argv prompt
  remains in any committed script.
- The focused runner test passes and no live provider call is needed for it.
- A public canary recovers both modes (single and pairwise) before any blind run.
- EXP-022 and EXP-025 remain byte-identical.
- The new experiment has `experiment.yaml`, `README.md`, `results.json`, and
  `report.md`; the telemetry ledger is regenerated with `--check` green.
- Local gates pass: repo contract, Ruff, mypy, pytest, telemetry `--check`.

## Checkpoint log

### 2026-10-04 - diagnosis and fix

- Reproduced through the real runner: single 9/16 as-committed vs 16/16 with
  `--prompt-file`; pairwise 0/8 (all `TIE`) as-committed vs 8/8 fixed.
- Isolated the trigger: the same prompt with newlines replaced by spaces works
  inline, so the newline (not the JSON quotes) causes the truncation.
- Fixed `_run_grok_build_one` and `run_one` to use `--prompt-file`; added
  `_isolated_grok_prompt_file`.
- Added `test_grok_prompt_is_passed_by_file_not_argv`; focused tests pass.

### 2026-10-05 - full re-run started; ablation test; finalizer

- Started the full public re-run of EXP-030 in the background
  (`--partition public_selection --models grok,grok_47 --workers 4 --timeout 240`).
  Partial predictions confirm the fix live: varied labels (`fail` 61, `pass` 59,
  `A` 37, `B` 41), no constant `TIE`, surfaced model `grok-4.6-build`, all `ok`.
- Added `test_ablation_prompt_is_passed_by_file_not_argv` to
  `tests/test_grok_protocol_ablation.py`, giving the ablation runner the same
  no-argv-prompt coverage the bakeoff runner has. Focused tests: 12 passed.
- Added `scripts/finalize_grok_harness_correction.py` to assemble the
  experiment-level `results.json`/`report.md` from the two partition runs.
- Note: `ruff format` (uv-pinned) reformats the changed runners and the ablation
  test beyond the functional hunks because HEAD's versions were not clean under
  the current formatter; CI's changed-file format gate requires this.
- Decision: EXP-025's protocol ablation is *not* re-run in TASK-0064. Its
  "protocol-specific underperformance" conclusion is void, but re-running the
  four variants is a separate research question and a separate experiment; the
  paper's ablation section is marked void/superseded instead.
- Part 2 finding (user goal: "check issue log for new required benchmark"): no
  newly-filed required-benchmark issue exists. The newest issue is #81 (this
  task). The documented next benchmark (HumanEval, TASK-0022) is blocked on
  sandbox availability; GLEIF (#45/EXP-026) is a separate open track. The Grok
  re-run is the current benchmark-execution work.

### 2026-10-05 - both partitions recovered; bundle finalized; paper corrected

- Public re-run finished: grok 648/648 ok (0.9861), grok_47 645 ok + 2
  provider_error + 1 rate_limited (0.9798) — recovered from the void ~0.50.
- Blind re-run finished: grok 760/760 ok (0.9908), grok_47 758 ok + 2
  provider_error (0.9855). Same-record agreement 746/758 (0.9842).
- The blind run had defaulted `experiment_id` to the pool ID (the launching
  command omitted `--experiment-id`); re-ran with `--resume` and the correct ID
  so the summary metadata matches. `--resume` made no provider calls (all
  records already checkpointed) and left the predictions byte-identical.
- Ran `scripts/finalize_grok_harness_correction.py`; wrote the experiment-level
  `results.json`/`report.md`. Pool fingerprint `b7edd612...`, blind record-ID
  fingerprint `409428fc...`, typed-spec `0d07bd8b...` all match EXP-015.
- Paper (`paper/paper.md`): corrected the prose that reported the void Grok
  numbers as findings (Finding 4, "What each run lost", the deep-dive, "Local
  models", Limitations) and added a new subsection "A bug in our own harness"
  citing EXP-030 (Grok 4.6 99.1%, Grok 4.7 98.5%). Marked Appendix D
  ("Grok Build protocol ablation") void/superseded. The generated tables come
  from EXP-029's frozen analysis and are not regenerated; they carry a void
  caveat. Added EXP-030's `results.json` to the prose-number provenance test's
  sources.
- Regenerated the run telemetry ledger (`uv run --locked python
  scripts/run_telemetry.py rebuild`): 154 records, `--check` green.
- Serialization: the EXP-031 Colab MoE work (a separate task, issue #83) was
  moved out of the working tree to `C:\work\scratch\hold-EXP-031\` so this
  checkpoint contains only TASK-0064 files and the repo-global telemetry ledger
  matches the committed tree.

## Handoff

Next atomic action: run the local gates (workspace policy, Ruff, mypy, pytest,
telemetry `--check`), publish this checkpoint with
`scripts/publish_checkpoint.py`, and after it merges, restore the EXP-031 bundle
and land TASK-0065 (issue #83).
