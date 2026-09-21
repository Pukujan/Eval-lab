# EXP-20260921-017 — Local Qwen 4B judge calibration

This experiment tests whether a locally hosted Qwen 4B forced-choice judge can
produce probabilities that become more reliable after split-safe temperature
scaling. The public selection partition is the only calibration fit partition; the
blind holdout is evaluation-only.

The direct Grok Build, Luna, remote Qwen Flash, and pinned Jev outputs are immutable
reference artifacts from EXP-015 and EXP-014. They remain label-only references
because those runs did not expose validated probabilities. No OpenCode or OpenRouter
route is part of this experiment.

Model weights and caches are external runtime state and must not be committed.
