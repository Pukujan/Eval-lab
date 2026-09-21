# EXP-20260921-015 — Grok Build, Luna, and Qwen Flash Matched Bakeoff

Status: preregistered plan, frozen before final blind-holdout provider evaluation.

## Hypothesis

The authenticated Grok Build and Luna subscription routes will provide competitive
objective typed judgments on the same records as YOLO-Auto `qwen3.8-flash`, while
their coverage and provider behavior may differ materially. Agreement is descriptive;
the benchmark answer keys and deterministic verifiers remain the only objective gold.

## Frozen inputs

- Source experiment: `EXP-20260921-014-independent-jev-benchmark`.
- Source pool: 1,408 records in committed order: 648 `public_selection` and 760
  `blind_holdout`; no record selection is based on provider output.
- Record fingerprint: `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`.
- Blind record-ID fingerprint: `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.
- Typed packet: `eval-lab-system-one` v0.1.0, context cap 4,096, single labels
  `pass`/`fail`, pairwise labels `A`/`B`/`TIE`.
- Typed packet fingerprint: `0d07bd8b8b60bd7f0b5b7a5f5819b7d329ea121f686b240e465695b6f6eca1e4`.
- Gold provenance: answer key or deterministic verifier only.

## Arms and routes

| Arm | Requested model | Route | Role |
| --- | --- | --- | --- |
| `grok` | `opencode/grok-build-0.1` | authenticated OpenCode/xAI subscription | core |
| `luna` | `opencode/gpt-5.6-luna` | authenticated OpenCode/ChatGPT subscription | core |
| `qwen_flash` | `qwen3.8-flash` | YOLO-Auto OpenAI-compatible API | core |
| `sol` | `opencode/gpt-5.6-sol` | authenticated OpenCode/ChatGPT subscription | optional |

The runner records requested and surfaced model IDs separately. The initial
`opencode/grok-4.6` call is retained only as an exploratory preflight artifact after
the CLI catalog revealed the exact `grok-build-0.1` model; it is not part of the
primary arm. No final arm silently falls back to another model or provider.

## Evaluation rules

Each selected arm receives the same canonical record and the same typed System-One
payload. The smoke uses one public-selection record per route. The final run attempts
the full frozen pool, retaining separate normalized JSONL files per arm. Provider
failures, rate limits, parse errors, and skipped records remain unresolved and are
excluded from resolved-risk metrics; they never receive a fallback label.

The blind-holdout partition is the primary comparison and remains label-blind to all
selection and prompt decisions. The public-selection partition is reported separately
and is not pooled into the primary blind score. The one-pass stopping rule is to
attempt each selected record once; a later retry, if needed, must be a separate
timestamped run and cannot overwrite this evidence.

## Metrics

- accuracy, balanced accuracy, and macro-F1 among resolved predictions;
- resolved execution coverage and unresolved/provider-status counts;
- Wilson 95% interval for resolved accuracy as the primary finite-sample uncertainty;
- p50/p95 latency and provider-reported usage/cost when surfaced;
- native probability availability and risk/coverage only when a valid probability map
  is returned; label-only outputs are not treated as calibrated confidence;
- same-record pairwise agreement and comparable-record counts for every arm pair;
- per-partition and aggregate provider-status summaries with surfaced model IDs.

No calibration fit, threshold tuning, model selection, or prompt selection uses the
blind labels. No provider output is promoted to gold.

## Planned artifacts

- `README.md`, `PLAN.md`, `experiment.yaml`;
- `pool-manifest.json`, copied source/typed-packet manifests, and pool checksums;
- `runs/smoke/` with one normalized output per core arm;
- `runs/blind/` and optionally `runs/public/` with one normalized output per arm;
- `results.json`, `report.md`, `provider-status.json`, `differential.json` per run;
- `checksums.sha256` per run and a root completion summary after all selected runs.

## Acceptance boundary

The experiment is complete when the preregistration and pool freeze are committed,
every selected core route has a smoke artifact or explicit provider status, the matched
pool has been attempted with separate arm outputs (including unresolved failures), and
the reports validate. A provider outage may leave an arm incomplete in resolved
coverage, but it must be represented explicitly and never relabeled as a wrong answer.
