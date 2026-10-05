# EXP-20261005-031 — Colab T4 MoE judge arms

Two recent small-active-parameter mixture-of-experts models, run as label-only
typed-choice judges on the immutable EXP-015 records using a free-tier Google
Colab T4. This is a new compute path (an ephemeral GPU VM driven by the official
`colab` CLI) and two new judge arms; it does not modify any completed
experiment.

## Question

Can recent MoE models that fit and run fast on a free T4 — Ornith 1.5 35B-A3B
(IQ2_XXS) and Maple Preview 20B-A1B (requantized to Q2_0) — act as useful
grading judges on the frozen Eval Lab decision pool, and how do single and
pairwise judgments differ?

## Method

- **Pool.** The 648 public-selection and 760 blind-holdout records of the frozen
  EXP-015 pool, read by reference. Fingerprints in `source-pool-fingerprint.json`.
- **Protocol.** The frozen typed-choice protocol `eval-lab-local-decision-v1`
  (`eval_lab.judges.local_decision_models.request_for_record`, benchmark
  `exp027-frozen-pool`). Requests are built offline by
  `scripts/build_colab_moe_requests.py` and contain **no gold label**, so the
  file is safe to upload to the shared compute host.
- **Runner.** `scripts/run_colab_moe_judge.py` serves the GGUF with
  `llama-server` and asks for exactly one legal label per record under a GBNF
  grammar (`root ::= "pass" | "fail"` or `root ::= "A" | "B" | "TIE"`),
  temperature 0. Every prediction is appended and `fsync`ed, so a killed
  free-tier session resumes by skipping record IDs already present.
- **Reasoning models.** Ornith emits a thinking block; with a grammar the label
  can land in `reasoning_content` while `content` stays empty. The runner
  disables the chat template's thinking block and falls back to
  `reasoning_content` if `content` is empty.
- **Maple requantization.** The official ternary TQ2_0 file has no CUDA kernel
  in stock llama.cpp (~41 prompt t/s on CPU). It is requantized to Q2_0 keeping
  the Q4_K output head (~2,000 prompt t/s / ~200 gen t/s on the T4). The
  requantized file is regenerated each session and is not committed; its hash is
  in `model-revisions.json`.

## Result

Blind holdout (760 records), coverage 1.0000 for both arms:

| Arm | Single (652) | Pairwise (108) | All 760 | 95% Wilson |
| --- | ---: | ---: | ---: | --- |
| Ornith 1.5 35B-A3B (IQ2_XXS) | 0.5337 | 0.6759 | 0.5539 | 0.5184–0.5889 |
| Maple Preview 20B-A1B (Q2_0) | 0.4969 | 0.4444 | 0.4895 | 0.4541–0.5250 |

Both arms answered every record and produced varied labels (no constant-answer
collapse), so the scores are honest. Ornith is the stronger of the two,
especially on pairwise judgments; Maple is near chance. Both are far below the
API leaders in EXP-029. See `report.md` for the full tables and `results.json`
for the machine-readable numbers.

## Boundaries

- Label-only arms: no probabilities, so Brier, NLL, and ECE are unavailable.
- Two arms only; this is a compute-path demonstration, not a leaderboard sweep.
- HumanEval and using the T4 as a code sandbox are out of scope here.
- No gold label was uploaded to the compute host; scoring is done offline in the
  repository against the frozen EXP-015 gold.
