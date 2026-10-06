# TASK-0068 - Graph RAG eval bench: legal citation graph vs semantic and lexical retrieval

## Status

Complete. GitHub issue #92. Branch `task/TASK-0068-graph-rag-eval`. The
preregistration merged as PR #102; the test split is scored and the results
checkpoint is published. Hypothesis **not supported on the primary metric**.

## Goal

Open a retrieval-architecture axis in Eval Lab. Every existing arm answers *which
judge is better*; none answers *does a graph earn its inference cost over plain
vector search*. This task runs an existing open-source retrieval setup against a
semantic baseline and a lexical baseline over one corpus, scores them
deterministically, and publishes the comparison.

Nothing novel is built. The corpus, its prebuilt graph, its BM25 postings and the
embedding stack all exist and are already installable.

## Substrate (measured 2026-10-06, recorded on issue #92)

Hugging Face `justicedao/patent-legal-ir-graphrag` at revision
`29d510841f112bbe41fb209307a55cd1bdc70ca0` (English patent law):

- 2,174 corpus documents. CFR Title 37 1,246, MPEP 746, 35 U.S.C. 175, USPTO
  guidance 7.
- Prebuilt BM25: 854,046 postings over 30,514 terms, with shipped
  `idf`/`document_frequency`, so the lexical arm needs no re-tokenisation.
- Prebuilt graph: 37,764 nodes, 883,628 edges. Of the 20,886
  `references_authority` edges, **8,626 are document -> document** (a real
  citation network over 1,502 documents; out-degree max 171, in-degree max 221,
  no self-loops).
- The shipped 256-d "vectors" are `local-hashed-term-projection`, not neural
  embeddings, and no encoder ships. The semantic arm must embed the corpus
  itself.
- **No gold questions ship.** They are retrieval releases, not benchmarks.

## Scope

In scope:

- `experiments/EXP-20261006-034-graphrag-citation-holdout/` - the preregistered
  Tier-1 experiment (deterministic, no LLM, no judge).
- `src/eval_lab/datasets/patent_ir.py` - loader, CID/node normalisation, hold-out
  builder, and the leak/mapping diagnostics.
- `scripts/build_graphrag_holdout.py` - freeze corpus/edges/split, write the
  frozen artifacts and query set.
- `scripts/run_graphrag_arms.py` - the four arms.
- `scripts/report_graphrag_holdout.py` - `results.json` and `report.md`.
- `tests/test_patent_ir.py` - the leak and mapping assertions.
- `tasks/TASK-0068-graph-rag-eval.md` - this file.
- `checkpoints/CURRENT.md` - new top entry (repository-wide next action changes).

Out of scope:

- Tier 2 (legal QA scored by Jev). Deferred; see Decisions.
- Any change to a completed experiment. `experiments/EXP-20261005-032-*` and
  `EXP-20261006-033-*` are other writers' work and are not touched.
- GraphRAG/LightRAG index construction. The graph is used as shipped; a
  converted-index arm is a separate experiment if wanted.

## Acceptance criteria

- The preregistration commit lands **before** any test-split scoring, carrying
  hypothesis, metrics, primary comparison, split policy, calibration method,
  exclusion rules and stopping rule.
- Gold is a deterministic structural fact of the frozen dataset. No model
  judgment enters the gold.
- Four arms scored on one split: graph (2-hop co-citation over held-out
  citation edges), popularity (retained in-degree, the no-structure null),
  semantic (neural embedding), lexical (BM25).
- Leak and mapping assertions pass as tests, not convention: gold has zero
  intersection with each source's readable out-neighbours; every citation
  endpoint resolves to exactly one corpus document; the traversal index contains
  only document -> document edges; no gold target shares its source document's
  body.
- `results.json` and `report.md` are generated from computed artifacts, never
  hand-typed.
- Telemetry regenerated in the same checkpoint (`scripts/run_telemetry.py
  rebuild`).
