"""Export provenance-aware chart data for the paper's interactive charts (TASK-0059).

Offline only: reads committed artifacts, makes no model or provider calls, and
hand-types no numbers.  Outputs (all under ``paper/data/``):

* ``judges-blind-760.json``: the explorer dataset (schema ``research-chart-data``
  v1).  It has dimensions, measures, entities (one per judge arm = one run of
  a judge configuration), tidy observations ``(entity, slice, metric) ->
  value/CI/n``, paired comparisons, and per-experiment and per-run levels.  It
  holds **no per-record items or gold labels**: the 760 records are a blind
  holdout, so the finest level is one row per arm/run.
* ``charts/<figure>.json``: one file per paper figure, wrapping the figure's
  plotted values (``paper/figures/benchmark/<figure>.data.json``).
* ``index.json``: every exported file with its SHA-256 and size, for the
  Design Bakery sync.

Every exported JSON file is also JSON-LD.  Its ``@context`` maps only the
provenance keys (schema.org Dataset + W3C PROV-O).  All other keys are plain
data that JSON-LD processors ignore.  ``provenance`` is a JSON-LD ``@nest``
block: the generating activity (this script, the git commit and dirty flag, the
commit time) and the hashed input entities.  Validation lives in
``schemas/research-chart-data.v1.schema.json`` (JSON Schema) and
``schemas/chart-provenance.shapes.ttl`` (SHACL).  See ``docs/PROVENANCE.md``.

Usage:
    uv run --locked python scripts/export_chart_data.py            # write
    uv run --locked python scripts/export_chart_data.py --check    # verify committed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.analyze_judge_comparison import ARMS, sha256, wilson
except ImportError:  # executed as a file from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.analyze_judge_comparison import ARMS, sha256, wilson

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/Pukujan/Eval-lab"
SCHEMA_VERSION = "1.0"
DATASET_ID = "eval-lab/judges-blind-760"

OUT_DIR = Path("paper/data")
CHART_DIR = OUT_DIR / "charts"
DATASET_PATH = OUT_DIR / "judges-blind-760.json"
INDEX_PATH = OUT_DIR / "index.json"
ARM_METADATA = OUT_DIR / "sources" / "arm-metadata.yaml"
ANALYSIS = Path("experiments/EXP-20260924-029-consolidated-judge-analysis/results.json")
FIGURE_MANIFEST = Path("paper/figures/benchmark/manifest.json")
HEADLINE_FIGURE = "finding_accuracy_range"  # the paper's accuracy bar chart selects the body judges
SCHEMA_FILES = (
    Path("schemas/research-chart-data.v1.schema.json"),
    Path("schemas/chart-provenance.shapes.ttl"),
)
GENERATOR = Path("scripts/export_chart_data.py")
# Paths whose modification does not make the export "dirty": the outputs themselves.
OUTPUT_PREFIXES = (
    "paper/data/judges-blind-760.json",
    "paper/data/charts/",
    "paper/data/index.json",
)

CONTEXT: dict[str, Any] = {
    "@version": 1.1,
    "schema": "https://schema.org/",
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "ev": f"{REPO_URL}/blob/main/docs/PROVENANCE.md#",
    "id": "@id",
    "type": "@type",
    "title": "schema:name",
    "description": "schema:description",
    "schemaVersion": "ev:schemaVersion",
    "provenance": "@nest",
    "wasGeneratedBy": {"@id": "prov:wasGeneratedBy", "@type": "@id"},
    "wasDerivedFrom": {"@id": "prov:wasDerivedFrom", "@type": "@id", "@container": "@set"},
    "wasAssociatedWith": {"@id": "prov:wasAssociatedWith", "@type": "@id"},
    "used": {"@id": "prov:used", "@type": "@id", "@container": "@set"},
    "endedAtTime": {"@id": "prov:endedAtTime", "@type": "xsd:dateTime"},
    "gitCommit": "ev:gitCommit",
    "gitDirty": {"@id": "ev:gitDirty", "@type": "xsd:boolean"},
    "sha256": "ev:sha256",
    "path": "ev:path",
    "role": "ev:role",
    "experimentId": "ev:experimentId",
    "recordCount": {"@id": "ev:recordCount", "@type": "xsd:integer"},
}

POLICY = {
    "pooling": (
        "Arms are separate runs on the same 760 records. Nothing is averaged or pooled "
        "across arms, except the declared EXP-015 + EXP-016 Qwen merge, which is its own "
        "entity (derived=true). Consumers must not compute cross-arm means."
    ),
    "aggregates": (
        "Only exporter-computed aggregates appear in `aggregates`, each with its method. "
        "This release exports none."
    ),
    "interval": "95% Wilson score interval, computed from integer counts",
    "blind_holdout": (
        "No per-record items, record IDs, or gold labels are exported. The finest level "
        "is one row per arm/run."
    ),
    "comparisons": (
        "Exact two-sided McNemar tests, Holm-corrected over all arm pairs separately per "
        "view, copied from EXP-029 for the paper's focus pairs."
    ),
}

MEASURES: list[dict[str, Any]] = [
    {
        "key": "all_record_accuracy",
        "label": "Accuracy over all questions",
        "unit": "fraction",
        "format": ".1%",
        "better": "higher",
        "interval": "wilson_95",
        "definition": "correct / records in the slice; an unresolved record earns no credit",
        "n": "records in the slice",
    },
    {
        "key": "conditional_accuracy",
        "label": "Accuracy when answered",
        "unit": "fraction",
        "format": ".1%",
        "better": "higher",
        "interval": "wilson_95",
        "definition": "correct / resolved records in the slice (what accuracy-only tables report)",
        "n": "resolved records in the slice",
    },
    {
        "key": "coverage",
        "label": "Share answered",
        "unit": "fraction",
        "format": ".1%",
        "better": "higher",
        "interval": "wilson_95",
        "definition": "resolved / records in the slice",
        "n": "records in the slice",
    },
    {
        "key": "median_resolved_latency_ms",
        "label": "Median latency (answered)",
        "unit": "ms",
        "format": ",.0f",
        "better": "lower",
        "interval": "none",
        "definition": "median wall-clock latency over resolved records, when recorded",
        "n": "resolved records",
    },
    {
        "key": "median_resolved_completion_tokens",
        "label": "Median completion tokens (answered)",
        "unit": "tokens",
        "format": ",.0f",
        "better": "none",
        "interval": "none",
        "definition": "median completion tokens over resolved records, when the provider reports usage",
        "n": "resolved records",
    },
]

DEPLOYMENT = {"provider_api": "api", "local": "local", "baseline": "baseline"}

LEVELS = [
    {"key": "summary", "label": "Summary", "description": "headline entities, overall slice"},
    {
        "key": "breakdown",
        "label": "Breakdown",
        "description": "slice-scope dimensions (mode, task source)",
    },
    {"key": "experiments", "label": "Experiments", "description": "entities grouped by experiment"},
    {"key": "runs", "label": "Runs", "description": "every arm with its hashed prediction files"},
    {
        "key": "table",
        "label": "Table",
        "description": "all observations; one row per arm/slice/metric",
    },
]


# --------------------------------------------------------------------------- helpers
def _read_json(path: Path) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def git_info() -> dict[str, Any]:
    """HEAD commit, its commit time, and whether non-output files differ from it."""
    status = _git("status", "--porcelain", "--untracked-files=all")
    dirty_paths = [
        line[3:].strip()
        for line in status.splitlines()
        if line.strip() and not line[3:].strip().strip('"').startswith(OUTPUT_PREFIXES)
    ]
    return {
        "commit": _git("rev-parse", "HEAD"),
        "committedAt": _git("show", "-s", "--format=%cI", "HEAD"),
        "dirty": bool(dirty_paths),
    }


def _blob(commit: str, path: Path | str) -> str:
    return f"{REPO_URL}/blob/{commit}/{Path(path).as_posix()}"


def _entity(commit: str, path: Path | str, role: str, **extra: Any) -> dict[str, Any]:
    rel = Path(path).as_posix()
    node = {
        "id": _blob(commit, rel),
        "type": "prov:Entity",
        "path": rel,
        "sha256": sha256(ROOT / rel),
        "role": role,
    }
    node.update(extra)
    return node


def _activity(git: dict[str, Any], name: str, used: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": f"urn:eval-lab:export:{git['commit']}:{name}",
        "type": "prov:Activity",
        "endedAtTime": git["committedAt"],
        "gitCommit": git["commit"],
        "gitDirty": git["dirty"],
        "wasAssociatedWith": {
            "id": _blob(git["commit"], GENERATOR),
            "type": ["prov:SoftwareAgent", "schema:SoftwareSourceCode"],
            "path": GENERATOR.as_posix(),
            "sha256": sha256(ROOT / GENERATOR),
        },
        "used": [node["id"] for node in used],
    }


def _provenance(
    git: dict[str, Any], name: str, sources: list[dict[str, Any]], summary: str
) -> dict[str, Any]:
    return {
        "summary": summary,
        "repository": REPO_URL,
        "commit": git["commit"],
        "dirty": git["dirty"],
        "generatedAt": git["committedAt"],
        "generator": GENERATOR.as_posix(),
        "policy": POLICY,
        "wasGeneratedBy": _activity(git, name, sources),
        "wasDerivedFrom": sources,
    }


def load_arm_metadata() -> dict[str, dict[str, Any]]:
    payload = yaml.safe_load((ROOT / ARM_METADATA).read_text(encoding="utf-8"))
    arms: dict[str, dict[str, Any]] = payload["arms"]
    return arms


def _experiment_dirs() -> dict[str, Path]:
    """Map short IDs (EXP-024) to experiment directories."""
    out = {}
    for path in sorted((ROOT / "experiments").glob("EXP-*")):
        if path.is_dir():
            out[f"EXP-{path.name.split('-')[2]}"] = path.relative_to(ROOT)
    return out


def _short_ids(experiment: str) -> list[str]:
    """'EXP-015+016' -> ['EXP-015', 'EXP-016']."""
    head, *rest = experiment.split("+")
    return [head, *(f"EXP-{part}" for part in rest)]


def _obs(entity: str, slice_: str, value_: str, metric: str, value: Any, ci: Any, n: int) -> dict:
    return {
        "entity": entity,
        "slice": slice_,
        "sliceValue": value_,
        "metric": metric,
        "value": value,
        "ciLow": ci[0] if ci else None,
        "ciHigh": ci[1] if ci else None,
        "n": n,
    }


def _slice_observations(entity: str, slice_: str, cells: dict[str, Any]) -> list[dict]:
    rows = []
    for value_, cell in cells.items():
        records, resolved, correct = cell["records"], cell["resolved"], cell["correct"]
        rows.append(
            _obs(
                entity,
                slice_,
                value_,
                "all_record_accuracy",
                correct / records,
                wilson(correct, records),
                records,
            )
        )
        rows.append(
            _obs(
                entity,
                slice_,
                value_,
                "conditional_accuracy",
                cell["accuracy"],
                cell["accuracy_95_wilson"],
                resolved,
            )
        )
        rows.append(
            _obs(
                entity,
                slice_,
                value_,
                "coverage",
                resolved / records,
                wilson(resolved, records),
                records,
            )
        )
    return rows


# --------------------------------------------------------------------------- dataset
def build_dataset(git: dict[str, Any]) -> dict[str, Any]:
    analysis = _read_json(ANALYSIS)
    metadata = load_arm_metadata()
    headline_rows = _read_json(Path(f"paper/figures/benchmark/{HEADLINE_FIGURE}.data.json"))["rows"]
    headline = {row["key"] for row in headline_rows}
    arm_paths = {arm.key: arm.paths for arm in ARMS}
    exp_dirs = _experiment_dirs()
    order = analysis["rank_by_all_record_accuracy"]
    ranks = analysis["shared_ranks_all_record"]

    entities, observations, runs = [], [], []
    run_entities: list[dict[str, Any]] = []
    for key in sorted(analysis["arms"], key=lambda k: (order.index(k) if k in order else 999, k)):
        arm = analysis["arms"][key]
        meta = metadata[key]
        settings = meta["settings"]
        entities.append(
            {
                "id": key,
                "label": arm["label"],
                "shortLabel": meta["short_label"],
                "headline": key in headline,
                "experiment": arm["experiment"],
                "experimentIds": _short_ids(arm["experiment"]),
                "deployment": DEPLOYMENT[arm["family"]],
                "modelFamily": meta["model_family"],
                "modelId": meta["model_id"],
                "paramsB": meta["params_b"],
                "route": arm["route"],
                "harness": arm["harness"],
                "settings": {
                    "maxOutputTokens": settings["max_output_tokens"],
                    "maxOutputTokensStatus": settings["max_output_tokens_status"],
                    "contextCapTokens": settings["context_cap_tokens"],
                    "thinking": settings["thinking"],
                    "decoding": settings["decoding"],
                    "temperature": settings["temperature"],
                },
                "settingsEvidence": meta["evidence"],
                "derived": arm["derived"],
                "rankAllRecord": order.index(key) + 1 if key in order else None,
                "sharedRankAllRecord": ranks.get(key),
                "recordCount": arm["record_count"],
                "resolved": arm["resolved"],
                "correct": arm["correct"],
                "statusCounts": arm["status_counts"],
            }
        )
        n, resolved = arm["record_count"], arm["resolved"]
        observations += [
            _obs(
                key,
                "overall",
                "all",
                "all_record_accuracy",
                arm["all_record_accuracy"],
                arm["all_record_accuracy_95_wilson"],
                n,
            ),
            _obs(
                key,
                "overall",
                "all",
                "conditional_accuracy",
                arm["conditional_accuracy"],
                arm["conditional_accuracy_95_wilson"],
                resolved,
            ),
            _obs(key, "overall", "all", "coverage", arm["coverage"], arm["coverage_95_wilson"], n),
        ]
        for metric in ("median_resolved_latency_ms", "median_resolved_completion_tokens"):
            if arm.get(metric) is not None:
                observations.append(
                    _obs(key, "overall", "all", metric, arm[metric], None, resolved)
                )
        observations += _slice_observations(key, "mode", arm["by_mode"])
        observations += _slice_observations(key, "taskSource", arm["by_source"])

        if [s["path"] for s in arm["sources"]] != list(arm_paths[key]):
            raise ValueError(f"{key}: EXP-029 sources differ from analyze_judge_comparison.ARMS")
        for order_index, source in enumerate(arm["sources"]):
            current = sha256(ROOT / source["path"])
            if current != source["sha256"]:
                raise ValueError(f"{source['path']}: sha256 differs from EXP-029 results.json")
            parts = Path(source["path"]).parts
            runs.append(
                {
                    "entity": key,
                    "experiment": f"EXP-{parts[1].split('-')[2]}",
                    "experimentDirectory": Path(*parts[:2]).as_posix(),
                    "runPath": Path(*parts[2:-1]).as_posix() or ".",
                    "path": source["path"],
                    "sha256": source["sha256"],
                    "mergeOrder": order_index,
                }
            )
            run_entities.append(
                {
                    "id": _blob(git["commit"], source["path"]),
                    "type": "prov:Entity",
                    "path": source["path"],
                    "sha256": source["sha256"],
                    "role": "judge_predictions",
                }
            )

    experiments = []
    for short in sorted({s for e in entities for s in e["experimentIds"]}):
        directory = exp_dirs[short]
        manifest = yaml.safe_load(
            (ROOT / directory / "experiment.yaml").read_text(encoding="utf-8")
        )
        experiments.append(
            {
                "id": short,
                "experimentId": manifest.get("id"),
                "directory": directory.as_posix(),
                "status": manifest.get("status"),
                "createdAt": str(manifest.get("created_at"))
                if manifest.get("created_at")
                else None,
                "codeCommit": manifest.get("code_commit"),
                "entities": [e["id"] for e in entities if short in e["experimentIds"]],
            }
        )

    comparisons = []
    for pair_key in analysis["focus_pairs"]:
        pair = analysis["paired_tests"]["pairs"][pair_key]
        for view, n in (
            ("all", analysis["records"]["blind_count"]),
            ("shared", pair["shared_resolved"]),
        ):
            comparisons.append(
                {
                    "left": pair["left"],
                    "right": pair["right"],
                    "view": view,
                    "n": n,
                    "leftOnlyCorrect": pair[f"{view}_left_only_correct"],
                    "rightOnlyCorrect": pair[f"{view}_right_only_correct"],
                    "pExact": pair[f"{view}_p_exact"],
                    "pHolm": pair[f"{view}_p_holm"],
                }
            )

    records = analysis["records"]
    results_entity = _entity(
        git["commit"],
        ANALYSIS,
        "analysis_results",
        experimentId=analysis["experiment_id"],
        wasDerivedFrom=run_entities
        + [
            {
                "id": _blob(git["commit"], records["path"]),
                "type": "prov:Entity",
                "path": records["path"],
                "sha256": records["sha256"],
                "role": "blind_records",
            }
        ],
    )
    sources = [
        results_entity,
        _entity(git["commit"], ARM_METADATA, "arm_metadata"),
        _entity(
            git["commit"],
            f"paper/figures/benchmark/{HEADLINE_FIGURE}.data.json",
            "headline_selection",
        ),
    ]
    summary = (
        f"EXP-029 · {records['blind_count']} blind records · {len(entities)} arms · "
        f"{GENERATOR.name} @ {git['commit'][:7]}"
    )
    dimension_values = {
        "deployment": sorted({e["deployment"] for e in entities}),
        "modelFamily": sorted({e["modelFamily"] for e in entities}),
        "experiment": [x["id"] for x in experiments],
        "thinking": sorted({e["settings"]["thinking"] for e in entities}),
        "decoding": sorted({e["settings"]["decoding"] for e in entities}),
        "mode": sorted({o["sliceValue"] for o in observations if o["slice"] == "mode"}),
        "taskSource": sorted({o["sliceValue"] for o in observations if o["slice"] == "taskSource"}),
    }
    dimensions = [
        {
            "key": "entity",
            "label": "Judge (arm)",
            "type": "nominal",
            "scope": "entity",
            "field": "id",
        },
        {
            "key": "deployment",
            "label": "Local vs API",
            "type": "nominal",
            "scope": "entity",
            "field": "deployment",
            "values": dimension_values["deployment"],
        },
        {
            "key": "modelFamily",
            "label": "Model family",
            "type": "nominal",
            "scope": "entity",
            "field": "modelFamily",
            "values": dimension_values["modelFamily"],
        },
        {
            "key": "paramsB",
            "label": "Size (B params, public only)",
            "type": "quantitative",
            "scope": "entity",
            "field": "paramsB",
            "unit": "B",
        },
        {
            "key": "experiment",
            "label": "Experiment",
            "type": "nominal",
            "scope": "entity",
            "field": "experimentIds",
            "values": dimension_values["experiment"],
        },
        {
            "key": "thinking",
            "label": "Thinking",
            "type": "nominal",
            "scope": "entity",
            "field": "settings.thinking",
            "values": dimension_values["thinking"],
        },
        {
            "key": "maxOutputTokens",
            "label": "Max output tokens",
            "type": "ordinal",
            "scope": "entity",
            "field": "settings.maxOutputTokens",
        },
        {
            "key": "contextCapTokens",
            "label": "Context cap (local)",
            "type": "ordinal",
            "scope": "entity",
            "field": "settings.contextCapTokens",
        },
        {
            "key": "decoding",
            "label": "Decision method",
            "type": "nominal",
            "scope": "entity",
            "field": "settings.decoding",
            "values": dimension_values["decoding"],
        },
        {
            "key": "mode",
            "label": "Task type (mode)",
            "type": "nominal",
            "scope": "slice",
            "values": dimension_values["mode"],
        },
        {
            "key": "taskSource",
            "label": "Task source",
            "type": "nominal",
            "scope": "slice",
            "values": dimension_values["taskSource"],
        },
    ]
    return {
        "@context": CONTEXT,
        "id": f"{REPO_URL}/blob/main/{DATASET_PATH.as_posix()}",
        "type": ["schema:Dataset", "prov:Entity"],
        "kind": "dataset",
        "schemaVersion": SCHEMA_VERSION,
        "datasetId": DATASET_ID,
        "title": "Judge accuracy and coverage on the 760-record blind holdout",
        "description": (
            "One row per judge arm (a run of one judge configuration) on identical typed "
            "decisions with objective gold labels. Numbers are copied or computed from "
            "EXP-029 results.json; no per-record data is included."
        ),
        "experimentId": analysis["experiment_id"],
        "recordCount": records["blind_count"],
        "population": {
            "partition": "blind_holdout",
            "records": records["blind_count"],
            "composition": records["composition"],
        },
        "provenance": _provenance(git, "judges-blind-760", sources, summary),
        "levels": LEVELS,
        "dimensions": dimensions,
        "measures": MEASURES,
        "entities": entities,
        "observations": observations,
        "aggregates": [],
        "comparisons": comparisons,
        "experiments": experiments,
        "runs": runs,
        "notes": {
            "definitions": analysis["definitions"],
            "excluded": analysis["excluded"],
            "notRun": analysis["not_run"],
        },
    }


# --------------------------------------------------------------------------- charts
def build_charts(git: dict[str, Any]) -> dict[Path, dict[str, Any]]:
    manifest = _read_json(FIGURE_MANIFEST)
    by_experiment = {}
    for name, source in manifest["sources"].items():
        short = f"EXP-{Path(source['path']).parts[1].split('-')[2]}"
        by_experiment[short] = (name, source)
    charts: dict[Path, dict[str, Any]] = {}
    for figure, spec in manifest["figures"].items():
        data_path = Path(spec["data"])
        data = _read_json(data_path)
        short = data.get("source")
        source_name, source = (
            by_experiment[short]
            if short in by_experiment
            else ("analysis", manifest["sources"]["analysis"])
        )
        if sha256(ROOT / source["path"]) != source["sha256"]:
            raise ValueError(f"figure manifest is stale for {source['path']}")
        experiment_short = f"EXP-{Path(source['path']).parts[1].split('-')[2]}"
        sources = [
            _entity(
                git["commit"],
                data_path,
                "figure_data",
                wasDerivedFrom=[_blob(git["commit"], source["path"])],
            ),
            _entity(git["commit"], source["path"], f"{source_name}_results"),
            _entity(git["commit"], FIGURE_MANIFEST, "figure_manifest"),
        ]
        summary = f"{experiment_short} · {data_path.name} · {GENERATOR.name} @ {git['commit'][:7]}"
        out = CHART_DIR / f"{figure}.json"
        charts[out] = {
            "@context": CONTEXT,
            "id": f"{REPO_URL}/blob/main/{out.as_posix()}",
            "type": ["schema:Dataset", "prov:Entity"],
            "kind": "chart",
            "schemaVersion": SCHEMA_VERSION,
            "chartId": figure,
            "title": spec["title"],
            "experimentId": experiment_short,
            "dataset": DATASET_ID if source_name == "analysis" else None,
            "figure": {"generator": manifest["generator"], "variants": spec["variants"]},
            "provenance": _provenance(git, f"chart:{figure}", sources, summary),
            "data": data,
        }
    return charts


def build_all(git: dict[str, Any]) -> dict[Path, dict[str, Any]]:
    outputs: dict[Path, dict[str, Any]] = {DATASET_PATH: build_dataset(git)}
    outputs.update(build_charts(git))
    return outputs


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _dump(doc: dict[str, Any]) -> str:
    """Deterministic, diff-friendly JSON: one top-level key per line and one list item
    (observation, entity, run, ...) per line, each compact."""
    lines = []
    for key, value in doc.items():
        if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            body = ",\n  ".join(_compact(item) for item in value)
            lines.append(f" {_compact(key)}: [\n  {body}\n ]")
        else:
            lines.append(f" {_compact(key)}: {_compact(value)}")
    return "{\n" + ",\n".join(lines) + "\n}\n"


def build_index(git: dict[str, Any], outputs: dict[Path, dict[str, Any]]) -> dict[str, Any]:
    files = []
    for path, doc in sorted(outputs.items()):
        text = _dump(doc).encode("utf-8")
        files.append(
            {
                "path": path.as_posix(),
                "kind": doc["kind"],
                "id": doc.get("datasetId") or doc.get("chartId"),
                "bytes": len(text),
                "sha256": hashlib.sha256(text).hexdigest(),
            }
        )
    for path in SCHEMA_FILES:
        files.append(
            {
                "path": path.as_posix(),
                "kind": "schema",
                "id": path.name,
                "bytes": len((ROOT / path).read_bytes().replace(b"\r\n", b"\n")),
                "sha256": sha256(ROOT / path),
            }
        )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "repository": REPO_URL,
        "commit": git["commit"],
        "dirty": git["dirty"],
        "generatedAt": git["committedAt"],
        "generator": GENERATOR.as_posix(),
        "files": files,
    }


def render(git: dict[str, Any]) -> dict[Path, str]:
    outputs = build_all(git)
    rendered = {path: _dump(doc) for path, doc in outputs.items()}
    rendered[INDEX_PATH] = _dump(build_index(git, outputs))
    return rendered


def committed_git_info() -> dict[str, Any]:
    """Git fields recorded in the committed index (used to re-render for --check)."""
    index = json.loads((ROOT / INDEX_PATH).read_text(encoding="utf-8"))
    return {"commit": index["commit"], "committedAt": index["generatedAt"], "dirty": index["dirty"]}


def stale_outputs() -> list[str]:
    """Paths whose committed bytes differ from a re-render with the recorded git fields."""
    rendered = render(committed_git_info())
    stale = []
    for path, text in rendered.items():
        target = ROOT / path
        if not target.is_file() or target.read_text(encoding="utf-8") != text:
            stale.append(path.as_posix())
    expected = {path.as_posix() for path in rendered}
    for extra in (ROOT / CHART_DIR).glob("*.json"):
        if extra.relative_to(ROOT).as_posix() not in expected:
            stale.append(f"unexpected {extra.relative_to(ROOT).as_posix()}")
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="verify committed outputs; write nothing"
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="write even if non-output files are uncommitted (recorded as dirty)",
    )
    args = parser.parse_args(argv)
    if args.check:
        stale = stale_outputs()
        for item in stale:
            print(f"stale: {item}")
        return 1 if stale else 0
    git = git_info()
    if git["dirty"] and not args.allow_dirty:
        print("refusing to export from a dirty tree; commit inputs first or pass --allow-dirty")
        return 2
    rendered = render(git)
    (ROOT / CHART_DIR).mkdir(parents=True, exist_ok=True)
    for path, text in rendered.items():
        (ROOT / path).write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.as_posix()} ({len(text.encode('utf-8')):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
