# EXP-20260920-003 — External Judge and Teacher Bakeoff

Status: planned. This experiment freezes the TASK-0006 canonical 20-record slice and compares available external judge paths without treating any model as objective gold.

The required automated arm is YOLO-Auto `qwen3.8-flash` at `https://yolo-auto.com/v1`. The OpenCode census is recorded at run time. The preferred free arms are `opencode/nemotron-3.5-lightning-free` and `opencode/mimo-v2.5-free`; the surfaced SuperGrok arm is `opencode/grok-4.6` when the subscription path accepts it. Jev is reused only when successful predictions exist.

The primary comparison uses identical canonical record IDs from `experiments/EXP-20260920-002-qwen-0-6b-calibrated/manifest.json`. Provider failures, rate limits, malformed outputs, and unavailable subscription paths are retained as execution states and excluded from accuracy metrics. Wrong labels are counted only for `ok` predictions.

The final test slice is limited to public/synthetic records, uses the common 4,096-token context cap, and has no calibration fit. Deterministic Luna and Sol audit batches are produced from the frozen records and disagreement/uncertainty rankings; they are teacher-review inputs, never gold labels.
