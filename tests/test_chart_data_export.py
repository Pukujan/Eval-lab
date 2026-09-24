"""TASK-0059: provenance-aware chart data export checks.

These run in CI through `pytest tests`:
- the committed exports are byte-identical to a fresh render (so every input
  hash and the generator hash are current);
- JSON Schema and SHACL validation of every export;
- recomputation of every recorded source hash;
- the export came from a clean tree;
- no blind-holdout items or gold labels leak;
- structured arm settings agree with the harness text and the prediction metadata;
- EXP-029 code_commit reproduces results.json, and the figure manifest is current;
- the archived TASK-0010 v0.1.0 release (RO-Crate/PROV-O/SHACL) still validates.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from pyshacl import validate
from rdflib import Graph

from scripts.analyze_judge_comparison import ARMS, sha256
from scripts.export_chart_data import (
    ANALYSIS,
    ARM_METADATA,
    CHART_DIR,
    DATASET_PATH,
    FIGURE_MANIFEST,
    INDEX_PATH,
    ROOT,
    SCHEMA_FILES,
    load_arm_metadata,
    stale_outputs,
)

SCHEMA = ROOT / "schemas" / "research-chart-data.v1.schema.json"
SHAPES = ROOT / "schemas" / "chart-provenance.shapes.ttl"
BLIND_RECORDS = ROOT / "experiments/EXP-20260921-015-grok-luna-qwen-bakeoff/records.jsonl"
EXP029_YAML = ROOT / "experiments/EXP-20260924-029-consolidated-judge-analysis/experiment.yaml"


def _exports() -> list[Path]:
    return [ROOT / DATASET_PATH, *sorted((ROOT / CHART_DIR).glob("*.json"))]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for key, child in value.items():
            if key != "@context":  # term definitions, not data
                yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _graph(doc: dict[str, Any]) -> Graph:
    return Graph().parse(data=json.dumps(doc), format="json-ld")


def _shacl(doc: dict[str, Any]) -> tuple[bool, str]:
    conforms, _, text = validate(_graph(doc), shacl_graph=Graph().parse(SHAPES, format="turtle"))
    return bool(conforms), str(text)


def test_committed_exports_match_a_fresh_render() -> None:
    assert stale_outputs() == [], "run: uv run --locked python scripts/export_chart_data.py"


def test_index_lists_every_export_and_schema_with_current_hashes() -> None:
    index = _load(ROOT / INDEX_PATH)
    listed = {entry["path"]: entry for entry in index["files"]}
    expected = {p.relative_to(ROOT).as_posix() for p in _exports()} | {
        p.as_posix() for p in SCHEMA_FILES
    }
    assert set(listed) == expected
    for rel, entry in listed.items():
        data = (ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
        assert entry["bytes"] == len(data)
        assert entry["sha256"] == sha256(ROOT / rel)


def test_json_schema_accepts_every_export() -> None:
    schema = _load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for path in _exports():
        errors = [e.message for e in validator.iter_errors(_load(path))]
        assert errors == [], f"{path.name}: {errors[:3]}"


def test_json_schema_rejects_unstructured_settings_and_bad_hashes() -> None:
    validator = Draft202012Validator(_load(SCHEMA), format_checker=FormatChecker())
    doc = _load(ROOT / DATASET_PATH)
    broken = copy.deepcopy(doc)
    broken["entities"][0]["settings"]["thinking"] = "maybe"
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(doc)
    broken["runs"][0]["sha256"] = "abc"
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(doc)
    broken["provenance"]["wasDerivedFrom"][0]["path"] = "D:/claude/eval-lab/x.json"
    assert list(validator.iter_errors(broken))


def test_shacl_accepts_every_export_provenance_graph() -> None:
    for path in _exports():
        conforms, report = _shacl(_load(path))
        assert conforms, f"{path.name}: {report}"


def test_shacl_rejects_missing_commit_and_bad_source_hash() -> None:
    doc = _load(ROOT / DATASET_PATH)
    broken = copy.deepcopy(doc)
    broken["provenance"]["wasGeneratedBy"]["gitCommit"] = "main"
    assert not _shacl(broken)[0]
    broken = copy.deepcopy(doc)
    broken["provenance"]["wasDerivedFrom"][0]["wasDerivedFrom"][0]["sha256"] = "0" * 12
    assert not _shacl(broken)[0]
    broken = copy.deepcopy(doc)
    del broken["provenance"]["wasGeneratedBy"]
    assert not _shacl(broken)[0]


def test_every_recorded_source_hash_matches_the_current_file() -> None:
    checked = 0
    for path in _exports():
        for node in _walk(_load(path)):
            if "path" in node and "sha256" in node:
                assert sha256(ROOT / node["path"]) == node["sha256"], node["path"]
                checked += 1
    assert checked >= 40


def test_exports_come_from_a_clean_tree_at_a_full_commit() -> None:
    index = _load(ROOT / INDEX_PATH)
    assert index["dirty"] is False
    assert re.fullmatch(r"[0-9a-f]{40}", index["commit"])
    for path in _exports():
        provenance = _load(path)["provenance"]
        assert provenance["dirty"] is False
        assert provenance["commit"] == index["commit"]
        assert provenance["wasGeneratedBy"]["gitDirty"] is False


def test_no_blind_items_gold_labels_or_unresolvable_paths_are_exported() -> None:
    record_ids = set()
    for line in BLIND_RECORDS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            record_ids.add(row["record"]["record_id"])
    assert len(record_ids) > 760
    for path in [*_exports(), ROOT / INDEX_PATH, SCHEMA, SHAPES]:
        text = path.read_text(encoding="utf-8")
        assert "example.org" not in text and "D:/" not in text and "D:\\" not in text, path
        if path.suffix == ".json" and path != SCHEMA:
            leaked = [rid for rid in record_ids if rid in text]
            assert leaked == [], f"{path.name} leaks record ids {leaked[:3]}"
            for node in _walk(_load(path)):
                assert not any("gold" in key.lower() for key in node), path


def test_dataset_observations_match_entity_counts_and_pooling_policy() -> None:
    doc = _load(ROOT / DATASET_PATH)
    analysis = json.loads((ROOT / ANALYSIS).read_text(encoding="utf-8"))
    entities = {e["id"]: e for e in doc["entities"]}
    assert set(entities) == set(analysis["arms"])
    assert doc["aggregates"] == []
    assert [e["id"] for e in doc["entities"] if e["derived"]] == ["qwen_flash_exp015_016"]
    overall = {
        (o["entity"], o["metric"]): o for o in doc["observations"] if o["slice"] == "overall"
    }
    for key, entity in entities.items():
        acc = overall[(key, "all_record_accuracy")]
        assert acc["value"] == entity["correct"] / entity["recordCount"]
        assert acc["n"] == 760
        assert overall[(key, "coverage")]["value"] == entity["resolved"] / 760
        assert acc["ciLow"] <= acc["value"] <= acc["ciHigh"]
    headline = {e["id"] for e in doc["entities"] if e["headline"]}
    figure = json.loads(
        (ROOT / "paper/figures/benchmark/finding_accuracy_range.data.json").read_text("utf-8")
    )
    assert headline == {row["key"] for row in figure["rows"]}
    measures = {m["key"] for m in doc["measures"]}
    assert {o["metric"] for o in doc["observations"]} <= measures


HARNESS_MAX = re.compile(r"max_tokens=(\d+)")
HARNESS_CAP = re.compile(r"([\d,]+)-token cap")


def test_arm_metadata_is_structured_complete_and_consistent() -> None:
    metadata = load_arm_metadata()
    analysis = json.loads((ROOT / ANALYSIS).read_text(encoding="utf-8"))
    assert set(metadata) == set(analysis["arms"]) == {arm.key for arm in ARMS}
    for key, meta in metadata.items():
        arm = analysis["arms"][key]
        settings = meta["settings"]
        for evidence in meta["evidence"]:
            assert (ROOT / evidence).is_file(), f"{key}: missing evidence {evidence}"
        harness = arm["harness"]
        if match := HARNESS_MAX.search(harness):
            assert settings["max_output_tokens"] == int(match.group(1)), key
            assert settings["max_output_tokens_status"] == "set", key
        elif arm["family"] == "provider_api":
            assert settings["max_output_tokens"] is None, key
            assert settings["max_output_tokens_status"] == "provider_default", key
        if match := HARNESS_CAP.search(harness):
            assert settings["context_cap_tokens"] == int(match.group(1).replace(",", "")), key
        if "enable_thinking=False" in harness:
            assert settings["thinking"] == "off", key
        if arm["family"] in ("local", "baseline"):
            assert settings["thinking"] == "not_applicable", key
            assert settings["max_output_tokens_status"] == "not_applicable", key
        else:
            assert settings["thinking"] in ("on", "off", "provider_default"), key


def test_arm_metadata_matches_recorded_prediction_metadata() -> None:
    metadata = load_arm_metadata()
    for arm in ARMS:
        meta = metadata[arm.key]
        with (ROOT / arm.paths[0]).open(encoding="utf-8") as handle:
            row = json.loads(handle.readline())
        prediction = row.get("prediction", row)
        assert prediction["judge_id"] == meta["model_id"], arm.key
        provider = prediction.get("provider_metadata") or {}
        if "max_tokens" in provider:
            assert provider["max_tokens"] == meta["settings"]["max_output_tokens"], arm.key
        if "context_cap" in provider:
            assert provider["context_cap"] == meta["settings"]["context_cap_tokens"], arm.key


def test_arm_metadata_file_documents_its_schema() -> None:
    payload = yaml.safe_load((ROOT / ARM_METADATA).read_text(encoding="utf-8"))
    assert payload["schema"] == "eval-lab.arm-metadata/1"


def _git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=False)


def test_exp029_code_commit_reproduces_committed_results() -> None:
    manifest = yaml.safe_load(EXP029_YAML.read_text(encoding="utf-8"))
    assert manifest["results_sha256"] == sha256(ROOT / ANALYSIS)
    commit = str(manifest["code_commit"])
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    shown = _git("show", f"{commit}:{ANALYSIS.as_posix()}")
    if shown.returncode != 0:
        pytest.skip("git history for code_commit is unavailable (shallow checkout)")
    assert hashlib.sha256(shown.stdout.replace(b"\r\n", b"\n")).hexdigest() == sha256(
        ROOT / ANALYSIS
    )


def test_figure_manifest_sources_and_outputs_are_current() -> None:
    manifest = json.loads((ROOT / FIGURE_MANIFEST).read_text(encoding="utf-8"))
    for source in manifest["sources"].values():
        assert sha256(ROOT / source["path"]) == source["sha256"], source["path"]
    for spec in manifest["figures"].values():
        assert (ROOT / spec["data"]).is_file()
        for variant in spec["variants"].values():
            assert (ROOT / variant).is_file(), variant
    charts = {p.stem for p in (ROOT / CHART_DIR).glob("*.json")}
    assert charts == set(manifest["figures"])


def test_archived_v010_release_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.validate_research_artifacts import validate_bundle

    monkeypatch.chdir(ROOT)
    assert validate_bundle(Path("benchmark/eval-lab-select-v0.1.0")) == {
        "checksums": "ok",
        "ro_crate": "ok",
        "prov_o": "parsed",
        "shacl": "conforms",
        "citation": "parsed",
        "paper": "present",
    }
