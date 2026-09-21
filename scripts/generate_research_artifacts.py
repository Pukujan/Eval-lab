"""Generate the TASK-0010 research bundle from committed machine results."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

BENCHMARK = Path("benchmark/eval-lab-select-v0.1.0")
EXPERIMENT = Path("experiments/EXP-20260920-009-selective-escalation")
SMOKE_EXPERIMENT = EXPERIMENT
PAPER = Path("paper")

REQUIRED_PAPER_SECTIONS = (
    "Abstract",
    "Introduction",
    "Related Work",
    "Benchmark and Objective-Gold Construction",
    "Local Judge and Calibration",
    "Selective Escalation Method",
    "Jev/System-One Differential Method",
    "Experiments",
    "Results",
    "Statistical Uncertainty",
    "Ablations/Controls",
    "Limitations and Threats to Validity",
    "Reproducibility and Artifact Availability",
    "Conclusion",
    "Appendices",
)

PCM_NOTE = (
    "Project Continuity Modules (PCM) was inspected at "
    "`Pukujan/project-continuity-modules@3a34b4a73842c824de5359f06e04568e8ce4aaa4`. "
    "Eval Lab maps PROJECT.md to PCM PROJECT, checkpoints/CURRENT.md to CURRENT, "
    "TASK files to TASK, and checkpoint logs to CHECKPOINT. PCM currently exposes "
    "minimal and software templates; its planned research profile is not implemented, "
    "so this release treats PCM as a continuity compatibility reference and keeps "
    "RO-Crate 1.3 plus PROV-O as the scientific provenance standard."
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def _write_json(path: Path, value: Any) -> None:
    _write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _write_checksums(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(f"{digest}  {path.relative_to(root).as_posix()}")
    _write_text(root / "checksums.sha256", "\n".join(entries) + "\n")


def _tex(value: str) -> str:
    return str(value).replace("_", "\\_").replace("%", "\\%")


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def _claim(point: dict[str, Any] | None) -> str:
    if not point:
        return "n/a"
    if point.get("collapsed"):
        return "collapsed/descriptive" if point.get("claim_status") != "confidence-supported" else "collapsed"
    return str(point.get("claim_status", "descriptive"))


def _smoke_differential() -> dict[str, Any]:
    arms = {}
    for name in ("pinned", "rolling", "qwen"):
        path = SMOKE_EXPERIMENT / "smoke" / f"{name}.jsonl"
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
    dcterms:identifier "{results['experiment_id']}/results.json" ;
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


def _metric_table(results: dict[str, Any]) -> str:
    rows = []
    for policy, value in sorted(results["policies"].items()):
        point = value.get("selected_operating_point") or {}
        interval = value.get("final_resolved_risk_interval_95") or {}
        rows.append(
            " & ".join(
                [
                    _tex(policy),
                    str(value.get("total_count", "")),
                    _fmt(value.get("accuracy")),
                    _fmt(value.get("balanced_accuracy")),
                    _fmt(value.get("macro_f1")),
                    _fmt(value.get("local_coverage")),
                    _fmt(value.get("escalation_rate")),
                    _fmt(value.get("execution_coverage")),
                    _fmt(value.get("unresolved_rate")),
                    _fmt(value.get("final_resolved_risk")),
                    _fmt(interval.get("upper")),
                    _tex(_claim(point) if point else "n/a"),
                ]
            )
            + r" \\"
        )
    header = (
        r"\begin{tabular}{lrrrrrrrrrrr}" + "\n"
        r"\toprule" + "\n"
        r"Policy & N & Acc. & Bal.\ acc. & Macro F1 & Local cov. & Escalation "
        r"& Exec.\ cov. & Unresolved & Resolved risk & Wilson upper & Claim \\" + "\n"
        r"\midrule" + "\n"
    )
    return header + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n"


def _coverage_figure(results: dict[str, Any]) -> tuple[str, str]:
    names = sorted(results["policies"])
    bars = []
    tex_rows = []
    width = max(900, 20 + len(names) * 34)
    for index, name in enumerate(names):
        value = float(results["policies"][name].get("execution_coverage") or 0.0)
        x = 20 + index * 34
        height = max(1, int(value * 160))
        bars.append(f'<rect x="{x}" y="{180-height}" width="24" height="{height}" fill="#3264a8"/>')
        bar = "X" * max(1, round(value * 20))
        tex_rows.append(f"{_tex(name)} & {bar} & {_fmt(value)} \\\\")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="220" viewBox="0 0 {width} 220">'
        '<title>Execution coverage by routing policy</title>'
        f'<line x1="10" y1="180" x2="{width - 10}" y2="180" stroke="black"/>'
        + "".join(bars)
        + "</svg>\n"
    )
    tex = (
        "\\begin{tabular}{llr}\n\\toprule\nPolicy & Execution coverage bar & Value \\\\\n\\midrule\n"
        + "\n".join(tex_rows)
        + "\n\\bottomrule\n\\end{tabular}\n"
    )
    return svg, tex


def _collapsed_text(results: dict[str, Any]) -> str:
    collapsed = []
    underpowered = []
    for name, value in sorted(results["policies"].items()):
        point = value.get("selected_operating_point") or {}
        if point.get("collapsed"):
            collapsed.append(name)
        if point.get("claim_status") == "descriptive":
            underpowered.append(name)
    parts = []
    if collapsed:
        parts.append(
            "Collapsed target operating points (identical selected coverage/threshold): "
            + ", ".join(_tex(name) for name in collapsed)
            + "."
        )
    if underpowered:
        parts.append(
            "Descriptive/underpowered target points, because the Wilson 95\\% upper bound exceeds the "
            "preregistered target: "
            + ", ".join(_tex(name) for name in underpowered)
            + "."
        )
    if not parts:
        parts.append("No collapsed or underpowered target points were recorded in results.json.")
    return " ".join(parts)


def _report_markdown(results: dict[str, Any], experiment: Path) -> str:
    lines = [
        f"# {results['experiment_id']} — Selective escalation",
        "",
        f"Benchmark fingerprint: `{results['benchmark_fingerprint']}`",
        "",
        (
            f"Threshold-selection records: {results['counts']['threshold_selection']}; "
            f"final-evaluation records: {results['counts']['final_evaluation']}; "
            f"provider prefix: {results['counts']['provider_evaluation']}."
        ),
        "",
        (
            "Machine metrics are sourced from `results.json`. Provider failures remain unresolved. "
            "Pinned Jev and rolling Jev are separate arms."
        ),
        "",
        "## Policies",
        "",
    ]
    for name, value in sorted(results["policies"].items()):
        point = value.get("selected_operating_point") or {}
        lines.append(
            f"- `{name}`: accuracy={_fmt(value.get('accuracy'))}, "
            f"balanced_accuracy={_fmt(value.get('balanced_accuracy'))}, "
            f"macro_f1={_fmt(value.get('macro_f1'))}, "
            f"local_coverage={_fmt(value.get('local_coverage'))}, "
            f"escalation_rate={_fmt(value.get('escalation_rate'))}, "
            f"unresolved_rate={_fmt(value.get('unresolved_rate'))}, "
            f"resolved_risk={_fmt(value.get('final_resolved_risk'))}, "
            f"claim={_claim(point) if point else 'n/a'}."
        )
    differential = results.get("system_one_differential", {})
    lines.extend(
        [
            "",
            "## Differential",
            "",
            (
                f"Jev/Qwen comparable records: {differential.get('comparable_count', 0)}; "
                f"agreements: {differential.get('agreement_count', 0)}."
            ),
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def render_paper(
    results: dict[str, Any],
    differential: dict[str, Any],
    experiment: Path,
    smoke_experiment: Path,
    *,
    paper_root: Path | None = None,
) -> None:
    root = paper_root or PAPER
    generated = root / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    final_differential = results.get("system_one_differential", {})
    local = results["policies"].get("local_only", {})
    pinned = results["policies"].get("pinned_jev_only", {})
    qwen = results["policies"].get("qwen_flash_only", {})
    experiment_id = results["experiment_id"]
    fingerprint = results["benchmark_fingerprint"]
    counts = results["counts"]
    svg, figure_tex = _coverage_figure(results)
    _write_text(generated / "table_selective_results.tex", _metric_table(results))
    _write_text(generated / "figure_execution_coverage.svg", svg)
    _write_text(generated / "figure_execution_coverage.tex", figure_tex)
    _write_text(
        root / "reproducibility.md",
        "# Reproducibility appendix\n\n"
        "```powershell\n"
        "$env:PYTHONPATH = \"$PWD\\src\"\n"
        ".venv\\Scripts\\python.exe scripts/build_selective_benchmark.py\n"
        f".venv\\Scripts\\python.exe scripts/run_selective_escalation.py --skip-providers --provider-limit 500 --output {experiment.as_posix()} --pinned-predictions experiments/EXP-20260920-009-selective-escalation/provider-pinned.jsonl --rolling-predictions experiments/EXP-20260920-009-selective-escalation/provider-rolling.jsonl --qwen-predictions experiments/EXP-20260920-009-selective-escalation/qwen-streaming-final-merged-20260920-010/predictions.jsonl --experiment-id {experiment_id}\n"
        f".venv\\Scripts\\python.exe scripts/generate_research_artifacts.py --experiment {experiment.as_posix()} --smoke-experiment {smoke_experiment.as_posix()}\n"
        ".venv\\Scripts\\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0\n"
        "```\n\n"
        "Provider smoke calls are isolated with `scripts/smoke_task0010_providers.py`; pinned and rolling Jev outputs are never pooled.\n\n"
        f"{PCM_NOTE}\n",
    )
    _write_text(
        root / "limitations.md",
        "# Limitations and threats to validity\n\n"
        "The frozen student is a compact TF-IDF plus logistic-regression arm trained on the small TASK-0009 corpus. "
        "ARC answer-key labels measure objective choice correctness and do not establish broad human-evaluation validity. "
        "The calibrated threshold claims have Wilson uncertainty and are descriptive when the upper bound does not meet "
        "the target. Provider smoke and partial live availability can leave unresolved records; unresolved calls are not "
        "scored as local errors and never receive a local fallback. The rolling Jev alias is a separate canary and is "
        "excluded from pinned estimates.\n\n"
        f"{PCM_NOTE}\n",
    )
    _write_text(
        root / "main.tex",
        f"""\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{booktabs}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{verbatim}}
