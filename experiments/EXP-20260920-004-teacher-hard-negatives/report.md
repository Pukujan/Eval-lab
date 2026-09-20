# TASK-0008 Verified Teacher-Assisted Hard Negatives

Generated source families: 20; accepted independently verified hard negatives: 18.

Verification rate among requests: 0.900. Test sources were excluded.

Failure modes: {'arithmetic_near_miss': 5, 'code_output_mutation': 3, 'multiple_choice_distractor': 5, 'structured_field_mutation': 5}
Rejection reasons: {'structured_payload_not_found': 1, 'teacher_candidate_verified_correct': 1}

Luna audit status: ok; Sol audit status: parse_error.
SuperGrok was recorded as unavailable/provider-blocked from TASK-0007 and was not substituted silently.

## Limitations

Teacher proposals are weak supervision metadata. Every accepted candidate is independently rejected by a deterministic verifier before entering the corpus, and no test source is included.
