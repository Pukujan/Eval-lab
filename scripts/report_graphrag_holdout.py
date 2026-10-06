"""Score the EXP-034 arms from their committed predictions and write the report.

Reads ``arm-predictions/*.jsonl`` plus the freeze manifest and emits
``results.json`` and ``report.md``. Pure arithmetic over committed files: it
never touches the dataset, so a reader can recompute every number offline.

Usage:
    uv run --locked python scripts/report_graphrag_holdout.py
    uv run --locked python scripts/report_graphrag_holdout.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "EXP-20261006-034-graphrag-citation-holdout"
ARMS = ("graph", "popularity", "semantic", "lexical")
RECALL_KS = (5, 10, 20, 50)
MRR_K = 100
ECHO_K = 10


def recall_at(ranked: Sequence[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    return len(set(ranked[:k]) & gold) / len(gold)


def reciprocal_rank(ranked: Sequence[str], gold: set[str], k: int) -> float:
    for position, cid in enumerate(ranked[:k], start=1):
        if cid in gold:
            return 1.0 / position
    return 0.0


def mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def load_predictions(arm: str, split: str) -> list[dict[str, Any]]:
    """Load one arm's predictions; ``both`` is dev and test concatenated."""

    names = ("dev", "test") if split == "both" else (split,)
    records: list[dict[str, Any]] = []
    for name in names:
        path = EXPERIMENT / "arm-predictions" / f"{arm}-{name}.jsonl"
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            records.extend(json.loads(line) for line in handle)
    return records


