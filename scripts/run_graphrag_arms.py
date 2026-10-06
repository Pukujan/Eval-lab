"""Run the three EXP-034 retrieval arms over the frozen citation hold-out.

Arms, all over the same corpus and the same source-document queries:

- ``lexical``  BM25 over ``title`` + ``text`` with the release's documented
  tokenizer and parameters.
- ``semantic`` mean-pooled sentence embeddings, cosine k-NN.
- ``graph``    2-hop co-citation over the *retained* document->document citation
  subgraph, entered at the source document. The source is the query, so entry is
  exact - there is no entity-linking step to get wrong.

The source document is excluded from every arm's candidate set: the query text
*is* that document's text, so leaving it in would let every arm return it.

No held-out edge is loaded into the graph arm's index. Predictions are written
per arm and per split so scoring can happen after the preregistration commit.

Usage:
    uv run --locked python scripts/run_graphrag_arms.py [--split dev|test|both]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
import time
import warnings
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

try:
    from eval_lab.datasets.patent_ir import Document, load_corpus
except ImportError:  # executed as a file from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from eval_lab.datasets.patent_ir import Document, load_corpus

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "EXP-20261006-034-graphrag-citation-holdout"
ARMS = ("graph", "popularity", "semantic", "lexical")

# the release's documented BM25 tokenizer and parameters
TOKEN_RE = re.compile(r"[a-z0-9]+")
BM25_K1 = 1.2
BM25_B = 0.75
TITLE_WEIGHT = 5.0
BODY_WEIGHT = 1.0
IDF_FLOOR = 1e-6
# rankings are truncated to the deepest preregistered depth (MRR@100): every
# metric is defined at k <= 100, and committing the near-zero-score tail would add
# tens of MB of unread candidates to the artifact for no measurable result
CANDIDATE_LIMIT = 100

# pinned so the semantic arm is reproducible; chunk-max-pooling over overlapping
# windows is the documented remedy for long-document retrieval, so no
# sentence-transformers dependency is needed
SEMANTIC_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEMANTIC_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
SEMANTIC_BATCH = 32
SEMANTIC_WINDOW = 512
SEMANTIC_STRIDE = 256


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def latency_summary(latencies_ms: list[float]) -> dict[str, float]:
    if not latencies_ms:
        return {"query_latency_ms_mean": 0.0, "query_latency_ms_p95": 0.0}
    ordered = sorted(latencies_ms)
    position = min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))
    return {
        "query_latency_ms_mean": sum(ordered) / len(ordered),
        "query_latency_ms_p95": ordered[position],
    }


class BM25:
    """BM25 over weighted title+body, with the release's documented parameters."""

    def __init__(self, documents: dict[str, Document]) -> None:
        self.ids = sorted(documents)
        self.doc_len: dict[str, float] = {}
        self.postings: dict[str, dict[str, float]] = defaultdict(dict)
        for cid in self.ids:
            doc = documents[cid]
            weighted: Counter[str] = Counter()
            for term, count in Counter(tokenize(doc.title)).items():
                weighted[term] += TITLE_WEIGHT * count
            for term, count in Counter(tokenize(doc.body)).items():
                weighted[term] += BODY_WEIGHT * count
            self.doc_len[cid] = float(sum(weighted.values())) or 1.0
            for term, weight in weighted.items():
                self.postings[term][cid] = weight
        self.avg_len = sum(self.doc_len.values()) / max(1, len(self.ids))
        self.idf = {
            term: max(IDF_FLOOR, math.log((len(self.ids) - len(post) + 0.5) / (len(post) + 0.5)))
            for term, post in self.postings.items()
        }

    @property
    def index_size_bytes(self) -> int:
        return 8 * sum(len(post) for post in self.postings.values()) + 8 * len(self.doc_len)

    def score(self, query_tokens: Sequence[str]) -> dict[str, float]:
        scores: dict[str, float] = defaultdict(float)
        for term in set(query_tokens):
            post = self.postings.get(term)
            if not post:
                continue
            idf = self.idf[term]
            for cid, freq in post.items():
                denominator = freq + BM25_K1 * (
                    1 - BM25_B + BM25_B * self.doc_len[cid] / self.avg_len
                )
                scores[cid] += idf * (freq * (BM25_K1 + 1)) / denominator
        return dict(scores)


