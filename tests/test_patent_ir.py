"""Tests for the EXP-034 citation hold-out: split, leak safeguards, mapping.

The point of these tests is that a mapping or split mistake silently prunes the
wrong edges, which is the one failure mode that would turn a graph result into a
leak rather than a measurement. They run on synthetic edges and on a tiny
in-memory corpus, so no download is needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eval_lab.datasets.patent_ir import (
    CITATION_RELATION,
    DOC_NODE_KIND,
    Document,
    HoldoutSplit,
    build_holdout,
    citation_is_echoed,
    dumps_manifest,
    duplicate_body_diagnostic,
    load_citations,
    normalize_citation,
    reachability_diagnostic,
    readable_out_neighbours,
    source_split,
)
from eval_lab.schema import Split

SALT = 20261006


def document(cid: str, citation: str, *, title: str = "T", text: str = "B") -> Document:
    return Document(
        entry_cid=cid,
        citation=citation,
        family="test",
        title=title,
        text=text,
        section_id="s",
    )


# --- citation normalisation -------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("37 CFR 1.56", "37-cfr-1-56"),
        ("35 U.S.C. § 101", "35-usc-101"),
        ("MPEP § 1002.02", "mpep-1002-02"),
        ("35-usc-101", "35-usc-101"),
        ("37-cfr-1-56", "37-cfr-1-56"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_citation_both_forms(value: str | None, expected: str) -> None:
    assert normalize_citation(value) == expected


def test_normalize_citation_display_and_slug_agree() -> None:
    # the property that matters: display and slug forms must collide, because
    # identity is keyed on entry_cid but the echo check compares normalised text
    assert normalize_citation("35 U.S.C. § 101") == normalize_citation("35-usc-101")
    assert normalize_citation("MPEP § 1002.02") == normalize_citation("mpep-1002-02")


# --- split determinism ------------------------------------------------------


def test_source_split_is_deterministic_and_partitions() -> None:
    cids = [f"cid-{i}" for i in range(200)]
    first = {cid: source_split(cid, salt=SALT) for cid in cids}
    second = {cid: source_split(cid, salt=SALT) for cid in cids}
    assert first == second
    assert set(first.values()) <= {Split.DEV, Split.TEST}
    # both sides are populated, so a dev-only or test-only split cannot pass
    assert len(set(first.values())) == 2


def test_source_split_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        source_split("", salt=SALT)


# --- hold-out construction --------------------------------------------------


def fan(source: str, targets: list[str]) -> list[tuple[str, str]]:
    return [(source, target) for target in targets]


def test_build_holdout_keeps_and_holds_at_least_one_per_source() -> None:
    edges = fan("a", ["b", "c", "d", "e", "f", "g"])
    split = build_holdout(edges, salt=SALT, holdout_fraction=0.3, min_out_edges=3)
    assert len(split.gold_for("a")) == 2  # round(0.3 * 6)
    assert len(split.retained) == 4
    assert set(split.held) | set(split.retained) == set(edges)
    assert not set(split.held) & set(split.retained)


def test_build_holdout_below_min_out_edges_is_fully_retained() -> None:
    edges = fan("a", ["b", "c"])
    split = build_holdout(edges, salt=SALT, min_out_edges=3)
    assert split.held == frozenset()
    assert split.retained == frozenset(edges)
    assert split.dev_sources == () and split.test_sources == ()


def test_build_holdout_drops_self_loops() -> None:
    split = build_holdout([("a", "a"), *fan("a", ["b", "c", "d"])], salt=SALT, min_out_edges=3)
    assert ("a", "a") not in split.held
    assert ("a", "a") not in split.retained


def test_build_holdout_rejects_bad_parameters() -> None:
    edges = fan("a", ["b", "c", "d"])
    with pytest.raises(ValueError):
        build_holdout(edges, salt=SALT, holdout_fraction=0.0)
    with pytest.raises(ValueError):
        build_holdout(edges, salt=SALT, holdout_fraction=1.0)
    with pytest.raises(ValueError):
        build_holdout(edges, salt=SALT, min_out_edges=1)


def test_build_holdout_is_deterministic() -> None:
    edges = fan("a", [f"t{i}" for i in range(20)]) + fan("b", [f"u{i}" for i in range(10)])
    first = build_holdout(edges, salt=SALT)
    second = build_holdout(edges, salt=SALT)
    assert first.held == second.held
    assert first.retained == second.retained
    assert first.dev_sources == second.dev_sources
    assert first.test_sources == second.test_sources


def test_holdout_salt_changes_the_selection() -> None:
    edges = fan("a", [f"t{i}" for i in range(20)])
    assert build_holdout(edges, salt=1).held != build_holdout(edges, salt=2).held


# --- safeguard 1: no gold is a readable out-neighbour ------------------------


def test_safeguard_1_gold_is_never_a_readable_out_neighbour() -> None:
    edges = fan("a", [f"t{i}" for i in range(20)]) + fan("b", [f"u{i}" for i in range(9)])
    split = build_holdout(edges, salt=SALT, holdout_fraction=0.3, min_out_edges=3)
    readable = readable_out_neighbours(split)
    for source, targets in split.gold.items():
        assert not (targets & readable.get(source, frozenset())), source


# --- safeguard 3: no readable reverse edge ----------------------------------


def test_safeguard_3_reciprocal_edges_are_not_gold() -> None:
    # a<->b plus a fan from a; whichever of (a,b)/(b,a) is drawn as held, the
    # surviving reverse must not leave the other readable
    edges = [("a", "b"), ("b", "a"), *fan("a", ["c", "d", "e", "f", "g", "h"])]
    split = build_holdout(edges, salt=SALT, holdout_fraction=0.5, min_out_edges=3)
    retained = set(split.retained)
    assert all((t, s) not in retained for s, t in split.held)


def test_safeguard_3_holds_across_many_salts() -> None:
    edges = [("a", "b"), ("b", "a"), *fan("a", [f"x{i}" for i in range(12)])]
    for salt in range(1, 60):
        split = build_holdout(edges, salt=salt, holdout_fraction=0.4, min_out_edges=3)
        retained = set(split.retained)
        assert all((t, s) not in retained for s, t in split.held), salt


def test_demoted_reciprocal_edge_stays_retained_not_dropped() -> None:
    # a demoted edge must join the retained graph, not vanish: the arms build the
    # traversal index as (edges - held), so a dropped edge would make the manifest
    # undercount the index the graph arm actually traverses
    edges = [("a", "b"), ("b", "a"), *fan("a", [f"x{i}" for i in range(12)])]
    for salt in range(1, 60):
        split = build_holdout(edges, salt=salt, holdout_fraction=0.4, min_out_edges=3)
        assert set(split.held) | set(split.retained) == set(edges), salt
        assert not set(split.held) & set(split.retained), salt


# --- split unit: no source crosses the boundary -----------------------------


def test_no_source_document_crosses_the_dev_test_boundary() -> None:
    edges: list[tuple[str, str]] = []
    for i in range(80):
        source = f"src-{i}"
        edges += fan(source, [f"tgt-{i}-{j}" for j in range(6)])
    split = build_holdout(edges, salt=SALT, min_out_edges=3)
    dev, test = set(split.dev_sources), set(split.test_sources)
    assert not dev & test
    assert dev and test
    # every held edge belongs to a query source, and that source is in exactly
    # one split; the split unit is the source document, never the edge
    for source, _ in split.held:
        assert source in dev or source in test
    assert {s for s, _ in split.held} <= dev | test


# --- echo diagnostic --------------------------------------------------------


def test_citation_is_echoed_requires_the_full_citation() -> None:
    target = document("t", "35 U.S.C. § 41")
    assert citation_is_echoed(document("s", "x", text="see 35 U.S.C. § 41"), target)
    # a bare trailing number must not count: "41" appears in almost any body
    assert not citation_is_echoed(document("s", "x", text="claim 41 was allowed"), target)
    assert not citation_is_echoed(document("s", "x", text="unrelated body"), target)


def test_citation_is_echoed_false_for_empty_target_citation() -> None:
    assert not citation_is_echoed(document("s", "x", text="anything"), document("t", ""))


# --- reachability diagnostic ------------------------------------------------


def test_reachability_diagnostic_reports_two_hop() -> None:
    # a -> b and b -> c retained, a -> c held: c is reachable from a in two hops,
    # which is the only structural signal the graph arm can use
    split = HoldoutSplit(
        held=frozenset({("a", "c")}),
        retained=frozenset({("a", "b"), ("b", "c")}),
        dev_sources=("a",),
        test_sources=(),
        salt=SALT,
        holdout_fraction=0.5,
        min_out_edges=2,
    )
    diagnostic = reachability_diagnostic(split)
    assert diagnostic["sources_measured"] == 1
    assert diagnostic["two_hop_fraction"] == 1.0
    assert diagnostic["any_signal_fraction"] == 1.0


def test_reachability_diagnostic_is_zero_without_structure() -> None:
    split = HoldoutSplit(
        held=frozenset({("a", "z")}),
        retained=frozenset({("a", "b"), ("b", "c")}),
        dev_sources=("a",),
        test_sources=(),
        salt=SALT,
        holdout_fraction=0.5,
        min_out_edges=2,
    )
    diagnostic = reachability_diagnostic(split)
    assert diagnostic["two_hop_fraction"] == 0.0
    assert diagnostic["any_signal_fraction"] == 0.0


# --- duplicate-body safeguard -----------------------------------------------


def test_duplicate_body_diagnostic_flags_gold_sharing_its_source_body() -> None:
    # source and target have identical text; the diagnostic must surface it
    corpus = {
        "s": document("s", "35 USC 1", text="[Reserved]"),
        "t": document("t", "37 CFR 1", text="[Reserved]"),
        "u": document("u", "37 CFR 2", text="unique body"),
    }
    split = HoldoutSplit(
        held=frozenset({("s", "t")}),
        retained=frozenset({("s", "u")}),
        dev_sources=("s",),
        test_sources=(),
        salt=SALT,
        holdout_fraction=0.5,
        min_out_edges=2,
    )
    diagnostic = duplicate_body_diagnostic(split, corpus)
    assert diagnostic["duplicate_body_groups"] == 1
    assert diagnostic["documents_in_duplicate_groups"] == 2
    assert diagnostic["query_sources_sharing_a_body"] == 1
    assert diagnostic["gold_pairs"] == 1
    assert diagnostic["gold_pairs_on_duplicated_body"] == 1
    assert diagnostic["gold_pairs_sharing_the_source_body"] == 1


def test_duplicate_body_diagnostic_clean_when_all_bodies_unique() -> None:
    corpus = {
        "s": document("s", "35 USC 1", text="alpha"),
        "t": document("t", "37 CFR 1", text="beta"),
        "u": document("u", "37 CFR 2", text="gamma"),
    }
    split = HoldoutSplit(
        held=frozenset({("s", "t")}),
        retained=frozenset({("s", "u")}),
        dev_sources=("s",),
        test_sources=(),
        salt=SALT,
        holdout_fraction=0.5,
        min_out_edges=2,
    )
    diagnostic = duplicate_body_diagnostic(split, corpus)
    assert diagnostic["duplicate_body_groups"] == 0
    assert diagnostic["gold_pairs_sharing_the_source_body"] == 0


# --- manifest ---------------------------------------------------------------


def test_dumps_manifest_round_trips() -> None:
    import json

    split = build_holdout(fan("a", ["b", "c", "d", "e"]), salt=SALT, min_out_edges=3)
    sources = {"a": {"split": "dev", "citation": "35 USC 1", "family": "f"}}
    payload = json.loads(dumps_manifest(split, sources=sources))
    assert payload["schema"] == "eval-lab/graphrag-holdout-split/v1"
    assert payload["salt"] == SALT
    assert payload["sources"] == sources
    assert payload["held_edge_count"] == len(split.held)


# --- load_citations: graph join ---------------------------------------------


def test_load_citations_resolves_document_nodes_and_filters_relations(tmp_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    nodes_dir = tmp_path / "nodes"
    edges_dir = tmp_path / "edges"
    nodes_dir.mkdir()
    edges_dir.mkdir()
    pq.write_table(
        pa.table(
            {
                "node_cid": ["n1", "n2", "n3", "n4"],
                "kind": [DOC_NODE_KIND, DOC_NODE_KIND, DOC_NODE_KIND, "citation"],
                "entry_cid": ["d1", "d2", "d3", "tok"],
            }
        ),
        nodes_dir / "part-000000.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "subject_cid": ["n1", "n1", "n2"],
                "object_cid": ["n2", "n4", "n3"],
                "relation": [CITATION_RELATION, CITATION_RELATION, "contains_term"],
            }
        ),
        edges_dir / "part-000000.parquet",
    )
    corpus = {cid: document(cid, cid) for cid in ("d1", "d2", "d3")}
    # n1->n4 resolves to a citation token, not a document: skipped
    # n2->n3 is contains_term: skipped
    assert load_citations(edges_dir, nodes_dir, corpus) == [("d1", "d2")]


def test_load_citations_rejects_endpoint_outside_corpus(tmp_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    nodes_dir = tmp_path / "nodes"
    edges_dir = tmp_path / "edges"
    nodes_dir.mkdir()
    edges_dir.mkdir()
    pq.write_table(
        pa.table(
            {
                "node_cid": ["n1", "n2"],
                "kind": [DOC_NODE_KIND, DOC_NODE_KIND],
                "entry_cid": ["d1", "ghost"],
            }
        ),
        nodes_dir / "part-000000.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "subject_cid": ["n1"],
                "object_cid": ["n2"],
                "relation": [CITATION_RELATION],
            }
        ),
        edges_dir / "part-000000.parquet",
    )
    corpus = {"d1": document("d1", "d1")}
    with pytest.raises(ValueError, match="not in corpus"):
        load_citations(edges_dir, nodes_dir, corpus)


def test_load_citations_rejects_duplicate_document_node(tmp_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    nodes_dir = tmp_path / "nodes"
    edges_dir = tmp_path / "edges"
    nodes_dir.mkdir()
    edges_dir.mkdir()
    pq.write_table(
        pa.table(
            {
                "node_cid": ["n1", "n1"],
                "kind": [DOC_NODE_KIND, DOC_NODE_KIND],
                "entry_cid": ["d1", "d1"],
            }
        ),
        nodes_dir / "part-000000.parquet",
    )
    pq.write_table(
        pa.table({"subject_cid": [], "object_cid": [], "relation": []}),
        edges_dir / "part-000000.parquet",
    )
    with pytest.raises(ValueError, match="duplicate document node_cid"):
        load_citations(edges_dir, nodes_dir, {"d1": document("d1", "d1")})


def test_load_citations_requires_shards(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        load_citations(empty, empty, {})
