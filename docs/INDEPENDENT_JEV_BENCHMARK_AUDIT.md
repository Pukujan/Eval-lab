# Independent Jev Benchmark Audit

## Purpose

Eval Lab should not accept JevBench's composite rank as evidence that Jev is generally superior. This note records how the public JevBench suite works and defines the separation required for an independent Eval Lab benchmark.

## What JevBench does

The public JevBench repository evaluates typed decision systems: a state, a bounded rubric, and an exact label set go in; a typed answer and, when supported, a probability distribution come out. Its current v1.2 line reports 534 decisions per system, including easy, standard, judge, and hard tiers. The hard tier contains public and held-out decisions. The harness records model adapters, raw outputs, costs, latency, schema validity, calibration, and missing provider responses.

The current public score combines four axes with equal weight through a geometric mean:

- Intelligence: weighted accuracy across hard, easy, standard, and judge tiers;
- Calibration: hard-tier ECE and fidelity to exact gold distributions;
- Speed: a logarithmic function of p50 and p95 latency;
- Cost: a logarithmic function of dollars per 1,000 decisions.

This is a coherent product benchmark, but the composite is a design choice. It is not a neutral fact about model quality. Cost for systems without a public tariff is estimated, and self-hosted/demo latency is adjusted by a stated multiplier and additive constant. Those values should not be pooled with directly billed, directly measured values in an independent scientific estimate.

JevBench's own repository also documents that native probability distributions and verbalized probabilities are different objects. It records provider failures as missing and stops after declared failure conditions. Those are practices Eval Lab should retain.

## Independence risks

The benchmark is openly published and its task text is visible. That improves reproducibility but allows adaptation to public items. The hard tier is described as authored and cross-reviewed by the benchmark team, which is valuable curation but does not make it external gold. Some imported cohorts use labels produced by the benchmark authors' human or deterministic processes. The suite therefore measures a meaningful task collection, while its score should be read as evidence about that suite rather than a universal Jev capability.

The option-order sensitivity documented for one open Jev-style entrant is a useful warning for Eval Lab: a typed label set can still encode order effects. We will test label permutation explicitly rather than assume type safety implies semantic invariance.

## Independent Eval Lab rule

The primary independent score will never use JevBench task text, labels, result files, or composite weights. It will use source revisions and objective gold from EvalLab-Select, ARC, GSM8K, MMLU, and deterministic synthetic fixtures. The source/split fingerprint, canonical packet, prompt version, option order, and model arms will be committed before final evaluation.

Primary results will be a table of separately interpretable quantities:

- accuracy, balanced accuracy, macro F1, and majority-class baseline;
- Brier, NLL, and ECE only for verified probability distributions;
- Wilson intervals and accepted/resolved sample sizes;
- unresolved/provider status rates;
- raw p50/p95 latency and actual usage/cost metadata;
- option-order invariance, rubric-paraphrase agreement, and repeated-call stability;
- per-domain results and source-family leakage checks.

JevBench scores may appear in related-work or contextual comparison text, but they cannot select thresholds, determine acceptance, or serve as objective gold. Pinned Jev and rolling Jev are separate arms. Qwen and the frozen local student are comparison arms only when they use identical record IDs and the same evidence packet.

## Public sources audited

- JevBench repository: <https://github.com/fstandhartinger/jevbench>
- JevBench public results: <https://www.benchmarkheaven.com/jev-models>
- TypeSafe launch post: <https://typesafe.ai/blog/introducing-system-one-models-and-jev>
- Independent Jev phishing benchmark: <https://github.com/anisselbd/jev-phishing-bench>
- Independent Jev cost/latency study: <https://github.com/WallerChen/jev-measured>

The sources above are external context. Eval Lab's acceptance evidence will come from its own frozen records, provenance, raw predictions, and metrics.
