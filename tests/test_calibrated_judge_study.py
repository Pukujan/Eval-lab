from __future__ import annotations

import json
from pathlib import Path

from scripts.report_calibrated_judge_study import build_report


def test_exp019_report_excludes_vendor_domain_arms_and_keeps_calibration() -> None:
    repo = Path(__file__).resolve().parents[1]
    report = build_report(repo)

    assert report["included_arms"] == ["grok", "jev", "qwen_flash", "local_qwen4b"]
    assert report["excluded_arms"] == {
        "luna": "vendor-independent orchestrator comparison policy",
        "sol": "vendor-independent orchestrator comparison policy",
    }
    assert report["arms"]["local_qwen4b"]["resolved_count"] == 760
    assert report["calibration"]["blind_holdout"]["raw"]["accuracy"] == report["calibration"]["blind_holdout"]["calibrated"]["accuracy"]


def test_exp019_report_does_not_silently_replace_qwen_retry_predictions() -> None:
    repo = Path(__file__).resolve().parents[1]
    report = build_report(repo)
    qwen = report["arms"]["qwen_flash"]

    assert qwen["resolved_count"] == 759
    assert qwen["correct_count"] == 740
    assert report["source_artifacts"]["qwen_flash_retry"].startswith("EXP-016/")


def test_exp019_results_are_json_serializable() -> None:
    repo = Path(__file__).resolve().parents[1]
    report = build_report(repo)
    json.dumps(report)
