from collections import Counter

from eval_lab.datasets.synthetic import (
    assign_split,
    generate_synthetic_fixtures,
    serialize_fixture,
)
from eval_lab.schema import JudgmentMode, PairwiseLabel, swap_pairwise_record


def test_fixture_counts_domains_and_split_inheritance() -> None:
    fixture = generate_synthetic_fixtures()
    assert len(fixture.sources) >= 24
    assert len(fixture.single_records) >= 72
    assert len(fixture.pairwise_records) >= 48
    assert Counter(source.domain for source in fixture.sources) == {
        "arithmetic": 6,
        "multiple_choice": 6,
        "structured": 6,
        "code_output": 6,
    }

    source_splits = {source.source_problem_id: source.split for source in fixture.sources}
    assert all(record.split is source_splits[record.source_problem_id] for record in fixture.records)
    assert {record.gold.label for record in fixture.pairwise_records} == {
        PairwiseLabel.A.value,
        PairwiseLabel.B.value,
    }
    assert {record.gold.label for record in fixture.single_records} == {"pass", "fail"}


def test_split_assignment_is_fixed_by_source_id_and_seed() -> None:
    first = [assign_split(f"source-{i}") for i in range(20)]
    second = [assign_split(f"source-{i}") for i in range(20)]
    changed_seed = [assign_split(f"source-{i}", seed=7) for i in range(20)]
    assert first == second
    assert first != changed_seed


def test_fixture_serialization_is_byte_stable_for_fixed_seed() -> None:
    first = serialize_fixture(generate_synthetic_fixtures(seed=11, split_seed=22))
    second = serialize_fixture(generate_synthetic_fixtures(seed=11, split_seed=22))
    changed = serialize_fixture(generate_synthetic_fixtures(seed=12, split_seed=22))
    assert first == second
    assert first != changed


def test_swap_transform_reverses_candidates_and_gold() -> None:
    pair = next(
        record
        for record in generate_synthetic_fixtures().pairwise_records
        if record.mode is JudgmentMode.PAIRWISE and record.gold.label == PairwiseLabel.A.value
    )
    swapped = swap_pairwise_record(pair)
    assert swapped.candidate_a == pair.candidate_b
    assert swapped.candidate_b == pair.candidate_a
    assert swapped.gold.label == PairwiseLabel.B.value
    assert swapped.perturbation["kind"] == "ab_swap"


def test_tie_swap_preserves_tie() -> None:
    pair = next(
        record
        for record in generate_synthetic_fixtures().pairwise_records
        if record.mode is JudgmentMode.PAIRWISE
    )
    tie = pair.model_copy(
        update={
            "gold": pair.gold.model_copy(update={"label": PairwiseLabel.TIE.value}),
        }
    )
    assert swap_pairwise_record(tie).gold.label == PairwiseLabel.TIE.value
