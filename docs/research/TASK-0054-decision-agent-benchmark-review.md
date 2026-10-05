# Decision-agent benchmark harness review

**Date:** 2026-09-24  
**Issue:** [#58](https://github.com/Pukujan/Eval-lab/issues/58)  
**Status:** research only. No adapter was implemented and no model was scored.

Labels used below: `observed` means read from this repository; `source_backed` means a primary source fetched on 2026-09-24 supports the claim; `inferred` means a conclusion from those two; `unknown` means not established.

## TL;DR

Eval Lab can already score a **typed decision**. It cannot yet score a **registry, filing, or case decision**, because GLEIF is frozen but not adapted, and SEC EDGAR and CourtListener are protocol only. The useful next benchmarks are short, closed-label, source-frozen slices. Long-horizon agent suites such as SWE-bench, GAIA, and tau-bench measure a different job and should not be pooled with Jev or the local decision models.

## What a decision-agent benchmark needs

`inferred` from the lab contract plus the external suites below. A benchmark is useful for these agents only when all of the following are true:

- The label set is closed and small enough to emit a probability vector.
- Gold is a source fact, an answer key, or a deterministic verifier. A strong model is not gold.
- The snapshot is frozen. A live API is a moving target.
- The prompt fits the shortest model in the comparison, or the report separates context-limit skips from wrong answers.
- Abstention is a legal output, not a parse failure.
- Calibration is fit only on a public split and frozen before blind scoring.
- Evidence, when required, is a source identifier, not a fluent citation.
- Entity, filing, or case IDs do not cross splits.
- Provider failures stay execution statuses.

`observed` The current common envelope is 4,096 tokens. Laya-421M and Verdict have a 512-token limit. Kev-9B and Nimble-9B do not fit the 16 GiB Mac as pinned. A harness that only a 9B model can read is not a comparison harness.

## Harness inventory

| Track | State | Proof | What a decision agent can be asked |
| --- | --- | --- | --- |
| Synthetic objective fixtures | Implemented | `src/eval_lab/datasets/synthetic.py` | pass/fail against a deterministic verifier |
| ARC-Challenge | Implemented | `src/eval_lab/datasets/arc.py` | multiple choice against a frozen answer key |
| HumanEval | Adapter only | `src/eval_lab/datasets/humaneval.py` says it never downloads and never executes | not yet a scored decision |
| LegalBench hearsay | Implemented slice | `src/eval_lab/datasets/legalbench.py` | Yes/No |
| Multidomain and selective pools | Implemented | `src/eval_lab/datasets/multidomain.py`, `selective.py` | typed choice on frozen records |
| EXP-015 / EXP-027 frozen pool | Scored for some models | `src/eval_lab/judges/local_decision_models.py` accepts only `exp027-frozen-pool` and `exp028-legalbench-hearsay` | pass/fail or A/B/TIE |
| GLEIF | Snapshot only | `experiments/EXP-20260922-026-gleif-objective-track/source-manifest.json` | nothing yet. No `gleif.py` |
| SEC EDGAR/XBRL | Protocol only | `docs/OBJECTIVE_DOMAIN_TRACKS.md` | nothing yet |
| CourtListener | Protocol only | `docs/OBJECTIVE_DOMAIN_TRACKS.md` | nothing yet |
| FinanceBench, ARC-AGI, SWE-bench, OSWorld, HLE | Roadmap only | `docs/BENCHMARK_EXPANSION_ROADMAP.md` | nothing yet |

`observed` Verifiers on disk are arithmetic, structured output, multiple choice, code output, and a HumanEval execution-result checker. The HumanEval checker does not by itself download or run the benchmark.

`observed` Jev has a direct runner (`src/eval_lab/jev.py`, `jev_runner.py`) that can return a typed label and a probability vector. Local decision models share abstention labels `__insufficient_evidence__`, `insufficient_evidence`, and `abstain`. That is the right shape. It is wired to two benchmarks only.

`observed` EXP-014 blind Jev, pinned `typesafe/jev-1.13`, resolved 760/760 records at 90.00% accuracy. That number is a completed experiment. It is not a license to treat Jev as gold for a new track.

## Fit for the agents under test

| Agent | What the current harness can measure | What it cannot measure |
| --- | --- | --- |
| Jev 1.13 | Typed choice, probabilities, parse/provider status, on the frozen pool | Registry or filing facts. No GLEIF, EDGAR, or CourtListener records exist |
| Qwen3 0.6B / 1.7B / 4B | Same typed pool, inside the 4,096-token envelope | Tool use, long filings, multi-file code repair |
| Kev-0.8B, Laya-421M, Verdict 1.4 and pre-v1.4 | EXP-027 and EXP-028, with abstention and context-limit skips reported separately | Any task whose prompt exceeds 512 tokens for Laya and Verdict |
| Kev-4B, SemIf-4B | Protocol only, until a completed run exists | Do not invent a score from a failed or paused load |
| Kev-9B, Nimble-9B | Not measurable on the pinned 16 GiB host | A harness that assumes they ran |

`inferred` The comparison that is fair today is a short closed-label decision with an explicit abstain option. A harness that needs browsing, a virtual machine, or a repository checkout measures a tool agent, not these models.

## External findings

Access date for every source below is **2026-09-24**.

### GLEIF

`source_backed` GLEIF's access page says Level 1 data answers who is who, Level 2 answers who owns whom, and the Golden Copy plus delta files are updated three times daily so users can avoid downloading the full population. The same page says the data pool is free to access.  
[LEI Data: Access and Use](https://www.gleif.org/en/lei-data/access-and-use-lei-data)

`observed` The frozen 2026-09-24 Golden Copy manifest records CC0 1.0, LEI-CDF 3.1, RR-CDF 2.1, 3,440,285 LEI rows reported by the publish API, and 488,776 relationship rows. Canonical records are not built. The archives live in the ignored `outputs/` cache, not in git.

`unknown` No public LEI decision-benchmark, with a frozen question set and an answer key, was found in this pass. GLEIF's own data-quality checks are a publisher control, not a model benchmark.

`inferred` The right GLEIF harness is not "read the Golden Copy." It is a few thousand entity-disjoint items drawn from the frozen ZIP: exact LEI lookup, status and date extraction, legal-name normalization, and parent/child direction. Fuzzy name matching is a perturbation of a known LEI, not a model-voted gold label.

### SEC EDGAR / XBRL

`unknown` Live fetches of `https://www.sec.gov/search-filings/edgar-application-programming-interfaces` and `https://www.sec.gov/os/accessing-edgar-data` returned HTTP 403 on 2026-09-24. Do not treat the 2026-09-22 protocol note as a fresh verification of SEC's user-agent or rate rules.

`source_backed` FinanceBench comprises 10,231 questions about public companies, with answers and evidence strings. On a 150-case sample, GPT-4-Turbo with retrieval incorrectly answered or refused 81% of questions. The paper's license is CC BY-NC-ND 4.0.  
[FinanceBench, arXiv:2311.11944](https://arxiv.org/abs/2311.11944)

`source_backed` FinQA is expert-written question answering over financial reports, with gold reasoning programs. The authors report that large pretrained models fall far short of expert humans on multi-step numerical reasoning.  
[FinQA, arXiv:2109.00122](https://arxiv.org/abs/2109.00122)

`inferred` FinanceBench and FinQA are the wrong first EDGAR harness for a 512-token local model. They need long evidence and, in FinQA's case, a program. The right first slice is a frozen company-facts or XBRL frame: concept, unit, period, and value, with the accession or CIK as the evidence target. Numeric tolerance belongs to the verifier. A narrative "is this a sound investment" item is not objective gold.

`unknown` TAT-QA and ConvFinQA were not re-read in this pass. Do not cite their sizes from memory.

### CourtListener and legal decision sets

`source_backed` CourtListener REST API v4.7 documents case-law, citation-lookup, and citation-graph APIs. The project describes citation lookup as a guardrail against hallucinated citations. Authenticated default limits are 5 requests per minute, 50 per hour, and 125 per day. The wiki lists 3,359 jurisdictions.  
[CourtListener REST API v4.7](https://www.courtlistener.com/help/api/rest/)

`source_backed` LegalBench has 162 tasks covering six types of legal reasoning, built with legal professionals.  
[LegalBench, arXiv:2308.11462](https://arxiv.org/abs/2308.11462)

`observed` Eval Lab already uses one of those tasks, hearsay, as Yes/No. That is the right shape. It is not a CourtListener harness. Hearsay gold is the LegalBench answer key, not a docket fact.

`inferred` The first CourtListener harness should be metadata and citation existence on a frozen opinion or cluster snapshot: court, date, cluster id, and whether a citation resolves. Quote attribution is next, and only against a frozen span. Holdings, precedent weight, and legal advice stay non-objective. CourtListener's rate limit means the snapshot must be downloaded once, not queried live during scoring.

`unknown` LexGLUE and CaseHOLD were not re-read in this pass.

### Agent suites that should not be mixed in

`source_backed` GAIA has 466 questions requiring reasoning, multimodal input, browsing, and tool use. Humans scored 92%; GPT-4 with plugins scored 15%. Answers for 300 questions were held out.  
[GAIA, arXiv:2311.12983](https://arxiv.org/abs/2311.12983)

`source_backed` tau-bench scores a tool agent by comparing the database state after a conversation with an annotated goal, and adds pass^k for consistency across trials. The paper reports gpt-4o under 50% task success and pass^8 under 25% in retail.  
[tau-bench, arXiv:2406.12045](https://arxiv.org/abs/2406.12045)

`source_backed` SWE-bench has 2,294 GitHub issues across 12 Python repositories. In that paper, Claude 2 solved 1.96%.  
[SWE-bench, arXiv:2310.06770](https://arxiv.org/abs/2310.06770)

`source_backed` Humanity's Last Exam has 2,500 closed-ended multimodal questions across dozens of subjects. Items are meant to be unambiguous and hard to answer by quick retrieval. The authors report low accuracy and calibration for frontier models.  
[Humanity's Last Exam, arXiv:2501.14249](https://arxiv.org/abs/2501.14249)

`inferred` These suites are informative about tool agents and frontier models. They are a bad next step for Jev-style decision agents. GAIA and tau-bench require tools and multi-turn state. SWE-bench requires a repository and a test runner. HLE is closed-ended, so a small multiple-choice slice could be graded, but it does not test the registry, filing, or case decision the lab is trying to build, and contamination risk is high.

`unknown` OSWorld, BrowseComp, Terminal-Bench, AgentBench, and ARC-AGI-2 were not re-read in this pass. The roadmap already ranks HumanEval, ARC-AGI, LegalBench, FinanceBench, SWE-bench, OSWorld, and HLE. That order is a plan, not a result.

## Ranked changes

### Do now

1. Finish the GLEIF adapter on the frozen 2026-09-24 ZIP. Emit short records: LEI, status, date, legal name, and one relationship direction. Keep the entity as the split unit. Cap prompts at 512 tokens so Laya and Verdict are not silently dropped.
2. Add abstain as a first-class label on that track, and report coverage separately from accuracy. The local decision protocol already has the label names.
3. Keep one new experiment id. Do not write GLEIF rows into EXP-027 or EXP-028.
4. When EDGAR starts, freeze a bulk company-facts or frame file first. Score concept, unit, period, and value. Do not call the live API during a blind run.
5. When CourtListener starts, freeze clusters and citation edges once. Score metadata and citation existence. Do not ask the model for a holding.

### Do later

1. Add a second LegalBench task only if its label set is closed and its prompt fits 512 tokens. Do not import all 162 tasks.
2. Add a FinanceBench evidence slice only after the short XBRL fact slice works. Require an evidence identifier, and do not treat a fluent explanation as gold.
3. Run HumanEval only inside the existing isolated verifier, on a small frozen slice. The adapter already refuses to execute by itself.
4. Report calibration only for routes that emit a legal probability vector. Label-only routes stay uncalibrated.

### Do not do

1. Do not pool GLEIF, EDGAR, CourtListener, hearsay, and the frozen typed pool into one leaderboard number. The roadmap already forbids that, and the external suites confirm they measure different jobs.
2. Do not use Jev, Luna, Sol, or Grok labels as gold for a new track.
3. Do not score a live GLEIF, SEC, or CourtListener API. All three move.
4. Do not start SWE-bench, OSWorld, GAIA, or tau-bench as the next decision-agent harness. They need tools, long context, or a machine the current comparison does not have.
5. Do not treat FinanceBench's published model scores as Eval Lab results. The paper's own sample showed a strong model failing most items.
6. Do not build a cyber, trading, or legal-advice task. The lab contract already excludes those.

## What this changes for Jev and the local models

`inferred` Jev is the only in-scope agent already shown, on a different frozen pool, to return a full typed decision with probabilities. The local models are the stress test: several cannot read a long filing, two cannot load on this host, and two are capped at 512 tokens. A better benchmark is therefore the one that stays hard after the prompt is shortened.

The hardness should come from the label, not the document length. Examples that fit that rule:

- Which of these normalized names is the LEI in the frozen record?
- Does this relationship row point parent-to-child or child-to-parent?
- Which XBRL concept and unit match the frozen fact?
- Does this citation resolve to the frozen cluster, or is it absent?
- Is this hearsay under the frozen definition? Already built.

A model that abstains on the 512-token slice is a measured result. A model that never sees the record because the prompt was a whole 10-K is not.

## Open unknowns

- No public LEI question-answer benchmark was verified.
- SEC's current developer wording was not re-fetched.
- TAT-QA, ConvFinQA, LexGLUE, CaseHOLD, OSWorld, BrowseComp, Terminal-Bench, AgentBench, and ARC-AGI-2 were named but not re-read.
- Exact token limits for Kev-0.8B and SemIf-4B were not re-measured here. TASK-0053 already records the 512-token Laya and Verdict limits and the 16 GiB host constraint.