def score_records(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    gold_by_query = {record["query_id"]: set(record["gold_entry_cids"]) for record in records}
    metrics: dict[str, Any] = {
        "queries": len(records),
        "gold_targets": sum(len(gold) for gold in gold_by_query.values()),
    }
    for k in RECALL_KS:
        metrics[f"recall_at_{k}"] = mean(
            recall_at(record["ranked_entry_cids"], gold_by_query[record["query_id"]], k)
            for record in records
        )
    metrics[f"mrr_at_{MRR_K}"] = mean(
        reciprocal_rank(record["ranked_entry_cids"], gold_by_query[record["query_id"]], MRR_K)
        for record in records
    )

    # Preregistered secondary: recall@10 over gold targets whose full normalised
    # citation does not appear in the query text. Pooled over gold *edges*, not
    # averaged over queries: a query with one echo-free target must not weigh the
    # same as a query with five, and most queries have only a single echo-free
    # target. The macro query-level number is reported alongside so the choice is
    # visible rather than buried.
    free_pairs = 0
    free_hits = 0
    per_query: list[float] = []
    for record in records:
        echoed = record.get("gold_echoed", {})
        ranked_k = set(record["ranked_entry_cids"][:ECHO_K])
        free = [cid for cid in gold_by_query[record["query_id"]] if not echoed.get(cid, False)]
        if not free:
            continue
        hits = sum(1 for cid in free if cid in ranked_k)
        free_pairs += len(free)
        free_hits += hits
        per_query.append(hits / len(free))
    metrics[f"recall_at_{ECHO_K}_echo_free_subset"] = free_hits / free_pairs if free_pairs else 0.0
    metrics["echo_free_macro_query_mean"] = mean(per_query)
    metrics["echo_free_queries"] = len(per_query)
    metrics["echo_free_gold_pairs"] = free_pairs
    metrics["echo_free_hits"] = free_hits
    metrics["candidates_per_query_mean"] = mean(
        float(len(record["ranked_entry_cids"])) for record in records
    )
    return metrics


def load_cost(split: str, arm: str) -> dict[str, Any]:
    path = EXPERIMENT / f"arm-timings-{split}.json"
    if not path.exists():
        return {}
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded.get(arm, {})


def build_results() -> dict[str, Any]:
    freeze = json.loads((EXPERIMENT / "freeze-manifest.json").read_text(encoding="utf-8"))
    manifest = json.loads((EXPERIMENT / "split-manifest.json").read_text(encoding="utf-8"))

    results: dict[str, Any] = {
        "experiment_id": EXPERIMENT.name,
        "schema": "eval-lab/graphrag-holdout-results/v1",
        "gold_provenance": "deterministic_verifier",
        "task_shape": "link_prediction_not_question_answering",
        "dataset_revision": freeze["dataset_revision"],
        "seed": manifest["salt"],
        "holdout_fraction": manifest["holdout_fraction"],
        "min_out_edges": manifest["min_out_edges"],
        "corpus_documents": freeze["counts"]["corpus_documents"],
        "citation_edges": freeze["counts"]["citation_edges"],
        "held_out_edges": freeze["counts"]["held_out_edges"],
        "retained_edges": freeze["counts"]["retained_edges"],
        "reachability": freeze["reachability"],
        "arms": {},
    }

    for arm in ARMS:
        arm_block: dict[str, Any] = {}
        for split in ("dev", "test", "both"):
            records = load_predictions(arm, split)
            if not records:
                continue
            arm_block[split] = score_records(records)
        if not arm_block:
            continue
        arm_block["cost"] = {split: load_cost(split, arm) for split in ("dev", "test")}
        results["arms"][arm] = arm_block

    graph_test = results["arms"].get("graph", {}).get("test", {})
    semantic_test = results["arms"].get("semantic", {}).get("test", {})
    lexical_test = results["arms"].get("lexical", {}).get("test", {})
    popularity_test = results["arms"].get("popularity", {}).get("test", {})
    primary_key = f"recall_at_{ECHO_K}"
    echo_key = f"recall_at_{ECHO_K}_echo_free_subset"

    def delta(arm_a: dict[str, Any], arm_b: dict[str, Any], key: str) -> float | None:
        if key not in arm_a or key not in arm_b:
            return None
        return arm_a[key] - arm_b[key]

    results["primary_comparison"] = {
        "metric": primary_key,
        "split": "test",
        "graph": graph_test.get(primary_key),
        "semantic": semantic_test.get(primary_key),
        "lexical": lexical_test.get(primary_key),
        "popularity": popularity_test.get(primary_key),
        "graph_minus_semantic": delta(graph_test, semantic_test, primary_key),
        "graph_minus_lexical": delta(graph_test, lexical_test, primary_key),
        "graph_minus_popularity": delta(graph_test, popularity_test, primary_key),
    }
    results["primary_comparison_echo_free"] = {
        "metric": echo_key,
        "split": "test",
        "graph": graph_test.get(echo_key),
        "semantic": semantic_test.get(echo_key),
        "lexical": lexical_test.get(echo_key),
        "popularity": popularity_test.get(echo_key),
        "graph_minus_semantic": delta(graph_test, semantic_test, echo_key),
        "graph_minus_popularity": delta(graph_test, popularity_test, echo_key),
    }
    return results


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _fmt_delta(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.3f}"


def render_report(results: dict[str, Any]) -> str:
    reach = results["reachability"]
    primary = results["primary_comparison"]
    echo = results["primary_comparison_echo_free"]

    lines: list[str] = []
    lines.append(f"# {results['experiment_id']} - results")
    lines.append("")
    lines.append(
        "Deterministic retrieval benchmark. Gold is a held-out citation edge, a structural "
        "fact of the frozen dataset (`deterministic_verifier`); no model was scored and no "
        "judge was called, so the Jev integration contract does not apply."
    )
    lines.append("")
    lines.append("## Substrate")
    lines.append("")
    lines.append(f"- corpus documents: {results['corpus_documents']}")
    lines.append(f"- document->document citation edges: {results['citation_edges']}")
    lines.append(
        f"- held out: {results['held_out_edges']}; retained for traversal: "
        f"{results['retained_edges']}"
    )
    lines.append(
        "- reachability of held-out targets from retained structure: two-hop "
        f"{reach['two_hop_fraction']:.3f}, co-citation {reach['co_citation_fraction']:.3f}, "
        f"common-citer {reach['common_citer_fraction']:.3f}, any {reach['any_signal_fraction']:.3f}"
    )
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    columns = [f"R@{k}" for k in RECALL_KS] + [f"MRR@{MRR_K}", f"R@{ECHO_K} echo-free"]
    lines.append("| arm | split | n | " + " | ".join(columns) + " |")
    lines.append("|" + "---|" * (3 + len(columns)))
    for arm in ARMS:
        block = results["arms"].get(arm)
        if not block:
            continue
        for split in ("dev", "test", "both"):
            metrics = block.get(split)
            if not metrics:
                continue
            cells = [f"{metrics[f'recall_at_{k}']:.3f}" for k in RECALL_KS]
            cells.append(f"{metrics[f'mrr_at_{MRR_K}']:.3f}")
            cells.append(f"{metrics[f'recall_at_{ECHO_K}_echo_free_subset']:.3f}")
            lines.append(f"| {arm} | {split} | {metrics['queries']} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## Primary comparison (test split)")
    lines.append("")
    lines.append(
        f"Preregistered metric `{primary['metric']}`: graph {_fmt(primary['graph'])}, semantic "
        f"{_fmt(primary['semantic'])}, lexical {_fmt(primary['lexical'])}, popularity "
        f"{_fmt(primary['popularity'])}; graph - semantic = "
        f"{_fmt_delta(primary['graph_minus_semantic'])}, graph - lexical = "
        f"{_fmt_delta(primary['graph_minus_lexical'])}, graph - popularity = "
        f"{_fmt_delta(primary['graph_minus_popularity'])}."
    )
    lines.append("")
    lines.append(
        f"Echo-free secondary `{echo['metric']}`: graph {_fmt(echo['graph'])}, semantic "
        f"{_fmt(echo['semantic'])}, lexical {_fmt(echo['lexical'])}, popularity "
        f"{_fmt(echo['popularity'])}; graph - semantic = "
        f"{_fmt_delta(echo['graph_minus_semantic'])}, graph - popularity = "
        f"{_fmt_delta(echo['graph_minus_popularity'])}."
    )
    lines.append("")
    lines.append("## Cost")
    lines.append("")
    for arm in ARMS:
        block = results["arms"].get(arm)
        if not block:
            continue
        cost = block.get("cost", {}).get("test") or block.get("cost", {}).get("dev") or {}
        if not cost:
            continue
        parts = []
        for key, value in sorted(cost.items()):
            rendered = f"{value:.4g}" if isinstance(value, float) else str(value)
            parts.append(f"{key}={rendered}")
        lines.append(f"- {arm}: " + ", ".join(parts))
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "- Link prediction, not question answering: the query is the source document's own "
        "text and gold is what it cites, so this is not a question-answering result."
    )
    lines.append(
        "- Co-citation predicting citation is close to bibliometrics-tautological; the "
        "contribution is magnitude against a neural baseline and zero index-time LLM cost, "
        "not the direction of the effect."
    )
    lines.append(
        "- One small static encoder stands in for semantic retrieval; a stronger or "
        "domain-adapted encoder would raise that baseline."
    )
    lines.append(
        "- One English patent-law corpus; findings are scoped to it and are not a general "
        "claim about Graph RAG."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed results match")
    args = parser.parse_args()

    results = build_results()
    results_path = EXPERIMENT / "results.json"
    report_path = EXPERIMENT / "report.md"
    payload = json.dumps(results, indent=2, sort_keys=True) + "\n"
    report = render_report(results)

    if args.check:
        current = results_path.read_text(encoding="utf-8") if results_path.exists() else ""
        if current != payload:
            print("FAIL: results.json is stale; re-run without --check", file=sys.stderr)
            return 1
        print("results.json matches")
        return 0

    results_path.write_text(payload, encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    print(f"wrote {results_path.relative_to(ROOT)}")
    print(f"wrote {report_path.relative_to(ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
