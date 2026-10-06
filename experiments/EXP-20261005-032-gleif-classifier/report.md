# EXP-20261005-032-gleif-classifier — Jev 1.13 as a closed-set GLEIF classifier

Partition `blind_holdout`; model `typesafe/jev-1.13`; gold is the frozen GLEIF source field value (`deterministic_verifier`). Each family is reported beside a majority-class baseline because raw accuracy is misleading under class imbalance.

Blind items: **2142** (2142 resolved, micro-accuracy 0.7390).

## entity-category

- items `714`; resolved `714`; coverage `1.0000`; valid-label rate `1.0000`
- accuracy `0.9034` (95% Wilson `[0.8794810368407852, 0.9229245541462298]`) vs majority baseline `0.8697` (always `GENERAL`)
- balanced accuracy `0.8399` vs baseline `0.2500`
- macro-F1 `0.5165` vs baseline `0.1551`; over classes with gold support `0.7748`
- Brier `0.1461`; NLL `0.4761`; ECE `0.0414`
- risk/coverage: coverage at 1% risk `0.0098`, at 5% risk `0.8529`
- status counts `{'ok': 714}`; p95 latency `422.2` ms; cost per 1000 `0.0245`
- gold distribution `{'FUND': 57, 'GENERAL': 621, 'RESIDENT_GOVERNMENT_ENTITY': 3, 'SOLE_PROPRIETOR': 33}`

## legal-jurisdiction

- items `714`; resolved `714`; coverage `1.0000`; valid-label rate `1.0000`
- accuracy `0.7451` (95% Wilson `[0.7118788047226045, 0.7756940370229776]`) vs majority baseline `0.2353` (always `OTHER`)
- balanced accuracy `0.6537` vs baseline `0.0476`
- macro-F1 `0.6482` vs baseline `0.0181`; over classes with gold support `0.6482`
- Brier `0.3537`; NLL `1.9243`; ECE `0.0868`
- risk/coverage: coverage at 1% risk `0.0112`, at 5% risk `0.4104`
- status counts `{'ok': 714}`; p95 latency `391.0` ms; cost per 1000 `0.0331`
- gold distribution `{'AT': 10, 'BE': 11, 'CH': 3, 'CN': 18, 'DE': 53, 'DK': 22, 'ES': 34, 'FI': 16, 'FR': 48, 'GB': 57, 'IE': 5, 'IN': 82, 'IT': 54, 'KY': 11, 'LI': 3, 'NL': 43, 'NO': 9, 'OTHER': 168, 'PL': 5, 'SE': 20, 'US-DE': 42}`

## registration-status

- items `714`; resolved `714`; coverage `1.0000`; valid-label rate `1.0000`
- accuracy `0.5686` (95% Wilson `[0.5320278650733586, 0.6044925306154042]`) vs majority baseline `0.5686` (always `ISSUED`)
- balanced accuracy `0.3333` vs baseline `0.3333`
- macro-F1 `0.1039` vs baseline `0.1036`; over classes with gold support `0.2425`
- Brier `0.7495`; NLL `1.6198`; ECE `0.3636`
- risk/coverage: coverage at 1% risk `0.0014`, at 5% risk `0.0014`
- status counts `{'ok': 714}`; p95 latency `382.2` ms; cost per 1000 `0.0255`
- gold distribution `{'ISSUED': 406, 'LAPSED': 253, 'RETIRED': 55}`
