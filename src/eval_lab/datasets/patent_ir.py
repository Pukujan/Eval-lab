"""Load the frozen patent-law IR release and build a leak-free citation hold-out.

The release ``justicedao/patent-legal-ir-graphrag`` ships a corpus, BM25 postings
and a typed authority graph, but no questions. This module turns the graph's
document->document citation edges into a retrieval task: a slice of each source
document's outgoing citations is held out, and a retriever must recover those
targets from the source document without being able to read the held-out edge.

Gold is a structural fact of the frozen dataset, so it is deterministic
verification, not model supervision. The split unit is the source document: every
held-out edge of a source shares that source's split, so no document crosses the
dev/test boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_lab.schema import Split

DATASET = "patent_ir"
SPLIT_FAMILY = "patent-ir-graphrag"
VERIFIER_ID = "patent-ir-citation-holdout-v1"
CITATION_RELATION = "references_authority"
DOC_NODE_KIND = "document"

# Substring normalisation is only used to decide whether a query text names a
# gold citation verbatim (the echo diagnostic); identity always uses entry_cid.
# The trailing period is optional but a trailing space is not consumed, so
# "37 CFR 1.56" and "37-cfr-1-56" both normalise to "37-cfr-1-56".
_ROMAN_U = re.compile(r"\bu\s*\.?\s*s\s*\.?\s*c\.?")
_ROMAN_C = re.compile(r"\bc\s*\.?\s*f\s*\.?\s*r\.?")


def normalize_citation(value: str | None) -> str:
    """Return a comparable slug for a citation in either display or slug form.

    Display values look like ``37 CFR 1.56`` / ``35 U.S.C. § 101`` / ``MPEP § 1002.02``
    and slug values like ``37-cfr-1-56`` / ``35-usc-101`` / ``mpep-1002-02``. Both
    normalise to the slug form.
    """

    text = (value or "").lower().replace("§", " ")
    text = _ROMAN_U.sub("usc", text)
    text = _ROMAN_C.sub("cfr", text)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _unit(*parts: object) -> float:
    digest = hashlib.sha256(":".join(str(part) for part in parts).encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big") / float(2**64)


def source_split(source_id: str, *, salt: int) -> Split:
    """Assign a source document to dev or test using only its identity."""

    if not source_id:
        raise ValueError("source_id must be non-empty")
    return Split.DEV if _unit(salt, SPLIT_FAMILY, "split", source_id) < 0.5 else Split.TEST


@dataclass(frozen=True)
class Document:
    entry_cid: str
    citation: str
    family: str
    title: str
    text: str
    section_id: str

    @property
    def body(self) -> str:
        return f"{self.title}\n{self.text}"


def load_corpus(path: Path) -> dict[str, Document]:
    """Load corpus documents keyed by ``entry_cid`` (the graph join key)."""

    import pyarrow.parquet as pq

    rows = pq.read_table(path).to_pylist()
    documents: dict[str, Document] = {}
    for row in rows:
        entry_cid = str(row["entry_cid"])
        if entry_cid in documents:
            raise ValueError(f"duplicate entry_cid in corpus: {entry_cid}")
        documents[entry_cid] = Document(
            entry_cid=entry_cid,
            citation=str(row.get("citation") or ""),
            family=str(row.get("family") or ""),
            title=str(row.get("title") or ""),
            text=str(row.get("text") or ""),
            section_id=str(row.get("section_id") or ""),
        )
    return documents


def _parquet_files(path: Path) -> list[Path]:
    if path.is_dir():
        files = sorted(path.glob("*.parquet"))
        if not files:
            raise FileNotFoundError(f"no parquet shards under {path}")
        return files
    return [path]


def load_citations(
    citations_path: Path, nodes_path: Path, corpus: Mapping[str, Document]
) -> list[tuple[str, str]]:
    """Resolve document->document citation edges to corpus ``entry_cid`` pairs.

    Graph endpoints are IPFS node CIDs; each ``document`` node carries the corpus
    ``entry_cid`` it was built from. An endpoint that does not resolve to exactly
    one corpus document is a mapping error and is rejected, because a silent
    mismatch would prune the wrong edges - the worst possible leak.

    ``citations_path`` and ``nodes_path`` may each be a directory of parquet
    shards (the release ships 216 citation shards and 10 node shards) or a single
    file.
    """

    import pyarrow.parquet as pq

    node_to_entry: dict[str, str] = {}
    for shard in _parquet_files(nodes_path):
        for node in pq.read_table(shard, columns=["node_cid", "kind", "entry_cid"]).to_pylist():
            if str(node["kind"]) != DOC_NODE_KIND:
                continue
            node_cid = str(node["node_cid"])
            if node_cid in node_to_entry:
                raise ValueError(f"duplicate document node_cid: {node_cid}")
            node_to_entry[node_cid] = str(node["entry_cid"])

    edges: set[tuple[str, str]] = set()
    for shard in _parquet_files(citations_path):
        for row in pq.read_table(shard).to_pylist():
            if str(row.get("relation")) != CITATION_RELATION:
                continue
            subject = node_to_entry.get(str(row["subject_cid"]))
            target = node_to_entry.get(str(row["object_cid"]))
            if subject is None or target is None:
                continue  # a citation-token or non-document endpoint, not a doc->doc edge
            if subject not in corpus or target not in corpus:
                raise ValueError(f"citation endpoint not in corpus: {subject} -> {target}")
            if subject != target:
                edges.add((subject, target))
    return sorted(edges)


@dataclass(frozen=True)
class HoldoutSplit:
    """A frozen citation hold-out with its dev/test source partition."""

    held: frozenset[tuple[str, str]]
    retained: frozenset[tuple[str, str]]
    dev_sources: tuple[str, ...]
    test_sources: tuple[str, ...]
    salt: int
    holdout_fraction: float
    min_out_edges: int

    @property
    def gold(self) -> dict[str, frozenset[str]]:
        gold: dict[str, set[str]] = {}
        for source, target in self.held:
            gold.setdefault(source, set()).add(target)
        return {source: frozenset(targets) for source, targets in gold.items()}

    def gold_for(self, source: str) -> frozenset[str]:
        return frozenset(target for src, target in self.held if src == source)

    def sources(self, split: Split) -> tuple[str, ...]:
        return self.dev_sources if split is Split.DEV else self.test_sources


def build_holdout(
    edges: Sequence[tuple[str, str]],
    *,
    salt: int,
    holdout_fraction: float = 0.3,
    min_out_edges: int = 3,
) -> HoldoutSplit:
    """Hold out a seeded fraction of each source's outgoing citations.

    A source is eligible as a query only when it keeps at least one held-out and
    one retained edge, so both arms have something to predict from and the graph
    arm always has retained structure to traverse.

    A held-out edge ``(s, t)`` whose reverse ``(t, s)`` survives in the retained
    graph is demoted to retained. The reverse edge would expose ``t`` to a graph
    arm that walks incoming edges from ``s``, which is a leak even though the
    forward edge was pruned.
    """

    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError("holdout_fraction must be in (0, 1)")
    if min_out_edges < 2:
        raise ValueError("min_out_edges must be at least 2")

    out_by_source: dict[str, set[str]] = {}
    for source, target in edges:
        if source != target:
            out_by_source.setdefault(source, set()).add(target)

    held: set[tuple[str, str]] = set()
    retained: set[tuple[str, str]] = set()
    for source, targets in out_by_source.items():
        ordered = sorted(targets)
        if len(ordered) < min_out_edges:
            retained.update((source, target) for target in ordered)
            continue
        count = max(1, round(holdout_fraction * len(ordered)))
        ranked = sorted(ordered, key=lambda target: _unit(salt, SPLIT_FAMILY, source, target))
        chosen = set(ranked[:count])
        for target in ordered:
            bucket = held if target in chosen else retained
            bucket.add((source, target))

    # a held edge is only gold if its reverse is not readable from the target side;
    # a demoted edge joins the retained graph rather than vanishing, so
    # held | retained is exactly the input edge set and the traversal index the
    # arms build from (edges minus held) matches the manifest
    demoted = {edge for edge in held if (edge[1], edge[0]) in retained}
    held -= demoted
    retained |= demoted

    dev: list[str] = []
    test: list[str] = []
    for source in sorted(out_by_source):
        has_held = any(src == source for src, _ in held)
        has_retained = any(src == source for src, _ in retained)
        if not (has_held and has_retained):
            continue
        (dev if source_split(source, salt=salt) is Split.DEV else test).append(source)

    return HoldoutSplit(
        held=frozenset(held),
        retained=frozenset(retained),
        dev_sources=tuple(dev),
        test_sources=tuple(test),
        salt=salt,
        holdout_fraction=holdout_fraction,
        min_out_edges=min_out_edges,
    )


def readable_out_neighbours(split: HoldoutSplit) -> dict[str, frozenset[str]]:
    """Targets a graph arm can read directly from a source's retained edges."""

    neighbours: dict[str, set[str]] = {}
    for source, target in split.retained:
        neighbours.setdefault(source, set()).add(target)
    return {source: frozenset(targets) for source, targets in neighbours.items()}


