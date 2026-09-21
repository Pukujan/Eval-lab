# EXP-20260920-012-selective-escalation-qwen-streaming — Selective escalation

Benchmark fingerprint: `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`

Threshold-selection records: 2863; final-evaluation records: 2356; provider prefix: 500.

Machine metrics are sourced from `results.json`. Provider failures remain unresolved. Pinned Jev and rolling Jev are separate arms.

## Policies

- `calibrated_local_to_jev_target_0.01`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `calibrated_local_to_jev_target_0.02`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `calibrated_local_to_jev_target_0.05`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `calibrated_local_to_jev_target_0.10`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `calibrated_local_to_qwen_flash_target_0.01`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `calibrated_local_to_qwen_flash_target_0.02`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `calibrated_local_to_qwen_flash_target_0.05`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `calibrated_local_to_qwen_flash_target_0.10`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `local_only`: accuracy=0.525, balanced_accuracy=0.526, macro_f1=0.407, local_coverage=1.000, escalation_rate=0.000, unresolved_rate=0.000, resolved_risk=0.475, claim=n/a.
- `pinned_jev_only`: accuracy=0.978, balanced_accuracy=0.978, macro_f1=0.978, local_coverage=0.000, escalation_rate=1.000, unresolved_rate=0.788, resolved_risk=0.022, claim=n/a.
- `qwen_flash_only`: accuracy=0.978, balanced_accuracy=0.978, macro_f1=0.978, local_coverage=0.000, escalation_rate=1.000, unresolved_rate=0.788, resolved_risk=0.022, claim=n/a.
- `random_matched_to_jev_target_0.01`: accuracy=0.972, balanced_accuracy=0.972, macro_f1=0.972, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.028, claim=collapsed/descriptive.
- `random_matched_to_jev_target_0.02`: accuracy=0.972, balanced_accuracy=0.972, macro_f1=0.972, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.028, claim=collapsed/descriptive.
- `random_matched_to_jev_target_0.05`: accuracy=0.972, balanced_accuracy=0.972, macro_f1=0.972, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.028, claim=collapsed/descriptive.
- `random_matched_to_jev_target_0.10`: accuracy=0.972, balanced_accuracy=0.972, macro_f1=0.972, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.028, claim=collapsed/descriptive.
- `raw_local_to_jev_target_0.01`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `raw_local_to_jev_target_0.02`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `raw_local_to_jev_target_0.05`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.
- `raw_local_to_jev_target_0.10`: accuracy=0.976, balanced_accuracy=0.976, macro_f1=0.976, local_coverage=0.003, escalation_rate=0.997, unresolved_rate=0.785, resolved_risk=0.024, claim=collapsed/descriptive.

## Differential

Jev/Qwen comparable records: 500; agreements: 486.
