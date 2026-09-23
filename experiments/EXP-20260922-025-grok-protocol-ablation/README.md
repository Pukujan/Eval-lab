# EXP-20260922-025 — Grok Build protocol ablation

This experiment tests whether the low Grok Build result in EXP-022 is caused by
the provider-facing prompt/output contract. It uses the immutable EXP-015 pool
and does not modify EXP-019 or EXP-022.

The public diagnostic is selection-only. The blind holdout remains untouched
until the protocol selection gate is evaluated from the public records alone.
Provider errors, rate limits, timeouts, and parse ambiguity remain explicit
execution statuses and are never converted into labels.

The experiment is defensive and objective. It contains no live cybersecurity
target, exploit payload, credential material, or instruction to bypass a real
system.
