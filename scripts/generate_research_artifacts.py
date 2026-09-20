"""Generate the TASK-0010 research bundle from committed machine results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BENCHMARK = Path("benchmark/eval-lab-select-v0.1.0")
EXPERIMENT = Path("experiments/EXP-20260920-009-selective-escalation")
PAPER = Path("paper")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _smoke_differential() -> dict[str, Any]:
    arms = {}
    for name in ("pinned", "rolling", "qwen"):
        path = EXPERIMENT / "smoke" / f"{name}.jsonl"
        arms[name] = _read_jsonl(path) if path.exists() else []
    by_arm = {name: {row["record_id"]: row for row in rows} for name, rows in arms.items()}
    comparable = []
    for record_id in sorted(set.intersection(*(set(values) for values in by_arm.values()))) if by_arm else []:
        rows = {name: by_arm[name][record_id] for name in by_arm}
        if all(row.get("execution_status") == "ok" for row in rows.values()):
            labels = {name: rows[name].get("label") for name in rows}
            comparable.append({"record_id": record_id, "labels": labels, "all_agree": len(set(labels.values())) == 1})
    return {
        "scope": "separate one-record provider smoke canary; not part of pinned/rolling pooled estimates",
        "arms": {
            name: {
                "model": (rows[0].get("judge_id") if rows else None),
                "status_counts": {
                    status: sum(row.get("execution_status") == status for row in rows)
                    for status in sorted({row.get("execution_status") for row in rows})
                },
            }
            for name, rows in arms.items()
        },
        "comparable_count": len(comparable),
        "agreement_count": sum(item["all_agree"] for item in comparable),
        "rows": comparable,
    }


def _crate(results: dict[str, Any], differential: dict[str, Any]) -> dict[str, Any]:
    files = [
        "benchmark.yaml",
        "records.jsonl",
        "splits.json",
        "source-manifest.json",
        "checksums.sha256",
        "fingerprint.json",
        "ro-crate-metadata.json",
        "provenance.ttl",
        "shapes.ttl",
    ]
    graph: list[dict[str, Any]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.3"},
            "about": {"@id": "./"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": "EvalLab-Select",
            "version": "0.1.0",
            "identifier": results["benchmark_fingerprint"],
            "description": "Frozen objective benchmark for calibrated selective escalation.",
            "hasPart": [{"@id": name} for name in files],
            "additionalType": "https://w3id.org/ro/crate/1.3",
        },
    ]
    graph.extend(
        {
            "@id": name,
            "@type": "MediaObject",
            "encodingFormat": "application/json" if name.endswith("json") else "text/plain",
        }
        for name in files
        if name != "ro-crate-metadata.json"
    )
    return {"@context": "https://w3id.org/ro/crate/1.3/context", "@graph": graph}


def _provenance(results: dict[str, Any]) -> str:
    fingerprint = results["benchmark_fingerprint"]
    return f'''@prefix ex: <https://example.org/eval-lab/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:agent a prov:Agent, prov:SoftwareAgent ;
    dcterms:identifier "eval-lab" ;
    dcterms:title "Eval Lab reproducibility runner" .

ex:source a prov:Entity ;
    dcterms:identifier "allenai/ai2_arc@210d026faf9955653af8916fad021475a3f00453" .

ex:benchmark a prov:Entity ;
    dcterms:identifier "EvalLab-Select v0.1.0" ;
    ex:fingerprint "{fingerprint}" .

ex:build a prov:Activity ;
    prov:used ex:source ;
    prov:generated ex:benchmark ;
    prov:wasAssociatedWith ex:agent .

ex:experiment a prov:Activity ;
    prov:used ex:benchmark ;
    prov:generated ex:results ;
    prov:wasAssociatedWith ex:agent ;
    ex:status "{results['status']}" .

ex:results a prov:Entity ;
    dcterms:identifier "EXP-20260920-009-selective-escalation/results.json" ;
    ex:providerEvaluationCount "{results['counts']['provider_evaluation']}"^^xsd:integer .
'''


def _shapes() -> str:
    return '''@prefix ex: <https://example.org/eval-lab/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:EntityShape a sh:NodeShape ;
    sh:targetClass prov:Entity ;
    sh:property [ sh:path dcterms:identifier ; sh:minCount 1 ; sh:datatype xsd:string ] .

ex:BenchmarkShape a sh:NodeShape ;
    sh:targetNode ex:benchmark ;
    sh:property [ sh:path ex:fingerprint ; sh:minCount 1 ; sh:datatype xsd:string ; sh:pattern "^[0-9a-f]{64}$" ] .
'''


def _paper(results: dict[str, Any], differential: dict[str, Any]) -> None:
    PAPER.mkdir(parents=True, exist_ok=True)
    generated = PAPER / "generated"
    generated.mkdir(exist_ok=True)
    rows = []
    for policy, value in sorted(results["policies"].items()):
        resolved_risk = value["final_resolved_risk"]
        risk_text = "n/a" if resolved_risk is None else f"{resolved_risk:.3f}"
        policy_text = policy.replace("_", "\\_")
        row = (
            f"{policy_text} & {value['total_count']} & {value['local_coverage']:.3f} & "
            f"{value['escalation_rate']:.3f} & {value['execution_coverage']:.3f} & {risk_text} "
        )
        rows.append(row + r"\\")
    (generated / "table_selective_results.tex").write_text(
        "\\begin{tabular}{lrrrrr}\n\\toprule\nPolicy & N & Local cov. & Escalation & Exec. cov. & Resolved risk \\\\\n\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{tabular}\n",
        encoding="utf-8",
    )
    bars = []
    names = sorted(results["policies"])
    for index, name in enumerate(names):
        value = results["policies"][name]["execution_coverage"]
        x = 20 + index * 34
        height = max(1, int(value * 160))
        bars.append(f'<rect x="{x}" y="{180-height}" width="24" height="{height}" fill="#3264a8"/>')
    (generated / "figure_execution_coverage.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="220" viewBox="0 0 900 220">'
        '<title>Execution coverage by routing policy</title><line x1="10" y1="180" x2="890" y2="180" stroke="black"/>'
        + "".join(bars)
        + "</svg>\n",
        encoding="utf-8",
    )
    (PAPER / "reproducibility.md").write_text(
        "# Reproducibility appendix\n\n"
        "```powershell\n"
        "$env:PYTHONPATH = \"$PWD\\src\"\n"
        ".venv\\Scripts\\python.exe scripts/build_selective_benchmark.py\n"
        ".venv\\Scripts\\python.exe scripts/run_selective_escalation.py --skip-providers\n"
        ".venv\\Scripts\\python.exe scripts/generate_research_artifacts.py\n"
        ".venv\\Scripts\\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0\n"
        "```\n\n"
        "Provider smoke calls are isolated with `scripts/smoke_task0010_providers.py`; pinned and rolling Jev outputs are never pooled.\n",
        encoding="utf-8",
    )
    (PAPER / "limitations.md").write_text(
        "# Limitations and threats to validity\n\n"
        "The frozen student is a compact TF-IDF plus logistic-regression arm trained on the small TASK-0009 corpus. ARC answer-key labels measure objective choice correctness and do not establish broad human-evaluation validity. The calibrated threshold claims have Wilson uncertainty and are descriptive when the upper bound does not meet the target. Provider smoke and partial live availability can leave unresolved records; unresolved calls are not scored as local errors and never receive a local fallback. The rolling Jev alias is a separate canary and is excluded from pinned estimates.\n",
        encoding="utf-8",
    )
    (PAPER / "main.tex").write_text(
        f'''\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{booktabs}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\title{{Calibrated Selective Escalation for Lightweight Rubric Judges}}
\\author{{Eval Lab}}
\\date{{2026-09-20}}
\\begin{{document}}
\\maketitle
\\begin{{abstract}}
We evaluate a frozen TASK-0009 TF-IDF plus logistic-regression student with confidence-based selective escalation on EvalLab-Select v0.1.0. The benchmark contains {results['counts']['threshold_selection']} threshold-selection and {results['counts']['final_evaluation']} final-evaluation records with disjoint source families. Provider failures remain explicitly unresolved. The benchmark fingerprint is \\texttt{{{results['benchmark_fingerprint']}}}.
\\end{{abstract}}
\\section{{Introduction}}
Selective escalation trades local coverage for a lower-risk accepted subset while retaining an external judge for uncertain records.
\\section{{Benchmark and objective gold}}
EvalLab-Select combines ARC-Challenge at the pinned source revision with non-training synthetic source families. Each ARC source yields one correct and one deterministic incorrect single-answer record. Source manifests, partitions, checksums, and canonicalization are committed with the release.
\\section{{Student and calibration}}
The primary student is the frozen TASK-0009 arm D artifact. Calibration uses the committed temperature artifact fit on the TASK-0009 calibration split. Confidence is the maximum calibrated class probability; the top-two margin is retained as a secondary measure.
\\section{{Routing and controls}}
Thresholds are selected only on the threshold-selection partition. We report local-only, calibrated and raw local-to-pinned-Jev policies, matched random escalation, and a calibrated local-to-Qwen policy. The rolling Jev alias is a separate canary.
\\section{{Results}}
Machine-generated routing results are in `generated/table_selective_results.tex`. The complete machine result is `../experiments/EXP-20260920-009-selective-escalation/results.json`.
\\begin{{table}}[h]
\\centering
\\input{{generated/table_selective_results.tex}}
\\caption{{Machine-generated routing results. Resolved risk excludes unresolved provider calls.}}
\\end{{table}}
\\section{{System-One differential}}
The typed System-One specification is provider-independent. The smoke differential contains {differential['comparable_count']} comparable record(s), with {differential['agreement_count']} agreement(s). Pinned and rolling Jev outputs are stored separately.
\\section{{Uncertainty}}
Every low-error coverage summary includes an exact Wilson 95\\% interval. A nominal empirical risk below a target is not treated as supported when the interval upper bound exceeds that target.
\\section{{Limitations and threats to validity}}
This is an objective ARC answer-key benchmark, not evidence of universal human-evaluation quality. The student training corpus is small. Calibration and provider availability are separate sources of uncertainty. Provider errors remain unresolved rather than receiving an implicit local fallback.
\\section{{Reproducibility and artifact availability}}
Run the commands in `reproducibility.md`. The release includes RO-Crate 1.3 metadata, PROV-O provenance, SHACL shapes, a valid CFF citation file, checksums, and generated tables and figures.
\\appendix
\\section{{Exact reproduction commands}}
\\verbatiminput{{reproducibility.md}}
\\bibliographystyle{{plain}}
\\bibliography{{references}}
\\end{{document}}
''',
        encoding="utf-8",
    )


def generate() -> None:
    results = json.loads((EXPERIMENT / "results.json").read_text(encoding="utf-8"))
    differential = _smoke_differential()
    results["system_one_differential"] = differential
    results["provider_smoke"] = differential["arms"]
    _write_json(EXPERIMENT / "differential.json", differential)
    _write_json(EXPERIMENT / "results.json", results)
    _write_json(BENCHMARK / "ro-crate-metadata.json", _crate(results, differential))
    (BENCHMARK / "provenance.ttl").write_text(_provenance(results), encoding="utf-8")
    (BENCHMARK / "shapes.ttl").write_text(_shapes(), encoding="utf-8")
    _write_json(
        BENCHMARK / "datacite.json",
        {
            "@context": "https://schema.datacite.org/meta/kernel-4.6/metadata.xsd",
            "identifier": {"identifierType": "SHA256", "identifier": results["benchmark_fingerprint"]},
            "creators": [{"name": "Pukujan"}],
            "titles": [{"title": "EvalLab-Select"}],
            "publisher": "Eval Lab",
            "publicationYear": 2026,
            "types": {"resourceTypeGeneral": "Dataset"},
            "version": "0.1.0",
        },
    )
    _paper(results, differential)


if __name__ == "__main__":
    generate()