def rank_from_scores(
    scores: dict[str, float], exclude: str, limit: int = CANDIDATE_LIMIT
) -> list[str]:
    """Rank by score descending, breaking ties on entry_cid for determinism."""

    ranked = sorted(
        ((score, cid) for cid, score in scores.items() if cid != exclude and score > 0.0),
        key=lambda item: (-item[0], item[1]),
    )
    return [cid for _, cid in ranked[:limit]]


class Semantic:
    """Chunked sentence embeddings with cosine k-NN.

    Documents run to a mean of ~2,300 tokens, so a single 512-token window would
    represent only the opening of most of the corpus and make this a strawman.
    Each document is split into overlapping windows, every window is embedded,
    and the document vector is the elementwise max over its windows - the standard
    chunk-max-pooling remedy for long-document retrieval.

    The corpus matrix is cached in the work directory, keyed by model revision
    and window geometry, because dev and test runs share one corpus embedding.
    """

    def __init__(self, documents: dict[str, Document], cache_dir: Path | None = None) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.ids = sorted(documents)
        self.position = {cid: index for index, cid in enumerate(self.ids)}
        cache = cache_dir / "semantic-windows-cache.pt" if cache_dir is not None else None
        if cache is not None and cache.exists():
            loaded = torch.load(cache, weights_only=True)
            if (
                loaded.get("model") == SEMANTIC_MODEL
                and loaded.get("revision") == SEMANTIC_REVISION
                and loaded.get("window") == SEMANTIC_WINDOW
                and loaded.get("stride") == SEMANTIC_STRIDE
                and loaded.get("ids") == self.ids
            ):
                self.window_matrix = loaded["matrix"]
                self.owner = loaded["owner"]
                self.window_count = int(self.window_matrix.shape[0])
                self.owner_index = self._owner_index()
                return

        tokenizer = AutoTokenizer.from_pretrained(SEMANTIC_MODEL, revision=SEMANTIC_REVISION)
        model = AutoModel.from_pretrained(SEMANTIC_MODEL, revision=SEMANTIC_REVISION)
        model.eval()

        chunks: list[str] = []
        owner: list[int] = []
        for index, cid in enumerate(self.ids):
            tokens = tokenizer.tokenize(documents[cid].body)
            if not tokens:
                chunks.append("")
                owner.append(index)
                continue
            start = 0
            while True:
                window = tokens[start : start + SEMANTIC_WINDOW]
                chunks.append(tokenizer.convert_tokens_to_string(window))
                owner.append(index)
                if start + SEMANTIC_WINDOW >= len(tokens):
                    break
                start += SEMANTIC_STRIDE

        windows: list[Any] = []
        with torch.no_grad():
            for start in range(0, len(chunks), SEMANTIC_BATCH):
                encoded = tokenizer(
                    chunks[start : start + SEMANTIC_BATCH],
                    padding=True,
                    truncation=True,
                    max_length=SEMANTIC_WINDOW,
                    return_tensors="pt",
                )
                hidden = model(**encoded).last_hidden_state
                mask = encoded["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
                windows.append(torch.nn.functional.normalize(pooled, dim=1))
        self.window_matrix = torch.cat(windows, dim=0)
        self.owner = torch.tensor(owner)
        self.window_count = len(chunks)
        self.owner_index = self._owner_index()

        if cache is not None:
            torch.save(
                {
                    "model": SEMANTIC_MODEL,
                    "revision": SEMANTIC_REVISION,
                    "window": SEMANTIC_WINDOW,
                    "stride": SEMANTIC_STRIDE,
                    "ids": self.ids,
                    "matrix": self.window_matrix,
                    "owner": self.owner,
                },
                cache,
            )

    def _owner_index(self) -> dict[int, list[int]]:
        index: dict[int, list[int]] = defaultdict(list)
        for window, owner in enumerate(self.owner.tolist()):
            index[owner].append(window)
        return dict(index)

    @property
    def index_size_bytes(self) -> int:
        return int(self.window_matrix.numel() * self.window_matrix.element_size())

    def scores_for(self, cid: str) -> dict[str, float]:
        """Max-similarity of each candidate's best window to the query's windows.

        maxP: score(candidate) = max over the query's windows and the candidate's
        windows of the cosine similarity. Using the best chunk of each side is the
        standard multi-vector long-document scoring; the query's own windows are
        excluded from the candidate side by ownership.
        """

        query_windows = self.owner_index[self.position[cid]]
        query = self.window_matrix[query_windows]  # (q, d)
        similarity = query @ self.window_matrix.T  # (q, n_windows)
        best_per_window = similarity.max(dim=0).values  # (n_windows,)
        scores: dict[str, float] = {}
        best_by_doc = best_per_window.new_full((len(self.ids),), float("-inf"))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # index_reduce_ is beta and warns once
            best_by_doc.index_reduce_(0, self.owner, best_per_window, "amax", include_self=True)
        for index, other in enumerate(self.ids):
            if other != cid:
                scores[other] = float(best_by_doc[index])
        return scores


def build_graph_index(retained: Sequence[tuple[str, str]]) -> dict[str, set[str]]:
    """Out-neighbour index built from retained edges only."""

    out: dict[str, set[str]] = defaultdict(set)
    for source, target in retained:
        out[source].add(target)
    return out


def build_popularity_index(retained: Sequence[tuple[str, str]]) -> list[str]:
    """Documents ranked by retained in-degree: the no-structure baseline.

    If a graph arm cannot beat this, its traversal adds nothing over "return the
    most-cited documents", which is the sharpest null for a citation task.
    """

    in_degree: Counter[str] = Counter(target for _, target in retained)
    return sorted(in_degree, key=lambda cid: (-in_degree[cid], cid))


def graph_scores(source: str, out: dict[str, set[str]]) -> dict[str, float]:
    """Count retained paths of length <= 2 out of the source.

    A held-out ``source -> target`` edge is absent from ``out``, so the only route
    to the target is ``source -> u -> target`` through retained edges. Retained
    one-hop neighbours are also returned, because a real traversal would return
    them; they can never be gold by construction, so they act as a precision tax
    the graph arm pays rather than a hidden advantage.
    """

    scores: dict[str, float] = defaultdict(float)
    for step in out.get(source, set()):
        scores[step] += 1.0
        for candidate in out.get(step, set()):
            if candidate != source:
                scores[candidate] += 1.0
    scores.pop(source, None)
    return dict(scores)


def load_queries(split: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with (EXPERIMENT / "queries.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if split in ("both", record["split"]):
                records.append(record)
    return records


def load_edges() -> tuple[list[tuple[str, str]], set[tuple[str, str]]]:
    edges: list[tuple[str, str]] = []
    held: set[tuple[str, str]] = set()
    with (EXPERIMENT / "citation-edges.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            pair = (record["source_entry_cid"], record["target_entry_cid"])
            edges.append(pair)
            if record["held_out"]:
                held.add(pair)
    return edges, held


def write_predictions(
    arm: str,
    split: str,
    queries: Sequence[dict[str, Any]],
    corpus: dict[str, Document],
    rankings: dict[str, list[str]],
    out_dir: Path,
) -> Path:
    path = out_dir / f"{arm}-{split}.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in queries:
            source = record["source_entry_cid"]
            handle.write(
                json.dumps(
                    {
                        "query_id": record["query_id"],
                        "split": record["split"],
                        "arm": arm,
                        "source_entry_cid": source,
                        "ranked_entry_cids": rankings[source],
                        "gold_entry_cids": record["gold_entry_cids"],
                        "gold_echoed": record["gold_echoed"],
                        "query_text_sha256": hashlib.sha256(
                            corpus[source].body.encode()
                        ).hexdigest(),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    return path


def rank_all(
    queries: Sequence[dict[str, Any]], scorer: Any, *, build_seconds: float, size_bytes: int
) -> tuple[dict[str, list[str]], dict[str, float]]:
    rankings: dict[str, list[str]] = {}
    latencies: list[float] = []
    for record in queries:
        source = record["source_entry_cid"]
        tick = time.perf_counter()
        rankings[source] = scorer(source)
        latencies.append(1000 * (time.perf_counter() - tick))
    cost = {
        "index_build_seconds": build_seconds,
        "index_size_bytes": size_bytes,
        **latency_summary(latencies),
    }
    return rankings, cost


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "both"), default="both")
    parser.add_argument(
        "--work-dir",
        type=Path,
        # scratch lives outside the checkout, per the workspace contract
        default=Path(tempfile.gettempdir()) / "eval-lab-graphrag-work",
        help="scratch directory holding the downloaded release",
    )
    parser.add_argument("--arms", default=",".join(ARMS))
    args = parser.parse_args()

    corpus_path = args.work_dir / "release" / "data" / "corpus" / "part-000000.parquet"
    if not corpus_path.exists():
        print(f"FAIL: corpus not found at {corpus_path}; run build_graphrag_holdout.py first")
        return 1

    selected = [arm for arm in args.arms.split(",") if arm]
    for arm in selected:
        if arm not in ARMS:
            print(f"FAIL: unknown arm {arm}", file=sys.stderr)
            return 1

    corpus = load_corpus(corpus_path)
    queries = load_queries(args.split)
    edges, held = load_edges()
    retained = [edge for edge in edges if edge not in held]
    print(
        f"corpus {len(corpus)} docs; queries {len(queries)} ({args.split}); "
        f"retained edges {len(retained)}",
        flush=True,
    )

    out_dir = EXPERIMENT / "arm-predictions"
    out_dir.mkdir(exist_ok=True)
    timings: dict[str, dict[str, float]] = {}
    rankings: dict[str, dict[str, list[str]]] = {}

    if "lexical" in selected:
        started = time.perf_counter()
        lexical = BM25(corpus)
        build = time.perf_counter() - started
        print(f"lexical index built in {build:.1f}s", flush=True)
        rankings["lexical"], timings["lexical"] = rank_all(
            queries,
            lambda source: rank_from_scores(
                lexical.score(tokenize(corpus[source].body)), exclude=source
            ),
            build_seconds=build,
            size_bytes=lexical.index_size_bytes,
        )

    if "semantic" in selected:
        started = time.perf_counter()
        semantic = Semantic(corpus, cache_dir=args.work_dir)
        build = time.perf_counter() - started
        print(
            f"semantic index built in {build:.1f}s "
            f"({semantic.window_count} windows over {len(semantic.ids)} docs)",
            flush=True,
        )
        rankings["semantic"], timings["semantic"] = rank_all(
            queries,
            lambda source: rank_from_scores(semantic.scores_for(source), exclude=source),
            build_seconds=build,
            size_bytes=semantic.index_size_bytes,
        )

    if "graph" in selected:
        out = build_graph_index(retained)
        size = 8 * sum(len(targets) for targets in out.values())
        rankings["graph"], timings["graph"] = rank_all(
            queries,
            # the query *is* the source document, so the graph arm enters exactly
            # at the source; only traversal over retained edges can reach a target
            lambda source: rank_from_scores(graph_scores(source, out), exclude=source),
            build_seconds=0.0,
            size_bytes=size,
        )

    if "popularity" in selected:
        # a single global ranking: the graph arm's sharpest null
        popular = build_popularity_index(retained)
        rankings["popularity"], timings["popularity"] = rank_all(
            queries,
            # truncated to the same depth as every other arm, so the null is scored
            # on equal footing and the artifact is the same shape
            lambda source: [cid for cid in popular if cid != source][:CANDIDATE_LIMIT],
            build_seconds=0.0,
            size_bytes=8 * len(popular),
        )

    for arm in selected:
        path = write_predictions(arm, args.split, queries, corpus, rankings[arm], out_dir)
        print(f"wrote {path.relative_to(ROOT)}", flush=True)

    timings_path = EXPERIMENT / f"arm-timings-{args.split}.json"
    timings_path.write_text(json.dumps(timings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {timings_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
