# EXP-20260920-008 — Small Judge Training and Calibration Pilot

This experiment preregisters a bounded single-answer correctness student using the frozen synthetic objective fixture and the verified TASK-0008 hard-negative corpus.

The student is a compact TF-IDF plus logistic-regression classifier. Arms A-D use train-split objective records only: A objective labels, B objective labels plus rubric criterion paraphrases, C objective labels plus verified hard negatives, and D both augmentations. The arm with the lowest dev negative log likelihood, then highest dev accuracy, is selected without consulting test labels. Arm E applies scalar temperature calibration fit on calibration records only.

Teacher text is retained as augmentation metadata and is never promoted to objective gold. Every hard negative must retain deterministic-verifier provenance. Test source families remain frozen until the final run.

The final run writes normalized predictions, JSON model artifacts, training manifests and fingerprints, an ablation report, calibration metadata, leakage checks, and limitations.