\\title{{Calibrated Selective Escalation for Lightweight Rubric Judges}}
\\author{{Eval Lab}}
\\date{{2026-09-20}}
\\begin{{document}}
\\maketitle
\\section*{{Abstract}}
\\begin{{abstract}}
We evaluate a frozen TASK-0009 TF-IDF plus logistic-regression student with confidence-based selective escalation on EvalLab-Select v0.1.0. Experiment \\texttt{{{_tex(experiment_id)}}} is the completion replay of the planned EXP-20260920-009 baseline using committed provider artifacts. The benchmark contains {counts['threshold_selection']} threshold-selection and {counts['final_evaluation']} final-evaluation records with disjoint source families. Provider-only pinned Jev and Qwen policies are reported over the frozen final pool with unresolved records retained. Provider failures remain explicitly unresolved. The benchmark fingerprint is \\texttt{{{fingerprint}}}.
\\end{{abstract}}
\\section{{Introduction}}
Selective escalation asks whether a calibrated lightweight judge can keep high-confidence cases local and send the remainder to a stronger judge. The scientific questions are local coverage at declared error targets, the value of pinned Jev structured decisions, avoided external calls relative to strong-judge-only operation, and whether a typed System-One specification yields a reproducible Jev/Qwen differential. This report is generated from \\texttt{{{_tex(experiment.name)}/results.json}}.
\\section{{Related Work}}
Selective classification and risk-coverage analysis study when a predictor should abstain. Confidence calibration, including temperature scaling, is a standard post-hoc reliability tool for probabilistic classifiers. Recent routing work sends uncertain queries to larger models. This study keeps objective gold labels, a frozen student, and explicit provider missingness rather than treating model judgments as gold.
\\section{{Benchmark and Objective-Gold Construction}}
EvalLab-Select v0.1.0 combines ARC-Challenge at pinned revision \\texttt{{210d026faf9955653af8916fad021475a3f00453}} with non-training synthetic source families. Each ARC source yields one correct and one deterministic incorrect single-answer record. Gold labels are answer-key or deterministic-verifier provenance. Threshold-selection and final-evaluation partitions are source-family disjoint. Canonicalization, splits, checksums, RO-Crate, PROV-O, and SHACL artifacts are committed with fingerprint \\texttt{{{fingerprint}}}.
\\section{{Local Judge and Calibration}}
The primary student is the frozen TASK-0009 arm D TF-IDF plus logistic-regression artifact. Calibration uses the committed temperature artifact fit on the TASK-0009 calibration split only. The primary confidence signal is the maximum calibrated class probability; the top-two margin is retained as a secondary diagnostic. The student is not retrained after final-pool inspection.
\\section{{Selective Escalation Method}}
Thresholds are selected only on the threshold-selection partition. Final-evaluation labels never influence threshold, confidence definition, provider, typed-question wording, target error, or policy. Local routes always record \\texttt{{provider\\_status=not\\_called}}. Escalated routes record the provider execution status and remain unresolved on failure. Policies are P0 local-only, P1 pinned Jev only, P2 Qwen3.8 Flash only, P3 calibrated local to pinned Jev, P4 raw-confidence local to pinned Jev, P5 matched-random to pinned Jev, and P6 calibrated local to Qwen. Rolling Jev remains a separate canary and is never pooled with pinned Jev.
\\section{{Jev/System-One Differential Method}}
The typed System-One specification is provider-independent and is executed through pinned OpenRouter \\texttt{{typesafe/jev-1.13}} and a YOLO-Auto Qwen3.8 Flash adapter. Objective verifier and answer-key labels remain gold. The frozen final-prefix differential contains {final_differential.get('comparable_count', 0)} comparable record(s) and {final_differential.get('agreement_count', 0)} agreement(s). The separate smoke differential contains {differential.get('comparable_count', 0)} comparable record(s) and {differential.get('agreement_count', 0)} agreement(s).
\\section{{Experiments}}
Experiment \\texttt{{{_tex(experiment_id)}}} replays the frozen student and EvalLab-Select split over a deterministic 500-record provider prefix of the final-evaluation order. Provider artifacts are loaded from committed EXP-009 pinned, rolling, and streaming Qwen files. Offline metrics, including accuracy, balanced accuracy, macro F1, coverage, escalation, unresolved rate, Wilson intervals, latency p95, external calls per 1,000, and provider resource metadata, are computed from those artifacts.
\\section{{Results}}
Machine-generated routing results are in \\texttt{{generated/table\\_selective\\_results.tex}} and Figure~\\ref{{fig:coverage}}, both sourced from \\texttt{{results.json}}. Local-only accuracy is {_fmt(local.get('accuracy'))} with resolved risk {_fmt(local.get('final_resolved_risk'))}. Provider-only pinned Jev execution coverage is {_fmt(pinned.get('execution_coverage'))} with unresolved rate {_fmt(pinned.get('unresolved_rate'))}; Qwen-only execution coverage is {_fmt(qwen.get('execution_coverage'))} with unresolved rate {_fmt(qwen.get('unresolved_rate'))}. {_collapsed_text(results)}
\\begin{{table}}[h]
\\centering
\\resizebox{{\\textwidth}}{{!}}{{\\input{{generated/table_selective_results.tex}}}}
\\caption{{Machine-generated policy metrics from \\texttt{{{_tex(experiment_id)}/results.json}}. Resolved risk excludes unresolved provider calls.}}
\\end{{table}}
\\begin{{table}}[h]
\\centering
\\input{{generated/figure_execution_coverage.tex}}
\\caption{{Execution coverage by policy, generated from the same results artifact.}}
\\label{{fig:coverage}}
\\end{{table}}
\\section{{Statistical Uncertainty}}
Every low-error coverage summary includes an exact Wilson 95\\% interval on the accepted or resolved set. A nominal empirical risk below a target is treated as descriptive when the interval upper bound exceeds that target. Coverage and support flags are reported at 1\\%, 2\\%, 5\\%, and 10\\% without using final labels to choose thresholds.
\\section{{Ablations/Controls}}
Raw-confidence routing, calibrated routing, and a matched-random escalation control use the same final record IDs. Provider-only P1/P2 policies isolate judge quality from routing. Rolling Jev is retained as a canary and is excluded from pinned estimates. Probability metrics are reported when class probabilities exist and otherwise carry explicit unavailability metadata.
\\section{{Limitations and Threats to Validity}}
This is an objective ARC answer-key benchmark, not evidence of universal human-evaluation quality. The student training corpus is small. Calibration and provider availability are separate sources of uncertainty. Provider errors remain unresolved rather than receiving an implicit local fallback. {_collapsed_text(results)} {PCM_NOTE}
\\section{{Reproducibility and Artifact Availability}}
Run the commands in \\texttt{{reproducibility.md}}. The release includes RO-Crate 1.3 metadata, PROV-O provenance, SHACL shapes, a valid CFF citation file, checksums, generated tables and figures, and experiment \\texttt{{{_tex(experiment_id)}}}. {PCM_NOTE}
\\section{{Conclusion}}
The committed replay records local-only, provider-only, selective, matched-random, and Jev/Qwen differential outcomes with explicit unresolved states. Low-error reliability statements remain descriptive wherever Wilson upper bounds miss the preregistered targets.
\\appendix
\\section{{Appendices}}
Exact reproduction commands, PCM compatibility, and the machine-readable metric bundle follow. Headline numbers in the tables are regenerated from \\texttt{{results.json}} and are not copied by hand.
\\verbatiminput{{reproducibility.md}}
\\bibliographystyle{{plain}}
\\bibliography{{references}}
\\end{{document}}
""",
    )


def generate() -> None:
    results = json.loads((EXPERIMENT / "results.json").read_text(encoding="utf-8"))
    differential = _smoke_differential()
    results["provider_smoke"] = differential["arms"]
    if "system_one_differential" in results:
        results["system_one_smoke_differential"] = differential
    else:
        results["system_one_differential"] = differential
    _write_json(EXPERIMENT / "differential.json", differential)
    _write_json(EXPERIMENT / "results.json", results)
    _write_text(EXPERIMENT / "report.md", _report_markdown(results, EXPERIMENT))
    _write_json(BENCHMARK / "ro-crate-metadata.json", _crate(results, differential))
    _write_text(BENCHMARK / "provenance.ttl", _provenance(results))
    _write_text(BENCHMARK / "shapes.ttl", _shapes())
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
    render_paper(results, differential, EXPERIMENT, SMOKE_EXPERIMENT)
    _write_checksums(BENCHMARK)
    _write_checksums(EXPERIMENT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=EXPERIMENT)
    parser.add_argument("--smoke-experiment", type=Path)
    args = parser.parse_args()
    EXPERIMENT = args.experiment
    SMOKE_EXPERIMENT = args.smoke_experiment or EXPERIMENT
    generate()
