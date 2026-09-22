# EXP-20260921-014 limitations and threats to validity

- The primary independent pool is objective and excludes JevBench material, but it is derived from the same frozen Eval Lab objective pool used for the TASK-0011 Qwen comparison. It is independent of JevBench, not a wholly new dataset.
- Pinned Jev returned labels without native probability maps in this run. Brier, NLL, ECE, and risk/coverage are therefore unavailable for Jev; no verbalized confidence was promoted to a probability.
- The pinned arm resolved all 760 records. Its aggregate accuracy is 0.9000, with 95% Wilson interval [0.8766, 0.9194]. Low-error or high-coverage claims should use the interval rather than a point estimate.
- The rolling alias is a canary only. It stopped after two consecutive HTTP 503 provider errors at 263 successful records, leaving 495 records unattempted. Its 0.9468 accuracy is a nonrandom observed prefix and is not comparable to the complete pinned estimate.
- The Qwen comparison has 754 resolved records and six parse errors; its comparison accuracy is 0.8448 over resolved records with unresolved rate 0.0079. It is imported from the completed EXP-013 immutable artifact.
- The local TASK-0009 arm D is defined for single-answer correctness, so 108 pairwise records are explicitly out of scope and skipped in that arm.
- Actual provider cost metadata was unavailable in the normalized Jev responses. The report records cost as unavailable rather than estimating it from a tariff.
- The first 60-call robustness pass recorded HTTP 503 for every call. A subsequent recovery pass recorded ten successful calls and fifty provider errors. A later bounded pass completed the pre-frozen 60-call schedule with repeatability 1.0, option-order agreement 1.0, and rubric-paraphrase agreement 0.9167. All execution artifacts remain separate from the primary arm and are not silently merged.
- Provider availability, model serving changes, and any adaptation to the public source text may affect future runs. The frozen source, protocol, model IDs, and perturbation schedule make a later run a new execution artifact.
