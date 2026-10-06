# EXP-20261006-034-graphrag-citation-holdout - results

Deterministic retrieval benchmark. Gold is a held-out citation edge, a structural fact of the frozen dataset (`deterministic_verifier`); no model was scored and no judge was called, so the Jev integration contract does not apply.

## Substrate

- corpus documents: 2174
- document->document citation edges: 8626
- held out: 2296; retained for traversal: 6330
- reachability of held-out targets from retained structure: two-hop 0.572, co-citation 0.471, common-citer 0.540, any 0.790

## Metrics

| arm | split | n | R@5 | R@10 | R@20 | R@50 | MRR@100 | R@10 echo-free |
|---|---|---|---|---|---|---|---|---|
| graph | dev | 304 | 0.116 | 0.174 | 0.246 | 0.327 | 0.177 | 0.281 |
| graph | test | 292 | 0.088 | 0.163 | 0.235 | 0.313 | 0.144 | 0.385 |
| graph | both | 596 | 0.102 | 0.169 | 0.240 | 0.320 | 0.161 | 0.338 |
| popularity | dev | 304 | 0.115 | 0.184 | 0.281 | 0.407 | 0.191 | 0.062 |
| popularity | test | 292 | 0.118 | 0.201 | 0.324 | 0.443 | 0.179 | 0.128 |
| popularity | both | 596 | 0.117 | 0.193 | 0.302 | 0.425 | 0.185 | 0.099 |
| semantic | dev | 304 | 0.040 | 0.069 | 0.102 | 0.203 | 0.073 | 0.031 |
| semantic | test | 292 | 0.031 | 0.067 | 0.101 | 0.190 | 0.076 | 0.000 |
| semantic | both | 596 | 0.036 | 0.068 | 0.101 | 0.197 | 0.074 | 0.014 |
| lexical | dev | 304 | 0.032 | 0.052 | 0.082 | 0.138 | 0.071 | 0.031 |
| lexical | test | 292 | 0.041 | 0.063 | 0.095 | 0.171 | 0.082 | 0.000 |
| lexical | both | 596 | 0.036 | 0.057 | 0.088 | 0.154 | 0.077 | 0.014 |

## Primary comparison (test split)

Preregistered metric `recall_at_10`: graph 0.163, semantic 0.067, lexical 0.063, popularity 0.201; graph - semantic = +0.096, graph - lexical = +0.101, graph - popularity = -0.038.

Echo-free secondary `recall_at_10_echo_free_subset`: graph 0.385, semantic 0.000, lexical 0.000, popularity 0.128; graph - semantic = +0.385, graph - popularity = +0.256.

## Cost

- graph: index_build_seconds=0, index_size_bytes=50640, query_latency_ms_mean=0.07354, query_latency_ms_p95=0.3231
- popularity: index_build_seconds=0, index_size_bytes=7584, query_latency_ms_mean=0.06751, query_latency_ms_p95=0.0802
- semantic: index_build_seconds=33.84, index_size_bytes=29587968, query_latency_ms_mean=23.42, query_latency_ms_p95=31.48
- lexical: index_build_seconds=2.394, index_size_bytes=6064872, query_latency_ms_mean=183.6, query_latency_ms_p95=274.1

## Post-hoc diagnostics (not preregistered)

On the echo-free stratum, graph versus popularity at recall@10, per query: graph wins 15, ties 16, loses 4. The pooled echo-free rate is carried by a small number of queries, so this is reported beside it.

Recall@10 by the gold target's retained in-degree. Popularity returns a single query-independent ranking, so a high-degree bucket is where it wins without using the query at all; a graph edge that survives high in-degree is query-conditioned.

| target in-degree | gold pairs | graph R@10 | popularity R@10 |
|---|---|---|---|
| 0 | 38 | 0.000 | 0.000 |
| 1 | 48 | 0.042 | 0.000 |
| 2-3 | 95 | 0.053 | 0.000 |
| 4-7 | 152 | 0.053 | 0.000 |
| 8+ | 718 | 0.219 | 0.227 |

## Limitations

- Link prediction, not question answering: the query is the source document's own text and gold is what it cites, so this is not a question-answering result.
- The popularity null leads the graph arm on the full test set. A graph arm that cannot beat 'return the most-cited documents' has not shown that traversal adds query-conditioned value; the aggregate result must not be reported as a graph win.
- The echo-free stratum is thin: it covers only the queries whose gold targets are not named in the query text, and the pooled rate rests on a few dozen gold pairs. Treat it as directional evidence, not a precise effect size.
- Co-citation predicting citation is close to bibliometrics-tautological; the contribution is magnitude against a neural baseline and zero index-time LLM cost, not the direction of the effect.
- One small static encoder stands in for semantic retrieval; a stronger or domain-adapted encoder would raise that baseline.
- One English patent-law corpus; findings are scoped to it and are not a general claim about Graph RAG.

