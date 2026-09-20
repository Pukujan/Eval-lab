# Qwen3-0.6B calibrated feasibility

This preregistered follow-up repeats the bounded 20-record Qwen3-0.6B slice and fits scalar temperature scaling only on separate synthetic `split=calibration` single-label records. The held-out report applies that artifact to eligible single-label predictions and leaves pairwise predictions unchanged.

The primary comparison is raw versus calibrated NLL, Brier, ECE, and risk/coverage on the same canonical record IDs. No model weights or dataset cache belongs in this directory.
