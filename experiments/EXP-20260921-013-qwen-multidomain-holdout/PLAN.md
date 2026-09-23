# EXP-20260921-013 — Qwen Multidomain Holdout Study

## Status

Planned/preregistered. No holdout labels have been evaluated.

## Hypothesis

Qwen3.8 Flash will be substantially more accurate than the frozen lightweight student on objective tasks, but performance and latency will vary by dataset family. Cross-dataset reliability cannot be inferred from the TASK-0010 ARC-only result.

## Primary question

Does YOLO-Auto `qwen3.8-flash` provide reliable objective judging across multiple task families and disjoint public blind holdouts under one typed evaluation contract?

## Arms

- Qwen3.8 Flash via YOLO-Auto streaming, one canonical record per request.
- Historical pinned Jev `typesafe/jev-1.13` results from EXP-20260920-012 for ARC-Challenge context only; not pooled with Qwen and not re-run by this plan.
- The frozen TASK-0009 TF-IDF/logistic-regression arm D remains a historical local comparator; it is not retrained here.

## Datasets and source revisions

- `allenai/ai2_arc`, `ARC-Challenge`, revision `210d026faf9955653af8916fad021475a3f00453`, CC BY-SA 4.0.
- `allenai/ai2_arc`, `ARC-Easy`, resolved revision to be recorded by the adapter before holdout freeze, CC BY-SA 4.0.
- `openai/gsm8k`, `main`, revision `740312add88f781978c0658806c59bc2815b9866`, MIT.
- `cais/mmlu`, preregistered selected subjects, revision `c30699e8356da336a370243923dbaf21066bb9fe`, MIT.
- Existing deterministic EvalLab synthetic fixtures with verifier provenance.

The source manifest will record exact retrieval metadata, licenses, configs, source IDs, canonicalization versions, and content fingerprints. Sources with unresolved objective-gold or licensing status are excluded.

## Splits

Source-family deterministic split policy: train/dev/calibration/public_test/blind_holdout. All variants of one source problem inherit one split. The blind holdout is selected before provider evaluation and is not used for prompt, model, adapter, threshold, or stopping choices. Counts are reported rather than padded.

## Prompt and output contract

Use `eval-lab-system-one` v0.1.0 semantics where applicable. The provider receives the same canonical evidence packet for every backend, with `temperature=0`, thinking disabled, and a legal typed verdict. Streaming is one request per record. The returned model ID must equal `qwen3.8-flash`.

## Metrics

Accuracy, balanced accuracy, macro F1, unresolved rate, status counts, per-domain and per-dataset metrics, position-swap consistency, rubric-paraphrase consistency where defined, latency mean/median/p95, calls per 1,000, and provider usage/cost when available. Brier/NLL/ECE and risk/coverage are unavailable unless real probabilities/logprobs are present; self-reported confidence alone is not promoted to calibrated probability.

## Stopping and exclusion rules

Stop live evaluation if provider credentials are unavailable, repeated rate limits make the declared pool incomplete, or model identity/typed parsing fails. Preserve every failure as an execution record. Exclude only records failing preregistered schema/context/identity checks, and report exclusion counts and reasons. Never retry indefinitely or silently substitute a different model.

## Required freeze before holdout

Commit this plan, source manifest, canonicalization and split code, holdout ID/checksum manifest, and prompt/model/provider settings before the first blind holdout request. Any change after that freeze creates `EXP-20260921-014` or later.

## Reproduction

Planned commands will be added to the completed experiment README and report. The credentialed run reads `YOLO_AUTO_API_KEY` from the process environment or an ignored local `.env`; no secret is printed or committed. Offline validation must run without provider credentials.
