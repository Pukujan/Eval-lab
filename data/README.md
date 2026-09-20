# Data

Keep public benchmark-derived records under version control only when their licenses permit redistribution.

Canonical row fields:

- id
- domain
- source_dataset
- source_problem_id
- prompt
- candidate_a / candidate_b or candidate
- rubric
- objective_gold
- verifier_type
- split
- model_predictions
- probabilities
- metadata

Never let variants from one source problem cross train/calibration/test splits.