- Local gates green: repo contract, workspace policy, Ruff, mypy, pytest,
  telemetry `--check`.

## Decisions

- **Tier 1 is deterministic and self-contained.** No judge and no LLM, so it is
  free, fast and fully reproducible. The Jev decision route is not applicable to
  this experiment, which is the point of its self-containment.
- **Query shape is link prediction, not question answering.** Queries arrive as
  text but both arms are given the source document; the mechanism under test is
  whether graph traversal generalises beyond edges it can read. This is stated
  as a limitation, not hidden.
- **The graph arm cannot read its own gold.** A slice of citation edges is held
  out and excluded from the traversal index.
- **Semantic arm uses the canonical environment.** `transformers` and `torch`
  are already locked under the repo's `local` extra, so `uv sync --extra dev
  --extra local` needs no lockfile change.
- **Tier 2 references EXP-033 rather than duplicating it.** The LegalBench
  answer-key subset already covers legal QA with objective gold; Tier 2 will
  point at it and, if a graph arm is wanted over a legal QA set, pair it with
  that work rather than aligning a second dataset.
- **A graph arm based on converting the prebuilt graph into GraphRAG's index
  format is deferred.** The shipped graph is not in GraphRAG's
  `entities.parquet`/`relationships.parquet` schema, and conversion would make
  the first experiment depend on a schema mapping that has not been validated.
  The direct-traversal arm answers the same question without that dependency.
- **A popularity arm was added as the graph arm's sharpest null.** A citation
  task is naturally friendly to "return the most-cited documents"; without it, a
  graph win could not be distinguished from in-degree ranking. It was added
  during preregistration, before any test-split scoring.
- **The semantic arm chunks and max-pools.** A mean corpus document is ~2,300
  tokens (p90 ~5,100, max ~94,000) and only 41% fit in one 512-token window, so
  single-window encoding would represent the opening of most documents and make
  the baseline a strawman. Documents are embedded as overlapping 512/256 windows
  and scored by maxP (best-chunk cosine). Revised during preregistration, before
  any test-split scoring; the pre-revision dev numbers are not reported.
- **The echo-free secondary pools over gold edges, not queries.** Most queries
  have a single echo-free target, so a per-query mean would let a query with five
  such targets weigh the same as a query with one. The macro query-level mean is
  reported beside the pooled rate.
- **A duplicate-body safeguard was added.** The corpus carries reserved-stub
  sections with identical text (15 groups, 58 documents). The build measures how
  many gold pairs sit on a duplicated body and fails if any gold target shares its
  own source's body. Measured: 0 sources, 7 of 2,296 gold targets on a duplicated
  body, 0 sharing their source's body.

## Risks and honest failure modes

- A graph win that is large on the echo-containing set should be distrusted:
  documents often name the provisions they cite. The preregistered secondary
  result is the echo-free subset.
- If held-out citations are not reachable by structure, the graph arm cannot
  win; that is a design limitation and must be reported, not hidden. A dev
  prototype measured 79% of held-out edges carrying at least one structural
  signal.
- Co-citation predicting citation is close to bibliometrics-tautological. The
  contribution is the magnitude against a neural baseline and the zero index
  cost, not the direction.
- One small static embedding model is not "semantic retrieval" in general.

## Checkpoint log

- 2026-10-06: issue #92 filed with reconnaissance; substrate built and verified
  in the gravebuster pod; dev prototypes run (graph > semantic > lexical); branch
  created; preregistration written.
- 2026-10-06: review response applied before any test-split scoring. Three
  changes: (a) duplicate-body leak diagnostic added and measured (15 groups, 58
  documents, 0 gold pairs sharing their source body, 3 distinct gold targets on a
  duplicated body, 0 citation strings shared by >1 document); (b) the echo-free
  secondary now pools over gold edges with the macro query mean reported beside
  it; (c) the semantic arm chunks (512/256) and scores by maxP because only 41.3%
  of documents fit a single 512-token window (mean 2,324 tokens, p90 5,105), and
  a popularity (retained in-degree) arm was added as the graph arm's sharpest
  null.
- 2026-10-06: fixed a real `build_holdout` defect found while reconciling the
  manifest against the arm run. The safeguard-3 demotion removed reciprocal held
  edges from `held` but did not add them to `retained`, so 126 edges were dropped
  entirely and `held | retained` was 8,500 of 8,626. The arm script derived its
  traversal index as `edges - held` (6,330) while the manifest said 6,204; the
  fix makes the demoted edges retained so the two agree at 6,330 and the split is
  a partition of the input edge set. No gold set changed (0 edges were demoted on
  this data), so the running dev scoring stays valid; the reachability diagnostic
  moved 2-hop 0.5621 -> 0.5721 and common-citer 0.5268 -> 0.5403. A regression
  test asserts `held | retained == edges` across 59 salts.
- 2026-10-06: results checkpoint. PR #102 (preregistration) merged with required
  CI green; test split scored. Result: **hypothesis not supported on the primary
  metric**. Test recall@10 - graph 0.163, semantic 0.067, lexical 0.063,
  popularity 0.201; graph - semantic +0.096, graph - lexical +0.101, graph -
  popularity **-0.038**. The preregistered echo-free secondary inverts the
  comparison (graph 0.385, popularity 0.128, semantic 0.000, lexical 0.000). A
  post-hoc in-degree stratification explains the split: popularity scores 0.000
  on every gold target with retained in-degree <= 7, where the graph arm scores
  0.042-0.053, and the two are effectively tied on the 8+ bucket (0.219 vs 0.227,
  718 of 1,051 test gold pairs), so popularity's aggregate lead is a
  query-independent prior. Echo-free is thin (39 gold pairs over 35 of 292
  queries; graph wins 15, ties 16, loses 4) and is reported as directional.
  Regenerated `results.json`, `report.md` and telemetry in the same checkpoint;
  `report_graphrag_holdout.py --check` and `run_telemetry.py --check` both pass;
  full suite 329 passed.
- 2026-10-06: preregistration merged as PR #102 with required CI green; test
  split scored. Result: **the hypothesis is not supported on the primary
  metric**. Test recall@10 graph 0.163, semantic 0.067, lexical 0.063,
  popularity 0.201; graph - semantic +0.096, graph - lexical +0.101, graph -
  popularity **-0.038**. The preregistered echo-free secondary inverts the
  comparison (graph 0.385, popularity 0.128, semantic 0.000, lexical 0.000). A
  post-hoc in-degree stratification explains the split: popularity scores 0.000
  on every gold target with retained in-degree <= 7 (where the graph arm scores
  0.042-0.053) and is effectively tied on the 8+ bucket (0.219 vs 0.227, 718 of
  1,051 gold pairs), so its aggregate lead is a query-independent prior. The
  echo-free stratum is thin (39 gold pairs over 35 of 292 queries; graph wins 15,
  ties 16, loses 4), reported as directional. Cost, `results.json`, `report.md`
  and telemetry regenerated in the same checkpoint.

## Handoff

The release download and the semantic embedding cache live in scratch outside the
checkout (`%TEMP%/eval-lab-graphrag-work`); nothing from the dataset is
committed except derived counts, identifiers, citations and fingerprints. To
reproduce, run the four commands in the experiment README in order — the build
script downloads the pinned revision, the arms script writes
`arm-predictions/*.jsonl`, the report script derives `results.json`/`report.md`,
and telemetry is regenerated last.

The experiment is complete and its result is negative: the graph arm beats both
text baselines but loses to the popularity null on the primary metric, and the
preregistered echo-free secondary is the only stratum where it clearly leads. Do
not re-report the full-set numbers as a graph win. Tier 2 (legal QA scored by
Jev) is deferred and should reference EXP-033 rather than align a second legal QA
dataset. Do not overwrite any completed experiment; a change to the hypothesis,
metrics, primary comparison or split policy requires a new experiment id.
