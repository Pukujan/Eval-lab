# EXP-20261006-034 - Graph RAG citation hold-out: graph vs semantic vs lexical retrieval

Status: **completed**. The test split is scored; see `results.json` and
`report.md`. Dev-split numbers committed earlier were pipeline evidence only.

## Result in one paragraph

The hypothesis is **not supported on the primary metric**. On test recall@10 the
graph arm reaches 0.163 against semantic 0.067 and lexical 0.063, so it beats
both text baselines by roughly ten points - but the popularity null reaches 0.201,
so the graph arm loses to "return the most-cited documents" by 3.8 points and
cannot be said to have added query-conditioned value. The preregistered echo-free
secondary inverts the comparison (graph 0.385 vs popularity 0.128; both text
baselines 0.000). A post-hoc in-degree stratification explains why: popularity
scores 0.000 on every gold target with retained in-degree <= 7, where the graph
arm scores 0.042-0.053, while on the 8+ bucket (718 of 1,051 test gold pairs) the
two are effectively tied. Popularity's aggregate lead comes almost entirely from
high-degree targets it would return for any query.

## The question

Does traversing a document citation graph recover a citation the retriever cannot
read, more often than neural semantic similarity or plain lexical retrieval, over
the same corpus and the same source documents?

Every existing Eval Lab arm compares judges. This is the first arm that compares
*retrieval architectures*, which is the axis an external reader asks about first
for Graph RAG.

## The trap this design exists to avoid

The naive version is circular. If a query names a source document and the gold is
what that document cites, then a graph arm just reads the document's outgoing
edges - which *are* the gold - and scores near 100% by construction.

This experiment breaks the circle by **holding out** a slice of citation edges. The
traversal index is built without them, so the graph arm cannot read its own gold;
its only route to a held-out target is structure that survives in the remaining
graph (co-citation, shared citers). What is measured is whether graph structure
*generalises beyond the edges it can see*.

## Task

Link prediction over held-out citations. For each eligible source document:

- **Query**: the source document's own title and body text, verbatim.
- **Gold**: the source's held-out citation targets, as corpus document identity.

Both arms are handed the source document; one acts on its text, one on the graph.
This is therefore **link prediction, not question answering** - a limitation, not
a detail.

## Arms

| arm | mechanism | reads |
| --- | --- | --- |
| **graph** | 2-hop co-citation over the retained doc->doc citation subgraph, entered at the source | `data/graph/edges` (document->document only) |
| **popularity** | documents ranked by retained in-degree; no query structure | `data/graph/edges` (document->document only) |
| **semantic** | chunked sentence embeddings (`all-MiniLM-L6-v2`, pinned), maxP chunk scoring | corpus `title` + `text` |
| **lexical** | BM25 with the release's documented parameters | corpus `title` + `text` |

The graph arm enters exactly at the source document, because the source *is* the
query; there is no entity-linking step to get wrong. The source document is
excluded from every arm's candidate set, since the query text is that document's
own text and leaving it in would let every arm return it.

**Popularity is the graph arm's sharpest null.** A citation task is naturally
friendly to "return the most-cited documents", so the graph arm must beat
in-degree ranking for its traversal to have added anything. The semantic arm is
given a fair shot at long documents: a mean corpus document is ~2,300 tokens, so
single-window 512-token encoding would represent only the opening of most of the
corpus; documents are embedded as overlapping windows and scored by maxP
(best-chunk similarity), the standard multi-vector long-document method.

## Split

For each source with at least three outgoing document->document citation edges, a
seeded 30% of its out-edges are held out (minimum one). A source is a query only if
it keeps at least one held-out and one retained edge. Query sources are then split
dev/test by SHA-256 of the source identity, salt `20261006`. No source document
crosses the boundary. The split is frozen in `split-manifest.json`.

## Metrics

Primary: recall@10, and recall@{5,20,50} plus MRR@100. Cost: index size, index
build seconds, mean and p95 query latency.

**Preregistered secondary result:** recall@10 on the **echo-free subset** - gold
targets whose full normalised citation string does not appear in the query text.
Legal documents frequently name the provisions they cite, so a full-set win could
be lexical leakage; the echo-free subset is where a graph win is trustworthy. The
secondary is pooled over gold **edges**, not averaged over queries: most queries
have a single echo-free target, and averaging per query would let a query with
five such targets weigh the same as a query with one. The macro query-level mean
is reported beside it so the choice is visible.

## Stopping rule

No test-split scoring happens until this preregistration commit has merged. If the
reachability diagnostic reports `any_signal_fraction < 0.05`, the graph arm
structurally cannot win, and that is reported as a design limitation rather than a
model result. After the test split is scored, no change to the hypothesis,
metrics, primary comparison or split policy is permitted; a change would require a
new experiment id.

## Leak and mapping safeguards (tests, not convention)

1. Zero intersection between each query's gold set and its source's readable
   out-neighbours in the pruned index.
2. Every held-out edge endpoint resolves to exactly one corpus document; sources
   or targets with ambiguous identity are dropped. A mapping mistake here would
   silently prune the wrong edges - the worst possible leak.
3. Reciprocal-pair check: a held-out edge whose reverse survives in the retained
   graph is demoted to retained, so gold never has a readable edge in either
   direction from the source. Enforced in `build_holdout`, asserted in the build
   script and in `tests/test_patent_ir.py`.
4. The traversal index contains only document->document edges. The 12,260
   document->citation-token edges are excluded because normalising the token slugs
   would exactly reconstruct held-out edges.
5. Held-out reachability is reported as a diagnostic. Near-zero reachability means
   the graph arm structurally cannot win, which must be stated, not hidden.
6. Duplicate-body check: the corpus contains reserved-stub sections whose text is
   identical across documents. The build reports how many duplicate-body groups
   exist, how many gold targets sit on a duplicated body, and how many gold pairs
   share their source document's body; any nonzero value in that last count fails
   the build, because a target matching its own source by text would leak to every
   arm at once.

## Gold provenance

`deterministic_verifier`. A held-out citation edge is a structural fact of the
frozen dataset. No model judgment is promoted to gold, and no model-generated
question text is used, so the repo's ground-truth rule is satisfied without weak
supervision.

## Reproduce

```
uv sync --extra dev --extra local
uv run --locked python scripts/build_graphrag_holdout.py
uv run --locked python scripts/run_graphrag_arms.py
uv run --locked python scripts/report_graphrag_holdout.py
uv run --locked python scripts/run_telemetry.py rebuild
```

Frozen inputs are pinned in `artifact-fingerprints.json`; the dataset revision is
`justicedao/patent-legal-ir-graphrag@29d51084`.

## Limitations (stated before results)

- Link prediction, not question answering.
- Co-citation predicting citation is close to bibliometrics-tautological; the
  contribution is magnitude against a neural baseline and zero index cost, not
  direction.
- One small static embedding model does not represent semantic retrieval in
  general.
- The corpus is one English patent-law release; findings are scoped to it.