def citation_is_echoed(source: Document, target: Document) -> bool:
    """Whether the query text names the target's citation verbatim.

    Used only for the preregistered echo-free secondary result. A bare number like
    ``41`` would match almost anywhere in a legal body, so the whole normalised
    citation is required, not a trailing fragment.
    """

    needle = normalize_citation(target.citation)
    if not needle:
        return False
    haystack = normalize_citation(source.body)
    return needle in haystack


def reachability_diagnostic(
    split: HoldoutSplit, *, max_sources: int | None = None
) -> dict[str, Any]:
    """Report whether held-out targets are reachable from their source by structure.

    If this is near zero the graph arm cannot win, which is a design limitation to
    state rather than a model result to hide.
    """

    out: dict[str, set[str]] = {}
    incoming: dict[str, set[str]] = {}
    for source, target in split.retained:
        out.setdefault(source, set()).add(target)
        incoming.setdefault(target, set()).add(source)

    sources = list(split.gold)
    if max_sources is not None:
        sources = sources[:max_sources]

    two_hop = cocite = common_citer = any_signal = 0
    total = 0
    for source in sources:
        targets = split.gold_for(source)
        if not targets:
            continue
        total += 1
        successors = out.get(source, set())
        has_two = any(target in out.get(step, set()) for target in targets for step in successors)
        has_cocite = any(
            (out.get(source, set()) - {target}) & (out.get(target, set()) - {source})
            for target in targets
        )
        has_citer = any(
            (incoming.get(source, set()) - {target}) & (incoming.get(target, set()) - {source})
            for target in targets
        )
        two_hop += has_two
        cocite += has_cocite
        common_citer += has_citer
        any_signal += has_two or has_cocite or has_citer
    denominator = max(1, total)
    return {
        "sources_measured": total,
        "two_hop_fraction": two_hop / denominator,
        "co_citation_fraction": cocite / denominator,
        "common_citer_fraction": common_citer / denominator,
        "any_signal_fraction": any_signal / denominator,
    }


