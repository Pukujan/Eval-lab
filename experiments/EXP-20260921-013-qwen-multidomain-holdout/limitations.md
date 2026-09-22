# Limitations and threats to validity

- This experiment evaluates objective answer-key/verifier tasks. It does not establish validity for subjective human rubric judgments.
- Qwen returned labels but no verifiable probabilities or logprobs, so Brier, NLL, ECE, and Qwen confidence calibration are unavailable.
- Accuracy is reported over resolved predictions; parse errors and other provider failures are reported separately and are not silently treated as labels.
- The initial blind pass encountered a provider rate limit. The unresolved records were retried only after the provider recovery smoke succeeded, using the frozen retry ID list and one worker. The final merged result retains the six parse errors.
- The public and blind partitions contain different dataset counts by design. They are source-problem and source-family disjoint, but their aggregate accuracies should not be interpreted as a single identically distributed sample.
- The synthetic variants are deterministic fixtures and are useful for protocol checks, but they are not a substitute for broad natural task distributions.
- Jev was not run in this experiment. The Jev comparison remains a separate TASK-0010 ARC experiment and is not pooled into these Qwen multidomain results.
- One provider route and one frozen model version were evaluated. These results do not establish behavior under provider changes, model updates, or higher concurrency.
