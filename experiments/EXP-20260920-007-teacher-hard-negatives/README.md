# EXP-20260920-007 — Verified Teacher-Assisted Hard Negatives

Status: planned. This experiment asks the exact YOLO-Auto Qwen3.8 Flash model for plausible incorrect candidates and keeps only proposals independently rejected by the deterministic repository verifiers.

The source family is the 24-source synthetic fixture suite. Test sources are excluded from generation and the accepted corpus; train, dev, and calibration sources retain their original source split. Teacher identity is recorded as weak model supervision metadata and is never promoted to objective gold.

SuperGrok is attempted only if TASK-0007 integration is available. Luna and Sol are used through supported subscription/OpenCode audit workflows when available; audit outputs remain review metadata. Unavailable teacher paths are recorded with explicit provider status.

The stopping rule rejects any candidate that is empty, malformed, verifier-correct, unverifiable, from a test source, or cannot retain its source_problem_id and split. Accepted records include verifier ID, evidence, source family, teacher request ID, and a failure-mode taxonomy label.
