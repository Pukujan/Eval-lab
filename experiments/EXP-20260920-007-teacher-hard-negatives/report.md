# TASK-0008 Verified Teacher-Assisted Hard Negatives

Generated source families: 20; accepted independently verified hard negatives: 5.

Verification rate among requests: 0.250. Test sources were excluded.

Failure modes: {'arithmetic_near_miss': 3, 'code_output_mutation': 2}
Rejection reasons: {'structured_payload_not_found': 2, 'teacher_candidate_verified_correct': 2, 'timeout': 11}

Luna audit status: ok; Sol audit status: ok.
SuperGrok was recorded as unavailable/provider-blocked from TASK-0007 and was not substituted silently.

## Limitations

Teacher proposals are weak supervision metadata. Every accepted candidate is independently rejected by a deterministic verifier before entering the corpus, and no test source is included.
