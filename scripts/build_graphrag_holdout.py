"""Freeze the patent-law IR release and build the citation hold-out for EXP-034.

Downloads the pinned release revision, resolves the graph's document->document
citation edges onto corpus documents, holds out a seeded slice per source, and
writes the split manifest and query set into the experiment directory. Offline
after the download: no model and no provider call.

Usage:
    uv run --locked python scripts/build_graphrag_holdout.py [--work-dir DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

try:
    from eval_lab.datasets.patent_ir import (
        build_holdout,
        citation_is_echoed,
        dumps_manifest,
        duplicate_body_diagnostic,
        load_citations,
        load_corpus,
        reachability_diagnostic,
        source_split,
    )
except ImportError:  # executed as a file from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from eval_lab.datasets.patent_ir import (
        build_holdout,
        citation_is_echoed,
        dumps_manifest,
        duplicate_body_diagnostic,
        load_citations,
        load_corpus,
        reachability_diagnostic,
        source_split,
    )

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "EXP-20261006-034-graphrag-citation-holdout"
REPO = "justicedao/patent-legal-ir-graphrag"
REVISION = "29d510841f112bbe41fb209307a55cd1bdc70ca0"
SALT = 20261006
HOLDOUT_FRACTION = 0.3
MIN_OUT_EDGES = 3
PATTERNS = ["data/corpus/*", "data/graph/edges/*", "data/graph/nodes/*"]


def _fetch(work_dir: Path) -> Path:
    from huggingface_hub import snapshot_download

    release = work_dir / "release"
    snapshot_download(
        REPO,
        repo_type="dataset",
        revision=REVISION,
        local_dir=release,
        allow_patterns=PATTERNS,
    )
    return release


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_work_dir() -> Path:
    """Scratch lives outside the checkout, per the workspace contract."""

    return Path(tempfile.gettempdir()) / "eval-lab-graphrag-work"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=default_work_dir(),
        help="scratch directory for the downloaded release (outside the commit set)",
    )
    args = parser.parse_args()
    work_dir: Path = args.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"fetching {REPO}@{REVISION[:12]} into {work_dir} ...", flush=True)
    release = _fetch(work_dir)

    corpus = load_corpus(release / "data" / "corpus" / "part-000000.parquet")
    edges = load_citations(
        release / "data" / "graph" / "edges",
        release / "data" / "graph" / "nodes",
        corpus,
    )
    print(f"corpus documents: {len(corpus)}")
    print(f"document->document citation edges: {len(edges)}")

    split = build_holdout(
        edges, salt=SALT, holdout_fraction=HOLDOUT_FRACTION, min_out_edges=MIN_OUT_EDGES
    )
    gold = split.gold
    print(
        f"held out {len(split.held)} edges, retained {len(split.retained)}; "
        f"queries dev {len(split.dev_sources)} test {len(split.test_sources)}"
    )

    # safeguard 1: no gold target is readable from the source's retained edges
    readable: dict[str, set[str]] = {}
    for source, target in split.retained:
        readable.setdefault(source, set()).add(target)
    leaks = [s for s, targets in gold.items() if targets & readable.get(s, set())]
    if leaks:
        print(
            f"FAIL: {len(leaks)} sources have gold in their readable out-neighbours",
            file=sys.stderr,
        )
        return 1
    print("safeguard 1 OK: no gold target is a readable out-neighbour")

    # safeguard 3: reciprocal pairs must not be readable from the target side
    retained_set = set(split.retained)
    reciprocal = sum(1 for s, t in split.held if (t, s) in retained_set)
    if reciprocal:
        print(
            f"FAIL: {reciprocal} held edges have their reverse readable in retained",
            file=sys.stderr,
        )
        return 1
    print("safeguard 3 OK: no held edge has a readable reverse")

    diagnostic = reachability_diagnostic(split)
    print(f"reachability diagnostic: {json.dumps(diagnostic)}")
    if diagnostic["any_signal_fraction"] < 0.05:
        print(
            "WARNING: held-out citations are almost never reachable by structure; "
            "the graph arm cannot win on this split (report as a design limitation)",
            file=sys.stderr,
        )

    # safeguard 6: reserved-stub documents share bodies; measure whether that could
    # let a gold target match its source by text alone
    duplicates = duplicate_body_diagnostic(split, corpus)
    print(f"duplicate-body diagnostic: {json.dumps(duplicates)}")
    if duplicates["gold_pairs_sharing_the_source_body"]:
        print(
            f"FAIL: {duplicates['gold_pairs_sharing_the_source_body']} gold pairs share "
            "their source document's body",
            file=sys.stderr,
        )
        return 1
    print("safeguard 6 OK: no gold target shares its source document's body")

    sources = {
        cid: {
            "split": source_split(cid, salt=SALT).value,
            "citation": doc.citation,
            "family": doc.family,
        }
        for cid, doc in corpus.items()
    }
    split_path = EXPERIMENT / "split-manifest.json"
    split_path.write_text(dumps_manifest(split, sources=sources), encoding="utf-8")

    queries_path = EXPERIMENT / "queries.jsonl"
    echoed_sources = 0
    with queries_path.open("w", encoding="utf-8", newline="\n") as handle:
        for split_name, source_list in (
            ("dev", split.dev_sources),
            ("test", split.test_sources),
        ):
            for source in source_list:
                doc = corpus[source]
                targets = sorted(gold.get(source, ()))
                echo_flags = {t: citation_is_echoed(doc, corpus[t]) for t in targets}
                if any(echo_flags.values()):
                    echoed_sources += 1
                # the query text is the dataset's own body, so it is identified by
                # hash and length here rather than redistributed; the arm script
                # re-derives it from the locally downloaded corpus by entry_cid
                record = {
                    "query_id": f"{split_name}:{source}",
                    "split": split_name,
                    "source_entry_cid": source,
                    "source_citation": doc.citation,
                    "source_family": doc.family,
                    "query_text_sha256": hashlib.sha256(doc.body.encode()).hexdigest(),
                    "query_text_chars": len(doc.body),
                    "gold_entry_cids": targets,
                    "gold_citations": [corpus[t].citation for t in targets],
                    "gold_echoed": echo_flags,
                }
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    total_queries = len(split.dev_sources) + len(split.test_sources)
    print(
        f"wrote {total_queries} queries; {echoed_sources} have at least one gold echoed "
        f"in the query text ({echoed_sources / max(1, total_queries):.0%})"
    )

    # the frozen citation graph, with each edge's hold-out status, so the arm script
    # and any auditor can see exactly which edges the graph arm may traverse
    edges_path = EXPERIMENT / "citation-edges.jsonl"
    held_set = set(split.held)
    with edges_path.open("w", encoding="utf-8", newline="\n") as handle:
        for source, target in edges:
            handle.write(
                json.dumps(
                    {
                        "source_entry_cid": source,
                        "target_entry_cid": target,
                        "held_out": (source, target) in held_set,
                        "source_split": source_split(source, salt=SALT).value,
                        "source_citation": corpus[source].citation,
                        "target_citation": corpus[target].citation,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    print(f"wrote {len(edges)} citation edges to {edges_path.relative_to(ROOT)}")

    freeze = {
        "schema": "eval-lab/graphrag-freeze/v1",
        "dataset_revision": REVISION,
        "source_file_sha256": {
            "data/corpus/part-000000.parquet": _sha256(
                release / "data" / "corpus" / "part-000000.parquet"
            ),
        },
        "query_set_sha256": _sha256(queries_path),
        "split_manifest_sha256": _sha256(split_path),
        "citation_edges_sha256": _sha256(edges_path),
        "counts": {
            "corpus_documents": len(corpus),
            "citation_edges": len(edges),
            "held_out_edges": len(split.held),
            "retained_edges": len(split.retained),
            "queries": total_queries,
        },
        "reachability": diagnostic,
        "duplicate_bodies": duplicates,
    }
    freeze_path = EXPERIMENT / "freeze-manifest.json"
    freeze_path.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for path in (split_path, queries_path, edges_path, freeze_path):
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
