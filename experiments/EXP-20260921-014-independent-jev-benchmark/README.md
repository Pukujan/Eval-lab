# EXP-20260921-014 — Independent Jev Benchmark

Status: primary blind evaluation and the pre-frozen robustness subset are complete; rolling remains a separate stopped canary.

The primary independent pool contains 648 public-selection records and 760 blind-holdout records from objective answer keys or deterministic verifiers. Its record fingerprint is `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`, and its blind record-ID fingerprint is `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`. JevBench task text, labels, and composite results are excluded.

The primary pinned arm `typesafe/jev-1.13` resolved all 760 blind records at 90.00% accuracy with a 95% Wilson interval of [87.66%, 91.94%]. The separate rolling alias resolved 263 records before the declared provider stop and must not be pooled with pinned Jev. Qwen and local TASK-0009 arm D are comparison arms; see `report.md` and `results.json`.

An intermediate OpenRouter recovery artifact encountered HTTP 503 responses, and it is preserved as failure evidence. A later bounded recovery pass completed all 60 pre-frozen robustness calls: repeatability 1.0, option-order agreement 1.0, and rubric-paraphrase agreement 0.9167.

Exact commands are recorded in `commands.md`; limitations and threats are in `limitations.md`.

See `PLAN.md` and `experiment.yaml`.
