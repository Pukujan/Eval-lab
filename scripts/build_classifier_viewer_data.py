"""Build the per-item viewer data for the EXP-032 GLEIF classifier.

The committed ``research-chart-data.v1`` exports are arm-level and deliberately
hold no per-record rows, so the >=1000-item table the viewer renders comes from
this sibling file instead. It joins the frozen blind records to the Jev
predictions and writes ``items.json`` (one row per blind item, gold-free prompt
plus the gold label and the predicted label) together with copies of the
committed chart exports, into a static data directory the viewer fetches at
runtime. Nothing here calls a model; the run must already be complete.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from eval_lab.schema import ExecutionStatus, JudgePrediction

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "EXP-20261005-032-gleif-classifier"
EXPERIMENT_DIR = ROOT / "experiments" / EXPERIMENT_ID
DATASET_PATH = ROOT / "paper" / "data" / "gleif-classifier.json"
CHART_DIR = ROOT / "paper" / "data" / "classifier-charts"
PARTITION = "blind_holdout"


def _load_predictions(path: Path) -> dict[str, JudgePrediction]:
    predictions: dict[str, JudgePrediction] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            prediction = JudgePrediction.model_validate_json(line)
            if prediction.record_id in predictions:
                raise ValueError(f"duplicate prediction record ID: {prediction.record_id}")
            predictions[prediction.record_id] = prediction
    return predictions


def _items() -> list[dict[str, Any]]:
    typed_spec = json.loads(
        (EXPERIMENT_DIR / "typed-question-spec.json").read_text(encoding="utf-8")
    )
    rows = [
        json.loads(line)
        for line in (EXPERIMENT_DIR / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    blind = [row for row in rows if row["partition"] == PARTITION]
    families = sorted({row["family"] for row in blind})
    predictions = {
        family: _load_predictions(EXPERIMENT_DIR / "runs" / family / "predictions.jsonl")
        for family in families
    }
    items: list[dict[str, Any]] = []
    for row in blind:
        family = row["family"]
        record = row["record"]
        prediction = predictions[family].get(record["record_id"])
        if prediction is None:
            raise ValueError(f"{family}: no prediction for {record['record_id']}")
        gold = record["gold"]["label"]
        resolved = (
            prediction.execution_status is ExecutionStatus.OK and prediction.label is not None
        )
        items.append(
            {
                "recordId": record["record_id"],
                "sourceProblemId": record["source_problem_id"],
                "family": family,
                "lei": record["gold"]["evidence"]["entity_lei"],
                "prompt": record["prompt"],
                "gold": gold,
                "prediction": prediction.label,
                "correct": bool(resolved and prediction.label == gold),
                "status": prediction.execution_status.value,
                "confidence": (
                    max(prediction.probabilities.values()) if prediction.probabilities else None
                ),
                "probabilities": prediction.probabilities,
                "latencyMs": prediction.latency_ms,
                "labels": typed_spec["families"][family]["legal_labels"],
            }
        )
    items.sort(key=lambda item: (item["family"], item["recordId"]))
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="static viewer data directory")
    args = parser.parse_args()
    out: Path = args.out
    (out / "charts").mkdir(parents=True, exist_ok=True)

    items = _items()
    resolved = sum(item["status"] == "ok" for item in items)
    payload = {
        "schemaVersion": "1.0",
        "datasetId": "eval-lab/gleif-classifier",
        "generator": "scripts/build_classifier_viewer_data.py",
        "experimentId": EXPERIMENT_ID,
        "partition": PARTITION,
        "recordCount": len(items),
        "resolvedCount": resolved,
        "families": sorted({item["family"] for item in items}),
        "items": items,
    }
    (out / "items.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )

    shutil.copyfile(DATASET_PATH, out / "dataset.json")
    for chart in sorted(CHART_DIR.glob("*.json")):
        shutil.copyfile(chart, out / "charts" / chart.name)

    print(
        json.dumps(
            {
                "items": len(items),
                "resolved": resolved,
                "charts": sorted(p.name for p in (out / "charts").glob("*.json")),
                "out": out.as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
