from __future__ import annotations

import json
from pathlib import Path

from scripts.analyze_judge_comparison import (
    OUT,
    build,
    holm,
    mcnemar_exact,
    paper_tables_current,
    wilson,
)


def test_wilson_matches_exp014_jev_interval() -> None:
    low, high = wilson(684, 760)  # EXP-014 pinned Jev: 90.00% of 760
    assert abs(low - 0.8766185431070428) < 1e-12
    assert abs(high - 0.9193581520290133) < 1e-12
    assert wilson(0, 0) is None


def test_mcnemar_exact_known_values() -> None:
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(0, 5) == 0.0625
    assert mcnemar_exact(3, 3) == 1.0


def test_holm_is_monotone_and_bounded() -> None:
    adjusted = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adjusted == {"a": 0.03, "c": 0.06, "b": 0.06}


def test_committed_results_are_reproducible() -> None:
    committed = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    result = json.loads(json.dumps(build(), sort_keys=True))
    assert result == committed


def test_arms_cover_all_blind_records_and_keep_unresolved_visible() -> None:
    result = build()
    assert result["records"]["blind_count"] == 760
    for arm in result["arms"].values():
        assert sum(arm["status_counts"].values()) == 760
        assert arm["resolved"] == arm["status_counts"].get("ok", 0)
        assert arm["all_record_accuracy"] <= (arm["conditional_accuracy"] or 0)
    one_pass = result["arms"]["qwen_flash_exp015"]
    assert one_pass["status_counts"]["rate_limited"] == 317


def test_paper_tables_are_generated() -> None:
    paper = Path(__file__).resolve().parents[1] / "paper" / "paper.md"
    assert paper_tables_current(build(), paper)
