from __future__ import annotations

import json
from pathlib import Path

from scripts.finalize_colab_moe_experiment import ARMS, _canonical

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "EXP-20261005-031-colab-t4-moe-judge-arms"


def test_canonical_row_carries_protocol_and_model_provenance() -> None:
    arm = ARMS[0]
    row = _canonical(
        {
            "record_id": "r1",
            "mode": "single",
            "legal_labels": ["pass", "fail"],
            "execution_status": "ok",
            "label": "pass",
            "raw_output": "pass",
            "latency_ms": 12.5,
        },
        arm,
    )
    assert row["record_id"] == "r1"
    assert row["protocol_version"] == "eval-lab-local-decision-v1"
    assert row["judge_id"] == arm["model_id"]
    assert row["probabilities"] is None
    assert row["provider_metadata"]["arm_id"] == arm["arm_id"]
    assert row["provider_metadata"]["model_sha256"] == arm["sha256"]


def test_committed_experiment_covers_every_record_for_both_arms() -> None:
    results = json.loads((EXP / "results.json").read_text(encoding="utf-8"))
    blind = results["partitions"]["blind"]
    public = results["partitions"]["public"]
    assert set(blind) == {arm["arm_id"] for arm in ARMS}
    for partition, expected in ((blind, 760), (public, 648)):
        for summary in partition.values():
            assert summary["record_count"] == expected
            assert summary["resolved_coverage"] == 1.0
            assert summary["status_counts"] == {"ok": expected}


def test_blind_single_and_pairwise_split_is_frozen() -> None:
    results = json.loads((EXP / "results.json").read_text(encoding="utf-8"))
    for summary in results["partitions"]["blind"].values():
        assert summary["by_mode"]["single"]["record_count"] == 652
        assert summary["by_mode"]["pairwise"]["record_count"] == 108