def duplicate_body_diagnostic(
    split: HoldoutSplit, corpus: Mapping[str, Document]
) -> dict[str, Any]:
    """Report whether any gold target shares a document body with its source.

    The corpus carries reserved-stub sections whose text is identical, so a
    document could in principle appear as its own gold by text match alone even
    though entry_cid identity is unambiguous. That would be a leak for every arm
    at once, so it is measured rather than assumed away.
    """

    digest = {cid: hashlib.sha256(doc.body.encode()).hexdigest() for cid, doc in corpus.items()}
    counts: dict[str, int] = {}
    for value in digest.values():
        counts[value] = counts.get(value, 0) + 1
    duplicated = {value for value, count in counts.items() if count > 1}

    sources_sharing_body = 0
    gold_pairs = 0
    gold_pairs_duplicated = 0
    gold_sharing_source_body = 0
    for source, targets in split.gold.items():
        if digest[source] in duplicated:
            sources_sharing_body += 1
        for target in targets:
            gold_pairs += 1
            if digest[target] in duplicated:
                gold_pairs_duplicated += 1
            if digest[target] == digest[source]:
                gold_sharing_source_body += 1
    return {
        "duplicate_body_groups": len(duplicated),
        "documents_in_duplicate_groups": sum(counts[value] for value in duplicated),
        "query_sources_sharing_a_body": sources_sharing_body,
        "gold_pairs": gold_pairs,
        "gold_pairs_on_duplicated_body": gold_pairs_duplicated,
        "gold_pairs_sharing_the_source_body": gold_sharing_source_body,
    }


def dumps_manifest(split: HoldoutSplit, *, sources: Mapping[str, Mapping[str, Any]]) -> str:
    """Serialise the split for the committed ``split-manifest.json``.

    ``sources`` maps each corpus ``entry_cid`` to its committed metadata
    (``split``, ``citation``, ``family``); the payload is JSON-serialised as-is.
    """

    payload = {
        "schema": "eval-lab/graphrag-holdout-split/v1",
        "salt": split.salt,
        "holdout_fraction": split.holdout_fraction,
        "min_out_edges": split.min_out_edges,
        "held_edge_count": len(split.held),
        "retained_edge_count": len(split.retained),
        "dev_source_count": len(split.dev_sources),
        "test_source_count": len(split.test_sources),
        "dev_sources": list(split.dev_sources),
        "test_sources": list(split.test_sources),
        "sources": dict(sources),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def iter_edges(pairs: Iterable[tuple[str, str]]) -> Iterable[tuple[str, str]]:
    return ((str(a), str(b)) for a, b in pairs)


__all__ = [
    "CITATION_RELATION",
    "DATASET",
    "DOC_NODE_KIND",
    "SPLIT_FAMILY",
    "VERIFIER_ID",
    "Document",
    "HoldoutSplit",
    "build_holdout",
    "citation_is_echoed",
    "dumps_manifest",
    "duplicate_body_diagnostic",
    "iter_edges",
    "load_citations",
    "load_corpus",
    "normalize_citation",
    "reachability_diagnostic",
    "readable_out_neighbours",
    "source_split",
]
