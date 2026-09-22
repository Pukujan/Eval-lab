# TASK-0041 — Grok Build protocol ablation and objective-domain follow-on

## Status

Active — preregistration and runner implementation in progress. Earlier EXP-022
Grok/Jev/Qwen outputs remain immutable.

## Objective

Determine whether the low Grok Build score in EXP-019 and EXP-022 is caused by
the Build harness/protocol contract rather than general model capability. Run a
public diagnostic over preregistered prompt/output variants, select a protocol
under a declared rule, and evaluate the selected protocol on the frozen blind
holdout. Preserve execution failures separately from wrong labels.

After the Grok diagnosis, prepare append-only objective real-world tracks for
GLEIF, SEC EDGAR/XBRL, and CourtListener. Cybersecurity work is limited to
defensive, non-exploitative robustness and jailbreak-resistance cases with no
live targets, credential theft, persistence, or weaponized payloads.

## Scope

- New experiment: `experiments/EXP-20260922-025-grok-protocol-ablation/`.
- Source pool: immutable EXP-015 records and typed packet.
- Diagnostic: 64 public records, balanced as 32 single and 32 pairwise,
  evaluated under four preregistered Grok protocol variants.
- Blind confirmation: the selected variant on all 760 frozen blind records for
  Grok 4.6 and, if the selection gate passes, Grok 4.7.
- Selection is based only on the public diagnostic. The blind holdout is not
  used to choose a prompt, label encoding, parser, or model.
- No prior experiment directory may be overwritten.

## Preregistered variants

1. `typed_schema`: current EXP-022 prompt, typed System-One JSON payload, and
   native canonical-label JSON schema.
2. `explicit_schema`: explicit human-readable task/rubric/candidate fields,
   canonical labels, and the same native JSON schema.
3. `semantic_schema`: explicit fields and semantic output labels
   (`CORRECT`/`INCORRECT` or `A_BETTER`/`B_BETTER`/`EQUIVALENT`) mapped to the
   canonical labels only after parsing.
4. `explicit_no_schema`: explicit fields and a strict final JSON instruction,
   but no native CLI JSON schema; the parser accepts only the final structured
   label and records parse ambiguity separately.

The variants change only the provider-facing protocol. Records, gold labels,
model aliases, route, timeout, and source pool remain fixed.

## Selection and stopping rules

For each diagnostic arm, report per-mode accuracy, coverage, valid-label rate,
and status counts. The primary selection score is the mean of single-mode and
pairwise resolved accuracy, with coverage as the first tie-breaker. A variant
passes the blind-confirmation gate only if it has at least 64 resolved public
labels, at least 95% public coverage, and improves over `typed_schema` by at
least 10 percentage points in the primary selection score. If no variant
passes, the blind run uses `typed_schema` as a reproducibility rerun and the
result is classified as protocol-unresolved rather than model-resolved.

The selected blind run is stopped only after all 760 IDs have terminal status
or after three consecutive provider-level recovery attempts fail; no labels
are fabricated for unresolved records.

## Calibration assessment

This task does not call a label-only provider calibrated. Existing reliable
calibration evidence is limited to local Qwen 4B: temperature scaling improved
blind Brier/NLL/ECE without changing labels. Jev and Qwen Flash have strong
accuracy/robustness evidence but no validated native probability map in the
completed artifacts. Grok has no valid calibration evidence; its current work
is protocol diagnosis.

## Required files

- this task file
- `experiments/EXP-20260922-025-grok-protocol-ablation/`
- `scripts/freeze_grok_ablation_sample.py`
- `scripts/run_grok_protocol_ablation.py`
- `scripts/report_grok_protocol_ablation.py`
- `scripts/run_grok_luna_qwen_bakeoff.py` (UTF-8-safe subprocess decoding)
- `docs/GROK_BUILD_CLI_AUTOMATION.md` (encoding failure mode)
- focused tests for prompt construction, label mapping, and status handling
- `checkpoints/CURRENT.md`

## Checkpoint

No provider calls are authorized until the experiment manifest, sample IDs,
variants, selection rule, and tests are committed. After execution, the report
must state whether the evidence supports a harness/protocol explanation,
model-specific weakness, or an unresolved mixture of both.
