# EXP-20260920-012 selective escalation with streaming Qwen

Status: plan-only at creation. This append-only replay regenerates TASK-0010 routing metrics from the frozen student, frozen benchmark, existing separate Jev outputs, and the validated streaming Qwen output.

Frozen inputs:

- EvalLab-Select v0.1.0 fingerprint `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`
- 2,863 threshold-selection records and 2,356 final-evaluation records from disjoint source families
- deterministic first 500 final-evaluation records for provider comparisons
- TASK-0009 TF-IDF + logistic-regression student arm D with existing calibration artifact
- Jev pinned `typesafe/jev-1.13` and rolling `~typesafe/jev-latest` remain separate
- Qwen `qwen3.8-flash` from `qwen-streaming-final-merged-20260920-010`, 500/500 ok
- targets 0.01, 0.02, 0.05, 0.10; confidence is maximum calibrated class probability

The replay writes routing, thresholds, results, report, and a Jev/Qwen System-One differential. It does not call a provider, retrain the student, alter the benchmark, pool pinned and rolling Jev, or use provider labels for threshold selection.
