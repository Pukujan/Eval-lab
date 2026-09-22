# TASK-0010 Metamorphic and Differential Test Contract

## Metamorphic tests

M-01 Threshold monotonicity: if t2 > t1, coverage(t2) <= coverage(t1).

M-02 Extreme thresholds: 0 accepts every valid prediction; >1 is invalid; 1 accepts only confidence exactly 1.

M-03 Batch-order invariance: permuting records cannot change record-id keyed routes.

M-04 Duplicate invariance: duplicate identical predictions get identical routes.

M-05 Pairwise A/B symmetry: swap A/B and corresponding probabilities; A<->B, TIE stays TIE, confidence and accept/escalate route remain unchanged.

M-06 Irrelevant metadata: metadata not consumed by routing cannot change route.

M-07 Random-control matching: fixed seed escalates exactly k unique records and is ID/order stable.

M-08 Provider-failure propagation: successful escalation transformed to provider failure must become unresolved, never silent local fallback.

M-09 Probability-map ordering: dictionary/key insertion order cannot change confidence or route.

M-10 Label-space bijection: synthetic bijective class rename preserves confidence/route while predicted label follows mapping.

M-11 Benchmark rebuild invariance: clean deterministic rebuild from identical source revisions/config produces the same benchmark record IDs and SHA-256 checksums.

M-12 Paper-table invariance: rebuilding paper tables from unchanged results produces byte-stable or numerically stable table data.

## Differential tests

D-01 Independent risk/coverage reference vs production implementation.

D-02 Production threshold search vs brute-force enumeration over all unique confidence boundaries.

D-03 Raw vs calibrated policies use identical record IDs/gold.

D-04 OpenRouter Jev single vs equivalent batch normalization with mocked responses.

D-05 System-One schema parity across Jev and LLM adapter: same question IDs/types/legal labels/score ordering/boolean semantics.

D-06 Pinned `typesafe/jev-1.13` and rolling `~typesafe/jev-latest` cannot be mislabeled as the same arm.

D-07 Equivalent mocked typed answers normalize to the same Eval Lab label/probability schema across providers.

D-08 Random control escalates exactly the same count as calibrated policy.

D-09 TASK-0009 frozen-student reproduction matches committed fixture within declared tolerance.

D-10 Confidence-interval implementation matches an independent reference.

D-11 RO-Crate/PROV identity: every result/paper table entity in the provenance graph resolves to a committed artifact or documented external source.

D-12 SHACL validation: intentionally removing commit, dataset fingerprint, model identity, benchmark version, or provenance edge must make the corresponding negative fixture fail validation.

D-13 Benchmark manifest vs files: source manifest/checksums agree with actual release contents.

D-14 Paper claims vs results: selected headline metrics in generated paper tables must match results.json exactly within declared formatting precision.

## Statistical property tests

Use deterministic generated fixtures where practical for:
- confidence arrays in [0,1];
- tied confidences;
- zero-error/all-error accepted sets;
- provider missingness;
- class-probability permutations.

## Integration differential

After offline tests pass, run an identical typed decision batch through:

1. OpenRouter pinned `typesafe/jev-1.13`
2. System-One adapter backed by YOLO-Auto `qwen3.8-flash`

Compare execution coverage, accuracy, probability semantics, latency, input size, cost/resource metadata, and disagreements.

Provider disagreement is experiment evidence, not test failure unless it exposes a normalization/schema defect.
