# Qwen3-0.6B raw feasibility

This bounded feasibility run tests whether `Qwen/Qwen3-0.6B` can score 20 canonical Eval Lab records locally with forced-choice conditional log-likelihoods under a 4,096-token context cap.

The run completed on the RTX 4060 Laptop GPU with normalized probabilities for all 20 records. It is retained as the raw baseline arm; `metrics.json` and `manifest.json` are the machine-readable companion outputs, while `predictions.jsonl` retains the normalized predictions and raw scores.

The six ARC records use the committed source fingerprint `b7a84b15c5ca352f2689f546721d8038ce9b31ecff711be606016a6996e05521`. Jev comparison is unavailable because the TASK-0003 live smoke was rate limited.
